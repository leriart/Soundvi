#!/usr/bin/env python3
"""
Módulo de barras circulares (Circular Bar Visualizer)
Inspirado en wav2bar-reborn: vo_visualizer_circular_bar

Visualiza el espectro de audio como barras dispuestas en círculo.
"""

import numpy as np
import cv2
import math

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QSpinBox, QCheckBox
)
from PyQt6.QtCore import Qt

from modules.core.base import Module


class CircularBarModule(Module):
    """Visualizador de barras circulares estilo wav2bar-reborn."""

    module_type = "audio"
    module_category = "visualization"
    module_tags = ["circular", "bars", "spectrum", "wav2bar", "radial"]
    module_version = "1.0.0"
    module_author = "Soundvi (wav2bar-reborn)"

    def __init__(self):
        super().__init__(
            nombre="Barras Circulares (wav2bar)",
            descripcion="Barras en disposición circular reactivas al audio"
        )
        self._audio_data = None
        self._prev_bands = None
        self._duration = 0.0
        self._config = {
            "n_bars": 64,
            "radius": 0.15,
            "bar_length": 0.15,
            "bar_width": 3,
            "center_x": 0.5,
            "center_y": 0.5,
            "opacity": 0.9,
            "smoothing": 0.3,
            "rotation_speed": 0.0,
            "color_start_r": 100, "color_start_g": 200, "color_start_b": 255,
            "color_end_r": 255, "color_end_g": 100, "color_end_b": 200,
            "mirror_bars": True,
            "inner_circle": True,
            "inner_circle_color_r": 50, "inner_circle_color_g": 50, "inner_circle_color_b": 50,
            "log_scale": True,
            "power_scale": 0.4,
        }

    def prepare_audio(self, audio_path, mel_data, sr, hop, duration, fps):
        try:
            import librosa
            y, sr = librosa.load(audio_path, sr=22050, mono=True)
            S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
            freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
            n_bars = self._config.get("n_bars", 64)
            bands_f = np.logspace(np.log10(50), np.log10(12000), n_bars + 1)
            energy = np.zeros((n_bars, S.shape[1]))
            for i in range(n_bars):
                idx = np.where((freqs >= bands_f[i]) & (freqs < bands_f[i+1]))[0]
                if len(idx) > 0:
                    energy[i] = np.mean(S[idx, :], axis=0)
            power = self._config.get("power_scale", 0.4)
            energy = np.power(np.maximum(energy, 1e-10), power)
            for i in range(n_bars):
                mx = np.max(energy[i])
                if mx > 0:
                    energy[i] /= mx
            from scipy.interpolate import interp1d
            n_frames = int(duration * fps)
            x_old = np.linspace(0, 1, energy.shape[1])
            x_new = np.linspace(0, 1, n_frames)
            self._audio_data = np.zeros((n_frames, n_bars))
            for i in range(n_bars):
                f = interp1d(x_old, energy[i], kind='linear', fill_value='extrapolate')
                self._audio_data[:, i] = np.clip(f(x_new), 0, 1)
            self._duration = duration
            self._prev_bands = None
        except Exception as e:
            print(f"[CircularBarModule] Error: {e}")

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado or self._audio_data is None:
            return frame
        try:
            h, w = frame.shape[:2]
            fps = kwargs.get('fps', 30)
            fi = min(int(tiempo * fps), len(self._audio_data) - 1)
            bands = self._audio_data[fi].copy()

            sm = self._config.get("smoothing", 0.3)
            if self._prev_bands is not None and sm > 0:
                bands = bands * (1 - sm) + self._prev_bands * sm
            self._prev_bands = bands.copy()

            n = len(bands)
            cx = int(w * self._config["center_x"])
            cy = int(h * self._config["center_y"])
            min_dim = min(w, h)
            radius = int(min_dim * self._config["radius"])
            max_bar_len = int(min_dim * self._config["bar_length"])
            bar_w = max(1, self._config["bar_width"])

            overlay = frame.copy()
            rotation = self._config.get("rotation_speed", 0.0) * tiempo * 360

            # Círculo interior
            if self._config.get("inner_circle", True):
                ic_color = (
                    self._config["inner_circle_color_b"],
                    self._config["inner_circle_color_g"],
                    self._config["inner_circle_color_r"]
                )
                cv2.circle(overlay, (cx, cy), radius, ic_color, 2)

            for i in range(n):
                bh = int(bands[i] * max_bar_len)
                if bh < 1:
                    continue

                angle_deg = (360.0 / n) * i + rotation
                angle_rad = math.radians(angle_deg)

                ratio = i / max(n - 1, 1)
                cr = int(self._config["color_start_r"] * (1 - ratio) + self._config["color_end_r"] * ratio)
                cg = int(self._config["color_start_g"] * (1 - ratio) + self._config["color_end_g"] * ratio)
                cb = int(self._config["color_start_b"] * (1 - ratio) + self._config["color_end_b"] * ratio)
                color = (cb, cg, cr)

                # Barra exterior
                x1 = int(cx + radius * math.cos(angle_rad))
                y1 = int(cy + radius * math.sin(angle_rad))
                x2 = int(cx + (radius + bh) * math.cos(angle_rad))
                y2 = int(cy + (radius + bh) * math.sin(angle_rad))
                cv2.line(overlay, (x1, y1), (x2, y2), color, bar_w)

                # Barra espejo interior
                if self._config.get("mirror_bars", True):
                    inner_len = int(bh * 0.5)
                    x3 = int(cx + (radius - inner_len) * math.cos(angle_rad))
                    y3 = int(cy + (radius - inner_len) * math.sin(angle_rad))
                    cv2.line(overlay, (x1, y1), (x3, y3), color, max(1, bar_w - 1))

            alpha = self._config.get("opacity", 0.9)
            return cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
        except Exception as e:
            return frame

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        # Barras
        row = QHBoxLayout()
        row.addWidget(QLabel("Barras:"))
        n_spin = QSpinBox()
        n_spin.setRange(16, 256)
        n_spin.setValue(self._config["n_bars"])
        n_spin.valueChanged.connect(lambda v: self._update_config("n_bars", v, app))
        row.addWidget(n_spin)
        layout.addLayout(row)

        # Radio
        layout.addWidget(QLabel("Radio:"))
        r_slider = QSlider(Qt.Orientation.Horizontal)
        r_slider.setRange(5, 40)
        r_slider.setValue(int(self._config["radius"] * 100))
        r_slider.valueChanged.connect(lambda v: self._update_config("radius", v / 100.0, app))
        layout.addWidget(r_slider)

        # Longitud barras
        layout.addWidget(QLabel("Longitud barras:"))
        bl_slider = QSlider(Qt.Orientation.Horizontal)
        bl_slider.setRange(2, 30)
        bl_slider.setValue(int(self._config["bar_length"] * 100))
        bl_slider.valueChanged.connect(lambda v: self._update_config("bar_length", v / 100.0, app))
        layout.addWidget(bl_slider)

        # Suavizado
        layout.addWidget(QLabel("Suavizado:"))
        sm_slider = QSlider(Qt.Orientation.Horizontal)
        sm_slider.setRange(0, 95)
        sm_slider.setValue(int(self._config["smoothing"] * 100))
        sm_slider.valueChanged.connect(lambda v: self._update_config("smoothing", v / 100.0, app))
        layout.addWidget(sm_slider)

        # Opciones
        mirror_cb = QCheckBox("Barras espejo interior")
        mirror_cb.setChecked(self._config["mirror_bars"])
        mirror_cb.toggled.connect(lambda v: self._update_config("mirror_bars", v, app))
        layout.addWidget(mirror_cb)

        inner_cb = QCheckBox("Círculo interior")
        inner_cb.setChecked(self._config["inner_circle"])
        inner_cb.toggled.connect(lambda v: self._update_config("inner_circle", v, app))
        layout.addWidget(inner_cb)

        return content
