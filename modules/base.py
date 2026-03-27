#!/usr/bin/env python3
from __future__ import annotations
"""
Clase base para el sistema de modulos de Soundvi (Qt6).

Todos los modulos (CAVA, Subtitulos, etc.) deben heredar de ``Module``
e implementar los metodos abstractos.

Usa PyQt6 para la interfaz de configuracion.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
import numpy as np

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QCheckBox, QSpinBox, QGroupBox, QSlider,
    QComboBox, QColorDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from utils.fonts import get_default_font


class Module(ABC):
    """
    Clase base abstracta para modulos de Soundvi.

    Cada modulo representa una capa visual que se puede activar/desactivar
    y tiene sus propias configuraciones.
    """

    def __init__(self, nombre: str, descripcion: str = "", capa: int = 0):
        self.nombre = nombre
        self.descripcion = descripcion
        self.capa = capa
        self._habilitado = False
        self._config: dict[str, Any] = {}
        self._config_widget: Optional[QWidget] = None

    @property
    def habilitado(self) -> bool:
        return self._habilitado

    @habilitado.setter
    def habilitado(self, valor: bool):
        old_value = self._habilitado
        self._habilitado = valor
        if self._config_widget is not None and old_value != valor:
            self._config_widget.setVisible(valor)

    @abstractmethod
    def render(self, frame: np.ndarray, tiempo: float, **kwargs) -> np.ndarray:
        ...

    @abstractmethod
    def get_config_widgets(self, parent: QWidget, app) -> QWidget:
        ...

    def create_module_frame(self, parent: QWidget, app, on_refresh=None) -> QWidget:
        """Crea un widget estandarizado para el modulo con PyQt6."""
        main_widget = QFrame(parent)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # Header
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        enabled_cb = QCheckBox(self.nombre)
        enabled_cb.setChecked(self._habilitado)

        def toggle_enabled(state):
            self.habilitado = bool(state)
            if hasattr(app, 'trigger_auto_save'):
                app.trigger_auto_save()
            if on_refresh:
                on_refresh()

        enabled_cb.stateChanged.connect(toggle_enabled)
        header_layout.addWidget(enabled_cb)

        if self.descripcion:
            desc_text = self.descripcion[:20] + "..." if len(self.descripcion) > 20 else self.descripcion
            desc_label = QLabel(desc_text)
            desc_label.setStyleSheet("color: gray; font-size: 10px;")
            header_layout.addWidget(desc_label)

        header_layout.addStretch()

        # Layer control
        layer_label = QLabel("Capa:")
        layer_label.setStyleSheet("font-size: 10px;")
        header_layout.addWidget(layer_label)

        layer_spin = QSpinBox()
        layer_spin.setRange(0, 10)
        layer_spin.setValue(self.capa)
        layer_spin.setFixedWidth(50)
        layer_spin.valueChanged.connect(lambda val: self._update_layer(val, app))
        header_layout.addWidget(layer_spin)

        delete_btn = QPushButton("\u2716")
        delete_btn.setFixedWidth(30)
        delete_btn.setStyleSheet("color: #dc3545;")

        def delete_module():
            if hasattr(app, 'module_manager'):
                app.module_manager.remove_module_instance(self)
            if hasattr(app, 'trigger_auto_save'):
                app.trigger_auto_save()
            if on_refresh:
                on_refresh()

        delete_btn.clicked.connect(delete_module)
        header_layout.addWidget(delete_btn)

        main_layout.addWidget(header_widget)

        # Config widgets
        config_group = QGroupBox(f"Configuracion {self.nombre}")
        config_layout = QVBoxLayout(config_group)
        config_layout.setContentsMargins(4, 4, 4, 4)

        config_content = self.get_config_widgets(config_group, app)
        if config_content:
            config_layout.addWidget(config_content)

        self._config_widget = config_group
        config_group.setVisible(self._habilitado)
        main_layout.addWidget(config_group)

        return main_widget

    def _update_layer(self, layer_value, app):
        try:
            self.capa = int(layer_value)
            if hasattr(app, 'trigger_auto_save'):
                app.trigger_auto_save()
        except ValueError:
            pass

    def create_color_picker(self, parent: QWidget, initial_color: str,
                            app, label: str = "Color:") -> QWidget:
        """Crea un selector de color estandarizado con PyQt6."""
        container = QWidget(parent)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel(label)
        layout.addWidget(lbl)

        color_preview = QFrame()
        color_preview.setFixedSize(24, 24)
        color_preview.setFrameShape(QFrame.Shape.Box)
        if not initial_color or not initial_color.startswith('#'):
            initial_color = "#FFFFFF"
        color_preview.setStyleSheet(f"background-color: {initial_color}; border: 1px solid gray;")
        layout.addWidget(color_preview)

        hex_label = QLabel(initial_color)
        hex_label.setStyleSheet("font-size: 10px;")
        layout.addWidget(hex_label)

        container.color_value = initial_color
        container._color_preview = color_preview
        container._hex_label = hex_label
        container._callbacks = []

        def pick_color():
            qcolor = QColor(container.color_value)
            color = QColorDialog.getColor(qcolor, parent, f"Color - {self.nombre}")
            if color.isValid():
                hex_val = color.name()
                container.color_value = hex_val
                color_preview.setStyleSheet(f"background-color: {hex_val}; border: 1px solid gray;")
                hex_label.setText(hex_val)
                for cb in container._callbacks:
                    cb(hex_val)

        color_btn = QPushButton("Seleccionar")
        color_btn.clicked.connect(pick_color)
        layout.addWidget(color_btn)
        layout.addStretch()

        def on_color_change(callback):
            container._callbacks.append(callback)

        container.on_color_change = on_color_change

        return container

    def enable(self):
        self._habilitado = True

    def disable(self):
        self._habilitado = False

    def get_config(self) -> dict:
        return self._config.copy()

    def set_config(self, config: dict):
        self._config.update(config)

    def _update_config(self, key: str, value: Any, app):
        self._config[key] = value
        if hasattr(app, 'trigger_auto_save'):
            app.trigger_auto_save()
        if hasattr(app, 'update_preview'):
            app.update_preview()

    def __repr__(self):
        estado = "habilitado" if self._habilitado else "deshabilitado"
        return f"<Module '{self.nombre}' capa={self.capa} [{estado}]>"

    def __lt__(self, other):
        return self.capa < other.capa
