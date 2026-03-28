#!/usr/bin/env python3
"""
Módulo de sombras y bordes
Inspirado en wav2bar-reborn: BoxShadowProperties, BorderProperties

Añade sombras, bordes y marcos decorativos al video.
"""

import numpy as np
import cv2

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QSlider, QSpinBox, QCheckBox
)
from PyQt6.QtCore import Qt

from modules.core.base import Module


class ShadowBorderModule(Module):
    """Sombras y bordes decorativos para el video."""

    module_type = "video"
    module_category = "effects"
    module_tags = ["shadow", "border", "frame", "wav2bar", "decoration"]
    module_version = "1.0.0"
    module_author = "Soundvi (wav2bar-reborn)"

    def __init__(self):
        super().__init__(
            nombre="Sombras y Bordes (wav2bar)",
            descripcion="Sombras, bordes y marcos decorativos"
        )
        self._config = {
            "border_enabled": True,
            "border_width": 3,
            "border_color_r": 255, "border_color_g": 255, "border_color_b": 255,
            "border_radius": 0,
            "inner_shadow": False,
            "inner_shadow_size": 30,
            "inner_shadow_alpha": 0.5,
            "outer_glow": False,
            "outer_glow_size": 10,
            "outer_glow_color_r": 100, "outer_glow_color_g": 200, "outer_glow_color_b": 255,
        }

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado:
            return frame
        try:
            result = frame.copy()
            h, w = result.shape[:2]

            # Inner shadow (vignette-like)
            if self._config.get("inner_shadow", False):
                size = self._config.get("inner_shadow_size", 30)
                alpha = self._config.get("inner_shadow_alpha", 0.5)
                mask = np.ones((h, w), dtype=np.float32)
                for i in range(size):
                    v = (i / size) * alpha
                    # Top
                    mask[i, :] = min(mask[i, 0], 1 - alpha + v)
                    # Bottom
                    mask[h - 1 - i, :] = min(mask[h - 1 - i, 0], 1 - alpha + v)
                    # Left
                    mask[:, i] = np.minimum(mask[:, i], 1 - alpha + v)
                    # Right
                    mask[:, w - 1 - i] = np.minimum(mask[:, w - 1 - i], 1 - alpha + v)
                mask_3d = np.stack([mask] * 3, axis=-1)
                result = (result.astype(np.float32) * mask_3d).astype(np.uint8)

            # Border
            if self._config.get("border_enabled", True):
                bw = self._config.get("border_width", 3)
                color = (
                    self._config["border_color_b"],
                    self._config["border_color_g"],
                    self._config["border_color_r"]
                )
                radius = self._config.get("border_radius", 0)
                if radius > 0:
                    cv2.rectangle(result, (radius, 0), (w - radius, bw), color, -1)
                    cv2.rectangle(result, (radius, h - bw), (w - radius, h), color, -1)
                    cv2.rectangle(result, (0, radius), (bw, h - radius), color, -1)
                    cv2.rectangle(result, (w - bw, radius), (w, h - radius), color, -1)
                else:
                    cv2.rectangle(result, (0, 0), (w - 1, h - 1), color, bw)

            return result
        except Exception as e:
            return frame

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        border_cb = QCheckBox("Borde")
        border_cb.setChecked(self._config["border_enabled"])
        border_cb.toggled.connect(lambda v: self._update_config("border_enabled", v, app))
        layout.addWidget(border_cb)

        layout.addWidget(QLabel("Ancho borde:"))
        bw_spin = QSpinBox()
        bw_spin.setRange(1, 20)
        bw_spin.setValue(self._config["border_width"])
        bw_spin.valueChanged.connect(lambda v: self._update_config("border_width", v, app))
        layout.addWidget(bw_spin)

        shadow_cb = QCheckBox("Sombra interior")
        shadow_cb.setChecked(self._config["inner_shadow"])
        shadow_cb.toggled.connect(lambda v: self._update_config("inner_shadow", v, app))
        layout.addWidget(shadow_cb)

        layout.addWidget(QLabel("Tamaño sombra:"))
        ss_slider = QSlider(Qt.Orientation.Horizontal)
        ss_slider.setRange(5, 100)
        ss_slider.setValue(self._config["inner_shadow_size"])
        ss_slider.valueChanged.connect(lambda v: self._update_config("inner_shadow_size", v, app))
        layout.addWidget(ss_slider)

        return content
