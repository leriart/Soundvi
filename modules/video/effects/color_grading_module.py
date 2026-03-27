#!/usr/bin/env python3
"""
Módulo de Color Grading.
Categorizado: video/effects
"""
import numpy as np
import cv2

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider
from PyQt6.QtCore import Qt

from modules.core.base import Module

class ColorGradingModule(Module):
    module_type = "video"
    module_category = "effects"
    module_tags = ["color", "grading", "brightness", "contrast", "saturation"]
    module_version = "1.0.0"

    def __init__(self):
        super().__init__(nombre="Color Grading", descripcion="Ajuste de color, brillo, contraste y saturación")
        self._config = {
            "brightness": 0, "contrast": 1.0, "saturation": 1.0,
            "temperature": 0, "tint": 0, "gamma": 1.0,
        }

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado: return frame
        try:
            result = frame.astype(np.float32)
            result = result * self._config["contrast"] + self._config["brightness"]
            gamma = self._config["gamma"]
            if gamma != 1.0:
                result = np.power(np.clip(result / 255.0, 0, 1), 1.0 / gamma) * 255.0
            sat = self._config["saturation"]
            if sat != 1.0:
                hsv = cv2.cvtColor(np.clip(result, 0, 255).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
                hsv[:, :, 1] *= sat
                result = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
            temp = self._config["temperature"]
            if temp != 0:
                result[:, :, 0] += temp * -1
                result[:, :, 2] += temp
            return np.clip(result, 0, 255).astype(np.uint8)
        except: return frame

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        # (label, key, lo, hi, multiplier for int slider, decimals)
        params = [
            ("Brillo", "brightness", -100, 100, 1),
            ("Contraste", "contrast", 10, 300, 100),  # 0.1-3.0 * 100
            ("Saturación", "saturation", 0, 300, 100),  # 0.0-3.0 * 100
            ("Temperatura", "temperature", -50, 50, 1),
            ("Gamma", "gamma", 10, 300, 100),  # 0.1-3.0 * 100
        ]
        for label_text, key, lo, hi, mult in params:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.addWidget(QLabel(f"{label_text}:"))
            val_label = QLabel(f"{self._config[key]:.1f}" if mult > 1 else str(self._config[key]))
            val_label.setFixedWidth(40)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(lo, hi)
            slider.setValue(int(self._config[key] * mult))

            def make_cb(k, m, lbl):
                def cb(v):
                    real_val = v / m if m > 1 else v
                    self._update_config(k, real_val, app)
                    lbl.setText(f"{real_val:.1f}" if m > 1 else str(real_val))
                return cb

            slider.valueChanged.connect(make_cb(key, mult, val_label))
            rl.addWidget(slider)
            rl.addWidget(val_label)
            layout.addWidget(row)

        return content
