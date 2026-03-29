#!/usr/bin/env python3
"""
Módulo de barras circulares (Circular Bar Visualizer)
Basado en wav2bar-reborn: visualizer_circular_bar

Visualiza el espectro de audio como barras dispuestas en círculo con física avanzada.
"""

import numpy as np
import cv2
import math

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QSpinBox, QCheckBox, QDoubleSpinBox, QGroupBox, QComboBox
)
from PyQt6.QtCore import Qt

from modules.core.base import Module
from modules.audio.visualization.wav2bar_base import Wav2BarBase, Wav2BarConfig


class CircularBarModule(Module):
    """Visualizador de barras circulares estilo wav2bar-reborn."""

    module_type = "audio"
    module_category = "visualization"
    module_tags = ["wav2bar", "circular_bar", "radial", "spectrum", "visualizer"]
    module_version = "2.0.0"
    module_author = "Soundvi (basado en wav2bar-reborn)"

    def __init__(self):
        super().__init__(
            nombre="Barras Circulares (wav2bar)",
            descripcion="Barras radiales con física avanzada estilo wav2bar-reborn"
        )
        
        # Configuración específica de barras circulares
        self.config = Wav2BarConfig(
            num_bars=64,
            scale_y=0.4,
            pos_x=0.5,
            pos_y=0.5,
            bar_width_ratio=0.1,
            spacing_ratio=0.05,
            corner_radius=2
        )
        
        # Motor wav2bar
        self.engine = Wav2BarBase(self.config)
        
        # Configuración del módulo (manteniendo compatibilidad con nombres antiguos)
        self._config = {
            "n_bars": self.config.num_bars,
            "radius": 0.3,
            "bar_length": 0.15,  # Manteniendo nombre antiguo para compatibilidad
            "bar_width": 3,
            "center_x": self.config.pos_x,
            "center_y": self.config.pos_y,
            "opacity": self.config.opacity,
            "smoothing": self.config.smoothing,
            "rotation_speed": 0.0,
            "color_start_r": self.config.color[0],
            "color_start_g": self.config.color[1],
            "color_start_b": self.config.color[2],
            "color_end_r": 255,
            "color_end_g": 100,
            "color_end_b": 200,
            "mirror_bars": False,  # No aplica para wav2bar circular
            "inner_circle": True,
            "inner_circle_color_r": 50,
            "inner_circle_color_g": 50,
            "inner_circle_color_b": 50,
            "log_scale": True,
            "power_scale": self.config.gamma,
            # Nuevos parámetros wav2bar
            "inner_radius": 0.1,
            "start_angle": 0,
            "end_angle": 360,
            "direction": "outward",
            "glow_intensity": self.config.glow_intensity,
            "gradient_enabled": self.config.gradient_enabled,
            "low_freq": self.config.low_freq,
            "high_freq": self.config.high_freq,
        }

    def prepare_audio(self, audio_path, mel_data, sr, hop, duration, fps, **kwargs):
        """Prepara el módulo con datos de audio usando motor wav2bar."""
        try:
            self.engine.load_audio(audio_path, fps)
            print(f"[CircularBarModule] Audio preparado: {duration:.2f}s, {fps} FPS")
            self._duration = duration
        except Exception as e:
            print(f"[CircularBarModule] Error preparando audio: {e}")

    def render(self, frame, tiempo, **kwargs):
        """Renderiza el visualizador en el frame usando motor wav2bar."""
        if not self.habilitado or not self.engine.is_ready():
            return frame
        
        try:
            fps = kwargs.get('fps', 30)
            frame_index = min(int(tiempo * fps), self.engine.total_frames - 1)
            
            # Obtener alturas actuales del motor wav2bar
            heights = self.engine.get_heights(frame_index)
            
            # Renderizar barras circulares
            rendered = self._render_circular_bars(frame, heights, tiempo)
            
            # Aplicar opacidad
            opacity = self._config["opacity"]
            if opacity < 1.0:
                blended = cv2.addWeighted(frame, 1.0 - opacity,
                                        rendered, opacity, 0)
                return blended
            
            return rendered
            
        except Exception as e:
            print(f"[CircularBarModule] Error en render: {e}")
            return frame
    
    def _render_circular_bars(self, frame: np.ndarray, heights: np.ndarray, tiempo: float) -> np.ndarray:
        """Renderiza barras circulares en el frame."""
        height, width = frame.shape[:2]
        output = frame.copy()
        
        # Parámetros circulares
        center_x = int(width * self._config["center_x"])
        center_y = int(height * self._config["center_y"])
        min_dim = min(width, height)
        max_radius = min_dim * self._config["radius"] / 2
        inner_radius = min_dim * self._config["inner_radius"] / 2
        
        # Ángulos
        start_angle = math.radians(self._config["start_angle"])
        end_angle = math.radians(self._config["end_angle"])
        total_angle = end_angle - start_angle
        
        # Rotación
        rotation = self._config.get("rotation_speed", 0.0) * tiempo * 360
        rotation_rad = math.radians(rotation)
        
        # Dimensiones de barras
        n_bars = len(heights)
        bar_width_rad = math.radians(self._config["bar_width"])
        gap_width_rad = math.radians(2)  # Espacio fijo
        total_bar_width = bar_width_rad + gap_width_rad
        
        # Color base (usando color_start para compatibilidad)
        color = (
            int(self._config["color_start_b"]),
            int(self._config["color_start_g"]),
            int(self._config["color_start_r"])
        )
        
        # Círculo interior si está activado
        if self._config.get("inner_circle", True):
            ic_color = (
                self._config["inner_circle_color_b"],
                self._config["inner_circle_color_g"],
                self._config["inner_circle_color_r"]
            )
            cv2.circle(output, (center_x, center_y), int(inner_radius), ic_color, 2)
        
        # Renderizar cada barra
        for i in range(n_bars):
            # Ángulo central de la barra (con rotación)
            angle = start_angle + (i / n_bars) * total_angle + rotation_rad
            
            # Altura de la barra
            h = heights[i] if i < len(heights) else heights[-1]
            bar_length = h * max_radius * self._config["bar_length"] * 2  # Escalar
            
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
                
                # Gradiente de color si está activado
                if self._config.get("gradient_enabled", False):
                    ratio = i / max(n_bars - 1, 1)
                    cr = int(self._config["color_start_r"] * (1 - ratio) + self._config["color_end_r"] * ratio)
                    cg = int(self._config["color_start_g"] * (1 - ratio) + self._config["color_end_g"] * ratio)
                    cb = int(self._config["color_start_b"] * (1 - ratio) + self._config["color_end_b"] * ratio)
                    bar_color = (cb, cg, cr)
                else:
                    bar_color = color
                
                cv2.fillPoly(output, [pts_array], bar_color)
                
                # Bordes
                cv2.polylines(output, [pts_array], True, (0, 0, 0), 1)
        
        # Brillo/glow si está activado
        if self._config.get("glow_intensity", 0) > 0:
            glow_color = tuple(min(255, c + 50) for c in color)
            glow_alpha = self._config["glow_intensity"]
            
            # Crear capa de glow
            glow_layer = np.zeros_like(output)
            
            # Dibujar barras con glow
            for i in range(n_bars):
                angle = start_angle + (i / n_bars) * total_angle + rotation_rad
                h = heights[i] if i < len(heights) else heights[-1]
                bar_length = h * max_radius * self._config["bar_length"] * 2.2  # Glow más grande
                
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
            glow_layer = cv2.GaussianBlur(glow_layer, (9, 9), 0)
            
            # Mezclar glow
            cv2.addWeighted(glow_layer, glow_alpha, output,
                          1 - glow_alpha, 0, output)
        
        return output

    
    def get_config(self):
        """Retorna la configuración actual del módulo."""
        return dict(self._config)
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
        
        # Número de barras
        bars_row = QWidget()
        brl = QHBoxLayout(bars_row)
        brl.setContentsMargins(0, 0, 0, 0)
        brl.addWidget(QLabel("Nº Barras:"))
        bars_spin = QSpinBox()
        bars_spin.setRange(16, 256)
        bars_spin.setValue(self._config["n_bars"])
        bars_spin.valueChanged.connect(lambda v: self._update_config("n_bars", v, _as))
        brl.addWidget(bars_spin)
        cgl.addWidget(bars_row)
        
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
        
        # Longitud de barras
        length_row = QWidget()
        lrl = QHBoxLayout(length_row)
        lrl.setContentsMargins(0, 0, 0, 0)
        lrl.addWidget(QLabel("Longitud:"))
        length_slider = QSlider(Qt.Orientation.Horizontal)
        length_slider.setRange(2, 30)
        length_slider.setValue(int(self._config["bar_length"] * 100))
        length_label = QLabel(f"{self._config['bar_length']:.2f}")
        def on_length(v):
            val = v / 100.0
            self._update_config("bar_length", val, _as)
            length_label.setText(f"{val:.2f}")
        length_slider.valueChanged.connect(on_length)
        lrl.addWidget(length_slider)
        lrl.addWidget(length_label)
        cgl.addWidget(length_row)
        
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
        
        # Rotación
        rotation_row = QWidget()
        rtr = QHBoxLayout(rotation_row)
        rtr.setContentsMargins(0, 0, 0, 0)
        rtr.addWidget(QLabel("Rotación:"))
        rotation_spin = QDoubleSpinBox()
        rotation_spin.setRange(-10.0, 10.0)
        rotation_spin.setSingleStep(0.1)
        rotation_spin.setValue(self._config["rotation_speed"])
        rotation_spin.valueChanged.connect(lambda v: self._update_config("rotation_speed", v, _as))
        rtr.addWidget(rotation_spin)
        cgl.addWidget(rotation_row)
        
        main_layout.addWidget(circle_group)
        
        # === OPCIONES VISUALES ===
        vis_group = QGroupBox("Opciones Visuales")
        vgl = QVBoxLayout(vis_group)
        
        # Círculo interior
        inner_cb = QCheckBox("Círculo interior")
        inner_cb.setChecked(self._config["inner_circle"])
        inner_cb.toggled.connect(lambda v: self._update_config("inner_circle", v, _as))
        vgl.addWidget(inner_cb)
        
        # Gradiente
        gradient_cb = QCheckBox("Gradiente de color")
        gradient_cb.setChecked(self._config.get("gradient_enabled", False))
        gradient_cb.toggled.connect(lambda v: self._update_config("gradient_enabled", v, _as))
        vgl.addWidget(gradient_cb)
        
        # Glow
        glow_row = QWidget()
        grl = QHBoxLayout(glow_row)
        grl.setContentsMargins(0, 0, 0, 0)
        grl.addWidget(QLabel("Glow:"))
        glow_slider = QSlider(Qt.Orientation.Horizontal)
        glow_slider.setRange(0, 100)
        glow_slider.setValue(int(self._config.get("glow_intensity", 0) * 100))
        glow_label = QLabel(f"{self._config.get('glow_intensity', 0):.2f}")
        def on_glow(v):
            val = v / 100.0
            self._update_config("glow_intensity", val, _as)
            glow_label.setText(f"{val:.2f}")
        glow_slider.valueChanged.connect(on_glow)
        grl.addWidget(glow_slider)
        grl.addWidget(glow_label)
        vgl.addWidget(glow_row)
        
        main_layout.addWidget(vis_group)
        
        return content
    
    def _update_config(self, key: str, value, app):
        """Actualiza la configuración y propaga al motor wav2bar."""
        super()._update_config(key, value, app)
        
        # Mapear configuraciones al motor wav2bar
        config_map = {
            "n_bars": "num_bars",
            "smoothing": "smoothing",
            "power_scale": "gamma",
            "low_freq": "low_freq",
            "high_freq": "high_freq",
        }
        
        if key in config_map:
            engine_key = config_map[key]
            self.engine.update_config(**{engine_key: value})
        
        # Actualizar posición
        if key == "center_x":
            self.engine.update_config(pos_x=value)
        elif key == "center_y":
            self.engine.update_config(pos_y=value)
    
    def get_config(self):
        """Retorna la configuración actual del módulo."""
        return dict(self._config)
