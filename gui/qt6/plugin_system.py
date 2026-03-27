# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- Sistema de plugins para coexistencia gradual.

Permite que modulos escritos para ttkbootstrap sigan funcionando mientras
se migra progresivamente a Qt6.  Los plugins Qt6 nativos obtienen acceso
directo a la API Qt6; los modulos legacy se envuelven con adaptadores.
"""

from __future__ import annotations

import os
import sys
import importlib
import importlib.util
import inspect
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Type

from PyQt6.QtCore import QObject, pyqtSignal

# ---------------------------------------------------------------------------
#  Logging
# ---------------------------------------------------------------------------
log = logging.getLogger("soundvi.plugins")

# ---------------------------------------------------------------------------
#  Metadatos de plugin
# ---------------------------------------------------------------------------
class MetadatosPlugin:
    """Metadatos descriptivos de un plugin."""

    def __init__(self, nombre: str, version: str = "1.0.0",
                 autor: str = "Comunidad Soundvi",
                 descripcion: str = "",
                 tipo_gui: str = "qt6",
                 categoria: str = "general",
                 dependencias: Optional[List[str]] = None,
                 perfil_minimo: str = "basico"):
        self.nombre = nombre
        self.version = version
        self.autor = autor
        self.descripcion = descripcion
        self.tipo_gui = tipo_gui            # "qt6" | "tkinter" | "headless"
        self.categoria = categoria
        self.dependencias = dependencias or []
        self.perfil_minimo = perfil_minimo   # perfil minimo requerido


# ---------------------------------------------------------------------------
#  Interfaz base de plugin Qt6
# ---------------------------------------------------------------------------
class PluginQt6Base:
    """
    Clase base para plugins nativos Qt6.
    Los plugins de la comunidad deben heredar de esta clase.
    """

    metadata: MetadatosPlugin = MetadatosPlugin("PluginBase")

    def activar(self, contexto: Dict[str, Any]) -> bool:
        """
        Llamado cuando el plugin se activa.
        El contexto contiene referencias al ProfileManager, ventana principal, etc.
        Retorna True si la activacion fue exitosa.
        """
        return True

    def desactivar(self) -> bool:
        """Llamado cuando el plugin se desactiva."""
        return True

    def obtener_widget(self) -> Any:
        """Retorna el widget principal del plugin (QWidget) o None."""
        return None

    def obtener_acciones_menu(self) -> List[Dict[str, Any]]:
        """
        Retorna lista de acciones para agregar al menu.
        Cada dict: {"menu": "Modules", "texto": "Mi Plugin", "callback": callable}
        """
        return []


# ---------------------------------------------------------------------------
#  Registro de plugins
# ---------------------------------------------------------------------------
class RegistroPlugins(QObject):
    """
    Registro central de plugins.  Descubre, carga y gestiona el ciclo de
    vida de todos los plugins (Qt6 nativos y legacy envueltos).
    """

    plugin_cargado = pyqtSignal(str)     # nombre del plugin
    plugin_activado = pyqtSignal(str)
    plugin_desactivado = pyqtSignal(str)
    plugin_error = pyqtSignal(str, str)  # nombre, mensaje error

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._plugins: Dict[str, PluginQt6Base] = {}
        self._plugins_activos: Dict[str, PluginQt6Base] = {}
        self._directorios_plugins: List[str] = []
        self._contexto: Dict[str, Any] = {}

    # -- Configuracion ---------------------------------------------------------
    def set_contexto(self, contexto: Dict[str, Any]):
        """Establece el contexto compartido con todos los plugins."""
        self._contexto = contexto

    def agregar_directorio(self, directorio: str):
        """Agrega un directorio donde buscar plugins."""
        if directorio not in self._directorios_plugins:
            self._directorios_plugins.append(directorio)

    # -- Descubrimiento --------------------------------------------------------
    def descubrir_plugins(self):
        """Escanea los directorios de plugins y registra los que encuentre."""
        for directorio in self._directorios_plugins:
            if not os.path.isdir(directorio):
                continue
            for nombre_archivo in os.listdir(directorio):
                if nombre_archivo.endswith("_plugin.py") or nombre_archivo.endswith("_module.py"):
                    ruta = os.path.join(directorio, nombre_archivo)
                    self._cargar_plugin_desde_archivo(ruta)

    def _cargar_plugin_desde_archivo(self, ruta: str):
        """Carga un archivo Python y busca clases que hereden de PluginQt6Base."""
        nombre_modulo = os.path.splitext(os.path.basename(ruta))[0]
        try:
            spec = importlib.util.spec_from_file_location(
                f"soundvi_plugins.{nombre_modulo}", ruta
            )
            if spec is None or spec.loader is None:
                return
            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)

            for _nombre, obj in inspect.getmembers(modulo, inspect.isclass):
                if issubclass(obj, PluginQt6Base) and obj is not PluginQt6Base:
                    instancia = obj()
                    nombre_plugin = instancia.metadata.nombre
                    self._plugins[nombre_plugin] = instancia
                    self.plugin_cargado.emit(nombre_plugin)
                    log.info("Plugin descubierto: %s v%s",
                             nombre_plugin, instancia.metadata.version)
        except Exception as e:
            log.error("Error cargando plugin %s: %s", ruta, e)
            self.plugin_error.emit(nombre_modulo, str(e))

    # -- Activacion / desactivacion -------------------------------------------
    def activar_plugin(self, nombre: str) -> bool:
        """Activa un plugin registrado."""
        plugin = self._plugins.get(nombre)
        if plugin is None:
            log.warning("Plugin no encontrado: %s", nombre)
            return False
        if nombre in self._plugins_activos:
            return True  # ya activo

        # Verificar dependencias
        for dep in plugin.metadata.dependencias:
            if dep not in self._plugins_activos:
                log.warning("Plugin %s requiere %s (no activo)", nombre, dep)
                self.plugin_error.emit(nombre, f"Dependencia faltante: {dep}")
                return False

        try:
            if plugin.activar(self._contexto):
                self._plugins_activos[nombre] = plugin
                self.plugin_activado.emit(nombre)
                log.info("Plugin activado: %s", nombre)
                return True
            else:
                self.plugin_error.emit(nombre, "activar() retorno False")
                return False
        except Exception as e:
            log.error("Error activando plugin %s: %s", nombre, e)
            self.plugin_error.emit(nombre, str(e))
            return False

    def desactivar_plugin(self, nombre: str) -> bool:
        """Desactiva un plugin activo."""
        plugin = self._plugins_activos.get(nombre)
        if plugin is None:
            return False
        try:
            plugin.desactivar()
            del self._plugins_activos[nombre]
            self.plugin_desactivado.emit(nombre)
            log.info("Plugin desactivado: %s", nombre)
            return True
        except Exception as e:
            log.error("Error desactivando plugin %s: %s", nombre, e)
            return False

    def activar_todos(self):
        """Activa todos los plugins registrados."""
        for nombre in list(self._plugins.keys()):
            self.activar_plugin(nombre)

    def desactivar_todos(self):
        """Desactiva todos los plugins activos."""
        for nombre in list(self._plugins_activos.keys()):
            self.desactivar_plugin(nombre)

    # -- Consultas -------------------------------------------------------------
    def listar_plugins(self) -> List[Dict[str, Any]]:
        """Retorna informacion de todos los plugins registrados."""
        resultado = []
        for nombre, plugin in self._plugins.items():
            m = plugin.metadata
            resultado.append({
                "nombre": m.nombre,
                "version": m.version,
                "autor": m.autor,
                "descripcion": m.descripcion,
                "tipo_gui": m.tipo_gui,
                "categoria": m.categoria,
                "activo": nombre in self._plugins_activos,
                "perfil_minimo": m.perfil_minimo,
            })
        return resultado

    def obtener_plugin(self, nombre: str) -> Optional[PluginQt6Base]:
        return self._plugins.get(nombre)

    def obtener_activos(self) -> Dict[str, PluginQt6Base]:
        return dict(self._plugins_activos)

    def obtener_acciones_menu(self) -> List[Dict[str, Any]]:
        """Recopila todas las acciones de menu de plugins activos."""
        acciones = []
        for plugin in self._plugins_activos.values():
            acciones.extend(plugin.obtener_acciones_menu())
        return acciones


# ---------------------------------------------------------------------------
#  Adaptador: Module legacy -> PluginQt6Base
# ---------------------------------------------------------------------------
class AdaptadorModuloLegacy(PluginQt6Base):
    """
    Envuelve un modulo ttkbootstrap existente (modules.core.base.Module)
    como un PluginQt6Base para que pueda participar en el sistema de
    plugins Qt6 sin modificar su codigo original.
    """

    def __init__(self, clase_modulo: type):
        super().__init__()
        self._clase = clase_modulo
        self._instancia = None
        nombre = getattr(clase_modulo, "__name__", "LegacyModule")
        tipo = getattr(clase_modulo, "module_type", "utility")
        cat = getattr(clase_modulo, "module_category", "general")
        self.metadata = MetadatosPlugin(
            nombre=nombre,
            version=getattr(clase_modulo, "module_version", "1.0.0"),
            autor=getattr(clase_modulo, "module_author", "Soundvi"),
            descripcion=f"Modulo legacy: {nombre}",
            tipo_gui="tkinter",
            categoria=f"{tipo}/{cat}",
        )

    def activar(self, contexto: Dict[str, Any]) -> bool:
        try:
            self._instancia = self._clase()
            return True
        except Exception as e:
            log.error("Error instanciando modulo legacy %s: %s",
                      self._clase.__name__, e)
            return False

    def desactivar(self) -> bool:
        self._instancia = None
        return True

    @property
    def instancia_modulo(self):
        return self._instancia
