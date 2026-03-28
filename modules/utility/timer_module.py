#!/usr/bin/env python3
"""
Módulo de temporizador visual
Inspirado en wav2bar-reborn: vo_timer_straight_bar, vo_timer_straight_line_point

Muestra el progreso del audio como una barra o línea con punto.
"""

import numpy as np
import cv2

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QSlider, QComboBox, QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt

from modules.core.base import Module


class TimerVisualizerModule(Module):
    """Temporizador visual con barra de progreso y punto indicador."""

    module_type = "utility"
    module_category = "utility"
    module_tags = ["timer", "progress", "bar", "wav2bar", "time"]
    module_version = "1.0.0"
    module_author = "Soundvi (wav2bar-reborn)"

    MODES = ["bar", "line_point", "circle"]

    def __init__(self):
        super().__init__(
            nombre="Temporizador Visual (wav2bar)",
            descripcion="Barra de progreso de tiempo con indicador"
        )
        self._duration = 0.0
        self._config = {
            "mode": "bar",
            "pos_y": 0.95,
            "height": 6,
            "margin": 0.05,
            "color_bg_r": 50, "color_bg_g": 50, "color_bg_b": 50,
            "color_fill_r": 0, "color_fill_g": 180, "color_fill_b": 255,
            "color_point_r": 255, "color_point_g": 255, "color_point_b": 255,
            "point_size": 8,
            "opacity": 0.8,
            "show_time_text": True,
            "rounded": True,
        }

    def prepare_audio(self, audio_path, mel_data, sr, hop, duration, fps):
        self._duration = duration

    def _format_time(self, seconds):
        m = int(seconds) // 60
        s = int(seconds) % 60
        return f"{m}:{s:02d}"

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado or self._duration <= 0:
            return frame
        try:
            h, w = frame.shape[:2]
            progress = min(1.0, tiempo / self._duration)
            mode = self._config.get("mode", "bar")
            margin = int(w * self._config.get("margin", 0.05))
            bar_y = int(h * self._config["pos_y"])
            bar_h = self._config.get("height", 6)
            bar_w = w - 2 * margin

            overlay = frame.copy()
            bg_color = (self._config["color_bg_b"], self._config["color_bg_g"], self._config["color_bg_r"])
            fill_color = (self._config["color_fill_b"], self._config["color_fill_g"], self._config["color_fill_r"])
            point_color = (self._config["color_point_b"], self._config["color_point_g"], self._config["color_point_r"])

            if mode == "bar":
                # Background bar
                cv2.rectangle(overlay, (margin, bar_y), (margin + bar_w, bar_y + bar_h), bg_color, -1)
                # Fill bar
                fill_w = int(bar_w * progress)
                if fill_w > 0:
                    if self._config.get("rounded", True):
                        cv2.rectangle(overlay, (margin, bar_y), (margin + fill_w, bar_y + bar_h), fill_color, -1)
                    else:
                        cv2.rectangle(overlay, (margin, bar_y), (margin + fill_w, bar_y + bar_h), fill_color, -1)

            elif mode == "line_point":
                # Line
                line_y = bar_y + bar_h // 2
                cv2.line(overlay, (margin, line_y), (margin + bar_w, line_y), bg_color, 2)
                cv2.line(overlay, (margin, line_y), (margin + int(bar_w * progress), line_y), fill_color, 2)
                # Point
                point_x = margin + int(bar_w * progress)
                ps = self._config.get("point_size", 8)
                cv2.circle(overlay, (point_x, line_y), ps, point_color, -1)

            elif mode == "circle":
                cx, cy = w // 2, bar_y
                radius = 20
                angle = int(360 * progress)
                cv2.ellipse(overlay, (cx, cy), (radius, radius), -90, 0, 360, bg_color, 3)
                cv2.ellipse(overlay, (cx, cy), (radius, radius), -90, 0, angle, fill_color, 3)

            # Time text
            if self._config.get("show_time_text", True):
                current = self._format_time(tiempo)
                total = self._format_time(self._duration)
                text = f"{current} / {total}"
                font = cv2.FONT_HERSHEY_SIMPLEX
                scale = 0.4
                (tw, th), _ = cv2.getTextSize(text, font, scale, 1)
                tx = margin + bar_w - tw
                ty = bar_y - 5
                cv2.putText(overlay, text, (tx, ty), font, scale, (255, 255, 255), 1, cv2.LINE_AA)

            alpha = self._config.get("opacity", 0.8)
            return cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
        except Exception as e:
            return frame

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Modo:"))
        mode_combo = QComboBox()
        mode_combo.addItems(self.MODES)
        mode_combo.setCurrentText(self._config["mode"])
        mode_combo.currentTextChanged.connect(lambda v: self._update_config("mode", v, app))
        layout.addWidget(mode_combo)

        layout.addWidget(QLabel("Altura:"))
        h_spin = QSpinBox()
        h_spin.setRange(2, 30)
        h_spin.setValue(self._config["height"])
        h_spin.valueChanged.connect(lambda v: self._update_config("height", v, app))
        layout.addWidget(h_spin)

        layout.addWidget(QLabel("Opacidad:"))
        op_slider = QSlider(Qt.Orientation.Horizontal)
        op_slider.setRange(0, 100)
        op_slider.setValue(int(self._config["opacity"] * 100))
        op_slider.valueChanged.connect(lambda v: self._update_config("opacity", v / 100.0, app))
        layout.addWidget(op_slider)

        time_cb = QCheckBox("Mostrar tiempo")
        time_cb.setChecked(self._config["show_time_text"])
        time_cb.toggled.connect(lambda v: self._update_config("show_time_text", v, app))
        layout.addWidget(time_cb)

        return content
