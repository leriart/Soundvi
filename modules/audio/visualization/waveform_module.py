#!/usr/bin/env python3
"""
Módulo de forma de onda (Waveform)
Visualiza el audio como una forma de onda clásica.
"""

import numpy as np
import cv2

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QSlider, QCheckBox, QSpinBox, QGroupBox,
    QHBoxLayout, QComboBox
)
from PyQt6.QtCore import Qt

from modules.core.base import Module


class WaveformModule(Module):
    """Visualizador de forma de onda clásica."""

    module_type = "audio"
    module_category = "visualization"
    module_tags = ["waveform", "audio", "classic", "line"]
    module_version = "1.0.0"
    module_author = "Soundvi"

    def __init__(self):
        super().__init__("Waveform")
        self._config = {
            "mode": "line",
            "mirror": False,
            "invert": False,
            "response": 0.5,
            "gravity": 0.5,
            "inertia": 0.5,
            "smoothing": 0.5,
            "glow_intensity": 0.0,
            "corner_radius": 0.0,
            "shadow_enabled": False,
            "gradient_enabled": False,
            "num_bars": 128,
            "pos_x": 0.5,
            "pos_y": 0.5,
            "scale_y": 1.0,
            "scale_x": 1.0,
            "rotation": 0.0,
            "opacity": 1.0,
            "color": [255, 255, 255],
            "color2": [0, 150, 255],
            "color3": [255, 100, 0],
            "color4": [100, 255, 100],
            "color5": [255, 255, 0]
        }
        self.engine = None
        self._audio_data = None
        self._sample_rate = None
        self._audio_duration = 0.0

    def get_config(self):
        """Retorna la configuración actual del módulo."""
        return dict(self._config)

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        # Modo
        layout.addWidget(QLabel("Modo:"))
        mode_combo = QComboBox()
        mode_combo.addItems(["line", "bars", "filled"])
        mode_combo.setCurrentText(self._config["mode"])
        mode_combo.currentTextChanged.connect(lambda t: self._update_config("mode", t, app))
        layout.addWidget(mode_combo)

        # Número de barras
        layout.addWidget(QLabel("Número de barras:"))
        bars_spin = QSpinBox()
        bars_spin.setRange(32, 512)
        bars_spin.setValue(self._config["num_bars"])
        bars_spin.valueChanged.connect(lambda v: self._update_config("num_bars", v, app))
        layout.addWidget(bars_spin)

        # Opciones booleanas
        mirror_cb = QCheckBox("Espejo")
        mirror_cb.setChecked(self._config["mirror"])
        mirror_cb.stateChanged.connect(lambda s: self._update_config("mirror", bool(s), app))
        layout.addWidget(mirror_cb)

        invert_cb = QCheckBox("Invertir")
        invert_cb.setChecked(self._config["invert"])
        invert_cb.stateChanged.connect(lambda s: self._update_config("invert", bool(s), app))
        layout.addWidget(invert_cb)

        # Grupo de física
        physics_group = QGroupBox("Física")
        pgl = QVBoxLayout(physics_group)

        for label_text, key, lo, hi in [
            ("Respuesta", "response", 0, 100),
            ("Gravedad", "gravity", 0, 100),
            ("Inercia", "inertia", 0, 100),
            ("Suavizado", "smoothing", 0, 100)
        ]:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.addWidget(QLabel(f"{label_text}:"))
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(lo, hi)
            slider.setValue(int(self._config.get(key, 0.5) * 100))
            slider.valueChanged.connect(lambda v, k=key: self._update_config(k, v / 100.0, app))
            rl.addWidget(slider)
            pgl.addWidget(row)

        layout.addWidget(physics_group)

        return content

    def _update_config(self, key: str, value, app):
        super()._update_config(key, value, app)
        if self.engine is not None:
            config_map = {
                "mode": "mode", "mirror": "mirror", "invert": "invert",
                "response": "response", "gravity": "gravity", "inertia": "inertia",
                "smoothing": "smoothing", "glow_intensity": "glow_intensity",
                "corner_radius": "corner_radius", "shadow_enabled": "shadow_enabled",
                "gradient_enabled": "gradient_enabled", "num_bars": "num_bars",
                "pos_x": "pos_x", "pos_y": "pos_y", "scale_y": "scale_y",
                "scale_x": "scale_x", "rotation": "rotation", "opacity": "opacity",
                "color": "color", "color2": "color2", "color3": "color3",
                "color4": "color4", "color5": "color5"
            }
            if key in config_map:
                setattr(self.engine, config_map[key], value)

    def render(self, frame, tiempo, **kwargs):
        # Obtener audio_data de kwargs si está disponible, sino usar self._audio_data
        audio_data = kwargs.get('audio_data', self._audio_data)
        fps = kwargs.get('fps', 30)
        
        if audio_data is None or len(audio_data) == 0:
            return frame

        height, width = frame.shape[:2]
        
        # Crear una copia del frame
        result = frame.copy()
        
        # Normalizar audio
        audio_norm = audio_data / np.max(np.abs(audio_data)) if np.max(np.abs(audio_data)) > 0 else audio_data
        
        # Calcular forma de onda
        if self._config["mode"] == "bars":
            # Modo barras
            num_bars = self._config["num_bars"]
            bar_width = width // num_bars
            
            for i in range(num_bars):
                if i < len(audio_norm):
                    bar_height = int(abs(audio_norm[i]) * height * 0.4)
                    x = i * bar_width
                    y = height // 2 - bar_height // 2
                    
                    color = tuple(map(int, self._config["color"]))
                    cv2.rectangle(result, (x, y), (x + bar_width - 1, y + bar_height), color, -1)
        
        elif self._config["mode"] == "filled":
            # Modo relleno
            points = []
            for i in range(width):
                idx = min(int(i / width * len(audio_norm)), len(audio_norm) - 1)
                y = int(height // 2 - audio_norm[idx] * height * 0.4)
                points.append((i, y))
            
            if len(points) > 1:
                pts = np.array(points, np.int32)
                pts = pts.reshape((-1, 1, 2))
                
                # Rellenar
                color = tuple(map(int, self._config["color"]))
                cv2.fillPoly(result, [pts], color)
        
        else:
            # Modo línea (default)
            points = []
            for i in range(width):
                idx = min(int(i / width * len(audio_norm)), len(audio_norm) - 1)
                y = int(height // 2 - audio_norm[idx] * height * 0.4)
                points.append((i, y))
            
            if len(points) > 1:
                color = tuple(map(int, self._config["color"]))
                thickness = 2
                for i in range(len(points) - 1):
                    cv2.line(result, points[i], points[i + 1], color, thickness)
        
        return result

    def prepare_audio(self, audio_path, mel_data=None, sr=None, hop=None, duration=None, fps=None, **kwargs):
        """Prepara el audio para el renderizado."""
        try:
            import librosa
            offset = kwargs.get('audio_offset', 0.0)
            
            if audio_path:
                # Cargar audio desde archivo
                y, sr = librosa.load(audio_path, sr=22050, mono=True, offset=offset, duration=duration)
                self._audio_data = y
                self._sample_rate = sr
                self._audio_duration = duration if duration else librosa.get_duration(y=y, sr=sr)
                print(f"DEBUG_WAVEFORM: Audio loaded, duration={self._audio_duration:.2f}s, samples={len(y)}")
            else:
                # No hay archivo de audio, usar datos de mel si están disponibles
                self._audio_data = None
                self._sample_rate = sr
                self._audio_duration = duration if duration else 0.0
                
        except Exception as e:
            print(f"ERROR_WAVEFORM: Failed to prepare audio: {e}")
            self._audio_data = None
            self._sample_rate = None
            self._audio_duration = 0.0
