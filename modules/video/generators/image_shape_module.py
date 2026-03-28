#!/usr/bin/env python3
"""
Módulo de imagen/forma (Image Shape)
Inspirado en wav2bar-reborn: vo_image_shape

Permite colocar imágenes que reaccionan al audio (escala, rotación, opacidad).
"""

import numpy as np
import cv2
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QCheckBox, QFileDialog
)
from PyQt6.QtCore import Qt

from modules.core.base import Module


class ImageShapeModule(Module):
    """Imagen decorativa con reactividad al audio."""

    module_type = "video"
    module_category = "generators"
    module_tags = ["image", "shape", "cover", "wav2bar", "artwork"]
    module_version = "1.0.0"
    module_author = "Soundvi (wav2bar-reborn)"

    def __init__(self):
        super().__init__(
            nombre="Imagen/Forma (wav2bar)",
            descripcion="Imagen con reactividad al audio"
        )
        self._image = None
        self._image_path = ""
        self._audio_energy = None
        self._duration = 0.0
        self._config = {
            "image_path": "",
            "pos_x": 0.5,
            "pos_y": 0.5,
            "scale": 0.3,
            "opacity": 1.0,
            "audio_reactive": True,
            "scale_reactivity": 0.1,
            "rotation_reactivity": 0.0,
            "opacity_reactivity": 0.0,
            "shadow": True,
            "shadow_blur": 15,
            "circular_mask": False,
        }

    def _load_image(self, path):
        if path and os.path.exists(path):
            img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            if img is not None:
                self._image = img
                self._image_path = path
                self._config["image_path"] = path
                return True
        return False

    def prepare_audio(self, audio_path, mel_data, sr, hop, duration, fps):
        if not self._config.get("audio_reactive", True):
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
            print(f"[ImageShapeModule] Error: {e}")

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado or self._image is None:
            return frame
        try:
            h, w = frame.shape[:2]
            fps = kwargs.get('fps', 30)

            # Audio energy
            energy = 0.0
            if self._audio_energy is not None:
                fi = min(int(tiempo * fps), len(self._audio_energy) - 1)
                energy = self._audio_energy[fi]

            # Calculate scale with audio reactivity
            base_scale = self._config["scale"]
            if self._config.get("audio_reactive", True):
                sr = self._config.get("scale_reactivity", 0.1)
                base_scale += energy * sr

            # Resize image
            img = self._image
            img_h, img_w = img.shape[:2]
            target_w = int(w * base_scale)
            target_h = int(target_w * img_h / img_w)
            if target_w < 1 or target_h < 1:
                return frame
            resized = cv2.resize(img, (target_w, target_h), interpolation=cv2.INTER_AREA)

            # Position
            px = int(w * self._config["pos_x"] - target_w / 2)
            py = int(h * self._config["pos_y"] - target_h / 2)

            # Circular mask
            if self._config.get("circular_mask", False):
                mask = np.zeros((target_h, target_w), dtype=np.uint8)
                cx, cy = target_w // 2, target_h // 2
                r = min(cx, cy)
                cv2.circle(mask, (cx, cy), r, 255, -1)
                if resized.shape[2] == 4:
                    resized[:, :, 3] = cv2.bitwise_and(resized[:, :, 3], mask)
                else:
                    resized_rgba = cv2.cvtColor(resized, cv2.COLOR_BGR2BGRA)
                    resized_rgba[:, :, 3] = mask
                    resized = resized_rgba

            # Blend onto frame
            result = frame.copy()
            opacity = self._config.get("opacity", 1.0)
            if self._config.get("audio_reactive") and self._config.get("opacity_reactivity", 0) > 0:
                opacity = max(0.1, opacity - (1 - energy) * self._config["opacity_reactivity"])

            # Calculate valid region
            x1, y1 = max(0, px), max(0, py)
            x2, y2 = min(w, px + target_w), min(h, py + target_h)
            sx1, sy1 = x1 - px, y1 - py
            sx2, sy2 = sx1 + (x2 - x1), sy1 + (y2 - y1)

            if x2 <= x1 or y2 <= y1:
                return frame

            roi = resized[sy1:sy2, sx1:sx2]
            if roi.shape[2] == 4:
                alpha_mask = roi[:, :, 3].astype(float) / 255.0 * opacity
                for c in range(3):
                    result[y1:y2, x1:x2, c] = (
                        roi[:, :, c] * alpha_mask +
                        result[y1:y2, x1:x2, c] * (1 - alpha_mask)
                    ).astype(np.uint8)
            else:
                cv2.addWeighted(roi[:, :, :3], opacity, result[y1:y2, x1:x2], 1 - opacity, 0, result[y1:y2, x1:x2])

            return result
        except Exception as e:
            return frame

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        # Image selector
        row = QHBoxLayout()
        row.addWidget(QLabel("Imagen:"))
        load_btn = QPushButton("Cargar imagen...")
        def load_image():
            path, _ = QFileDialog.getOpenFileName(
                parent, "Seleccionar imagen", "",
                "Imágenes (*.png *.jpg *.jpeg *.bmp *.webp);;Todos (*)"
            )
            if path:
                self._load_image(path)
                self._update_config("image_path", path, app)
        load_btn.clicked.connect(load_image)
        row.addWidget(load_btn)
        layout.addLayout(row)

        # Scale
        layout.addWidget(QLabel("Escala:"))
        scale_slider = QSlider(Qt.Orientation.Horizontal)
        scale_slider.setRange(5, 80)
        scale_slider.setValue(int(self._config["scale"] * 100))
        scale_slider.valueChanged.connect(lambda v: self._update_config("scale", v / 100.0, app))
        layout.addWidget(scale_slider)

        # Audio reactive
        reactive_cb = QCheckBox("Reactivo al audio")
        reactive_cb.setChecked(self._config["audio_reactive"])
        reactive_cb.toggled.connect(lambda v: self._update_config("audio_reactive", v, app))
        layout.addWidget(reactive_cb)

        # Circular mask
        circ_cb = QCheckBox("Máscara circular")
        circ_cb.setChecked(self._config["circular_mask"])
        circ_cb.toggled.connect(lambda v: self._update_config("circular_mask", v, app))
        layout.addWidget(circ_cb)

        return content
