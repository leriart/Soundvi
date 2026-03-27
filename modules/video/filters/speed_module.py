#!/usr/bin/env python3
"""
Módulo de Velocidad (Slow-mo / Time-lapse visual).
Categorizado: video/filters
"""
import numpy as np
import cv2

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider
from PyQt6.QtCore import Qt

from modules.core.base import Module

class SpeedModule(Module):
    module_type = "video"
    module_category = "filters"
    module_tags = ["speed", "velocidad", "slowmo", "timelapse"]
    module_version = "1.0.0"

    def __init__(self):
        super().__init__(nombre="Velocidad Visual", descripcion="Efectos de motion blur y trails")
        self._config = {"trail_intensity": 0.0, "motion_blur": 0}
        self._prev_frame = None

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado: return frame
        try:
            trail = self._config["trail_intensity"]
            if trail > 0 and self._prev_frame is not None:
                if self._prev_frame.shape == frame.shape:
                    frame = cv2.addWeighted(frame, 1.0 - trail * 0.5, self._prev_frame, trail * 0.5, 0)
            mb = self._config["motion_blur"]
            if mb > 0:
                kernel = np.zeros((mb * 2 + 1, mb * 2 + 1))
                kernel[mb, :] = np.ones(mb * 2 + 1)
                kernel /= (mb * 2 + 1)
                frame = cv2.filter2D(frame, -1, kernel)
            self._prev_frame = frame.copy()
            return frame
        except: return frame

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(QLabel("Trail:"))
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(int(self._config["trail_intensity"] * 100))
        slider.valueChanged.connect(lambda v: self._update_config("trail_intensity", v / 100.0, app))
        rl.addWidget(slider)
        layout.addWidget(row)

        row2 = QWidget()
        rl2 = QHBoxLayout(row2)
        rl2.setContentsMargins(0, 0, 0, 0)
        rl2.addWidget(QLabel("Motion Blur:"))
        slider2 = QSlider(Qt.Orientation.Horizontal)
        slider2.setRange(0, 20)
        slider2.setValue(self._config["motion_blur"])
        slider2.valueChanged.connect(lambda v: self._update_config("motion_blur", v, app))
        rl2.addWidget(slider2)
        layout.addWidget(row2)

        return content
