#!/usr/bin/env python3
"""
Módulo de espectro de audio.
Categorizado: audio/visualization
"""

import numpy as np
import cv2

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSpinBox
from PyQt6.QtCore import Qt

from modules.core.base import Module


class SpectrumModule(Module):
    """Visualizador de espectro de frecuencias con gradientes."""

    module_type = "audio"
    module_category = "visualization"
    module_tags = ["spectrum", "audio", "frequency", "visualization"]
    module_version = "1.0.0"

    def __init__(self):
        super().__init__(
            nombre="Espectro de Frecuencias",
            descripcion="Visualización de espectro con gradientes de color"
        )
        self._audio_data = None
        self._duration = 0.0
        self._config = {
            "color_low_r": 0, "color_low_g": 100, "color_low_b": 255,
            "color_high_r": 255, "color_high_g": 50, "color_high_b": 50,
            "opacity": 0.8, "height_ratio": 0.3, "n_bands": 32,
            "pos_y": 0.85, "smoothing": 0.5,
        }

    def prepare_audio(self, audio_path, mel_data, sr, hop, duration, fps):
        try:
            import librosa
            y, sr = librosa.load(audio_path, sr=22050, mono=True)
            S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
            n_bands = self._config.get("n_bands", 32)
            freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
            bands = np.logspace(np.log10(50), np.log10(10000), n_bands + 1)
            energy = np.zeros((n_bands, S.shape[1]))
            for i in range(n_bands):
                idx = np.where((freqs >= bands[i]) & (freqs < bands[i+1]))[0]
                if len(idx) > 0:
                    energy[i] = np.mean(S[idx, :], axis=0)
            energy = np.power(np.maximum(energy, 1e-10), 0.3)
            for i in range(n_bands):
                mx = np.max(energy[i])
                if mx > 0: energy[i] /= mx
            from scipy.interpolate import interp1d
            n_frames = int(duration * fps)
            x_old = np.linspace(0, 1, energy.shape[1])
            x_new = np.linspace(0, 1, n_frames)
            self._audio_data = np.zeros((n_frames, n_bands))
            for i in range(n_bands):
                f = interp1d(x_old, energy[i], kind='linear', fill_value='extrapolate')
                self._audio_data[:, i] = f(x_new)
            self._duration = duration
        except Exception as e:
            print(f"[SpectrumModule] Error: {e}")

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado or self._audio_data is None:
            return frame
        try:
            h, w = frame.shape[:2]
            fps = kwargs.get('fps', 30)
            fi = min(int(tiempo * fps), len(self._audio_data) - 1)
            bands = self._audio_data[fi]
            n = len(bands)
            max_h = int(h * self._config["height_ratio"])
            base_y = int(h * self._config["pos_y"])
            bar_w = w // n
            overlay = frame.copy()
            for i in range(n):
                ratio = i / max(n - 1, 1)
                cr = int(self._config["color_low_r"] * (1 - ratio) + self._config["color_high_r"] * ratio)
                cg = int(self._config["color_low_g"] * (1 - ratio) + self._config["color_high_g"] * ratio)
                cb = int(self._config["color_low_b"] * (1 - ratio) + self._config["color_high_b"] * ratio)
                bh = int(bands[i] * max_h)
                if bh < 2: continue
                x1, x2 = i * bar_w, (i + 1) * bar_w - 1
                y1, y2 = base_y - bh, base_y
                cv2.rectangle(overlay, (x1, y1), (x2, y2), (cb, cg, cr), -1)
            alpha = self._config["opacity"]
            return cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
        except:
            return frame

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Opacidad:"))
        op_slider = QSlider(Qt.Orientation.Horizontal)
        op_slider.setRange(0, 100)
        op_slider.setValue(int(self._config["opacity"] * 100))
        op_slider.valueChanged.connect(lambda v: self._update_config("opacity", v / 100.0, app))
        layout.addWidget(op_slider)

        layout.addWidget(QLabel("Bandas:"))
        n_spin = QSpinBox()
        n_spin.setRange(8, 128)
        n_spin.setValue(self._config["n_bands"])
        n_spin.valueChanged.connect(lambda v: self._update_config("n_bands", v, app))
        layout.addWidget(n_spin)

        return content
