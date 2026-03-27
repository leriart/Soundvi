# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- Clases base, adaptadores e interfaces abstractas.

Proporciona la capa de abstraccion entre el backend existente (core/, modules/)
y la nueva interfaz Qt6.  Permite que ambos frontends (ttkbootstrap y Qt6)
compartan el mismo motor sin duplicar logica.

Incluye UserLevelAdapter para adaptacion de interfaz segun nivel de usuario.
"""

from __future__ import annotations

import json
import os
import sys
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy, QCheckBox, QSpinBox,
    QSlider, QComboBox, QGroupBox, QMessageBox, QToolTip
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QColor, QFont

log = logging.getLogger("soundvi.qt6.base")

# ---------------------------------------------------------------------------
#  Constantes globales
# ---------------------------------------------------------------------------
_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ICONOS_UNICODE: Dict[str, str] = {
    "play":       "\u25B6",
    "pause":      "\u23F8",
    "stop":       "\u23F9",
    "forward":    "\u23E9",
    "backward":   "\u23EA",
    "record":     "\u23FA",
    "cut":        "\u2702",
    "copy":       "\u2398",
    "paste":      "\u2399",
    "undo":       "\u21B6",
    "redo":       "\u21B7",
    "save":       "\u2B07",
    "open":       "\u2B06",
    "settings":   "\u2699",
    "module":     "\u29C9",
    "audio":      "\u266B",
    "video":      "\u25A3",
    "text":       "\u2141",
    "effect":     "\u2728",
    "filter":     "\u29D6",
    "export":     "\u27A1",
    "trash":      "\u2717",
    "check":      "\u2713",
    "warning":    "\u26A0",
    "info":       "\u2139",
    "profile":    "\u2630",
    "layers":     "\u25A6",
    "zoom_in":    "\u2295",
    "zoom_out":   "\u2296",
    "fullscreen": "\u26F6",
}


# ---------------------------------------------------------------------------
#  Adaptador de modulos -- puente entre Module (tkinter) y Qt6
# ---------------------------------------------------------------------------
class ModuloAdaptadorQt6(QObject):
    """
    Envuelve una instancia de modules.core.base.Module para exponerla
    como un QObject con senales Qt6.  El modulo original sigue funcionando
    con su logica de render/config intacta; este adaptador solo maneja
    la parte visual Qt6.
    """

    config_cambiada = pyqtSignal(str, object)  # clave, valor
    habilitado_cambiado = pyqtSignal(bool)

    def __init__(self, modulo_original: Any, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._mod = modulo_original

    # -- Propiedades delegadas -------------------------------------------------
    @property
    def nombre(self) -> str:
        return type(self._mod).__name__

    @property
    def tipo(self) -> str:
        return getattr(self._mod, "module_type", "desconocido")

    @property
    def categoria(self) -> str:
        return getattr(self._mod, "module_category", "general")

    @property
    def tags(self) -> List[str]:
        return getattr(self._mod, "module_tags", [])

    @property
    def habilitado(self) -> bool:
        return getattr(self._mod, "habilitado", True)

    @habilitado.setter
    def habilitado(self, valor: bool):
        self._mod.habilitado = valor
        self.habilitado_cambiado.emit(valor)

    @property
    def modulo_original(self) -> Any:
        return self._mod

    # -- Delegacion de render --------------------------------------------------
    def render(self, frame, tiempo, **kwargs):
        """Delega al render original del modulo."""
        if self.habilitado:
            return self._mod.render(frame, tiempo, **kwargs)
        return frame

    # -- Configuracion ---------------------------------------------------------
    def get_config(self) -> Dict[str, Any]:
        if hasattr(self._mod, "get_config"):
            return self._mod.get_config()
        return {}

    def set_config(self, clave: str, valor: Any):
        if hasattr(self._mod, "set_config"):
            self._mod.set_config(clave, valor)
        self.config_cambiada.emit(clave, valor)


# ---------------------------------------------------------------------------
#  Widget base para paneles Qt6
# ---------------------------------------------------------------------------
class PanelBase(QFrame):
    """
    Clase base para todos los paneles/dock widgets de Soundvi Qt6.
    Proporciona estilo consistente, titulo y contenedor con scroll.
    """

    def __init__(self, titulo: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._layout_principal = QVBoxLayout(self)
        self._layout_principal.setContentsMargins(4, 4, 4, 4)
        self._layout_principal.setSpacing(4)

        if titulo:
            lbl = QLabel(titulo)
            lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self._layout_principal.addWidget(lbl)

        # Area scrolleable para contenido
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._contenido = QWidget()
        self._layout_contenido = QVBoxLayout(self._contenido)
        self._layout_contenido.setContentsMargins(0, 0, 0, 0)
        self._layout_contenido.setSpacing(2)
        self._scroll.setWidget(self._contenido)
        self._layout_principal.addWidget(self._scroll)

    def agregar_widget(self, widget: QWidget):
        """Agrega un widget al area de contenido scrolleable."""
        self._layout_contenido.addWidget(widget)

    def limpiar(self):
        """Elimina todos los widgets del contenido."""
        while self._layout_contenido.count():
            item = self._layout_contenido.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()


# ---------------------------------------------------------------------------
#  Interfaz abstracta para widgets de configuracion de modulo
# ---------------------------------------------------------------------------
class ConfigWidgetBase(QGroupBox):
    """
    Widget base para configurar un modulo en Qt6.
    Cada modulo que quiera exponer configuracion Qt6 debe heredar de esta
    clase e implementar _construir_controles().
    """

    valor_cambiado = pyqtSignal(str, object)

    def __init__(self, adaptador: ModuloAdaptadorQt6, parent: Optional[QWidget] = None):
        super().__init__(adaptador.nombre, parent)
        self._adaptador = adaptador
        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(4)
        self._construir_controles()

    def _construir_controles(self):
        """Implementar en subclases para crear los controles especificos del modulo."""
        pass

    def _emitir_cambio(self, clave: str, valor: Any):
        self._adaptador.set_config(clave, valor)
        self.valor_cambiado.emit(clave, valor)


# ---------------------------------------------------------------------------
#  Fabrica de widgets comunes
# ---------------------------------------------------------------------------
class FabricaWidgets:
    """Metodos estaticos para crear widgets Qt6 reutilizables."""

    @staticmethod
    def crear_slider(label: str, minimo: int = 0, maximo: int = 100,
                     valor: int = 50, callback: Optional[Callable] = None,
                     parent: Optional[QWidget] = None) -> QWidget:
        """Crea un slider horizontal con etiqueta y valor numerico."""
        contenedor = QWidget(parent)
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel(label)
        lbl.setMinimumWidth(80)
        layout.addWidget(lbl)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimo, maximo)
        slider.setValue(valor)
        layout.addWidget(slider)

        valor_lbl = QLabel(str(valor))
        valor_lbl.setMinimumWidth(35)
        valor_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(valor_lbl)

        def _on_change(v):
            valor_lbl.setText(str(v))
            if callback:
                callback(v)

        slider.valueChanged.connect(_on_change)
        contenedor._slider = slider  # referencia para acceso externo
        return contenedor

    @staticmethod
    def crear_combo(label: str, opciones: List[str],
                    seleccion: int = 0, callback: Optional[Callable] = None,
                    parent: Optional[QWidget] = None) -> QWidget:
        """Crea un combobox con etiqueta."""
        contenedor = QWidget(parent)
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel(label)
        lbl.setMinimumWidth(80)
        layout.addWidget(lbl)

        combo = QComboBox()
        combo.addItems(opciones)
        combo.setCurrentIndex(seleccion)
        layout.addWidget(combo)

        if callback:
            combo.currentIndexChanged.connect(lambda i: callback(opciones[i] if i < len(opciones) else ""))

        contenedor._combo = combo
        return contenedor

    @staticmethod
    def crear_boton(texto: str, icono_unicode: str = "",
                    callback: Optional[Callable] = None,
                    parent: Optional[QWidget] = None) -> QPushButton:
        """Crea un boton con texto e icono Unicode opcional."""
        label = f"{icono_unicode}  {texto}" if icono_unicode else texto
        btn = QPushButton(label, parent)
        if callback:
            btn.clicked.connect(callback)
        return btn

    @staticmethod
    def crear_check(texto: str, valor: bool = False,
                    callback: Optional[Callable] = None,
                    parent: Optional[QWidget] = None) -> QCheckBox:
        """Crea un checkbox."""
        chk = QCheckBox(texto, parent)
        chk.setChecked(valor)
        if callback:
            chk.stateChanged.connect(lambda s: callback(s == Qt.CheckState.Checked.value))
        return chk


# ---------------------------------------------------------------------------
#  Niveles de usuario
# ---------------------------------------------------------------------------
NIVEL_NOVATO = "basico"
NIVEL_INTERMEDIO = "creador"
NIVEL_PROFESIONAL = "profesional"

# Mapeo clave de perfil -> nivel conceptual
_PERFIL_A_NIVEL: Dict[str, str] = {
    "basico": NIVEL_NOVATO,
    "creador": NIVEL_INTERMEDIO,
    "profesional": NIVEL_PROFESIONAL,
    "personalizado": NIVEL_INTERMEDIO,  # personalizado se trata como intermedio
}


# ---------------------------------------------------------------------------
#  Tooltips extendidos por nivel
# ---------------------------------------------------------------------------
TOOLTIPS_EXTENDIDOS: Dict[str, Dict[str, str]] = {
    # nombre_accion: { nivel: texto }
    "new_project": {
        NIVEL_NOVATO: "Nuevo proyecto\n\nCrea un proyecto vacío donde podrás\nimportar tus videos y audios.\nAtajo: Ctrl+N",
        NIVEL_INTERMEDIO: "Nuevo proyecto (Ctrl+N)",
        NIVEL_PROFESIONAL: "Nuevo · Ctrl+N",
    },
    "open_project": {
        NIVEL_NOVATO: "Abrir proyecto\n\nAbre un proyecto guardado previamente\n(.svproj o .json).\nAtajo: Ctrl+O",
        NIVEL_INTERMEDIO: "Abrir proyecto (Ctrl+O)",
        NIVEL_PROFESIONAL: "Abrir · Ctrl+O",
    },
    "save_project": {
        NIVEL_NOVATO: "Guardar proyecto\n\nGuarda tu trabajo actual para poder\ncontinuar después.\nAtajo: Ctrl+S",
        NIVEL_INTERMEDIO: "Guardar proyecto (Ctrl+S)",
        NIVEL_PROFESIONAL: "Guardar · Ctrl+S",
    },
    "import_media": {
        NIVEL_NOVATO: "Importar medios\n\nAgrega archivos de video, audio\no imágenes a tu biblioteca.\nAtajo: Ctrl+I",
        NIVEL_INTERMEDIO: "Importar medios (Ctrl+I)",
        NIVEL_PROFESIONAL: "Importar · Ctrl+I",
    },
    "export_video": {
        NIVEL_NOVATO: "Exportar video\n\nConvierte tu proyecto en un archivo\nde video listo para compartir.\nAtajo: Ctrl+E",
        NIVEL_INTERMEDIO: "Exportar video (Ctrl+E)",
        NIVEL_PROFESIONAL: "Exportar · Ctrl+E",
    },
    "undo": {
        NIVEL_NOVATO: "Deshacer\n\nRevierte el último cambio que hiciste.\nMuy útil si te equivocas.\nAtajo: Ctrl+Z",
        NIVEL_INTERMEDIO: "Deshacer (Ctrl+Z)",
        NIVEL_PROFESIONAL: "Undo · Ctrl+Z",
    },
    "redo": {
        NIVEL_NOVATO: "Rehacer\n\nVuelve a aplicar el cambio que deshiciste.\nAtajo: Ctrl+Y",
        NIVEL_INTERMEDIO: "Rehacer (Ctrl+Y)",
        NIVEL_PROFESIONAL: "Redo · Ctrl+Y",
    },
    "split_clip": {
        NIVEL_NOVATO: "Dividir clip\n\nCorta el clip en dos partes en la\nposición actual del cabezal.\nAtajo: Ctrl+Shift+X",
        NIVEL_INTERMEDIO: "Dividir clip (Ctrl+Shift+X)",
        NIVEL_PROFESIONAL: "Split · Ctrl+Shift+X",
    },
    "delete_clip": {
        NIVEL_NOVATO: "Eliminar clip\n\nBorra el clip seleccionado del timeline.\n¡Puedes deshacerlo con Ctrl+Z!\nAtajo: Delete",
        NIVEL_INTERMEDIO: "Eliminar clip (Del)",
        NIVEL_PROFESIONAL: "Delete · Del",
    },
    "play": {
        NIVEL_NOVATO: "Reproducir\n\nInicia la reproducción de tu proyecto\ndesde la posición actual.\nAtajo: Espacio",
        NIVEL_INTERMEDIO: "Reproducir (Espacio)",
        NIVEL_PROFESIONAL: "Play · Space",
    },
    "pause": {
        NIVEL_NOVATO: "Pausar\n\nDetiene la reproducción temporalmente.\nPresiona Play para continuar.\nAtajo: Espacio",
        NIVEL_INTERMEDIO: "Pausar (Espacio)",
        NIVEL_PROFESIONAL: "Pause · Space",
    },
    "stop": {
        NIVEL_NOVATO: "Detener\n\nDetiene la reproducción y regresa\nal inicio del proyecto.\nAtajo: S",
        NIVEL_INTERMEDIO: "Detener (S)",
        NIVEL_PROFESIONAL: "Stop · S",
    },
    "zoom_in": {
        NIVEL_NOVATO: "Acercar\n\nAmplía la vista del timeline para ver\nmás detalle de tus clips.\nAtajo: Ctrl++",
        NIVEL_INTERMEDIO: "Acercar (Ctrl++)",
        NIVEL_PROFESIONAL: "Zoom+ · Ctrl++",
    },
    "zoom_out": {
        NIVEL_NOVATO: "Alejar\n\nReduce la vista del timeline para\nver más contenido.\nAtajo: Ctrl+-",
        NIVEL_INTERMEDIO: "Alejar (Ctrl+-)",
        NIVEL_PROFESIONAL: "Zoom- · Ctrl+-",
    },
    "zoom_fit": {
        NIVEL_NOVATO: "Ajustar vista\n\nAjusta automáticamente el zoom para\nver todo el timeline completo.\nAtajo: Ctrl+0",
        NIVEL_INTERMEDIO: "Ajustar al timeline (Ctrl+0)",
        NIVEL_PROFESIONAL: "Fit · Ctrl+0",
    },
    "settings": {
        NIVEL_NOVATO: "Configuración\n\nAbre las preferencias de la aplicación\npara personalizar tu experiencia.\nAtajo: Ctrl+,",
        NIVEL_INTERMEDIO: "Configuración (Ctrl+,)",
        NIVEL_PROFESIONAL: "Config · Ctrl+,",
    },
    "profile": {
        NIVEL_NOVATO: "Cambiar perfil\n\nCambia tu nivel de experiencia.\nElige entre Novato, Intermedio\no Profesional.",
        NIVEL_INTERMEDIO: "Cambiar perfil de usuario",
        NIVEL_PROFESIONAL: "Perfil",
    },
}


# ---------------------------------------------------------------------------
#  Mensajes de ayuda contextual por panel
# ---------------------------------------------------------------------------
AYUDA_CONTEXTUAL: Dict[str, str] = {
    "timeline": "\u2261 Timeline: Arrastra clips aqu\u00ed para organizar tu video. "
                "Usa el cabezal (l\u00ednea vertical) para navegar.",
    "inspector": "\u2315 Inspector: Selecciona un clip en el timeline para ver "
                 "y editar sus propiedades aqu\u00ed.",
    "media_library": "\u2302 Biblioteca: Importa archivos con Ctrl+I o arrastra "
                     "archivos desde tu explorador.",
    "modules_sidebar": "\u29C9 M\u00f3dulos: Haz doble clic en un m\u00f3dulo para aplicarlo "
                       "al clip seleccionado.",
    "audio_mixer": "\u266B Mixer: Ajusta el volumen y balance de cada pista de audio.",
    "keyframes": "\u25C7 Keyframes: Anima propiedades a lo largo del tiempo con "
                 "puntos clave.",
    "transitions": "\u2728 Transiciones: Arrastra una transici\u00f3n entre dos clips "
                   "para aplicarla.",
    "preview": "\u25B6 Preview: Aqu\u00ed se muestra el resultado de tu edici\u00f3n en "
               "tiempo real.",
}


# ---------------------------------------------------------------------------
#  UserLevelAdapter -- adaptador de UI segun nivel de usuario
# ---------------------------------------------------------------------------
class UserLevelAdapter(QObject):
    """
    Adaptador central que lee el nivel del usuario desde el ProfileManager
    (o user_preferences.json) y proporciona métodos para adaptar la interfaz.

    Niveles soportados:
      - basico (Novato): tooltips extendidos, ayuda contextual, wizard, confirmaciones
      - creador (Intermedio): tooltips estándar, atajos básicos, balance funcional
      - profesional: tooltips mínimos, todo visible, scripting panel, sin confirmaciones

    Uso:
        adapter = UserLevelAdapter(profile_manager)
        adapter.obtener_tooltip("play")
        adapter.confirmar_accion_destructiva(parent, "Eliminar clip")
    """

    # Señal emitida cuando el nivel cambia dinámicamente
    nivel_cambiado = pyqtSignal(str)  # emite la clave del nivel

    def __init__(self, profile_manager=None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._pm = profile_manager
        self._nivel: str = NIVEL_INTERMEDIO  # default

        if self._pm and self._pm.perfil_activo:
            self._nivel = _PERFIL_A_NIVEL.get(
                self._pm.perfil_activo.clave, NIVEL_INTERMEDIO
            )
        else:
            # Fallback: leer desde user_preferences.json
            self._nivel = self._leer_nivel_desde_prefs()

        log.info("UserLevelAdapter inicializado: nivel=%s", self._nivel)

    # -- Lectura de nivel ------------------------------------------------------
    def _leer_nivel_desde_prefs(self) -> str:
        """Lee el nivel del usuario desde el sistema de configuracion persistente."""
        try:
            from utils.config import load_user_prefs
            datos = load_user_prefs()
            perfil = datos.get("perfil", "creador")
            return _PERFIL_A_NIVEL.get(perfil, NIVEL_INTERMEDIO)
        except Exception:
            return NIVEL_INTERMEDIO

    # -- Propiedades -----------------------------------------------------------
    @property
    def nivel(self) -> str:
        """Retorna el nivel actual: 'basico', 'creador' o 'profesional'."""
        return self._nivel

    @property
    def es_novato(self) -> bool:
        return self._nivel == NIVEL_NOVATO

    @property
    def es_intermedio(self) -> bool:
        return self._nivel == NIVEL_INTERMEDIO

    @property
    def es_profesional(self) -> bool:
        return self._nivel == NIVEL_PROFESIONAL

    # -- Cambio dinámico de nivel ----------------------------------------------
    def actualizar_nivel(self, profile_manager=None):
        """Recalcula el nivel desde el ProfileManager actual."""
        pm = profile_manager or self._pm
        if pm and pm.perfil_activo:
            nuevo_nivel = _PERFIL_A_NIVEL.get(
                pm.perfil_activo.clave, NIVEL_INTERMEDIO
            )
        else:
            nuevo_nivel = self._leer_nivel_desde_prefs()

        if nuevo_nivel != self._nivel:
            self._nivel = nuevo_nivel
            self.nivel_cambiado.emit(self._nivel)
            log.info("Nivel de usuario cambiado a: %s", self._nivel)

    # -- Tooltips --------------------------------------------------------------
    def obtener_tooltip(self, nombre_accion: str) -> str:
        """Retorna el tooltip adaptado al nivel para una acción."""
        info = TOOLTIPS_EXTENDIDOS.get(nombre_accion)
        if info:
            return info.get(self._nivel, info.get(NIVEL_INTERMEDIO, nombre_accion))
        return nombre_accion

    # -- Ayuda contextual (solo para novatos) ----------------------------------
    def obtener_ayuda_panel(self, nombre_panel: str) -> Optional[str]:
        """Retorna mensaje de ayuda contextual para un panel (solo novatos)."""
        if self._nivel == NIVEL_NOVATO:
            return AYUDA_CONTEXTUAL.get(nombre_panel)
        return None

    def crear_label_ayuda(self, nombre_panel: str,
                          parent: Optional[QWidget] = None) -> Optional[QLabel]:
        """Crea un QLabel con ayuda contextual si el usuario es novato."""
        texto = self.obtener_ayuda_panel(nombre_panel)
        if texto is None:
            return None
        lbl = QLabel(texto, parent)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("""
            QLabel {
                background-color: #1a3a2a;
                color: #00BC8C;
                border: 1px solid #00BC8C;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 11px;
            }
        """)
        lbl.setObjectName("ayuda_contextual")
        return lbl

    # -- Confirmaciones --------------------------------------------------------
    def confirmar_accion_destructiva(self, parent: QWidget,
                                     titulo: str,
                                     mensaje: str = "") -> bool:
        """
        Pide confirmación antes de una acción destructiva.
        - Novato: siempre confirma con detalle extra.
        - Intermedio: confirma con mensaje breve.
        - Profesional: nunca confirma (retorna True directamente).
        """
        if self._nivel == NIVEL_PROFESIONAL:
            return True

        if self._nivel == NIVEL_NOVATO:
            msg_text = mensaje or f"¿Estás seguro de que quieres {titulo.lower()}?"
            msg_text += "\n\n\u2022 Tip: Puedes deshacer esta acci\u00f3n con Ctrl+Z."
            result = QMessageBox.warning(
                parent, f"\u26A0 {titulo}",
                msg_text,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
        else:
            result = QMessageBox.question(
                parent, titulo,
                mensaje or f"¿{titulo}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

        return result == QMessageBox.StandardButton.Yes

    # -- Visibilidad de opciones -----------------------------------------------
    def opciones_avanzadas_visibles(self) -> bool:
        """Retorna True si se deben mostrar opciones avanzadas en el inspector."""
        return self._nivel in (NIVEL_INTERMEDIO, NIVEL_PROFESIONAL)

    def opciones_profesionales_visibles(self) -> bool:
        """Retorna True si se deben mostrar opciones solo para profesionales."""
        return self._nivel == NIVEL_PROFESIONAL

    def mostrar_wizard_bienvenida(self) -> bool:
        """Retorna True si se debe mostrar el wizard de bienvenida."""
        return self._nivel == NIVEL_NOVATO

    def mostrar_panel_scripting(self) -> bool:
        """Retorna True si se debe mostrar el panel de scripting Python."""
        return self._nivel == NIVEL_PROFESIONAL

    def mostrar_primeros_pasos(self) -> bool:
        """Retorna True si se debe mostrar el panel de Primeros Pasos."""
        return self._nivel == NIVEL_NOVATO

    # -- Atajos de teclado -----------------------------------------------------
    def atajos_completos_habilitados(self) -> bool:
        """Retorna True si se habilitan atajos complejos (profesional)."""
        return self._nivel == NIVEL_PROFESIONAL

    def obtener_atajos_extra(self) -> Dict[str, str]:
        """Retorna atajos extra para profesionales."""
        if self._nivel != NIVEL_PROFESIONAL:
            return {}
        return {
            "Ctrl+Shift+E": "Exportación rápida",
            "Ctrl+Shift+D": "Duplicar clip",
            "Ctrl+Shift+M": "Silenciar clip",
            "Ctrl+Alt+S": "Guardar snapshot",
            "Ctrl+Shift+P": "Abrir consola Python",
            "Alt+1": "Ir a track 1",
            "Alt+2": "Ir a track 2",
            "Alt+3": "Ir a track 3",
            "J": "Retroceder playhead",
            "K": "Pausar/Reproducir",
            "L": "Avanzar playhead",
            "I": "Marcar punto de entrada",
            "O": "Marcar punto de salida",
        }
