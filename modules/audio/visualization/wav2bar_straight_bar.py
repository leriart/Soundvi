#!/usr/bin/env python3
"""
Módulo de barras rectas inspirado en wav2bar-reborn: visualizer_straight_bar

Implementa un visualizador de barras verticales con:
- Escalado logarítmico de frecuencias
- Física realista (gravedad, inercia, rebote)
- Efectos visuales (sombras, gradientes, esquinas redondeadas)
- Configuración en tiempo real
"""

import numpy as np
import cv2
from typing import Optional, Tuple

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QSpinBox, QComboBox, QCheckBox, QDoubleSpinBox, QGroupBox
)
from PyQt6.QtCore import Qt

from modules.base import Module
from .wav2bar_base import Wav2BarBase, Wav2BarConfig


class Wav2BarStraightBarModule(Module):
    """
    Visualizador de barras rectas estilo wav2bar-reborn.
    
    Corresponde a visualizer_straight_bar en wav2bar-reborn.
    """
    
    module_type = "audio"
    module_category = "visualization"
    module_tags = ["wav2bar", "straight_bar", "bars", "spectrum", "visualizer"]
    module_version = "2.0.0"
    module_author = "Soundvi (basado en wav2bar-reborn)"
    
    def __init__(self):
        super().__init__(
            nombre="Wav2Bar: Barras Rectas",
            descripcion="Visualizador de barras verticales con física avanzada (wav2bar-reborn)"
        )
        
        # Configuración específica de barras rectas
        self.config = Wav2BarConfig(
            num_bars=64,
            bar_width_ratio=0.7,
            spacing_ratio=0.3,
            scale_y=0.4,
            pos_y=0.85,
            corner_radius=4
        )
        
        # Motor wav2bar
        self.engine = Wav2BarBase(self.config)
        
        # Configuración del módulo
        self._config = {
            "n_bars": self.config.num_bars,
            "bar_width_ratio": self.config.bar_width_ratio,
            "spacing_ratio": self.config.spacing_ratio,
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
            "gradient_enabled": self.config.gradient_enabled,
            "corner_radius": self.config.corner_radius,
            "low_freq": self.config.low_freq,
            "high_freq": self.config.high_freq,
            "gamma": self.config.gamma,
        }
    
    def prepare_audio(self, audio_path, mel_data, sr, hop, duration, fps):
        """Prepara el módulo con datos de audio."""
        try:
            self.engine.load_audio(audio_path, fps)
            print(f"[Wav2BarStraightBar] Audio preparado: {duration:.2f}s, {fps} FPS")
        except Exception as e:
            print(f"[Wav2BarStraightBar] Error preparando audio: {e}")
    
    def render(self, frame: np.ndarray, tiempo: float, **kwargs) -> np.ndarray:
        """Renderiza el visualizador en el frame."""
        if not self.habilitado or not self.engine.is_ready():
            return frame
        
        try:
            fps = kwargs.get('fps', 30)
            frame_index = min(int(tiempo * fps), self.engine.total_frames - 1)
            
            # Obtener alturas actuales
            heights = self.engine.get_heights(frame_index)
            
            # Renderizar barras
            rendered = self._render_bars(frame, heights)
            
            # Aplicar opacidad
            opacity = self._config["opacity"]
            if opacity < 1.0:
                blended = cv2.addWeighted(frame, 1.0 - opacity,
                                        rendered, opacity, 0)
                return blended
            
            return rendered
            
        except Exception as e:
            print(f"[Wav2BarStraightBar] Error en render: {e}")
            return frame
    
    def _render_bars(self, frame: np.ndarray, heights: np.ndarray) -> np.ndarray:
        """Renderiza barras en el frame."""
        height, width = frame.shape[:2]
        output = frame.copy()
        
        # Calcular dimensiones
        n_bars = len(heights)
        total_width = width * self._config["bar_width_ratio"]
        total_spacing = self._config["spacing_ratio"] * total_width
        bar_width = (total_width - total_spacing) / n_bars
        spacing = total_spacing / (n_bars - 1) if n_bars > 1 else 0
        
        # Posición base
        start_x = (width - total_width) / 2
        base_y = int(height * self._config["pos_y"])
        max_h = height * self._config["height_ratio"]
        
        # Color
        color = (
            int(self._config["color_b"]),
            int(self._config["color_g"]),
            int(self._config["color_r"])
        )
        
        # Modo espejo
        if self._config["mirror"]:
            heights = np.concatenate([heights[::-1], heights])
            n_bars_display = n_bars * 2
            # Ajustar ancho para modo espejo
            bar_width_mirror = bar_width / 2
            spacing_mirror = spacing / 2
        else:
            n_bars_display = n_bars
            bar_width_mirror = bar_width
            spacing_mirror = spacing
        
        # Renderizar cada barra
        for i in range(n_bars_display):
            # Calcular posición X
            if self._config["mirror"]:
                if i < n_bars:
                    # Lado izquierdo (espejo)
                    x = start_x + (n_bars - 1 - i) * (bar_width_mirror + spacing_mirror)
                else:
                    # Lado derecho
                    x = start_x + total_width/2 + (i - n_bars) * (bar_width_mirror + spacing_mirror)
            else:
                x = start_x + i * (bar_width_mirror + spacing_mirror)
            
            # Altura de la barra
            h_idx = i % n_bars
            h = heights[h_idx] if i < len(heights) else heights[-1]
            h_px = int(h * max_h)
            
            if h_px < 1:
                continue
            
            # Coordenadas del rectángulo
            x1, y1 = int(x), int(base_y - h_px)
            x2, y2 = int(x + bar_width_mirror), base_y
            
            # Dibujar barra con esquinas redondeadas
            radius = min(self._config["corner_radius"], h_px // 2)
            if radius > 0:
                # Rectángulo principal
                cv2.rectangle(output, (x1 + radius, y1), 
                            (x2 - radius, y2), color, -1)
                cv2.rectangle(output, (x1, y1 + radius), 
                            (x2, y2 - radius), color, -1)
                
                # Semicírculos para esquinas
                cv2.ellipse(output, (x1 + radius, y1 + radius), 
                          (radius, radius), 180, 0, 90, color, -1)
                cv2.ellipse(output, (x2 - radius, y1 + radius), 
                          (radius, radius), 270, 0, 90, color, -1)
                cv2.ellipse(output, (x1 + radius, y2 - radius), 
                          (radius, radius), 90, 0, 90, color, -1)
                cv2.ellipse(output, (x2 - radius, y2 - radius), 
                          (radius, radius), 0, 0, 90, color, -1)
            else:
                cv2.rectangle(output, (x1, y1), (x2, y2), color, -1)
            
            # Sombra si está activada
            if self._config["shadow_enabled"] and h_px > 5:
                shadow_color = tuple(max(0, c - 40) for c in color)
                cv2.rectangle(output, (x1, y2 - 2), (x2, y2), 
                            shadow_color, -1)
            
            # Brillo/glow si está activado
            if self._config["glow_intensity"] > 0 and h_px > 10:
                glow_color = tuple(min(255, c + 50) for c in color)
                glow_alpha = self._config["glow_intensity"]
                glow_layer = output.copy()
                cv2.rectangle(glow_layer, (x1-2, y1-2), (x2+2, y2+2), 
                            glow_color, -1)
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
        
        # Número de barras
        bars_row = QWidget()
        brl = QHBoxLayout(bars_row)
        brl.setContentsMargins(0, 0, 0, 0)
        brl.addWidget(QLabel("Nº Barras:"))
        bars_spin = QSpinBox()
        bars_spin.setRange(8, 256)
        bars_spin.setValue(self._config["n_bars"])
        bars_spin.valueChanged.connect(lambda v: self._update_config("n_bars", v, _as))
        brl.addWidget(bars_spin)
        agl.addWidget(bars_row)
        
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
        
        # Compresión gamma
        gamma_row = QWidget()
        grl = QHBoxLayout(gamma_row)
        grl.setContentsMargins(0, 0, 0, 0)
        grl.addWidget(QLabel("Compresión:"))
        gamma_slider = QSlider(Qt.Orientation.Horizontal)
        gamma_slider.setRange(10, 100)
        gamma_slider.setValue(int(self._config["gamma"] * 100))
        gamma_label = QLabel(f"{self._config['gamma']:.2f}")
        def on_gamma(v):
            val = v / 100.0
            self._update_config("gamma", val, _as)
            gamma_label.setText(f"{val:.2f}")
        gamma_slider.valueChanged.connect(on_gamma)
        grl.addWidget(gamma_slider)
        grl.addWidget(gamma_label)
        agl.addWidget(gamma_row)
        
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
        
        # Gravedad
        gravity_row = QWidget()
        grl2 = QHBoxLayout(gravity_row)
        grl2.setContentsMargins(0, 0, 0, 0)
        grl2.addWidget(QLabel("Gravedad:"))
        gravity_slider = QSlider(Qt.Orientation.Horizontal)
        gravity_slider.setRange(0, 100)
        gravity_slider.setValue(int(self._config["gravity"] * 100))
        gravity_label = QLabel(f"{self._config['gravity']:.2f}")
        def on_gravity(v):
            val = v / 100.0
            self._update_config("gravity", val, _as)
            gravity_label.setText(f"{val:.2f}")
        gravity_slider.valueChanged.connect(on_gravity)
        grl2.addWidget(gravity_slider)
        grl2.addWidget(gravity_label)
        pgl.addWidget(gravity_row)
        
        # Inercia
        inertia_row = QWidget()
        irl = QHBoxLayout(inertia_row)
        irl.setContentsMargins(0, 0, 0, 0)
        irl.addWidget(QLabel("Inercia:"))
        inertia_slider = QSlider(Qt.Orientation.Horizontal)
        inertia_slider.setRange(1, 100)
        inertia_slider.setValue(int(self._config["inertia"] * 100))
        inertia_label = QLabel(f"{self._config['inertia']:.2f}")
        def on_inertia(v):
            val = v / 100.0
            self._update_config("inertia", val, _as)
            inertia_label.setText(f"{val:.2f}")