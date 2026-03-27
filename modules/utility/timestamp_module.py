#!/usr/bin/env python3
"""
Módulo de Timestamp.
Categorizado: utility
"""
import numpy as np
import cv2

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QComboBox
from PyQt6.QtCore import Qt

from modules.core.base import Module

class TimestampModule(Module):
    module_type = "utility"
    module_category = "timestamp"
    module_tags = ["timestamp", "time", "counter", "utility"]
    module_version = "1.0.0"

    def __init__(self):
        super().__init__(nombre="Timestamp", descripcion="Muestra el tiempo del video")
        self._config = {
            "format": "mm:ss", "pos_x": 10, "pos_y": 95,
            "font_size": 24, "color_r": 255, "color_g": 255, "color_b": 255,
            "bg_enabled": True, "bg_opacity": 0.5,
        }

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado: return frame
        try:
            h, w = frame.shape[:2]
            fmt = self._config["format"]
            m, s = int(tiempo // 60), int(tiempo % 60)
            ms = int((tiempo % 1) * 1000)
            if fmt == "mm:ss": text = f"{m:02d}:{s:02d}"
            elif fmt == "mm:ss.ms": text = f"{m:02d}:{s:02d}.{ms:03d}"
            elif fmt == "seconds": text = f"{tiempo:.1f}s"
            else: text = f"{m:02d}:{s:02d}"
            px = int(w * self._config["pos_x"] / 100)
            py = int(h * self._config["pos_y"] / 100)
            fs = self._config["font_size"] / 30.0
            color = (self._config["color_b"], self._config["color_g"], self._config["color_r"])
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, fs, 1)
            if self._config["bg_enabled"]:
                overlay = frame.copy()
                cv2.rectangle(overlay, (px - 5, py - th - 5), (px + tw + 5, py + 5), (0, 0, 0), -1)
                frame = cv2.addWeighted(overlay, self._config["bg_opacity"], frame, 1 - self._config["bg_opacity"], 0)
            cv2.putText(frame, text, (px, py), cv2.FONT_HERSHEY_SIMPLEX, fs, color, 1, cv2.LINE_AA)
            return frame
        except: return frame

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        combo = QComboBox()
        combo.addItems(["mm:ss", "mm:ss.ms", "seconds"])
        combo.setCurrentText(self._config["format"])
        combo.currentTextChanged.connect(lambda v: self._update_config("format", v, app))
        layout.addWidget(combo)

        for label_text, key, lo, hi in [("Pos X %", "pos_x", 0, 100), ("Pos Y %", "pos_y", 0, 100)]:
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

        return content
