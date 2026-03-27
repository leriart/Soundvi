# -*- coding: utf-8 -*-
"""
Soundvi -- ProfileManager: carga dinamica de modulos segun perfil de usuario.

El sistema de perfiles permite que Soundvi se adapte al nivel del usuario:
  - Basico:        solo corte, trim, preview (para el que nomas quiere partir un video)
  - Creador:       + transiciones, efectos, audio, subtitulos
  - Profesional:   todo desbloqueado, sin piedad
  - Personalizado: el usuario arma su propia mezcla

El ProfileManager se encarga de:
  1. Cargar profiles.json
  2. Filtrar modulos del CategorizedModuleManager segun el perfil activo
  3. Informar a la GUI que paneles/menus mostrar u ocultar
  4. Persistir la seleccion del usuario
"""

from __future__ import annotations

import json
import os
import logging
from typing import Any, Dict, List, Optional, Set

log = logging.getLogger("soundvi.profiles")

# Ruta base del proyecto
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROFILES_JSON = os.path.join(_RAIZ, "profiles.json")
_USER_PROFILE_FILE = os.path.join(_RAIZ, "user_profile.json")


class Perfil:
    """Representacion en memoria de un perfil."""

    def __init__(self, clave: str, datos: Dict[str, Any]):
        self.clave = clave
        self.nombre: str = datos.get("nombre", clave)
        self.descripcion: str = datos.get("descripcion", "")
        self.icono: str = datos.get("icono", "\u2630")

        # Modulos permitidos
        mp = datos.get("modulos_permitidos", {})
        self.tipos_permitidos: List[str] = mp.get("tipos", [])
        self.categorias_permitidas: List[str] = mp.get("categorias", [])
        self.clases_especificas: List[str] = mp.get("clases_especificas", [])

        # Paneles
        self.paneles_visibles: List[str] = datos.get("paneles_visibles", [])
        self.paneles_ocultos: List[str] = datos.get("paneles_ocultos", [])

        # Funciones habilitadas
        self.funciones: Dict[str, bool] = datos.get("funciones", {})

        # Menus ocultos
        self.menu_items_ocultos: List[str] = datos.get("menu_items_ocultos", [])

        # Limites
        self.max_pistas_audio: int = datos.get("max_pistas_audio", -1)
        self.max_capas_video: int = datos.get("max_capas_video", -1)

        # Configuracion de UI por nivel
        ui = datos.get("ui_config", {})
        self.ui_config: Dict[str, Any] = {
            "font_size_base": ui.get("font_size_base", 11),
            "toolbar_icon_size": ui.get("toolbar_icon_size", 28),
            "toolbar_text_visible": ui.get("toolbar_text_visible", True),
            "mostrar_ayuda_contextual": ui.get("mostrar_ayuda_contextual", False),
            "animaciones_ui": ui.get("animaciones_ui", True),
            "confirmar_acciones_destructivas": ui.get("confirmar_acciones_destructivas", True),
            "mostrar_wizard_inicio": ui.get("mostrar_wizard_inicio", False),
            "mostrar_panel_primeros_pasos": ui.get("mostrar_panel_primeros_pasos", False),
            "tooltips_detallados": ui.get("tooltips_detallados", False),
            "barra_estado_detallada": ui.get("barra_estado_detallada", False),
            "simplificar_menus": ui.get("simplificar_menus", False),
        }

    def permite_todo(self) -> bool:
        """Retorna True si el perfil no tiene restricciones de modulos."""
        return "*" in self.clases_especificas or "*" in self.categorias_permitidas

    def modulo_permitido(self, clase_nombre: str, tipo: str, categoria: str) -> bool:
        """Verifica si un modulo especifico esta permitido en este perfil."""
        if self.permite_todo():
            return True
        # Verificar por clase especifica
        if clase_nombre in self.clases_especificas:
            return True
        # Verificar por tipo + categoria
        if tipo in self.tipos_permitidos and categoria in self.categorias_permitidas:
            return True
        return False

    def funcion_habilitada(self, nombre_funcion: str) -> bool:
        """Verifica si una funcion especifica esta habilitada."""
        return self.funciones.get(nombre_funcion, False)

    def panel_visible(self, nombre_panel: str) -> bool:
        """Verifica si un panel debe ser visible."""
        if "*" in self.paneles_visibles:
            return True
        if nombre_panel in self.paneles_ocultos:
            return False
        return nombre_panel in self.paneles_visibles

    def to_dict(self) -> Dict[str, Any]:
        """Serializa el perfil a diccionario."""
        return {
            "clave": self.clave,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "icono": self.icono,
            "funciones": self.funciones,
        }


class ProfileManager:
    """
    Gestor principal de perfiles.

    Uso tipico:
        pm = ProfileManager()
        pm.cargar()
        pm.seleccionar_perfil("creador")
        modulos_filtrados = pm.filtrar_modulos(lista_todos_los_modulos)
    """

    def __init__(self, ruta_json: Optional[str] = None):
        self._ruta = ruta_json or _PROFILES_JSON
        self._perfiles: Dict[str, Perfil] = {}
        self._perfil_activo: Optional[Perfil] = None
        self._perfil_defecto: str = "creador"
        self._modulos_personalizados: Set[str] = set()  # para perfil personalizado
        self._cargado = False

    # -- Carga / persistencia --------------------------------------------------
    def cargar(self) -> bool:
        """Carga los perfiles desde profiles.json."""
        if not os.path.isfile(self._ruta):
            log.error("Archivo de perfiles no encontrado: %s", self._ruta)
            self._crear_perfil_emergencia()
            return False

        try:
            with open(self._ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log.error("Error leyendo profiles.json: %s", e)
            self._crear_perfil_emergencia()
            return False

        self._perfil_defecto = datos.get("perfil_defecto", "creador")

        for clave, info in datos.get("perfiles", {}).items():
            self._perfiles[clave] = Perfil(clave, info)

        # Cargar perfil del usuario si existe
        self._cargar_perfil_usuario()
        self._cargado = True
        log.info("Perfiles cargados: %s", list(self._perfiles.keys()))
        return True

    def _crear_perfil_emergencia(self):
        """Crea un perfil profesional de emergencia si no se puede cargar el JSON."""
        self._perfiles["profesional"] = Perfil("profesional", {
            "nombre": "Profesional (emergencia)",
            "descripcion": "Perfil de emergencia -- todo habilitado",
            "icono": "\u26A0",
            "modulos_permitidos": {"tipos": ["*"], "categorias": ["*"], "clases_especificas": ["*"]},
            "paneles_visibles": ["*"],
            "paneles_ocultos": [],
            "funciones": {k: True for k in [
                "corte", "trim", "transiciones", "efectos_video",
                "audio_reactivo", "keyframes", "color_grading",
                "subtitulos_ia", "gpu", "exportacion_avanzada"
            ]},
            "menu_items_ocultos": [],
            "max_pistas_audio": -1,
            "max_capas_video": -1,
        })
        self._perfil_defecto = "profesional"

    def _cargar_perfil_usuario(self):
        """Carga la seleccion previa del usuario."""
        if not os.path.isfile(_USER_PROFILE_FILE):
            return
        try:
            with open(_USER_PROFILE_FILE, "r", encoding="utf-8") as f:
                datos = json.load(f)
            clave = datos.get("perfil_activo", "")
            if clave in self._perfiles:
                self._perfil_activo = self._perfiles[clave]
                log.info("Perfil de usuario restaurado: %s", clave)
                
                # Si es perfil personalizado, restaurar su estado personalizado
                if clave == "personalizado":
                    perfil = self._perfil_activo
                    paneles_pers = datos.get("personalizado_paneles")
                    if paneles_pers:
                        perfil.paneles_visibles = paneles_pers
                    funciones_pers = datos.get("personalizado_funciones")
                    if funciones_pers:
                        # Actualizar solo las funciones que existen en el perfil base
                        for k, v in funciones_pers.items():
                            if k in perfil.funciones:
                                perfil.funciones[k] = v
                    
            # Restaurar modulos personalizados
            self._modulos_personalizados = set(datos.get("modulos_personalizados", []))
        except Exception as e:
            log.warning("No se pudo cargar perfil de usuario: %s", e)

    def guardar_seleccion(self):
        """Persiste la seleccion del usuario."""
        datos = {
            "perfil_activo": self._perfil_activo.clave if self._perfil_activo else self._perfil_defecto,
            "modulos_personalizados": list(self._modulos_personalizados),
        }
        # Si el perfil activo es personalizado, guardar su estado actual
        if self._perfil_activo and self._perfil_activo.clave == "personalizado":
            datos["personalizado_paneles"] = self._perfil_activo.paneles_visibles
            datos["personalizado_funciones"] = self._perfil_activo.funciones
        try:
            with open(_USER_PROFILE_FILE, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=2, ensure_ascii=False)
        except OSError as e:
            log.error("No se pudo guardar seleccion de perfil: %s", e)

    # -- Seleccion de perfil ---------------------------------------------------
    def seleccionar_perfil(self, clave: str) -> bool:
        """Selecciona un perfil activo por su clave."""
        if clave not in self._perfiles:
            log.warning("Perfil desconocido: %s", clave)
            return False
        self._perfil_activo = self._perfiles[clave]
        self.guardar_seleccion()
        log.info("Perfil activo: %s (%s)", clave, self._perfil_activo.nombre)
        return True

    @property
    def perfil_activo(self) -> Optional[Perfil]:
        if self._perfil_activo is None and self._perfiles:
            defecto = self._perfil_defecto
            if defecto in self._perfiles:
                self._perfil_activo = self._perfiles[defecto]
            else:
                self._perfil_activo = next(iter(self._perfiles.values()))
        return self._perfil_activo

    @property
    def perfiles_disponibles(self) -> Dict[str, Perfil]:
        return dict(self._perfiles)

    @property
    def esta_cargado(self) -> bool:
        return self._cargado

    # -- Filtrado de modulos ---------------------------------------------------
    def filtrar_modulos(self, modulos: list) -> list:
        """
        Filtra una lista de clases/instancias de modulo segun el perfil activo.

        Acepta tanto clases como instancias.  Usa module_type, module_category
        y el nombre de la clase para decidir.
        """
        perfil = self.perfil_activo
        if perfil is None or perfil.permite_todo():
            return list(modulos)

        resultado = []
        for mod in modulos:
            clase = mod if isinstance(mod, type) else type(mod)
            nombre = clase.__name__
            tipo = getattr(mod, "module_type", getattr(clase, "module_type", ""))
            cat = getattr(mod, "module_category", getattr(clase, "module_category", ""))

            # Perfil personalizado: verificar lista del usuario
            if perfil.clave == "personalizado":
                if nombre in self._modulos_personalizados or not self._modulos_personalizados:
                    resultado.append(mod)
                continue

            if perfil.modulo_permitido(nombre, tipo, cat):
                resultado.append(mod)

        return resultado

    def filtrar_tipos_modulo(self, tipos: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filtra el diccionario de tipos de modulo (MODULE_TYPES del registry)
        segun el perfil activo.
        """
        perfil = self.perfil_activo
        if perfil is None or perfil.permite_todo():
            return dict(tipos)

        resultado = {}
        for clave, info in tipos.items():
            if clave in perfil.tipos_permitidos:
                resultado[clave] = info
        return resultado

    # -- Perfil personalizado --------------------------------------------------
    def toggle_modulo_personalizado(self, nombre_clase: str):
        """Agrega o quita un modulo de la seleccion personalizada."""
        if nombre_clase in self._modulos_personalizados:
            self._modulos_personalizados.discard(nombre_clase)
        else:
            self._modulos_personalizados.add(nombre_clase)
        self.guardar_seleccion()

    def modulos_personalizados(self) -> Set[str]:
        return set(self._modulos_personalizados)

    # -- Consultas rapidas -----------------------------------------------------
    def funcion_habilitada(self, nombre: str) -> bool:
        """Shortcut para verificar si una funcion esta habilitada en el perfil activo."""
        perfil = self.perfil_activo
        return perfil.funcion_habilitada(nombre) if perfil else True

    def panel_visible(self, nombre: str) -> bool:
        """Shortcut para verificar visibilidad de panel."""
        perfil = self.perfil_activo
        return perfil.panel_visible(nombre) if perfil else True

    def menu_item_visible(self, nombre: str) -> bool:
        """Verifica si un item de menu debe mostrarse."""
        perfil = self.perfil_activo
        if perfil is None:
            return True
        return nombre not in perfil.menu_items_ocultos
