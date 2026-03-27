#!/usr/bin/env python3
"""
Módulo de Recorte.
Categorizado: video/filters
"""
import numpy as np
import cv2

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider
from PyQt6.QtCore import Qt

from modules.core.base import Module

class CropModule(Module):
    module_type = "video"
    module_category = "filters"
    module_tags = ["crop", "recorte", "video", "filter"]
    module_version = "1.0.0"

    def __init__(self):
        super().__init__(nombre="Recorte", descripcion="Recortar y reencuadrar video")
        self._config = {"top": 0, "bottom": 0, "left": 0, "right": 0, "zoom": 1.0}

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado: return frame
        try:
            h, w = frame.shape[:2]
            t = int(h * self._config["top"] / 100)
            b = int(h * self._config["bottom"] / 100)
            l = int(w * self._config["left"] / 100)
            r = int(w * self._config["right"] / 100)
            if t + b >= h or l + r >= w: return frame
            cropped = frame[t:h-b, l:w-r]
            zoomed = cv2.resize(cropped, (w, h))
            zoom = self._config["zoom"]
            if zoom != 1.0:
                M = cv2.getRotationMatrix2D((w/2, h/2), 0, zoom)
                zoomed = cv2.warpAffine(zoomed, M, (w, h))
            return zoomed
        except: return frame

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        for label_text, key in [("Arriba %", "top"), ("Abajo %", "bottom"), ("Izq %", "left"), ("Der %", "right")]:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.addWidget(QLabel(f"{label_text}:"))
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 45)
            slider.setValue(self._config[key])
            slider.valueChanged.connect(lambda v, k=key: self._update_config(k, v, app))
            rl.addWidget(slider)
            layout.addWidget(row)

        return content
