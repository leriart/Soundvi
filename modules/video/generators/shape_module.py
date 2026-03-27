#!/usr/bin/env python3
"""
Módulo Generador de Formas.
Categorizado: video/generators
"""
import numpy as np
import cv2

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QComboBox, QCheckBox
from PyQt6.QtCore import Qt

from modules.core.base import Module

class ShapeModule(Module):
    module_type = "video"
    module_category = "generators"
    module_tags = ["shape", "circle", "rectangle", "generator"]
    module_version = "1.0.0"

    def __init__(self):
        super().__init__(nombre="Generador de Formas", descripcion="Formas geométricas animadas")
        self._config = {
            "shape": "circle", "color_r": 255, "color_g": 100, "color_b": 50,
            "size": 50, "pos_x": 50, "pos_y": 50, "opacity": 0.8,
            "animate": True, "rotation_speed": 1.0,
        }

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado: return frame
        try:
            h, w = frame.shape[:2]
            overlay = frame.copy()
            color = (self._config["color_b"], self._config["color_g"], self._config["color_r"])
            cx = int(w * self._config["pos_x"] / 100)
            cy = int(h * self._config["pos_y"] / 100)
            size = self._config["size"]
            if self._config["animate"]:
                size = int(size + np.sin(tiempo * 2) * 10)
            shape = self._config["shape"]
            if shape == "circle":
                cv2.circle(overlay, (cx, cy), size, color, -1)
            elif shape == "rectangle":
                cv2.rectangle(overlay, (cx - size, cy - size), (cx + size, cy + size), color, -1)
            elif shape == "triangle":
                pts = np.array([
                    [cx, cy - size],
                    [cx - size, cy + size],
                    [cx + size, cy + size]
                ], np.int32)
                cv2.fillPoly(overlay, [pts], color)
            return cv2.addWeighted(overlay, self._config["opacity"], frame, 1 - self._config["opacity"], 0)
        except: return frame

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        combo = QComboBox()
        combo.addItems(["circle", "rectangle", "triangle"])
        combo.setCurrentText(self._config["shape"])
        combo.currentTextChanged.connect(lambda v: self._update_config("shape", v, app))
        layout.addWidget(combo)

        for label_text, key, lo, hi in [("Tamaño", "size", 5, 500), ("Pos X %", "pos_x", 0, 100), ("Pos Y %", "pos_y", 0, 100)]:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.addWidget(QLabel(f"{label_text}:"))
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(lo, hi)
            slider.setValue(self._config[key])
            slider.valueChanged.connect(lambda v, k=key: self._update_config(k, v, app))
            rl.addWidget(slider)
            layout.addWidget(row)

        anim_check = QCheckBox("Animar")
        anim_check.setChecked(self._config["animate"])
        anim_check.toggled.connect(lambda v: self._update_config("animate", v, app))
        layout.addWidget(anim_check)

        return content
