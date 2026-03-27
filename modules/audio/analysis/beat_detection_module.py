#!/usr/bin/env python3
"""
Módulo de detección de beats.
Categorizado: audio/analysis
"""

import numpy as np
import cv2

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QSlider
from PyQt6.QtCore import Qt

from modules.core.base import Module


class BeatDetectionModule(Module):
    """Efecto visual que pulsa con los beats del audio."""

    module_type = "audio"
    module_category = "analysis"
    module_tags = ["beat", "detection", "pulse", "rhythm", "audio"]
    module_version = "1.0.0"

    def __init__(self):
        super().__init__(
            nombre="Detector de Beats",
            descripcion="Efecto visual que pulsa al ritmo de la música"
        )
        self._beats = None
        self._onset_env = None
        self._duration = 0.0
        self._config = {
            "effect_type": "flash",
            "color_r": 255, "color_g": 100, "color_b": 50,
            "intensity": 0.5, "decay": 0.1,
        }

    def prepare_audio(self, audio_path, *args):
        try:
            import librosa
            y, sr = librosa.load(audio_path, sr=22050, mono=True)
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            self._beats = librosa.frames_to_time(beats, sr=sr)
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            mx = np.max(onset_env)
            if mx > 0: onset_env /= mx
            self._onset_env = onset_env
            self._sr = sr
            self._duration = len(y) / sr
        except Exception as e:
            print(f"[BeatDetection] Error: {e}")

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado or self._beats is None:
            return frame
        try:
            min_dist = float('inf')
            for bt in self._beats:
                dist = abs(tiempo - bt)
                if dist < min_dist:
                    min_dist = dist

            decay = self._config["decay"]
            intensity = self._config["intensity"]
            if min_dist < decay:
                strength = (1.0 - min_dist / decay) * intensity
                effect = self._config["effect_type"]
                if effect == "flash":
                    color = np.array([self._config["color_b"], self._config["color_g"], self._config["color_r"]], dtype=np.float32)
                    overlay = np.full_like(frame, color, dtype=np.uint8)
                    frame = cv2.addWeighted(overlay, strength * 0.3, frame, 1.0, 0)
                elif effect == "border":
                    h, w = frame.shape[:2]
                    thick = int(strength * 20)
                    color = (self._config["color_b"], self._config["color_g"], self._config["color_r"])
                    cv2.rectangle(frame, (0, 0), (w-1, h-1), color, thick)
                elif effect == "zoom":
                    h, w = frame.shape[:2]
                    scale = 1.0 + strength * 0.05
                    M = cv2.getRotationMatrix2D((w/2, h/2), 0, scale)
                    frame = cv2.warpAffine(frame, M, (w, h))
            return frame
        except:
            return frame

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Efecto:"))
        combo = QComboBox()
        combo.addItems(["flash", "border", "zoom"])
        combo.setCurrentText(self._config["effect_type"])
        combo.currentTextChanged.connect(lambda v: self._update_config("effect_type", v, app))
        layout.addWidget(combo)

        layout.addWidget(QLabel("Intensidad:"))
        int_slider = QSlider(Qt.Orientation.Horizontal)
        int_slider.setRange(0, 100)
        int_slider.setValue(int(self._config["intensity"] * 100))
        int_slider.valueChanged.connect(lambda v: self._update_config("intensity", v / 100.0, app))
        layout.addWidget(int_slider)

        return content
