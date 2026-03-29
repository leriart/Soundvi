#!/usr/bin/env python3
"""
Módulo de waveform recto inspirado en wav2bar-reborn: visualizer_straight_wave

Implementa un visualizador de waveform continuo con:
- Línea suave que sigue el espectro de audio
- Física realista
- Efectos visuales (brillo, sombras)
- Configuración en tiempo real
"""

import numpy as np
import cv2
from typing import Optional, Tuple, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QSpinBox, QComboBox, QCheckBox, QDoubleSpinBox, QGroupBox
)
from PyQt6.QtCore import Qt

from modules.base import Module
from .wav2bar_base import Wav2BarBase, Wav2BarConfig


class Wav2BarStraightWaveModule(Module):
    """
    Visualizador de waveform recto estilo wav2bar-reborn.
    
    Corresponde a visualizer_straight_wave en wav2bar-reborn.
    """
    
    module_type = "audio"
    module_category = "visualization"
    module_tags = ["wav2bar", "straight_wave", "waveform", "spectrum", "visualizer"]
    module_version = "2.0.0"
    module_author = "Soundvi (basado en wav2bar-reborn)"
    
    def __init__(self):
        super().__init__(
            nombre="Wav2Bar: Waveform Recto",
            descripcion="Visualizador de waveform continuo con física avanzada (wav2bar-reborn)"
        )
        
        # Configuración específica de waveform
        self.config = Wav2BarConfig(
            num_bars=128,  # Más barras para waveform suave
            scale_y=0.3,
            pos_y=0.5,
            smoothing=0.5,  # Más suavizado para waveform
            response=0.7,   # Respuesta más rápida
            bar_width_ratio=1.0,  # Usar todo el ancho
            spacing_ratio=0.0     # Sin espacio
        )
        
        # Motor wav2bar
        self.engine = Wav2BarBase(self.config)
        
        # Configuración del módulo
        self._config = {
            "n_points": self.config.num_bars,
            "line_width": 3,
            "height_ratio": self.config.scale_y,
            "pos_y": self.config.pos_y,
            "opacity": self.config.opacity,
            "smoothing": self.config.smoothing,
            "gravity": self.config.gravity,
            "inertia": self.config.inertia,
            "response": self.config.response,
            "mirror": self.config.mirror,
            "invert": self.config.invert,
            "color_r": self.config.color[0],
            "color_g": self.config.color[1],
            "color_b": self.config.color[2],
            "glow_intensity": self.config.glow_intensity,
            "shadow_enabled": self.config.shadow_enabled,
            "fill_enabled": True,
            "fill_opacity": 0.3,
            "low_freq": self.config.low_freq,
            "high_freq": self.config.high_freq,
            "gamma": self.config.gamma,
        }
    
    def prepare_audio(self, audio_path, mel_data, sr, hop, duration, fps):
        """Prepara el módulo con datos de audio."""
        try:
            self.engine.load_audio(audio_path, fps)
            print(f"[Wav2BarStraightWave] Audio preparado: {duration:.2f}s, {fps} FPS")
        except Exception as e:
            print(f"[Wav2BarStraightWave] Error preparando audio: {e}")
    
    def render(self, frame: np.ndarray, tiempo: float, **kwargs) -> np.ndarray:
        """Renderiza el visualizador en el frame."""
        if not self.habilitado or not self.engine.is_ready():
            return frame
        
        try:
            fps = kwargs.get('fps', 30)
            frame_index = min(int(tiempo * fps), self.engine.total_frames - 1)
            
            # Obtener alturas actuales
            heights = self.engine.get_heights(frame_index)
            
            # Renderizar waveform
            rendered = self._render_waveform(frame, heights)
            
            # Aplicar opacidad
            opacity = self._config["opacity"]
            if opacity < 1.0:
                blended = cv2.addWeighted(frame, 1.0 - opacity,
                                        rendered, opacity, 0)
                return blended
            
            return rendered
            
        except Exception as e:
            print(f"[Wav2BarStraightWave] Error en render: {e}")
            return frame
    
    def _render_waveform(self, frame: np.ndarray, heights: np.ndarray) -> np.ndarray:
        """Renderiza waveform en el frame."""
        height, width = frame.shape[:2]
        output = frame.copy()
        
        # Calcular puntos
        n_points = len(heights)
        max_h = height * self._config["height_ratio"]
        center_y = int(height * self._config["pos_y"])
        
        # Crear puntos para la línea
        points = []
        for i, h in enumerate(heights):
            x = int((i / (n_points - 1)) * width) if n_points > 1 else width // 2
            y = center_y - (h - 0.5) * max_h * 2  # Centrado en 0.5
            points.append((x, int(y)))
        
        # Modo espejo
        if self._config["mirror"]:
            mirrored_points = []
            for x, y in points:
                mirrored_x = width - x
                mirrored_points.append((mirrored_x, y))
            points = mirrored_points[::-1] + points
        
        # Rellenar si está activado
        if self._config["fill_enabled"] and len(points) >= 2:
            fill_points = points.copy()
            fill_points.append((points[-1][0], center_y))
            fill_points.append((points[0][0], center_y))
            
            fill_layer = output.copy()
            pts_array = np.array(fill_points, dtype=np.int32)
            fill_color = (
                int(self._config["color_b"]),
                int(self._config["color_g"]),
                int(self._config["color_r"])
            )
            cv2.fillPoly(fill_layer, [pts_array], fill_color)
            
            # Aplicar opacidad de relleno
            fill_opacity = self._config["fill_opacity"]
            cv2.addWeighted(fill_layer, fill_opacity, output,
                          1 - fill_opacity, 0, output)
        
        # Dibujar línea
        if len(points) >= 2:
            line_color = (
                int(self._config["color_b"]),
                int(self._config["color_g"]),
                int(self._config["color_r"])
            )
            line_width = self._config["line_width"]
            
            # Dibujar línea suave
            pts_array = np.array(points, dtype=np.int32)
            cv2.polylines(output, [pts_array], False, line_color, line_width)
            
            # Sombra si está activada
            if self._config["shadow_enabled"]:
                shadow_color = tuple(max(0, c - 40) for c in line_color)
                shadow_points = [(x, y + 2) for x, y in points]
                shadow_array = np.array(shadow_points, dtype=np.int32)
                cv2.polylines(output, [shadow_array], False, shadow_color, line_width)
            
            # Brillo/glow si está activado
            if self._config["glow_intensity"] > 0:
                glow_color = tuple(min(255, c + 50) for c in line_color)
                glow_alpha = self._config["glow_intensity"]
                glow_layer = output.copy()
                cv2.polylines(glow_layer, [pts_array], False, glow_color, line_width + 2)
                cv2.addWeighted(glow_layer, glow_alpha, output,
                              1 - glow_alpha, 0, output)
        
        return output
    
    def get_config_widgets(self, parent, app):
        """Crea widgets de configuración para el sidebar."""
        self.app = app
        _as = app
        
        content = QWidget(parent)
        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # === CONFIGURACIÓN DE AUDIO ===
        audio_group = QGroupBox("Procesamiento de Audio")
        agl = QVBoxLayout(audio_group)
        
        # Número de puntos
        points_row = QWidget()
        prl = QHBoxLayout(points_row)
        prl.setContentsMargins(0, 0, 0, 0)
        prl.addWidget(QLabel("Nº Puntos:"))
        points_spin = QSpinBox()
        points_spin.setRange(32, 512)
        points_spin.setValue(self._config["n_points"])
        points_spin.valueChanged.connect(lambda v: self._update_config("n_points", v, _as))
        prl.addWidget(points_spin)
        agl.addWidget(points_row)
        
        # Rango de frecuencias
        freq_row = QWidget()
        frl = QHBoxLayout(freq_row)
        frl.setContentsMargins(0, 0, 0, 0)
        frl.addWidget(QLabel("Freq Baja:"))
        low_freq = QDoubleSpinBox()
        low_freq.setRange(20, 20000)
        low_freq.setValue(self._config["low_freq"])
        low_freq.setSuffix(" Hz")
        low_freq.valueChanged.connect(lambda v: self._update_config("low_freq", v, _as))
        frl.addWidget(low_freq)
        frl.addWidget(QLabel("Freq Alta:"))
        high_freq = QDoubleSpinBox()
        high_freq.setRange(20, 20000)
        high_freq.setValue(self._config["high_freq"])
        high_freq.setSuffix(" Hz")
        high_freq.valueChanged.connect(lambda v: self._update_config("high_freq", v, _as))
        frl.addWidget(high_freq)
        agl.addWidget(freq_row)
        
        main_layout.addWidget(audio_group)
        
        # === OPCIONES DE VISUALIZACIÓN ===
        vis_group = QGroupBox("Opciones Visuales")
        vgl = QVBoxLayout(vis_group)
        
        # Espejo e Invertir
        options_row = QWidget()
        orl = QHBoxLayout(options_row)
        orl.setContentsMargins(0, 0, 0, 0)
        mirror_check = QCheckBox("Espejo")
        mirror_check.setChecked(self._config["mirror"])
        mirror_check.toggled.connect(lambda v: self._update_config("mirror", v, _as))
        orl.addWidget(mirror_check)
        invert_check = QCheckBox("Invertir")
        invert_check.setChecked(self._config["invert"])
        invert_check.toggled.connect(lambda v: self._update_config("invert", v, _as))
        orl.addWidget(invert_check)
        vgl.addWidget(options_row)
        
        # Transparencia
        opacity_row = QWidget()
        oprl = QHBoxLayout(opacity_row)
        oprl.setContentsMargins(0, 0, 0, 0)
        oprl.addWidget(QLabel("Transparencia:"))
        opacity_slider = QSlider(Qt.Orientation.Horizontal)
        opacity_slider.setRange(0, 100)
        opacity_slider.setValue(int(self._config["opacity"] * 100))
        opacity_label = QLabel(f"{self._config['opacity']:.2f}")
        def on_opacity(v):
            val = v / 100.0
            self._update_config("opacity", val, _as)
            opacity_label.setText(f"{val:.2f}")
        opacity_slider.valueChanged.connect(on_opacity)
        oprl.addWidget(opacity_slider)
        oprl.addWidget(opacity_label)
        vgl.addWidget(opacity_row)
        
        # Grosor de línea
        width_row = QWidget()
        wrl = QHBoxLayout(width_row)
        wrl.setContentsMargins(0, 0, 0, 0)
        wrl.addWidget(QLabel("Grosor:"))
        width_spin = QSpinBox()
        width_spin.setRange(1, 10)
        width_spin.setValue(self._config["line_width"])
        width_spin.valueChanged.connect(lambda v: self._update_config("line_width", v, _as))
        wrl.addWidget(width_spin)
        vgl.addWidget(width_row)
        
        # Relleno
        fill_row = QWidget()
        frl2 = QHBoxLayout(fill_row)
        frl2.setContentsMargins(0, 0, 0, 0)
        fill_check = QCheckBox("Rellenar")
        fill_check.setChecked(self._config["fill_enabled"])
        fill_check.toggled.connect(lambda v: self._update_config("fill_enabled", v, _as))
        frl2.addWidget(fill_check)
        frl2.addWidget(QLabel("Opacidad:"))
        fill_opacity = QDoubleSpinBox()
        fill_opacity.setRange(0.0, 1.0)
        fill_opacity.setSingleStep(0.1)
        fill_opacity.setValue(self._config["fill_opacity"])
        fill_opacity.valueChanged.connect(lambda v: self._update_config("fill_opacity", v, _as))
        frl2.addWidget(fill_opacity)
        vgl.addWidget(fill_row)
        
        main_layout.addWidget(vis_group)
        
        # === PARÁMETROS FÍSICOS ===
        physics_group = QGroupBox("Física")
        pgl = QVBoxLayout(physics_group)
        
        # Respuesta
        response_row = QWidget()
        rrl = QHBoxLayout(response_row)
        rrl.setContentsMargins(0, 0, 0, 0)
        rrl.addWidget(QLabel("Respuesta:"))
        response_slider = QSlider(Qt.Orientation.Horizontal)
        response_slider.setRange(1, 100)
        response_slider.setValue(int(self._config["response"] * 100))
        response_label = QLabel(f"{self._config['response']:.2f}")
        def on_response(v):
            val = v / 100.0
            self._update_config("response", val, _as)
            response_label.setText(f"{val:.2f}")
        response_slider.valueChanged.connect(on_response)
        rrl.addWidget(response_slider)
        rrl.addWidget(response_label)
        pgl.addWidget(response_row)
        
        # Suavizado
        smooth_row = QWidget()
        srl = QHBoxLayout(smooth_row)
        srl.setContentsMargins(0, 0, 0, 0)
        srl.addWidget(QLabel("Suavizado:"))
        smooth_slider = QSlider(Qt.Orientation.Horizontal)
        smooth_slider.setRange(0, 100)
        smooth_slider.setValue(int(self._config["smoothing"] * 100))
        smooth_label = QLabel(f"{self._config['smoothing']:.2f}")
        def on_smooth(v):
            val = v / 100.0
            self._update_config("smoothing", val, _as)
            smooth_label.setText(f"{val:.2f}")
        smooth_slider.valueChanged.connect(on_smooth)
        srl.addWidget(smooth_slider)
        srl.addWidget(smooth_label)
        pgl.addWidget(smooth_row)
        
        main_layout.addWidget(physics_group)
        
        return content
    
    def _update_config(self, key: str, value, app):
        """Actualiza la configuración y propaga al motor."""
        super()._update_config(key, value, app)
        
        # Mapear configuraciones al motor
        config_map = {
            "n_points": "num_bars",
            "height_ratio": "scale_y",
            "pos_y": "pos_y",
            "smoothing": "smoothing",
            "response": "response",
            "gravity": "gravity",
            "inertia": "inertia",
            "mirror": "mirror",
            "invert": "invert",
            "low_freq": "low_freq",
            "high_freq": "high_freq",
            "gamma": "gamma",
        }
        
        if key in config_map:
            engine_key = config_map[key]
            self.engine.update_config(**{engine_key: value})
        
        # Actualizar color
        if key.startswith("color_"):
            r = self._config.get("color_r", 255)
            g = self._config.get("color_g", 255)
            b = self._config.get("color_b", 255)
            self.engine.update_config(color=(r, g, b))