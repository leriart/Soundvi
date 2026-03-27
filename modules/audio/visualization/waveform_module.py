#!/usr/bin/env python3
"""
Módulo de visualización de waveform para Soundvi.
Categorizado: audio/visualization
"""

import numpy as np
import cv2

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QComboBox, QCheckBox, QGroupBox, QSpinBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt

from modules.core.base import Module


class WaveformModule(Module):
    """Visualizador de audio con física avanzada estilo Wav2Bar."""

    module_type = "audio"
    module_category = "visualization"
    module_tags = ["waveform", "audio", "visualization", "basic", "bars", "classic"]
    module_version = "2.0.0"
    module_author = "Soundvi Team"

    def __init__(self):
        super().__init__(
            nombre="Forma de Onda",
            descripcion="Visualización clásica de forma de onda de audio"
        )
        self.app = None
        self.engine = None
        self._config = {
            "mode": "bars", "mirror": True, "invert": False,
            "physics_enabled": True, "gravity": 0.2, "inertia": 0.8,
            "response": 0.5, "smoothing": 0.3, "glow_intensity": 0.0,
            "corner_radius": 2, "num_bars": 64,
            "bar_color_r": 255, "bar_color_g": 255, "bar_color_b": 255,
            "opacity": 1.0, "height_ratio": 0.6, "width_ratio": 0.98,
            "spacing_ratio": 0.1, "shadow_enabled": True, "gradient_enabled": False,
            "pos_x": 0.5, "pos_y": 0.9, "scale_y": 0.6,
            "bar_width_ratio": 0.98,
        }

    def prepare_audio(self, audio_path, mel_data, sr, hop, duration, fps):
        try:
            from core.wav2bar_engine import Wav2BarEngine
            if self.engine is None:
                self.engine = Wav2BarEngine(num_bars=64, framerate=fps, width=1280, height=720)
            bgr_color = (
                self._config.get("bar_color_b", 255),
                self._config.get("bar_color_g", 255),
                self._config.get("bar_color_r", 255)
            )
            self.engine.set_config(
                mode=self._config.get("mode", "bars"),
                mirror=self._config.get("mirror", True),
                invert=self._config.get("invert", False),
                response=self._config.get("response", 0.5),
                gravity=self._config.get("gravity", 0.2),
                inertia=self._config.get("inertia", 0.8),
                smoothing=self._config.get("smoothing", 0.3),
                color=bgr_color,
                glow_intensity=self._config.get("glow_intensity", 0.0),
                corner_radius=self._config.get("corner_radius", 2),
                shadow_enabled=self._config.get("shadow_enabled", True),
                gradient_enabled=self._config.get("gradient_enabled", False),
                num_bars=self._config.get("num_bars", 64),
                pos_x=self._config.get("pos_x", 0.5),
                pos_y=self._config.get("pos_y", 0.9),
                scale_y=self._config.get("scale_y", 0.6),
                bar_width_ratio=self._config.get("bar_width_ratio", 0.98),
                spacing_ratio=self._config.get("spacing_ratio", 0.1)
            )
            self.engine.load_audio(audio_path)
        except Exception as e:
            print(f"[WaveformModule] Error preparando audio: {e}")

    def render(self, frame: np.ndarray, tiempo: float, **kwargs) -> np.ndarray:
        if not self.habilitado or self.engine is None or not self.engine.is_ready():
            return frame
        try:
            height, width = frame.shape[:2]
            if self.engine.width != width or self.engine.height != height:
                self.engine.width = width
                self.engine.height = height
                self.engine._update_layout()
            fps = kwargs.get('fps', 30)
            frame_index = min(int(tiempo * fps), self.engine.total_frames - 1)
            rendered = self.engine.render_frame(frame_index, frame)
            opacity = self._config["opacity"]
            if opacity < 1.0:
                return cv2.addWeighted(frame, 1.0 - opacity, rendered, opacity, 0)
            return rendered
        except Exception as e:
            print(f"[WaveformModule] Error en render: {e}")
            return frame

    def get_config_widgets(self, parent, app):
        self.app = app
        _as = app
        content = QWidget(parent)
        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Color picker
        r = self._config.get("bar_color_r", 255)
        g = self._config.get("bar_color_g", 255)
        b = self._config.get("bar_color_b", 255)
        current_hex = f"#{r:02x}{g:02x}{b:02x}"
        color_picker = self.create_color_picker(content, current_hex, app, "Color:")

        def update_color(hex_val):
            if hex_val and hex_val.startswith('#') and len(hex_val) == 7:
                try:
                    self._update_config("bar_color_r", int(hex_val[1:3], 16), _as)
                    self._update_config("bar_color_g", int(hex_val[3:5], 16), _as)
                    self._update_config("bar_color_b", int(hex_val[5:7], 16), _as)
                except ValueError: pass
        color_picker.on_color_change(update_color)
        main_layout.addWidget(color_picker)

        # Mode
        mode_row = QWidget()
        mrl = QHBoxLayout(mode_row)
        mrl.setContentsMargins(0, 0, 0, 0)
        mrl.addWidget(QLabel("Modo:"))
        mode_combo = QComboBox()
        mode_combo.addItems(["bars", "waveform", "particles", "spectrum"])
        mode_combo.setCurrentText(self._config.get("mode", "bars"))
        mode_combo.currentTextChanged.connect(lambda v: self._update_config("mode", v, _as))
        mrl.addWidget(mode_combo)
        main_layout.addWidget(mode_row)

        # Options
        opt_row = QWidget()
        orl = QHBoxLayout(opt_row)
        orl.setContentsMargins(0, 0, 0, 0)
        mirror_check = QCheckBox("Espejo")
        mirror_check.setChecked(self._config.get("mirror", True))
        mirror_check.toggled.connect(lambda v: self._update_config("mirror", v, _as))
        orl.addWidget(mirror_check)
        invert_check = QCheckBox("Invertir")
        invert_check.setChecked(self._config.get("invert", False))
        invert_check.toggled.connect(lambda v: self._update_config("invert", v, _as))
        orl.addWidget(invert_check)
        main_layout.addWidget(opt_row)

        # Visual style group
        style_group = QGroupBox("Estilo Visual")
        sgl = QVBoxLayout(style_group)

        vis_row = QWidget()
        vrl = QHBoxLayout(vis_row)
        vrl.setContentsMargins(0, 0, 0, 0)
        shadow_check = QCheckBox("Sombra")
        shadow_check.setChecked(self._config.get("shadow_enabled", True))
        shadow_check.toggled.connect(lambda v: self._update_config("shadow_enabled", v, _as))
        vrl.addWidget(shadow_check)
        grad_check = QCheckBox("Gradiente")
        grad_check.setChecked(self._config.get("gradient_enabled", False))
        grad_check.toggled.connect(lambda v: self._update_config("gradient_enabled", v, _as))
        vrl.addWidget(grad_check)
        sgl.addWidget(vis_row)

        # Bars count
        num_row = QWidget()
        nrl = QHBoxLayout(num_row)
        nrl.setContentsMargins(0, 0, 0, 0)
        nrl.addWidget(QLabel("N\u00ba Barras:"))
        num_spin = QSpinBox()
        num_spin.setRange(8, 256)
        num_spin.setValue(self._config.get("num_bars", 64))
        num_spin.valueChanged.connect(lambda v: self._update_config("num_bars", v, _as))
        nrl.addWidget(num_spin)
        sgl.addWidget(num_row)
        main_layout.addWidget(style_group)

        # Physics group
        physics_group = QGroupBox("Física")
        pgl = QVBoxLayout(physics_group)
        for label_text, key, lo, hi in [("Sensibilidad", "response", 1, 100), ("Gravedad", "gravity", 1, 500)]:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.addWidget(QLabel(f"{label_text}:"))
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(lo, hi)
            slider.setValue(int(self._config.get(key, 0.5) * 100))
            slider.valueChanged.connect(lambda v, k=key: self._update_config(k, v / 100.0, _as))
            rl.addWidget(slider)
            pgl.addWidget(row)
        main_layout.addWidget(physics_group)

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
                "bar_width_ratio": "bar_width_ratio", "spacing_ratio": "spacing_ratio"
            }
            if key in config_map:
                self.engine.set_config(**{config_map[key]: value})
            elif key in ("bar_color_r", "bar_color_g", "bar_color_b"):
                r = self._config.get("bar_color_r", 255)
                g = self._config.get("bar_color_g", 255)
                b = self._config.get("bar_color_b", 255)
                self.engine.set_config(color=(b, g, r))
