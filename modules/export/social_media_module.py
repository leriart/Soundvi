#!/usr/bin/env python3
"""
Módulo de Exportación para Redes Sociales.
Categorizado: export
"""
import numpy as np
import cv2

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QCheckBox
from PyQt6.QtCore import Qt

from modules.core.base import Module

class SocialMediaModule(Module):
    module_type = "export"
    module_category = "social"
    module_tags = ["export", "youtube", "instagram", "tiktok", "social"]
    module_version = "1.0.0"

    def __init__(self):
        super().__init__(nombre="Exportar Social Media", descripcion="Perfiles de exportación para redes sociales")
        self._config = {
            "platform": "YouTube", "quality": "high",
            "add_padding": False, "padding_color_r": 0, "padding_color_g": 0, "padding_color_b": 0,
        }
        self.PROFILES = {
            "YouTube": {"w": 1920, "h": 1080, "fps": 30},
            "YouTube Shorts": {"w": 1080, "h": 1920, "fps": 30},
            "Instagram Reel": {"w": 1080, "h": 1920, "fps": 30},
            "Instagram Feed": {"w": 1080, "h": 1080, "fps": 30},
            "TikTok": {"w": 1080, "h": 1920, "fps": 30},
            "Twitter/X": {"w": 1280, "h": 720, "fps": 30},
        }

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado: return frame
        try:
            profile = self.PROFILES.get(self._config["platform"])
            if not profile: return frame
            target_w, target_h = profile["w"], profile["h"]
            h, w = frame.shape[:2]
            if self._config["add_padding"]:
                aspect = target_w / target_h
                current_aspect = w / h
                color = (self._config["padding_color_b"], self._config["padding_color_g"], self._config["padding_color_r"])
                if current_aspect > aspect:
                    new_h = int(w / aspect)
                    pad = (new_h - h) // 2
                    result = np.full((new_h, w, 3), color, dtype=np.uint8)
                    result[pad:pad+h, :] = frame
                else:
                    new_w = int(h * aspect)
                    pad = (new_w - w) // 2
                    result = np.full((h, new_w, 3), color, dtype=np.uint8)
                    result[:, pad:pad+w] = frame
                return cv2.resize(result, (target_w, target_h))
            return frame
        except: return frame

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Plataforma:"))
        combo = QComboBox()
        combo.addItems(list(self.PROFILES.keys()))
        combo.setCurrentText(self._config["platform"])
        layout.addWidget(combo)

        info_label = QLabel("")
        info_label.setStyleSheet("font-size: 8pt;")
        layout.addWidget(info_label)

        def on_plat(val):
            self._update_config("platform", val, app)
            p = self.PROFILES.get(val, {})
            info_label.setText(f"{p.get('w', '?')}x{p.get('h', '?')} @ {p.get('fps', '?')}fps")

        combo.currentTextChanged.connect(on_plat)
        on_plat(self._config["platform"])

        pad_check = QCheckBox("Añadir padding")
        pad_check.setChecked(self._config["add_padding"])
        pad_check.toggled.connect(lambda v: self._update_config("add_padding", v, app))
        layout.addWidget(pad_check)

        return content
