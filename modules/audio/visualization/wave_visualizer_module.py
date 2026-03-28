#!/usr/bin/env python3
"""
Módulo de onda de audio (Straight Wave Visualizer)
Inspirado en wav2bar-reborn: vo_visualizer_straight_wave

Visualiza el audio como una forma de onda suavizada.
"""

import numpy as np
import cv2

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QSlider, QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt

from modules.core.base import Module


class WaveVisualizerModule(Module):
    """Visualizador de forma de onda estilo wav2bar-reborn."""

    module_type = "audio"
    module_category = "visualization"
    module_tags = ["wave", "waveform", "wav2bar", "audio", "line"]
    module_version = "1.0.0"
    module_author = "Soundvi (wav2bar-reborn)"

    def __init__(self):
        super().__init__(
            nombre="Onda de Audio (wav2bar)",
            descripcion="Forma de onda suavizada y reactiva"
        )
        self._audio_data = None
        self._duration = 0.0
        self._config = {
            "n_points": 128,
            "amplitude": 0.2,
            "pos_y": 0.5,
            "line_width": 2,
            "opacity": 0.9,
            "smoothing": 0.4,
            "color_r": 0, "color_g": 255, "color_b": 200,
            "fill": True,
            "fill_alpha": 0.3,
            "mirror_y": True,
            "glow": True,
            "glow_size": 3,
        }
        self._prev_wave = None

    def prepare_audio(self, audio_path, mel_data, sr, hop, duration, fps, **kwargs):
        try:
            import librosa
            offset = kwargs.get('audio_offset', 0.0)
            y, sr = librosa.load(audio_path, sr=22050, mono=True, offset=offset, duration=duration)
            S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
            freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
            n_points = self._config.get("n_points", 128)
            bands = np.logspace(np.log10(30), np.log10(12000), n_points + 1)
            energy = np.zeros((n_points, S.shape[1]))
            for i in range(n_points):
                idx = np.where((freqs >= bands[i]) & (freqs < bands[i+1]))[0]
                if len(idx) > 0:
                    energy[i] = np.mean(S[idx, :], axis=0)
            energy = np.power(np.maximum(energy, 1e-10), 0.35)
            for i in range(n_points):
                mx = np.max(energy[i])
                if mx > 0:
                    energy[i] /= mx
            from scipy.interpolate import interp1d
            n_frames = int(duration * fps)
            x_old = np.linspace(0, 1, energy.shape[1])
            x_new = np.linspace(0, 1, n_frames)
            self._audio_data = np.zeros((n_frames, n_points))
            for i in range(n_points):
                f = interp1d(x_old, energy[i], kind='linear', fill_value='extrapolate')
                self._audio_data[:, i] = np.clip(f(x_new), 0, 1)
            self._duration = duration
            self._prev_wave = None
        except Exception as e:
            print(f"[WaveVisualizerModule] Error: {e}")

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado or self._audio_data is None:
            return frame
        try:
            h, w = frame.shape[:2]
            fps = kwargs.get('fps', 30)
            fi = min(int(tiempo * fps), len(self._audio_data) - 1)
            wave = self._audio_data[fi].copy()

            sm = self._config.get("smoothing", 0.4)
            if self._prev_wave is not None and sm > 0:
                wave = wave * (1 - sm) + self._prev_wave * sm
            self._prev_wave = wave.copy()

            n = len(wave)
            amplitude = h * self._config["amplitude"]
            center_y = int(h * self._config["pos_y"])
            color = (self._config["color_b"], self._config["color_g"], self._config["color_r"])
            line_w = max(1, self._config["line_width"])

            overlay = frame.copy()

            # Generate points
            xs = np.linspace(0, w, n).astype(int)
            ys_up = (center_y - wave * amplitude).astype(int)

            points_up = np.column_stack([xs, ys_up]).reshape(-1, 1, 2).astype(np.int32)

            # Glow
            if self._config.get("glow", True):
                gs = self._config.get("glow_size", 3)
                glow_color = tuple(int(c * 0.4) for c in color)
                cv2.polylines(overlay, [points_up], False, glow_color, line_w + gs * 2)

            # Main line
            cv2.polylines(overlay, [points_up], False, color, line_w)

            # Fill
            if self._config.get("fill", True):
                fill_points = np.vstack([
                    points_up.reshape(-1, 2),
                    np.array([[w, center_y], [0, center_y]])
                ]).reshape(-1, 1, 2).astype(np.int32)
                fill_overlay = frame.copy()
                cv2.fillPoly(fill_overlay, [fill_points], color)
                fa = self._config.get("fill_alpha", 0.3)
                cv2.addWeighted(fill_overlay, fa, overlay, 1 - fa, 0, overlay)

            # Mirror Y
            if self._config.get("mirror_y", True):
                ys_down = (center_y + wave * amplitude).astype(int)
                points_down = np.column_stack([xs, ys_down]).reshape(-1, 1, 2).astype(np.int32)
                cv2.polylines(overlay, [points_down], False, color, max(1, line_w - 1))
                if self._config.get("fill", True):
                    fill_points_d = np.vstack([
                        np.array([[0, center_y], [w, center_y]]),
                        points_down.reshape(-1, 2)
                    ]).reshape(-1, 1, 2).astype(np.int32)
                    fill_ov2 = overlay.copy()
                    cv2.fillPoly(fill_ov2, [fill_points_d], color)
                    cv2.addWeighted(fill_ov2, fa * 0.5, overlay, 1 - fa * 0.5, 0, overlay)

            alpha = self._config.get("opacity", 0.9)
            return cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
        except Exception as e:
            return frame

    
    def get_config(self):
        """Retorna la configuración actual del módulo."""
        return dict(self._config)
def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Puntos:"))
        n_spin = QSpinBox()
        n_spin.setRange(32, 512)
        n_spin.setValue(self._config["n_points"])
        n_spin.valueChanged.connect(lambda v: self._update_config("n_points", v, app))
        layout.addWidget(n_spin)

        layout.addWidget(QLabel("Amplitud:"))
        amp_slider = QSlider(Qt.Orientation.Horizontal)
        amp_slider.setRange(2, 50)
        amp_slider.setValue(int(self._config["amplitude"] * 100))
        amp_slider.valueChanged.connect(lambda v: self._update_config("amplitude", v / 100.0, app))
        layout.addWidget(amp_slider)

        layout.addWidget(QLabel("Suavizado:"))
        sm_slider = QSlider(Qt.Orientation.Horizontal)
        sm_slider.setRange(0, 95)
        sm_slider.setValue(int(self._config["smoothing"] * 100))
        sm_slider.valueChanged.connect(lambda v: self._update_config("smoothing", v / 100.0, app))
        layout.addWidget(sm_slider)

        fill_cb = QCheckBox("Rellenar")
        fill_cb.setChecked(self._config["fill"])
        fill_cb.toggled.connect(lambda v: self._update_config("fill", v, app))
        layout.addWidget(fill_cb)

        mirror_cb = QCheckBox("Espejo vertical")
        mirror_cb.setChecked(self._config["mirror_y"])
        mirror_cb.toggled.connect(lambda v: self._update_config("mirror_y", v, app))
        layout.addWidget(mirror_cb)

        glow_cb = QCheckBox("Efecto glow")
        glow_cb.setChecked(self._config["glow"])
        glow_cb.toggled.connect(lambda v: self._update_config("glow", v, app))
        layout.addWidget(glow_cb)

        return content
