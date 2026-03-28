#!/usr/bin/env python3
"""
Módulo de barras rectas (Straight Bar Visualizer)
Inspirado en wav2bar-reborn: vo_visualizer_straight_bar

Visualiza el espectro de audio como barras verticales con:
- Escalado logarítmico de frecuencias
- Suavizado temporal configurable
- Gradientes de color
- Sombras y bordes opcionales
- Modo espejo
"""

import numpy as np
import cv2

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QSpinBox, QComboBox, QCheckBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt

from modules.core.base import Module


class StraightBarModule(Module):
    """Visualizador de barras rectas estilo wav2bar-reborn."""

    module_type = "audio"
    module_category = "visualization"
    module_tags = ["bars", "straight", "spectrum", "wav2bar", "visualizer"]
    module_version = "1.0.0"
    module_author = "Soundvi (wav2bar-reborn)"

    def __init__(self):
        super().__init__(
            nombre="Barras Rectas (wav2bar)",
            descripcion="Barras verticales con escalado logarítmico y suavizado"
        )
        self._audio_data = None
        self._prev_bands = None
        self._duration = 0.0
        self._config = {
            "n_bars": 64,
            "bar_width_ratio": 0.7,
            "gap_ratio": 0.3,
            "height_ratio": 0.4,
            "pos_y": 0.85,
            "opacity": 0.9,
            "smoothing": 0.3,
            "color_mode": "gradient",
            "color_start_r": 0, "color_start_g": 200, "color_start_b": 255,
            "color_end_r": 255, "color_end_g": 50, "color_end_b": 100,
            "mirror": False,
            "rounded_caps": True,
            "shadow": True,
            "shadow_offset": 3,
            "shadow_alpha": 0.3,
            "min_freq": 50,
            "max_freq": 16000,
            "log_scale": True,
            "power_scale": 0.4,
        }

    def prepare_audio(self, audio_path, mel_data, sr, hop, duration, fps, **kwargs):
        """Pre-procesa el audio para la visualización."""
        try:
            import librosa
            offset = kwargs.get('audio_offset', 0.0)
            y, sr = librosa.load(audio_path, sr=22050, mono=True, offset=offset, duration=duration)
            n_fft = 2048
            hop_length = 512
            S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop_length))
            freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

            n_bars = self._config.get("n_bars", 64)
            min_f = self._config.get("min_freq", 50)
            max_f = self._config.get("max_freq", 16000)

            if self._config.get("log_scale", True):
                bands = np.logspace(np.log10(max(min_f, 20)), np.log10(min(max_f, sr//2)), n_bars + 1)
            else:
                bands = np.linspace(min_f, max_f, n_bars + 1)

            energy = np.zeros((n_bars, S.shape[1]))
            for i in range(n_bars):
                idx = np.where((freqs >= bands[i]) & (freqs < bands[i+1]))[0]
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
            print(f"[StraightBarModule] Error preparando audio: {e}")

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado or self._audio_data is None:
            return frame
        try:
            h, w = frame.shape[:2]
            fps = kwargs.get('fps', 30)
            fi = min(int(tiempo * fps), len(self._audio_data) - 1)
            bands = self._audio_data[fi].copy()

            # Suavizado temporal
            sm = self._config.get("smoothing", 0.3)
            if self._prev_bands is not None and sm > 0:
                bands = bands * (1 - sm) + self._prev_bands * sm
            self._prev_bands = bands.copy()

            n = len(bands)
            max_h = int(h * self._config["height_ratio"])
            base_y = int(h * self._config["pos_y"])
            total_w = w
            bar_section = total_w / n
            bar_w = max(1, int(bar_section * self._config["bar_width_ratio"]))
            gap = max(0, int(bar_section * self._config["gap_ratio"]))

            overlay = frame.copy()

            for i in range(n):
                bh = int(bands[i] * max_h)
                if bh < 2:
                    continue

                ratio = i / max(n - 1, 1)
                cr = int(self._config["color_start_r"] * (1 - ratio) + self._config["color_end_r"] * ratio)
                cg = int(self._config["color_start_g"] * (1 - ratio) + self._config["color_end_g"] * ratio)
                cb = int(self._config["color_start_b"] * (1 - ratio) + self._config["color_end_b"] * ratio)

                x1 = int(i * bar_section + gap // 2)
                x2 = x1 + bar_w
                y1 = base_y - bh
                y2 = base_y

                # Sombra
                if self._config.get("shadow", False):
                    so = self._config.get("shadow_offset", 3)
                    sa = self._config.get("shadow_alpha", 0.3)
                    shadow_overlay = overlay.copy()
                    cv2.rectangle(shadow_overlay, (x1 + so, y1 + so), (x2 + so, y2 + so), (0, 0, 0), -1)
                    cv2.addWeighted(shadow_overlay, sa, overlay, 1 - sa, 0, overlay)

                # Barra principal
                if self._config.get("rounded_caps", False) and bh > bar_w:
                    radius = bar_w // 2
                    cv2.rectangle(overlay, (x1, y1 + radius), (x2, y2), (cb, cg, cr), -1)
                    cv2.ellipse(overlay, (x1 + radius, y1 + radius), (radius, radius), 0, 180, 360, (cb, cg, cr), -1)
                else:
                    cv2.rectangle(overlay, (x1, y1), (x2, y2), (cb, cg, cr), -1)

                # Modo espejo
                if self._config.get("mirror", False):
                    mirror_y1 = base_y
                    mirror_y2 = base_y + int(bh * 0.5)
                    mirror_alpha = 0.4
                    mirror_overlay = overlay.copy()
                    cv2.rectangle(mirror_overlay, (x1, mirror_y1), (x2, mirror_y2), (cb, cg, cr), -1)
                    cv2.addWeighted(mirror_overlay, mirror_alpha, overlay, 1 - mirror_alpha, 0, overlay)

            alpha = self._config.get("opacity", 0.9)
            return cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
        except Exception as e:
            return frame

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        # Número de barras
        row = QHBoxLayout()
        row.addWidget(QLabel("Barras:"))
        n_spin = QSpinBox()
        n_spin.setRange(8, 256)
        n_spin.setValue(self._config["n_bars"])
        n_spin.valueChanged.connect(lambda v: self._update_config("n_bars", v, app))
        row.addWidget(n_spin)
        layout.addLayout(row)

        # Opacidad
        layout.addWidget(QLabel("Opacidad:"))
        op_slider = QSlider(Qt.Orientation.Horizontal)
        op_slider.setRange(0, 100)
        op_slider.setValue(int(self._config["opacity"] * 100))
        op_slider.valueChanged.connect(lambda v: self._update_config("opacity", v / 100.0, app))
        layout.addWidget(op_slider)

        # Suavizado
        layout.addWidget(QLabel("Suavizado temporal:"))
        sm_slider = QSlider(Qt.Orientation.Horizontal)
        sm_slider.setRange(0, 95)
        sm_slider.setValue(int(self._config["smoothing"] * 100))
        sm_slider.valueChanged.connect(lambda v: self._update_config("smoothing", v / 100.0, app))
        layout.addWidget(sm_slider)

        # Altura
        layout.addWidget(QLabel("Altura:"))
        h_slider = QSlider(Qt.Orientation.Horizontal)
        h_slider.setRange(5, 80)
        h_slider.setValue(int(self._config["height_ratio"] * 100))
        h_slider.valueChanged.connect(lambda v: self._update_config("height_ratio", v / 100.0, app))
        layout.addWidget(h_slider)

        # Opciones
        mirror_cb = QCheckBox("Modo espejo")
        mirror_cb.setChecked(self._config["mirror"])
        mirror_cb.toggled.connect(lambda v: self._update_config("mirror", v, app))
        layout.addWidget(mirror_cb)

        shadow_cb = QCheckBox("Sombras")
        shadow_cb.setChecked(self._config["shadow"])
        shadow_cb.toggled.connect(lambda v: self._update_config("shadow", v, app))
        layout.addWidget(shadow_cb)

        rounded_cb = QCheckBox("Bordes redondeados")
        rounded_cb.setChecked(self._config["rounded_caps"])
        rounded_cb.toggled.connect(lambda v: self._update_config("rounded_caps", v, app))
        layout.addWidget(rounded_cb)

        log_cb = QCheckBox("Escala logarítmica")
        log_cb.setChecked(self._config["log_scale"])
        log_cb.toggled.connect(lambda v: self._update_config("log_scale", v, app))
        layout.addWidget(log_cb)

        return content
