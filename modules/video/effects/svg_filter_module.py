#!/usr/bin/env python3
"""
Módulo de filtros SVG / efectos de imagen
Inspirado en wav2bar-reborn: SVGFilterProperties

Aplica filtros de procesamiento de imagen avanzados:
- Inversión de colores
- Desaturación
- Sepia
- Posterización
- Aberración cromática
"""

import numpy as np
import cv2

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QSlider, QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt

from modules.core.base import Module


class SVGFilterModule(Module):
    """Filtros de imagen avanzados inspirados en SVG filters."""

    module_type = "video"
    module_category = "effects"
    module_tags = ["filter", "svg", "invert", "sepia", "posterize", "chromatic", "wav2bar"]
    module_version = "1.0.0"
    module_author = "Soundvi (wav2bar-reborn)"

    FILTERS = [
        "none", "invert", "desaturate", "sepia", "posterize",
        "chromatic_aberration", "thermal", "emboss", "sharpen"
    ]

    def __init__(self):
        super().__init__(
            nombre="Filtros SVG (wav2bar)",
            descripcion="Filtros avanzados de imagen inspirados en SVG"
        )
        self._config = {
            "filter_type": "none",
            "intensity": 1.0,
            "audio_reactive": False,
            "posterize_levels": 4,
            "aberration_offset": 5,
        }
        self._audio_energy = None
        self._duration = 0.0

    def prepare_audio(self, audio_path, mel_data, sr, hop, duration, fps):
        if not self._config.get("audio_reactive", False):
            return
        try:
            import librosa
            y, sr = librosa.load(audio_path, sr=22050, mono=True)
            S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
            energy = np.mean(S, axis=0)
            energy = np.power(np.maximum(energy, 1e-10), 0.4)
            mx = np.max(energy)
            if mx > 0:
                energy /= mx
            from scipy.interpolate import interp1d
            n_frames = int(duration * fps)
            x_old = np.linspace(0, 1, len(energy))
            x_new = np.linspace(0, 1, n_frames)
            f = interp1d(x_old, energy, kind='linear', fill_value='extrapolate')
            self._audio_energy = np.clip(f(x_new), 0, 1)
            self._duration = duration
        except Exception as e:
            print(f"[SVGFilterModule] Error preparando audio: {e}")

    def _apply_invert(self, frame, intensity):
        inverted = 255 - frame
        return cv2.addWeighted(inverted, intensity, frame, 1 - intensity, 0)

    def _apply_desaturate(self, frame, intensity):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        return cv2.addWeighted(gray_bgr, intensity, frame, 1 - intensity, 0)

    def _apply_sepia(self, frame, intensity):
        kernel = np.array([
            [0.272, 0.534, 0.131],
            [0.349, 0.686, 0.168],
            [0.393, 0.769, 0.189]
        ])
        sepia = cv2.transform(frame, kernel)
        sepia = np.clip(sepia, 0, 255).astype(np.uint8)
        return cv2.addWeighted(sepia, intensity, frame, 1 - intensity, 0)

    def _apply_posterize(self, frame, intensity):
        levels = max(2, self._config.get("posterize_levels", 4))
        div = 256 // levels
        posterized = (frame // div) * div + div // 2
        posterized = np.clip(posterized, 0, 255).astype(np.uint8)
        return cv2.addWeighted(posterized, intensity, frame, 1 - intensity, 0)

    def _apply_chromatic_aberration(self, frame, intensity):
        offset = int(self._config.get("aberration_offset", 5) * intensity)
        if offset < 1:
            return frame
        result = frame.copy()
        h, w = frame.shape[:2]
        # Shift red channel right, blue left
        result[:, offset:, 2] = frame[:, :w-offset, 2]  # Red
        result[:, :w-offset, 0] = frame[:, offset:, 0]   # Blue
        return result

    def _apply_thermal(self, frame, intensity):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        thermal = cv2.applyColorMap(gray, cv2.COLORMAP_JET)
        return cv2.addWeighted(thermal, intensity, frame, 1 - intensity, 0)

    def _apply_emboss(self, frame, intensity):
        kernel = np.array([[-2, -1, 0], [-1, 1, 1], [0, 1, 2]])
        embossed = cv2.filter2D(frame, -1, kernel) + 128
        embossed = np.clip(embossed, 0, 255).astype(np.uint8)
        return cv2.addWeighted(embossed, intensity, frame, 1 - intensity, 0)

    def _apply_sharpen(self, frame, intensity):
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        sharpened = cv2.filter2D(frame, -1, kernel)
        return cv2.addWeighted(sharpened, intensity, frame, 1 - intensity, 0)

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado:
            return frame
        try:
            filter_type = self._config.get("filter_type", "none")
            if filter_type == "none":
                return frame

            intensity = self._config.get("intensity", 1.0)

            # Audio-reactive intensity
            if self._config.get("audio_reactive", False) and self._audio_energy is not None:
                fps = kwargs.get('fps', 30)
                fi = min(int(tiempo * fps), len(self._audio_energy) - 1)
                intensity *= self._audio_energy[fi]

            filters = {
                "invert": self._apply_invert,
                "desaturate": self._apply_desaturate,
                "sepia": self._apply_sepia,
                "posterize": self._apply_posterize,
                "chromatic_aberration": self._apply_chromatic_aberration,
                "thermal": self._apply_thermal,
                "emboss": self._apply_emboss,
                "sharpen": self._apply_sharpen,
            }

            apply_fn = filters.get(filter_type)
            if apply_fn:
                return apply_fn(frame, intensity)
            return frame
        except Exception as e:
            return frame

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Filtro:"))
        filter_combo = QComboBox()
        filter_combo.addItems(self.FILTERS)
        filter_combo.setCurrentText(self._config["filter_type"])
        filter_combo.currentTextChanged.connect(lambda v: self._update_config("filter_type", v, app))
        layout.addWidget(filter_combo)

        layout.addWidget(QLabel("Intensidad:"))
        int_slider = QSlider(Qt.Orientation.Horizontal)
        int_slider.setRange(0, 100)
        int_slider.setValue(int(self._config["intensity"] * 100))
        int_slider.valueChanged.connect(lambda v: self._update_config("intensity", v / 100.0, app))
        layout.addWidget(int_slider)

        reactive_cb = QCheckBox("Reactivo al audio")
        reactive_cb.setChecked(self._config["audio_reactive"])
        reactive_cb.toggled.connect(lambda v: self._update_config("audio_reactive", v, app))
        layout.addWidget(reactive_cb)

        return content
