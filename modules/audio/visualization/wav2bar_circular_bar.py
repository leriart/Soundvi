#!/usr/bin/env python3
"""
Módulo de barras circulares inspirado en wav2bar-reborn: visualizer_circular_bar

Implementa un visualizador de barras en forma circular con:
- Disposición radial de barras
- Física realista
- Efectos visuales (brillo, sombras, gradientes)
- Configuración en tiempo real
"""

import numpy as np
import cv2
import math
from typing import Optional, Tuple, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QSpinBox, QComboBox, QCheckBox, QDoubleSpinBox, QGroupBox
)
from PyQt6.QtCore import Qt

from modules.base import Module
from .wav2bar_base import Wav2BarBase, Wav2BarConfig


class Wav2BarCircularBarModule(Module):
    """
    Visualizador de barras circulares estilo wav2bar-reborn.
    
    Corresponde a visualizer_circular_bar en wav2bar-reborn.
    """
    
    module_type = "audio"
    module_category = "visualization"
    module_tags = ["wav2bar", "circular_bar", "radial", "spectrum", "visualizer"]
    module_version = "2.0.0"
    module_author = "Soundvi (basado en wav2bar-reborn)"
    
    def __init__(self):
        super().__init__(
            nombre="Wav2Bar: Barras Circulares",
            descripcion="Visualizador de barras radiales con física avanzada (wav2bar-reborn)"
        )
        
        # Configuración específica de barras circulares
        self.config = Wav2BarConfig(
            num_bars=64,
            scale_y=0.4,
            pos_x=0.5,
            pos_y=0.5,
            bar_width_ratio=0.1,  # Ancho angular
            spacing_ratio=0.05,   # Espacio angular
            corner_radius=2
        )
        
        # Motor wav2bar
        self.engine = Wav2BarBase(self.config)
        
        # Configuración específica circular
        self._config = {
            "n_bars": self.config.num_bars,
            "radius": 0.3,  # Radio relativo al tamaño del frame
            "inner_radius": 0.1,  # Radio interno (para anillo)
            "start_angle": 0,  # Ángulo inicial en grados
            "end_angle": 360,  # Ángulo final en grados
            "bar_width": 10,  # Ancho de barra en grados
            "gap_width": 2,   # Espacio entre barras en grados
            "height_ratio": self.config.scale_y,
            "opacity": self.config.opacity,
            "smoothing": self.config.smoothing,
            "gravity": self.config.gravity,
            "inertia": self.config.inertia,
            "response": self.config.response,
            "mirror": False,  # No aplica para circular
            "invert": self.config.invert,
            "color_r": self.config.color[0],
            "color_g": self.config.color[1],
            "color_b": self.config.color[2],
            "glow_intensity": self.config.glow_intensity,
            "shadow_enabled": self.config.shadow_enabled,
            "gradient_enabled": self.config.gradient_enabled,
            "corner_radius": self.config.corner_radius,
            "direction": "outward",  # "outward" o "inward"
            "low_freq": self.config.low_freq,
            "high_freq": self.config.high_freq,
            "gamma": self.config.gamma,
        }
    
    def prepare_audio(self, audio_path, mel_data, sr, hop, duration, fps):
        """Prepara el módulo con datos de audio."""
        try:
            self.engine.load_audio(audio_path, fps)
            print(f"[Wav2BarCircularBar] Audio preparado: {duration:.2f}s, {fps} FPS")
        except Exception as e:
            print(f"[Wav2BarCircularBar] Error preparando audio: {e}")
    
    def render(self, frame: np.ndarray, tiempo: float, **kwargs) -> np.ndarray:
        """Renderiza el visualizador en el frame."""
        if not self.habilitado or not self.engine.is_ready():
            return frame
        
        try:
            fps = kwargs.get('fps', 30)
            frame_index = min(int(tiempo * fps), self.engine.total_frames - 1)
            
            # Obtener alturas actuales
            heights = self.engine.get_heights(frame_index)
            
            # Renderizar barras circulares
            rendered = self._render_circular_bars(frame, heights)
            
            # Aplicar opacidad
            opacity = self._config["opacity"]
            if opacity < 1.0:
                blended = cv2.addWeighted(frame, 1.0 - opacity,
                                        rendered, opacity, 0)
                return blended
            
            return rendered
            
        except Exception as e:
            print(f"[Wav2BarCircularBar] Error en render: {e}")
            return frame
    
    def _render_circular_bars(self, frame: np.ndarray, heights: np.ndarray) -> np.ndarray:
        """Renderiza barras circulares en el frame."""
        height, width = frame.shape[:2]
        output = frame.copy()
        
        # Parámetros circulares
        center_x = int(width * self.config.pos_x)
        center_y = int(height * self.config.pos_y)
        max_radius = min(width, height) * self._config["radius"] / 2
        inner_radius = min(width, height) * self._config["inner_radius"] / 2
        
        # Ángulos
        start_angle = math.radians(self._config["start_angle"])
        end_angle = math.radians(self._config["end_angle"])
        total_angle = end_angle - start_angle
        
        # Dimensiones de barras
        n_bars = len(heights)
        bar_width_rad = math.radians(self._config["bar_width"])
        gap_width_rad = math.radians(self._config["gap_width"])
        total_bar_width = bar_width_rad + gap_width_rad
        
        # Color
        color = (
            int(self._config["color_b"]),
            int(self._config["color_g"]),
            int(self._config["color_r"])
        )
        
        # Renderizar cada barra
        for i in range(n_bars):
            # Ángulo central de la barra
            angle = start_angle + (i / n_bars) * total_angle
            
            # Altura de la barra
            h = heights[i] if i < len(heights) else heights[-1]
            bar_length = h * max_radius * self._config["height_ratio"]
            
            if bar_length < 1:
                continue
            
            # Calcular puntos para el trapecio/rectángulo curvilíneo
            angle_start = angle - bar_width_rad / 2
            angle_end = angle + bar_width_rad / 2
            
            # Radio según dirección
            if self._config["direction"] == "outward":
                r1 = inner_radius
                r2 = inner_radius + bar_length
            else:  # inward
                r1 = max_radius - bar_length
                r2 = max_radius
            
            # Puntos del polígono
            points = []
            
            # Punto 1: inicio, radio interno
            x1 = center_x + r1 * math.cos(angle_start)
            y1 = center_y + r1 * math.sin(angle_start)
            points.append((int(x1), int(y1)))
            
            # Punto 2: inicio, radio externo
            x2 = center_x + r2 * math.cos(angle_start)
            y2 = center_y + r2 * math.sin(angle_start)
            points.append((int(x2), int(y2)))
            
            # Punto 3: fin, radio externo
            x3 = center_x + r2 * math.cos(angle_end)
            y3 = center_y + r2 * math.sin(angle_end)
            points.append((int(x3), int(y3)))
            
            # Punto 4: fin, radio interno
            x4 = center_x + r1 * math.cos(angle_end)
            y4 = center_y + r1 * math.sin(angle_end)
            points.append((int(x4), int(y4)))
            
            # Dibujar barra
            if len(points) >= 3:
                pts_array = np.array(points, dtype=np.int32)
                
                # Dibujar barra principal
                cv2.fillPoly(output, [pts_array], color)
                
                # Bordes redondeados si está activado
                if self._config["corner_radius"] > 0:
                    radius = min(self._config["corner_radius"], int(bar_length / 4))
                    if radius > 0:
                        # Esquinas exteriores
                        cv2.circle(output, (int(x2), int(y2)), radius, color, -1)
                        cv2.circle(output, (int(x3), int(y3)), radius, color, -1)
                
                # Sombra si está activada
                if self._config["shadow_enabled"] and bar_length > 5:
                    shadow_color = tuple(max(0, c - 40) for c in color)
                    shadow_offset = 2
                    shadow_points = [(x + shadow_offset, y + shadow_offset) for x, y in points]
                    shadow_array = np.array(shadow_points, dtype=np.int32)
                    cv2.fillPoly(output, [shadow_array], shadow_color)
                    # Redibujar barra principal sobre la sombra
                    cv2.fillPoly(output, [pts_array], color)
            
            # Gradiente si está activado
            if self._config["gradient_enabled"] and bar_length > 10:
                # Crear máscara de gradiente radial
                gradient_layer = np.zeros_like(output)
                for pt in points:
                    cv2.circle(gradient_layer, pt, int(bar_length/2), color, -1)
                
                # Aplicar desenfoque para suavizar
                gradient_layer = cv2.GaussianBlur(gradient_layer, (5, 5), 0)
                
                # Mezclar con la barra
                cv2.addWeighted(gradient_layer, 0.3, output, 0.7, 0, output)
        
        # Brillo/glow global si está activado
        if self._config["glow_intensity"] > 0:
            glow_color = tuple(min(255, c + 50) for c in color)
            glow_alpha = self._config["glow_intensity"]
            
            # Crear capa de glow
            glow_layer = np.zeros_like(output)
            
            # Dibujar barras con glow
            for i in range(n_bars):
                angle = start_angle + (i / n_bars) * total_angle
                h = heights[i] if i < len(heights) else heights[-1]
                bar_length = h * max_radius * self._config["height_ratio"] * 1.2  # Glow más grande
                
                if bar_length < 1:
                    continue
                
                angle_start = angle - bar_width_rad / 2
                angle_end = angle + bar_width_rad / 2
                
                if self._config["direction"] == "outward":
                    r1 = inner_radius
                    r2 = inner_radius + bar_length
                else:
                    r1 = max_radius - bar_length
                    r2 = max_radius
                
                # Puntos para glow
                x1 = center_x + r1 * math.cos(angle_start)
                y1 = center_y + r1 * math.sin(angle_start)
                x2 = center_x + r2 * math.cos(angle_start)
                y2 = center_y + r2 * math.sin(angle_start)
                x3 = center_x + r2 * math.cos(angle_end)
                y3 = center_y + r2 * math.sin(angle_end)
                x4 = center_x + r1 * math.cos(angle_end)
                y4 = center_y + r1 * math.sin(angle_end)
                
                pts = np.array([
                    [int(x1), int(y1)],
                    [int(x2), int(y2)],
                    [int(x3), int(y3)],
                    [int(x4), int(y4)]
                ], dtype=np.int32)
                
                cv2.fillPoly(glow_layer, [pts], glow_color)
            
            # Aplicar desenfoque al glow
            glow_layer = cv2.GaussianBlur(glow_layer, (15, 15), 0)
            
            # Mezclar glow
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
        
        # === CONFIGURACIÓN CIRCULAR ===
        circle_group = QGroupBox("Configuración Circular")
        cgl = QVBoxLayout(circle_group)
        
        # Radio
        radius_row = QWidget()
        rrl = QHBoxLayout(radius_row)
        rrl.setContentsMargins(0, 0, 0, 0)
        rrl.addWidget(QLabel("Radio:"))
        radius_slider = QSlider(Qt.Orientation.Horizontal)
        radius_slider.setRange(10, 90)
        radius_slider.setValue(int(self._config["radius"] * 100))
        radius_label = QLabel(f"{self._config['radius']:.2f}")
        def on_radius(v):
            val = v / 100.0
            self._update_config("radius", val, _as)
            radius_label.setText(f"{val:.2f}")
        radius_slider.valueChanged.connect(on_radius)
        rrl.addWidget(radius_slider)
        rrl.addWidget(radius_label)
        cgl.addWidget(radius_row)
        
        # Radio interno
        inner_row = QWidget()
        irl = QHBoxLayout(inner_row)
        irl.setContentsMargins(0, 0, 0, 0)
        irl.addWidget(QLabel("Radio Int:"))
        inner_slider = QSlider(Qt.Orientation.Horizontal)
        inner_slider.setRange(0, 50)
        inner_slider.setValue(int(self._config["inner_radius"] * 100))
        inner_label = QLabel(f"{self._config['inner_radius']:.2f}")
        def on_inner(v):
            val = v / 100.0
            self._update_config("inner_radius", val, _as)
            inner_label.setText(f"{val:.2f}")
        inner_slider.valueChanged.connect(on_inner)
        irl.addWidget(inner_slider)
        irl.addWidget(inner_label)
        cgl.addWidget(inner_row)
        
        # Ángulo de inicio y fin
        angle_row = QWidget()
        arl = QHBoxLayout(angle_row)
        arl.setContentsMargins(0, 0, 0, 0)
        arl.addWidget(QLabel("Inicio:"))
        start_angle = QSpinBox()
        start_angle.setRange(0, 360)
        start_angle.setValue(self._config["start_angle"])
        start_angle.setSuffix("°")
        start_angle.valueChanged.connect(lambda v: self._update_config("start_angle", v, _as))
        arl.addWidget(start_angle)
        arl.addWidget(QLabel("Fin:"))
        end_angle = QSpinBox()
        end_angle.setRange(0, 360)
        end_angle.setValue(self._config["end_angle"])
        end_angle.setSuffix("°")
        end_angle.valueChanged.connect(lambda v: self._update_config("end_angle", v, _as))
        arl.addWidget(end_angle)
        cgl.addWidget(angle_row)
        
        # Dirección
        dir_row = QWidget()
        drl = QHBoxLayout(dir_row)
        drl.setContentsMargins(0, 0, 0, 0)
        drl.addWidget(QLabel("Dirección:"))
        dir_combo = QComboBox()
        dir_combo.addItems(["Hacia afuera", "Hacia adentro"])
        dir_combo.setCurrentText("Hacia afuera" if self._config["direction"] == "outward" else "Hacia adentro")
        dir_combo.currentTextChanged.connect(lambda v: self._update_config("direction", 
                                                                          "outward" if v == "Hacia afuera" else "inward", 
                                                                          _as))
        drl.addWidget(dir_combo)
        cgl.addWidget(dir_row)
        
        main_layout.addWidget(circle_group)
        
        # === CONFIGURACIÓN DE BARRAS ===
        bar_group = QGroupBox("Configuración de Barras")
        bgl = QVBoxLayout(bar_group)
        
        # Número de barras
        bars_row = QWidget()
        brl = QHBoxLayout(bars_row)
        brl.setContentsMargins(0, 0, 0, 0)
        brl.addWidget(QLabel("Nº Barras:"))
        bars_spin = QSpin