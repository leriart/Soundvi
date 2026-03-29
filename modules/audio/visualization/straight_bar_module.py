#!/usr/bin/env python3
"""
Módulo de barras rectas (Straight Bar Visualizer) - Versión Wav2Bar
Reemplazo del módulo original con funcionalidad wav2bar-reborn.
"""

import numpy as np
import cv2

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QSpinBox, QComboBox, QCheckBox, QDoubleSpinBox, QGroupBox
)
from PyQt6.QtCore import Qt

from modules.base import Module
from modules.audio.visualization.wav2bar_base import Wav2BarBase, Wav2BarConfig


class StraightBarModule(Module):
    """Visualizador de barras rectas estilo wav2bar-reborn."""

    module_type = "audio"
    module_category = "visualization"
    module_tags = ["wav2bar", "straight_bar", "bars", "spectrum", "visualizer"]
    module_version = "2.0.0"
    module_author = "Soundvi (basado en wav2bar-reborn)"
    
    def __init__(self):
        super().__init__(
            nombre="Barras Rectas (wav2bar)",
            descripcion="Barras verticales con física avanzada estilo wav2bar-reborn"
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
        
        # Configuración del módulo (manteniendo compatibilidad)
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
            print(f"[StraightBarModule] Audio preparado: {duration:.2f}s, {fps} FPS")
        except Exception as e:
            print(f"[StraightBarModule] Error preparando audio: {e}")
    
    def render(self, frame: np.ndarray, tiempo: float, **kwargs) -> np.ndarray:
        """Renderiza el visualizador en el frame."""
        if not self.habilitado or not self.engine.is_ready():
            return frame
        
        try:
            fps = kwargs.get('fps', 30)
            module_duration = kwargs.get('module_duration', None)
            
            # Calcular frame index proporcional a la duración del módulo
            if module_duration and module_duration > 0:
                # Tiempo normalizado (0 a 1) dentro de la duración del módulo
                normalized_time = min(tiempo / module_duration, 1.0)
                frame_index = int(normalized_time * (self.engine.total_frames - 1))
            else:
                # Fallback: usar tiempo absoluto (compatibilidad)
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
            print(f"[StraightBarModule] Error en render: {e}")
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
        from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSpinBox, QCheckBox, QGroupBox
        from PyQt6.QtCore import Qt
        
        self.app = app
        _as = app
        
        content = QWidget(parent)
        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Grupo de audio
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
        
        main_layout.addWidget(audio_group)
        
        # Grupo de opciones visuales
        vis_group = QGroupBox("Opciones Visuales")
        vgl = QVBoxLayout(vis_group)
        
        # Espejo
        mirror_check = QCheckBox("Espejo")
        mirror_check.setChecked(self._config["mirror"])
        mirror_check.toggled.connect(lambda v: self._update_config("mirror", v, _as))
        vgl.addWidget(mirror_check)
        
        main_layout.addWidget(vis_group)
        
        return content
    
    def _update_config(self, key: str, value, app):
        """Actualiza la configuración y propaga al motor."""
        super()._update_config(key, value, app)
        
        # Mapear configuraciones al motor
        config_map = {
            "n_bars": "num_bars",
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
            "bar_width_ratio": "bar_width_ratio",
            "spacing_ratio": "spacing_ratio",
            "corner_radius": "corner_radius",
            "glow_intensity": "glow_intensity",
            "shadow_enabled": "shadow_enabled",
            "gradient_enabled": "gradient_enabled",
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
    
    def get_config(self):
        """Retorna la configuración actual del módulo."""
        return dict(self._config)