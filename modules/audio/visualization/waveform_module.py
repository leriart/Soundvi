#!/usr/bin/env python3
"""
Módulo de forma de onda (Waveform) - Versión Wav2Bar
Basado en wav2bar-reborn: visualizer_straight_wave

Visualiza el audio como una forma de onda con física avanzada.
"""

import numpy as np
import cv2

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QSlider, QCheckBox, QSpinBox, QGroupBox,
    QHBoxLayout, QComboBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt

from modules.core.base import Module
from modules.audio.visualization.wav2bar_base import Wav2BarBase, Wav2BarConfig


class WaveformModule(Module):
    """Visualizador de forma de onda estilo wav2bar-reborn."""

    module_type = "audio"
    module_category = "visualization"
    module_tags = ["wav2bar", "waveform", "straight_wave", "audio", "visualizer"]
    module_version = "2.0.0"
    module_author = "Soundvi (basado en wav2bar-reborn)"

    def __init__(self):
        super().__init__("Waveform (wav2bar)")
        
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
        
        # Configuración del módulo (manteniendo compatibilidad)
        self._config = {
            "mode": "line",
            "mirror": self.config.mirror,
            "invert": self.config.invert,
            "response": self.config.response,
            "gravity": self.config.gravity,
            "inertia": self.config.inertia,
            "smoothing": self.config.smoothing,
            "glow_intensity": self.config.glow_intensity,
            "corner_radius": 0.0,
            "shadow_enabled": self.config.shadow_enabled,
            "gradient_enabled": False,
            "num_bars": self.config.num_bars,
            "pos_x": self.config.pos_x,
            "pos_y": self.config.pos_y,
            "scale_y": self.config.scale_y,
            "scale_x": 1.0,
            "rotation": 0.0,
            "opacity": self.config.opacity,
            "color": list(self.config.color),
            "color2": [0, 150, 255],
            "color3": [255, 100, 0],
            "color4": [100, 255, 100],
            "color5": [255, 255, 0],
            # Nuevos parámetros wav2bar
            "line_width": 3,
            "fill_enabled": True,
            "fill_opacity": 0.3,
            "low_freq": self.config.low_freq,
            "high_freq": self.config.high_freq,
            "gamma": self.config.gamma,
        }

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
        
        # === CONFIGURACIÓN GENERAL ===
        general_group = QGroupBox("Configuración General")
        ggl = QVBoxLayout(general_group)
        
        # Modo
        mode_row = QWidget()
        mrl = QHBoxLayout(mode_row)
        mrl.setContentsMargins(0, 0, 0, 0)
        mrl.addWidget(QLabel("Modo:"))
        mode_combo = QComboBox()
        mode_combo.addItems(["line", "bars", "filled"])
        mode_combo.setCurrentText(self._config["mode"])
        mode_combo.currentTextChanged.connect(lambda t: self._update_config("mode", t, _as))
        mrl.addWidget(mode_combo)
        ggl.addWidget(mode_row)
        
        # Número de puntos
        points_row = QWidget()
        prl = QHBoxLayout(points_row)
        prl.setContentsMargins(0, 0, 0, 0)
        prl.addWidget(QLabel("Nº Puntos:"))
        points_spin = QSpinBox()
        points_spin.setRange(32, 512)
        points_spin.setValue(self._config["num_bars"])
        points_spin.valueChanged.connect(lambda v: self._update_config("num_bars", v, _as))
        prl.addWidget(points_spin)
        ggl.addWidget(points_row)
        
        # Grosor de línea
        width_row = QWidget()
        wrl = QHBoxLayout(width_row)
        wrl.setContentsMargins(0, 0, 0, 0)
        wrl.addWidget(QLabel("Grosor:"))
        width_spin = QSpinBox()
        width_spin.setRange(1, 10)
        width_spin.setValue(self._config.get("line_width", 3))
        width_spin.valueChanged.connect(lambda v: self._update_config("line_width", v, _as))
        wrl.addWidget(width_spin)
        ggl.addWidget(width_row)
        
        main_layout.addWidget(general_group)
        
        # === OPCIONES VISUALES ===
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
        
        # Relleno
        fill_row = QWidget()
        frl = QHBoxLayout(fill_row)
        frl.setContentsMargins(0, 0, 0, 0)
        fill_check = QCheckBox("Rellenar")
        fill_check.setChecked(self._config.get("fill_enabled", True))
        fill_check.toggled.connect(lambda v: self._update_config("fill_enabled", v, _as))
        frl.addWidget(fill_check)
        frl.addWidget(QLabel("Opacidad:"))
        fill_opacity = QDoubleSpinBox()
        fill_opacity.setRange(0.0, 1.0)
        fill_opacity.setSingleStep(0.1)
        fill_opacity.setValue(self._config.get("fill_opacity", 0.3))
        fill_opacity.valueChanged.connect(lambda v: self._update_config("fill_opacity", v, _as))
        frl.addWidget(fill_opacity)
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
        """Actualiza la configuración y propaga al motor wav2bar."""
        super()._update_config(key, value, app)
        
        # Mapear configuraciones al motor wav2bar
        config_map = {
            "num_bars": "num_bars",
            "mirror": "mirror",
            "invert": "invert",
            "response": "response",
            "gravity": "gravity",
            "inertia": "inertia",
            "smoothing": "smoothing",
            "pos_y": "pos_y",
            "scale_y": "scale_y",
            "opacity": "opacity",
            "low_freq": "low_freq",
            "high_freq": "high_freq",
            "gamma": "gamma",
        }
        
        if key in config_map:
            engine_key = config_map[key]
            self.engine.update_config(**{engine_key: value})
        
        # Actualizar color
        if key == "color" and isinstance(value, list) and len(value) >= 3:
            self.engine.update_config(color=tuple(value[:3]))

    def render(self, frame, tiempo, **kwargs):
        """Renderiza el visualizador en el frame usando motor wav2bar."""
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
            
            # Obtener alturas actuales del motor wav2bar
            heights = self.engine.get_heights(frame_index)
            
            # Renderizar waveform según el modo
            if self._config["mode"] == "bars":
                rendered = self._render_bars(frame, heights)
            elif self._config["mode"] == "filled":
                rendered = self._render_filled_waveform(frame, heights)
            else:  # "line" por defecto
                rendered = self._render_line_waveform(frame, heights)
            
            # Aplicar opacidad
            opacity = self._config["opacity"]
            if opacity < 1.0:
                blended = cv2.addWeighted(frame, 1.0 - opacity,
                                        rendered, opacity, 0)
                return blended
            
            return rendered
            
        except Exception as e:
            print(f"[WaveformModule] Error en render: {e}")
            return frame
    
    def _render_line_waveform(self, frame: np.ndarray, heights: np.ndarray) -> np.ndarray:
        """Renderiza waveform como línea."""
        height, width = frame.shape[:2]
        output = frame.copy()
        
        # Calcular puntos
        n_points = len(heights)
        max_h = height * self._config["scale_y"]
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
        
        # Dibujar línea
        if len(points) >= 2:
            line_color = tuple(map(int, self._config["color"]))
            line_width = self._config.get("line_width", 3)
            
            # Dibujar línea suave
            pts_array = np.array(points, dtype=np.int32)
            cv2.polylines(output, [pts_array], False, line_color, line_width)
            
            # Sombra si está activada
            if self._config.get("shadow_enabled", False):
                shadow_color = tuple(max(0, c - 40) for c in line_color)
                shadow_points = [(x, y + 2) for x, y in points]
                shadow_array = np.array(shadow_points, dtype=np.int32)
                cv2.polylines(output, [shadow_array], False, shadow_color, line_width)
            
            # Brillo/glow si está activado
            if self._config.get("glow_intensity", 0) > 0:
                glow_color = tuple(min(255, c + 50) for c in line_color)
                glow_alpha = self._config["glow_intensity"]
                glow_layer = output.copy()
                cv2.polylines(glow_layer, [pts_array], False, glow_color, line_width + 2)
                cv2.addWeighted(glow_layer, glow_alpha, output,
                              1 - glow_alpha, 0, output)
        
        return output
    
    def _render_filled_waveform(self, frame: np.ndarray, heights: np.ndarray) -> np.ndarray:
        """Renderiza waveform con relleno."""
        height, width = frame.shape[:2]
        output = frame.copy()
        
        # Calcular puntos
        n_points = len(heights)
        max_h = height * self._config["scale_y"]
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
        if self._config.get("fill_enabled", True) and len(points) >= 2:
            fill_points = points.copy()
            fill_points.append((points[-1][0], center_y))
            fill_points.append((points[0][0], center_y))
            
            fill_layer = output.copy()
            pts_array = np.array(fill_points, dtype=np.int32)
            fill_color = tuple(map(int, self._config["color"]))
            cv2.fillPoly(fill_layer, [pts_array], fill_color)
            
            # Aplicar opacidad de relleno
            fill_opacity = self._config.get("fill_opacity", 0.3)
            cv2.addWeighted(fill_layer, fill_opacity, output,
                          1 - fill_opacity, 0, output)
        
        # Dibujar línea sobre el relleno
        if len(points) >= 2:
            line_color = tuple(map(int, self._config["color"]))
            line_width = self._config.get("line_width", 3)
            pts_array = np.array(points, dtype=np.int32)
            cv2.polylines(output, [pts_array], False, line_color, line_width)
        
        return output
    
    def _render_bars(self, frame: np.ndarray, heights: np.ndarray) -> np.ndarray:
        """Renderiza waveform como barras (modo alternativo)."""
        height, width = frame.shape[:2]
        output = frame.copy()
        
        n_bars = len(heights)
        bar_width = width // n_bars
        max_h = height * self._config["scale_y"]
        center_y = int(height * self._config["pos_y"])
        
        for i in range(n_bars):
            h = heights[i] if i < len(heights) else heights[-1]
            bar_height = int(h * max_h)
            
            if bar_height < 1:
                continue
            
            x = i * bar_width
            y_top = center_y - bar_height // 2
            y_bottom = center_y + bar_height // 2
            
            color = tuple(map(int, self._config["color"]))
            cv2.rectangle(output, (x, y_top), (x + bar_width - 1, y_bottom), color, -1)
        
        return output

    def prepare_audio(self, audio_path, mel_data=None, sr=None, hop=None, duration=None, fps=None, **kwargs):
        """Prepara el módulo con datos de audio usando motor wav2bar."""
        try:
            if audio_path:
                self.engine.load_audio(audio_path, fps)
                print(f"[WaveformModule] Audio preparado: {duration:.2f}s, {fps} FPS")
            else:
                print("[WaveformModule] Advertencia: No hay archivo de audio para cargar")
        except Exception as e:
            print(f"[WaveformModule] Error preparando audio: {e}")
    
    def get_config(self):
        """Retorna la configuración actual del módulo."""
        return dict(self._config)
