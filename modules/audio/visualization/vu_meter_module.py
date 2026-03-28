#!/usr/bin/env python3
"""
Módulo de VU Meter.
Categorizado: audio/visualization
"""

import numpy as np
import cv2

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox
from PyQt6.QtCore import Qt

from modules.core.base import Module


class VUMeterModule(Module):
    """Medidor VU clásico de nivel de audio."""

    module_type = "audio"
    module_category = "visualization"
    module_tags = ["vu", "meter", "level", "audio", "volume"]
    module_version = "1.0.0"

    def __init__(self):
        super().__init__(
            nombre="VU Meter",
            descripcion="Medidor de nivel de audio estilo VU"
        )
        self._rms_data = None
        self._config = {
            "color_r": 0, "color_g": 255, "color_b": 0,
            "warn_color_r": 255, "warn_color_g": 255, "warn_color_b": 0,
            "clip_color_r": 255, "clip_color_g": 0, "clip_color_b": 0,
            "opacity": 0.9, "width": 200, "height": 20,
            "pos_x": 20, "pos_y": 20, "style": "horizontal",
        }

    def prepare_audio(self, audio_path, mel_data=None, sr=None, hop=None, duration=None, fps=None, **kwargs):
        try:
            import librosa
            offset = kwargs.get('audio_offset', 0.0)
            y, sr = librosa.load(audio_path, sr=22050, mono=True, offset=offset, duration=duration)
            hop = 512
            rms = librosa.feature.rms(y=y, hop_length=hop)[0]
            mx = np.max(rms)
            if mx > 0: rms /= mx
            self._rms_data = rms
            self._sr = sr
            self._hop = hop
        except Exception as e:
            print(f"[VUMeter] Error: {e}")

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado or self._rms_data is None:
            return frame
        try:
            fps = kwargs.get('fps', 30)
            sample_idx = int(tiempo * self._sr / self._hop)
            sample_idx = min(sample_idx, len(self._rms_data) - 1)
            level = float(self._rms_data[sample_idx])
            h, w = frame.shape[:2]
            bar_w = self._config["width"]
            bar_h = self._config["height"]
            px, py = self._config["pos_x"], self._config["pos_y"]
            filled = int(bar_w * level)
            cv2.rectangle(frame, (px, py), (px + bar_w, py + bar_h), (40, 40, 40), -1)
            if filled > 0:
                if level > 0.9:
                    color = (self._config["clip_color_b"], self._config["clip_color_g"], self._config["clip_color_r"])
                elif level > 0.7:
                    color = (self._config["warn_color_b"], self._config["warn_color_g"], self._config["warn_color_r"])
                else:
                    color = (self._config["color_b"], self._config["color_g"], self._config["color_r"])
                cv2.rectangle(frame, (px, py), (px + filled, py + bar_h), color, -1)
            cv2.rectangle(frame, (px, py), (px + bar_w, py + bar_h), (100, 100, 100), 1)
            return frame
        except:
            return frame

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        for label, key in [("Ancho:", "width"), ("Alto:", "height"), ("Pos X:", "pos_x"), ("Pos Y:", "pos_y")]:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.addWidget(QLabel(label))
            spin = QSpinBox()
            spin.setRange(0, 2000)
            spin.setValue(self._config[key])
            spin.valueChanged.connect(lambda v, k=key: self._update_config(k, v, app))
            rl.addWidget(spin)
            layout.addWidget(row)

        return content
