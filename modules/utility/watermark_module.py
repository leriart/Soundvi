#!/usr/bin/env python3
"""
Módulo de Marca de Agua.
Categorizado: utility
"""
import numpy as np
import cv2
from PIL import Image

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QLineEdit
)
from PyQt6.QtCore import Qt

from modules.core.base import Module

class WatermarkModule(Module):
    module_type = "utility"
    module_category = "watermark"
    module_tags = ["watermark", "logo", "marca", "utility"]
    module_version = "1.0.0"

    def __init__(self):
        super().__init__(nombre="Marca de Agua", descripcion="Logo o texto como marca de agua")
        self._config = {
            "text": "Soundvi", "use_image": False, "image_path": "",
            "pos_x": 90, "pos_y": 10, "opacity": 0.3, "font_size": 20,
            "color_r": 255, "color_g": 255, "color_b": 255,
        }
        self._logo_img = None

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado: return frame
        try:
            h, w = frame.shape[:2]
            if self._config["use_image"] and self._logo_img is not None:
                logo = self._logo_img
                lh, lw = logo.shape[:2]
                px = int(w * self._config["pos_x"] / 100 - lw / 2)
                py = int(h * self._config["pos_y"] / 100 - lh / 2)
                px, py = max(0, px), max(0, py)
                if py + lh <= h and px + lw <= w:
                    roi = frame[py:py+lh, px:px+lw]
                    op = self._config["opacity"]
                    blended = cv2.addWeighted(logo[:lh, :lw], op, roi, 1 - op, 0)
                    frame[py:py+lh, px:px+lw] = blended
            else:
                text = self._config["text"]
                fs = self._config["font_size"] / 30.0
                color = (self._config["color_b"], self._config["color_g"], self._config["color_r"])
                px = int(w * self._config["pos_x"] / 100)
                py = int(h * self._config["pos_y"] / 100)
                overlay = frame.copy()
                cv2.putText(overlay, text, (px, py), cv2.FONT_HERSHEY_SIMPLEX, fs, color, 1, cv2.LINE_AA)
                op = self._config["opacity"]
                frame = cv2.addWeighted(overlay, op, frame, 1 - op, 0)
            return frame
        except: return frame

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Texto:"))
        t_edit = QLineEdit(self._config["text"])
        t_edit.textChanged.connect(lambda v: self._update_config("text", v, app))
        layout.addWidget(t_edit)

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

        op_row = QWidget()
        orl = QHBoxLayout(op_row)
        orl.setContentsMargins(0, 0, 0, 0)
        orl.addWidget(QLabel("Opacidad:"))
        op_slider = QSlider(Qt.Orientation.Horizontal)
        op_slider.setRange(0, 100)
        op_slider.setValue(int(self._config["opacity"] * 100))
        op_slider.valueChanged.connect(lambda v: self._update_config("opacity", v / 100.0, app))
        orl.addWidget(op_slider)
        layout.addWidget(op_row)

        return content
