#!/usr/bin/env python3
"""
Módulo de Ecualizador visual.
Categorizado: audio/effects
"""

import numpy as np
import cv2

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider
from PyQt6.QtCore import Qt

from modules.core.base import Module


class EqualizerModule(Module):
    """Ecualizador visual con bandas de frecuencia ajustables."""

    module_type = "audio"
    module_category = "effects"
    module_tags = ["equalizer", "eq", "audio", "frequency", "bands"]
    module_version = "1.0.0"

    def __init__(self):
        super().__init__(
            nombre="Ecualizador Visual",
            descripcion="Ecualizador de 10 bandas con visualización"
        )
        self._audio_bands = None
        self._config = {
            "band_gains": [1.0] * 10,
            "color_r": 100, "color_g": 200, "color_b": 255,
            "opacity": 0.7, "pos_y": 0.8, "height_ratio": 0.25,
        }

    def prepare_audio(self, audio_path, *args):
        try:
            import librosa
            y, sr = librosa.load(audio_path, sr=22050, mono=True)
            S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
            freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
            bands = np.logspace(np.log10(30), np.log10(16000), 11)
            energy = np.zeros((10, S.shape[1]))
            for i in range(10):
                idx = np.where((freqs >= bands[i]) & (freqs < bands[i+1]))[0]
                if len(idx) > 0: energy[i] = np.mean(S[idx, :], axis=0)
            energy = np.power(np.maximum(energy, 1e-10), 0.3)
            for i in range(10):
                mx = np.max(energy[i])
                if mx > 0: energy[i] /= mx
            self._audio_bands = energy
            self._sr = sr
        except Exception as e:
            print(f"[EQ] Error: {e}")

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado or self._audio_bands is None:
            return frame
        try:
            h, w = frame.shape[:2]
            fps = kwargs.get('fps', 30)
            sample_idx = min(int(tiempo * self._sr / 512), self._audio_bands.shape[1] - 1)
            values = self._audio_bands[:, sample_idx]
            gains = self._config["band_gains"]
            values = np.array([v * g for v, g in zip(values, gains)])
            max_h = int(h * self._config["height_ratio"])
            base_y = int(h * self._config["pos_y"])
            bar_w = w // 12
            overlay = frame.copy()
            color = (self._config["color_b"], self._config["color_g"], self._config["color_r"])
            labels_txt = ["32", "64", "125", "250", "500", "1K", "2K", "4K", "8K", "16K"]
            for i in range(10):
                bh = int(values[i] * max_h)
                if bh < 2: continue
                x1 = (i + 1) * bar_w
                x2 = x1 + bar_w - 4
                y1, y2 = base_y - bh, base_y
                cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
                cv2.putText(overlay, labels_txt[i], (x1, base_y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (200, 200, 200), 1)
            return cv2.addWeighted(overlay, self._config["opacity"], frame, 1 - self._config["opacity"], 0)
        except:
            return frame

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Ganancias EQ (10 bandas):"))
        labels = ["32Hz", "64", "125", "250", "500", "1K", "2K", "4K", "8K", "16K"]

        for i in range(10):
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(labels[i])
            lbl.setFixedWidth(40)
            rl.addWidget(lbl)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 200)  # 0.0 to 2.0 mapped to 0-200
            slider.setValue(int(self._config["band_gains"][i] * 100))

            def make_cb(idx):
                def cb(v):
                    gains = self._config["band_gains"]
                    gains[idx] = v / 100.0
                    self._update_config("band_gains", gains, app)
                return cb

            slider.valueChanged.connect(make_cb(i))
            rl.addWidget(slider)
            layout.addWidget(row)

        return content
