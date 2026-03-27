# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- Dialogo de Configuracion.

QDialog con pestanas (QTabWidget) para configuracion general,
rendimiento, timeline y atajos de teclado.
Opciones avanzadas solo visibles en perfil Profesional.
"""

from __future__ import annotations

import os
import sys
import json
import logging
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QFormLayout, QComboBox, QSpinBox,
    QDoubleSpinBox, QCheckBox, QLineEdit, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QKeySequence

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _RAIZ) if _RAIZ not in sys.path else None

from gui.qt6.base import ICONOS_UNICODE
from core.profiles import ProfileManager
from utils.config import (
    load_settings, save_settings, load_config, save_config,
    get_settings_path, DEFAULT_CONFIG
)

log = logging.getLogger("soundvi.qt6.settings_dialog")

# Configuracion por defecto para el dialogo de settings
_DEFAULTS: Dict[str, Any] = {
    # General
    "idioma": "Espanol",
    "tema": "Oscuro",
    "autosave_habilitado": True,
    "autosave_intervalo": 300,
    "carpeta_proyectos": os.path.join(os.path.expanduser("~"), "Soundvi"),

    # Performance
    "gpu_aceleracion": False,
    "cache_size_mb": 512,
    "preview_quality": "Media",
    "threads": 0,  # 0 = auto

    # Timeline
    "snap_habilitado": True,
    "snap_sensibilidad": 10,
    "track_height_default": 60,
    "mostrar_waveforms": True,
    "mostrar_thumbnails": True,

    # Shortcuts
    "shortcuts": DEFAULT_CONFIG.get("shortcuts", {
        "Nuevo proyecto":   "Ctrl+N",
        "Abrir proyecto":   "Ctrl+O",
        "Guardar proyecto":  "Ctrl+S",
        "Importar medios":   "Ctrl+I",
        "Exportar video":    "Ctrl+E",
        "Deshacer":          "Ctrl+Z",
        "Rehacer":           "Ctrl+Y",
        "Dividir clip":      "Ctrl+Shift+X",
        "Eliminar clip":     "Delete",
        "Play/Pause":        "Space",
        "Stop":              "S",
        "Zoom acercar":      "Ctrl++",
        "Zoom alejar":       "Ctrl+-",
    }),
}


class SettingsDialog(QDialog):
    """
    Dialogo de configuracion con pestanas para General, Performance,
    Timeline y Shortcuts.
    """

    # Senal emitida al aplicar cambios
    settings_changed = pyqtSignal(dict)

    def __init__(self, profile_manager: ProfileManager,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._pm = profile_manager
        self._settings = dict(_DEFAULTS)

        self.setWindowTitle("\u2699  Configuracion de Soundvi")
        self.setMinimumSize(560, 500)
        self.setModal(True)

        self._cargar_settings()
        self._construir_ui()
        self._aplicar_perfil()

    # -- Construccion de UI ----------------------------------------------------

    def _construir_ui(self):
        """Construye la interfaz del dialogo."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Tabs
        self._tabs = QTabWidget()
        self._tabs.addTab(self._crear_tab_general(), "\u2302  General")
        self._tabs.addTab(self._crear_tab_performance(), "\u26A1  Rendimiento")
        self._tabs.addTab(self._crear_tab_timeline(), "\u2261  Timeline")
        self._tabs.addTab(self._crear_tab_shortcuts(), "\u2328  Atajos")
        layout.addWidget(self._tabs)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_reset = QPushButton("Restablecer")
        btn_reset.setToolTip("Restaurar valores por defecto")
        btn_reset.clicked.connect(self._on_reset)
        btn_layout.addWidget(btn_reset)

        btn_aplicar = QPushButton("Aplicar")
        btn_aplicar.clicked.connect(self._on_aplicar)
        btn_layout.addWidget(btn_aplicar)

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancelar)

        btn_ok = QPushButton("Aceptar")
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #00BC8C;
                color: #FFFFFF;
                font-weight: bold;
                padding: 6px 20px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #00A67A; }
        """)
        btn_ok.clicked.connect(self._on_aceptar)
        btn_layout.addWidget(btn_ok)

        layout.addLayout(btn_layout)

    # -- Tab: General ----------------------------------------------------------

    def _crear_tab_general(self) -> QWidget:
        """Crea la pestana de configuracion general."""
        widget = QWidget()
        form = QFormLayout(widget)
        form.setSpacing(8)

        # Idioma
        self._combo_idioma = QComboBox()
        self._combo_idioma.addItems(["Espanol", "English", "Portugues"])
        self._combo_idioma.setCurrentText(self._settings.get("idioma", "Espanol"))
        form.addRow("Idioma:", self._combo_idioma)

        # Tema
        self._combo_tema = QComboBox()
        self._combo_tema.addItems(["Oscuro", "Claro", "Midnight", "Forest"])
        self._combo_tema.setCurrentText(self._settings.get("tema", "Oscuro"))
        form.addRow("Tema:", self._combo_tema)

        # Autosave
        self._chk_autosave = QCheckBox("Habilitado")
        self._chk_autosave.setChecked(self._settings.get("autosave_habilitado", True))
        form.addRow("Auto-guardado:", self._chk_autosave)

        self._spin_autosave = QSpinBox()
        self._spin_autosave.setRange(30, 3600)
        self._spin_autosave.setValue(self._settings.get("autosave_intervalo", 300))
        self._spin_autosave.setSuffix(" seg")
        form.addRow("Intervalo:", self._spin_autosave)

        # Carpeta de proyectos
        lay_carpeta = QHBoxLayout()
        self._txt_carpeta = QLineEdit(self._settings.get("carpeta_proyectos", ""))
        lay_carpeta.addWidget(self._txt_carpeta, 4)
        btn_carpeta = QPushButton("\u2026")
        btn_carpeta.setFixedWidth(30)
        btn_carpeta.clicked.connect(self._seleccionar_carpeta)
        lay_carpeta.addWidget(btn_carpeta)
        form.addRow("Carpeta proyectos:", lay_carpeta)

        return widget

    # -- Tab: Performance ------------------------------------------------------

    def _crear_tab_performance(self) -> QWidget:
        """Crea la pestana de rendimiento."""
        widget = QWidget()
        form = QFormLayout(widget)
        form.setSpacing(8)

        # GPU
        self._chk_gpu = QCheckBox("Usar aceleracion GPU")
        self._chk_gpu.setChecked(self._settings.get("gpu_aceleracion", False))
        form.addRow("GPU:", self._chk_gpu)

        # Cache
        self._spin_cache = QSpinBox()
        self._spin_cache.setRange(128, 8192)
        self._spin_cache.setValue(self._settings.get("cache_size_mb", 512))
        self._spin_cache.setSuffix(" MB")
        form.addRow("Cache:", self._spin_cache)

        # Preview quality
        self._combo_preview = QComboBox()
        self._combo_preview.addItems(["Alta", "Media", "Baja"])
        self._combo_preview.setCurrentText(self._settings.get("preview_quality", "Media"))
        form.addRow("Calidad preview:", self._combo_preview)

        # Threads
        self._spin_threads = QSpinBox()
        self._spin_threads.setRange(0, 32)
        self._spin_threads.setValue(self._settings.get("threads", 0))
        self._spin_threads.setSpecialValueText("Auto")
        form.addRow("Hilos de trabajo:", self._spin_threads)

        return widget

    # -- Tab: Timeline ---------------------------------------------------------

    def _crear_tab_timeline(self) -> QWidget:
        """Crea la pestana de configuracion de timeline."""
        widget = QWidget()
        form = QFormLayout(widget)
        form.setSpacing(8)

        # Snap
        self._chk_snap = QCheckBox("Habilitado")
        self._chk_snap.setChecked(self._settings.get("snap_habilitado", True))
        form.addRow("Snap:", self._chk_snap)

        self._spin_snap = QSpinBox()
        self._spin_snap.setRange(1, 50)
        self._spin_snap.setValue(self._settings.get("snap_sensibilidad", 10))
        self._spin_snap.setSuffix(" px")
        form.addRow("Sensibilidad snap:", self._spin_snap)

        # Track height
        self._spin_track_height = QSpinBox()
        self._spin_track_height.setRange(30, 200)
        self._spin_track_height.setValue(self._settings.get("track_height_default", 60))
        self._spin_track_height.setSuffix(" px")
        form.addRow("Altura de track:", self._spin_track_height)

        # Waveforms
        self._chk_waveforms = QCheckBox("Mostrar formas de onda")
        self._chk_waveforms.setChecked(self._settings.get("mostrar_waveforms", True))
        form.addRow("Waveforms:", self._chk_waveforms)

        # Thumbnails
        self._chk_thumbnails = QCheckBox("Mostrar miniaturas")
        self._chk_thumbnails.setChecked(self._settings.get("mostrar_thumbnails", True))
        form.addRow("Thumbnails:", self._chk_thumbnails)

        return widget

    # -- Tab: Shortcuts --------------------------------------------------------

    def _crear_tab_shortcuts(self) -> QWidget:
        """Crea la pestana de configuracion de atajos de teclado."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        lbl = QLabel("Doble click en un atajo para modificarlo.")
        lbl.setStyleSheet("color: #ADB5BD; font-size: 11px; padding: 4px;")
        layout.addWidget(lbl)

        self._tabla_shortcuts = QTableWidget()
        self._tabla_shortcuts.setColumnCount(2)
        self._tabla_shortcuts.setHorizontalHeaderLabels(["Accion", "Atajo"])
        self._tabla_shortcuts.horizontalHeader().setStretchLastSection(True)
        self._tabla_shortcuts.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._tabla_shortcuts.setAlternatingRowColors(True)
        self._tabla_shortcuts.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)

        shortcuts = self._settings.get("shortcuts", {})
        self._tabla_shortcuts.setRowCount(len(shortcuts))

        for i, (accion, atajo) in enumerate(shortcuts.items()):
            item_accion = QTableWidgetItem(accion)
            item_accion.setFlags(item_accion.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._tabla_shortcuts.setItem(i, 0, item_accion)

            item_atajo = QTableWidgetItem(atajo)
            self._tabla_shortcuts.setItem(i, 1, item_atajo)

        layout.addWidget(self._tabla_shortcuts)

        # Boton reset shortcuts
        btn_reset_sc = QPushButton("Restablecer atajos por defecto")
        btn_reset_sc.clicked.connect(self._reset_shortcuts)
        layout.addWidget(btn_reset_sc)

        return widget

    # -- Callbacks -------------------------------------------------------------

    def _seleccionar_carpeta(self):
        """Abre dialogo para seleccionar carpeta de proyectos."""
        from PyQt6.QtWidgets import QFileDialog as _QFD
        ruta = _QFD.getExistingDirectory(self, "Seleccionar carpeta de proyectos")
        if ruta:
            self._txt_carpeta.setText(ruta)

    def _reset_shortcuts(self):
        """Restablece los atajos a valores por defecto."""
        shortcuts = _DEFAULTS.get("shortcuts", {})
        self._tabla_shortcuts.setRowCount(len(shortcuts))
        for i, (accion, atajo) in enumerate(shortcuts.items()):
            self._tabla_shortcuts.item(i, 0).setText(accion)
            self._tabla_shortcuts.item(i, 1).setText(atajo)

    def _on_reset(self):
        """Restablece toda la configuracion a valores por defecto."""
        resp = QMessageBox.question(
            self, "Restablecer",
            "Quieres restaurar toda la configuracion a valores por defecto?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            self._settings = dict(_DEFAULTS)
            self._actualizar_ui_desde_settings()

    def _on_aplicar(self):
        """Aplica los cambios sin cerrar el dialogo."""
        self._recoger_valores()
        self._guardar_settings()
        self.settings_changed.emit(self._settings)

    def _on_aceptar(self):
        """Aplica los cambios y cierra el dialogo."""
        self._on_aplicar()
        self.accept()

    # -- Recoger valores de la UI ----------------------------------------------

    def _recoger_valores(self):
        """Lee los valores actuales de la UI y los guarda en _settings."""
        self._settings["idioma"] = self._combo_idioma.currentText()
        self._settings["tema"] = self._combo_tema.currentText()
        self._settings["autosave_habilitado"] = self._chk_autosave.isChecked()
        self._settings["autosave_intervalo"] = self._spin_autosave.value()
        self._settings["carpeta_proyectos"] = self._txt_carpeta.text()

        self._settings["gpu_aceleracion"] = self._chk_gpu.isChecked()
        self._settings["cache_size_mb"] = self._spin_cache.value()
        self._settings["preview_quality"] = self._combo_preview.currentText()
        self._settings["threads"] = self._spin_threads.value()

        self._settings["snap_habilitado"] = self._chk_snap.isChecked()
        self._settings["snap_sensibilidad"] = self._spin_snap.value()
        self._settings["track_height_default"] = self._spin_track_height.value()
        self._settings["mostrar_waveforms"] = self._chk_waveforms.isChecked()
        self._settings["mostrar_thumbnails"] = self._chk_thumbnails.isChecked()

        # Shortcuts
        shortcuts = {}
        for i in range(self._tabla_shortcuts.rowCount()):
            accion = self._tabla_shortcuts.item(i, 0).text()
            atajo = self._tabla_shortcuts.item(i, 1).text()
            shortcuts[accion] = atajo
        self._settings["shortcuts"] = shortcuts

    def _actualizar_ui_desde_settings(self):
        """Actualiza la UI desde los valores de _settings."""
        self._combo_idioma.setCurrentText(self._settings.get("idioma", "Espanol"))
        self._combo_tema.setCurrentText(self._settings.get("tema", "Oscuro"))
        self._chk_autosave.setChecked(self._settings.get("autosave_habilitado", True))
        self._spin_autosave.setValue(self._settings.get("autosave_intervalo", 300))
        self._txt_carpeta.setText(self._settings.get("carpeta_proyectos", ""))

        self._chk_gpu.setChecked(self._settings.get("gpu_aceleracion", False))
        self._spin_cache.setValue(self._settings.get("cache_size_mb", 512))
        self._combo_preview.setCurrentText(self._settings.get("preview_quality", "Media"))
        self._spin_threads.setValue(self._settings.get("threads", 0))

        self._chk_snap.setChecked(self._settings.get("snap_habilitado", True))
        self._spin_snap.setValue(self._settings.get("snap_sensibilidad", 10))
        self._spin_track_height.setValue(self._settings.get("track_height_default", 60))
        self._chk_waveforms.setChecked(self._settings.get("mostrar_waveforms", True))
        self._chk_thumbnails.setChecked(self._settings.get("mostrar_thumbnails", True))

    # -- Persistencia ----------------------------------------------------------

    def _guardar_settings(self):
        """Guarda la configuracion en disco usando el sistema centralizado."""
        if save_settings(self._settings):
            log.info("Configuracion guardada correctamente")
        else:
            log.error("Error guardando configuracion")

    def _cargar_settings(self):
        """Carga la configuracion desde disco usando el sistema centralizado."""
        datos = load_settings()
        if datos:
            self._settings.update(datos)
            log.info("Configuracion cargada correctamente")

    # -- Perfil ----------------------------------------------------------------

    def _aplicar_perfil(self):
        """Opciones avanzadas solo visibles en perfil Profesional."""
        avanzado = self._pm.funcion_habilitada("gpu")

        # Tab de rendimiento: ocultar GPU en perfiles basicos
        if not avanzado:
            self._chk_gpu.setVisible(False)
            self._spin_threads.setVisible(False)

    # -- API publica -----------------------------------------------------------

    def get_settings(self) -> dict:
        """Retorna la configuracion actual."""
        return dict(self._settings)
