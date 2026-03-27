# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- Toolbar personalizable.

Barra de herramientas superior con iconos Unicode tecnicos (sin emojis),
grupos de herramientas separados, tooltips con shortcuts y acciones
principales del editor.
"""

from __future__ import annotations

import os
import sys
import logging
from typing import Optional, Dict, List, Callable

from PyQt6.QtWidgets import (
    QToolBar, QWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QFont, QKeySequence

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _RAIZ) if _RAIZ not in sys.path else None

from gui.qt6.base import ICONOS_UNICODE, UserLevelAdapter
from core.profiles import ProfileManager

log = logging.getLogger("soundvi.qt6.toolbar")


# Definicion de grupos de herramientas con iconos Unicode tecnicos
# Formato: (icono_unicode, texto, tooltip, shortcut, nombre_accion, grupo)
HERRAMIENTAS: List[tuple] = [
    # -- Grupo: File --
    ("\u2750",  "Nuevo",     "Nuevo proyecto (Ctrl+N)",    "Ctrl+N",       "new_project",   "File"),
    ("\u2B06",  "Abrir",     "Abrir proyecto (Ctrl+O)",    "Ctrl+O",       "open_project",  "File"),
    ("\u2B07",  "Guardar",   "Guardar proyecto (Ctrl+S)",  "Ctrl+S",       "save_project",  "File"),
    (None, None, None, None, None, None),  # Separador

    # -- Grupo: Import/Export --
    ("\u2912",  "Importar",  "Importar medios (Ctrl+I)",   "Ctrl+I",       "import_media",  "Import"),
    ("\u➡",  "Exportar",  "Exportar video (Ctrl+E)",    "Ctrl+E",       "export_video",  "Export"),
    (None, None, None, None, None, None),  # Separador

    # -- Grupo: Edit --
    ("\u21B6",  "Deshacer",  "Deshacer (Ctrl+Z)",          "Ctrl+Z",       "undo",          "Edit"),
    ("\u21B7",  "Rehacer",   "Rehacer (Ctrl+Y)",           "Ctrl+Y",       "redo",          "Edit"),
    (None, None, None, None, None, None),  # Separador

    # -- Grupo: Timeline --
    ("\u2702",  "Dividir",   "Dividir clip (Ctrl+X)",      "Ctrl+Shift+X", "split_clip",    "Timeline"),
    ("\u2717",  "Eliminar",  "Eliminar clip (Del)",        "Delete",       "delete_clip",   "Timeline"),
    (None, None, None, None, None, None),  # Separador

    # -- Grupo: Playback --
    ("▶",  "Play",      "Reproducir (Espacio)",       "Space",        "play",          "Playback"),
    ("‖",  "Pausa",     "Pausar (Espacio)",           "",             "pause",         "Playback"),
    ("■",  "Stop",      "Detener (S)",                "S",            "stop",          "Playback"),
    (None, None, None, None, None, None),  # Separador

    # -- Grupo: View --
    ("\u2295",  "Zoom +",    "Acercar (Ctrl++)",           "Ctrl++",       "zoom_in",       "View"),
    ("\u2296",  "Zoom -",    "Alejar (Ctrl+-)",            "Ctrl+-",       "zoom_out",      "View"),
    ("\u26F6",  "Ajustar",   "Ajustar al timeline",        "Ctrl+0",       "zoom_fit",      "View"),
    (None, None, None, None, None, None),  # Separador

    # -- Grupo: Settings --
    ("\u2699",  "Config",    "Configuracion",              "Ctrl+,",       "settings",      "Settings"),
    ("\u2630",  "Perfil",    "Cambiar perfil",             "",             "profile",       "Settings"),
]


class SoundviToolBar(QToolBar):
    """
    Toolbar personalizable de Soundvi con iconos Unicode tecnicos.
    Emite senales por nombre de accion para conectar con la ventana principal.
    """

    # Senal generica: emite el nombre de la accion ejecutada
    accion_ejecutada = pyqtSignal(str)

    def __init__(self, profile_manager: ProfileManager,
                 user_level_adapter: Optional[UserLevelAdapter] = None,
                 parent: Optional[QWidget] = None):
        super().__init__("Herramientas Soundvi", parent)
        self._pm = profile_manager
        self._adapter = user_level_adapter or UserLevelAdapter(profile_manager)
        self._acciones: Dict[str, QAction] = {}

        # Configuracion visual
        self.setMovable(False)
        self.setIconSize(QSize(20, 20))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        # Estilos se heredan del tema QSS global
        pass

        self._construir_toolbar()
        self._aplicar_perfil()
        self._aplicar_tooltips_nivel()

    def _construir_toolbar(self):
        """Construye la toolbar con todos los grupos de herramientas."""
        for item in HERRAMIENTAS:
            icono, texto, tooltip, shortcut, nombre, grupo = item

            if icono is None:
                # Separador
                self.addSeparator()
                continue

            accion = QAction(f"{icono} {texto}", self)
            accion.setToolTip(tooltip)
            if shortcut:
                accion.setShortcut(QKeySequence(shortcut))
            accion.triggered.connect(lambda checked, n=nombre: self.accion_ejecutada.emit(n))
            self.addAction(accion)
            self._acciones[nombre] = accion

    def _aplicar_perfil(self):
        """Muestra/oculta acciones segun perfil activo."""
        pm = self._pm

        # Acciones avanzadas solo para perfiles Creador/Profesional
        acciones_avanzadas = {"split_clip", "zoom_in", "zoom_out", "zoom_fit"}
        habilitar_avanzado = pm.funcion_habilitada("corte")

        for nombre in acciones_avanzadas:
            if nombre in self._acciones:
                self._acciones[nombre].setVisible(habilitar_avanzado)

    def _aplicar_tooltips_nivel(self):
        """Actualiza tooltips de todas las acciones segun el nivel del usuario."""
        for nombre, accion in self._acciones.items():
            tooltip = self._adapter.obtener_tooltip(nombre)
            accion.setToolTip(tooltip)

    # -- API publica -----------------------------------------------------------

    def conectar_accion(self, nombre: str, callback: Callable):
        """Conecta un callback especifico a una accion por nombre."""
        if nombre in self._acciones:
            # Desconectar la senal generica para esta accion y conectar directa
            self._acciones[nombre].triggered.connect(lambda: callback())

    def habilitar_accion(self, nombre: str, habilitado: bool):
        """Habilita o deshabilita una accion."""
        if nombre in self._acciones:
            self._acciones[nombre].setEnabled(habilitado)

    def refrescar_perfil(self):
        """Refresca la visibilidad y tooltips segun perfil actual."""
        self._aplicar_perfil()
        self._adapter.actualizar_nivel(self._pm)
        self._aplicar_tooltips_nivel()

    def set_adapter(self, adapter: UserLevelAdapter):
        """Actualiza el adaptador de nivel de usuario."""
        self._adapter = adapter
        self._aplicar_tooltips_nivel()

    def get_accion(self, nombre: str) -> Optional[QAction]:
        """Retorna una accion por nombre."""
        return self._acciones.get(nombre)
