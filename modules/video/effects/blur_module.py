#!/usr/bin/env python3
"""
Módulo de Desenfoque.
Categorizado: video/effects
"""
import numpy as np
import cv2

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QComboBox
from PyQt6.QtCore import Qt

from modules.core.base import Module

class BlurModule(Module):
    module_type = "video"
    module_category = "effects"
    module_tags = ["blur", "desenfoque", "gaussian", "video"]
    module_version = "1.0.0"

    def __init__(self):
        super().__init__(nombre="Desenfoque", descripcion="Efecto de desenfoque gaussiano")
        self._config = {"radius": 5, "type": "gaussian", "opacity": 1.0}

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado: return frame
        try:
            r = max(1, self._config["radius"]) | 1
            if self._config["type"] == "gaussian":
                blurred = cv2.GaussianBlur(frame, (r, r), 0)
            elif self._config["type"] == "box":
                blurred = cv2.blur(frame, (r, r))
            elif self._config["type"] == "median":
                blurred = cv2.medianBlur(frame, r)
            else:
                blurred = cv2.GaussianBlur(frame, (r, r), 0)
            op = self._config["opacity"]
            if op < 1.0:
                return cv2.addWeighted(blurred, op, frame, 1 - op, 0)
            return blurred
        except: return frame

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(QLabel("Radio:"))
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(1, 99)
        slider.setValue(self._config["radius"])
        slider.valueChanged.connect(lambda v: self._update_config("radius", v | 1, app))
        rl.addWidget(slider)
        layout.addWidget(row)

        row2 = QWidget()
        rl2 = QHBoxLayout(row2)
        rl2.setContentsMargins(0, 0, 0, 0)
        rl2.addWidget(QLabel("Tipo:"))
        combo = QComboBox()
        combo.addItems(["gaussian", "box", "median"])
        combo.setCurrentText(self._config["type"])
        combo.currentTextChanged.connect(lambda v: self._update_config("type", v, app))
        rl2.addWidget(combo)
        layout.addWidget(row2)

        return content
