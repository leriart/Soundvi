#!/usr/bin/env python3
"""
Módulo de Transiciones.
Categorizado: video/effects
"""
import numpy as np
import cv2

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDoubleSpinBox
from PyQt6.QtCore import Qt

from modules.core.base import Module

class TransitionModule(Module):
    module_type = "video"
    module_category = "effects"
    module_tags = ["transition", "crossfade", "wipe", "slide"]
    module_version = "1.0.0"

    def __init__(self):
        super().__init__(nombre="Transiciones", descripcion="Efectos de transición entre escenas")
        self._config = {
            "type": "crossfade", "duration": 1.0,
            "trigger_time": 5.0, "direction": "left",
        }

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado: return frame
        try:
            trigger = self._config["trigger_time"]
            dur = self._config["duration"]
            if trigger <= tiempo <= trigger + dur:
                progress = (tiempo - trigger) / dur
                t_type = self._config["type"]
                h, w = frame.shape[:2]
                if t_type == "crossfade":
                    black = np.zeros_like(frame)
                    alpha = abs(0.5 - progress) * 2
                    frame = cv2.addWeighted(frame, alpha, black, 1 - alpha, 0)
                elif t_type == "wipe":
                    mask = np.zeros((h, w), dtype=np.uint8)
                    wipe_pos = int(w * progress)
                    mask[:, :wipe_pos] = 255
                    frame = cv2.bitwise_and(frame, frame, mask=mask)
                elif t_type == "slide":
                    shift = int(w * progress)
                    M = np.float32([[1, 0, -shift], [0, 1, 0]])
                    frame = cv2.warpAffine(frame, M, (w, h))
            return frame
        except: return frame

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(QLabel("Tipo:"))
        combo = QComboBox()
        combo.addItems(["crossfade", "wipe", "slide"])
        combo.setCurrentText(self._config["type"])
        combo.currentTextChanged.connect(lambda v: self._update_config("type", v, app))
        rl.addWidget(combo)
        layout.addWidget(row)

        for label_text, key, lo, hi in [("Duración (s)", "duration", 0.1, 5.0), ("Tiempo inicio", "trigger_time", 0.0, 300.0)]:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.addWidget(QLabel(f"{label_text}:"))
            spin = QDoubleSpinBox()
            spin.setRange(lo, hi)
            spin.setSingleStep(0.1)
            spin.setValue(self._config[key])
            spin.valueChanged.connect(lambda v, k=key: self._update_config(k, v, app))
            rl.addWidget(spin)
            layout.addWidget(row)

        return content
