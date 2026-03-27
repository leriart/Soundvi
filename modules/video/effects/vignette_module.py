#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vignette Effect Module para Soundvi.
Aplica un efecto de viñeta (bordes oscurecidos) al video.
"""

import numpy as np
import cv2

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider
from PyQt6.QtCore import Qt

from modules.base import Module

class VignetteModule(Module):
    """
    Modulo que aplica un efecto de viñeta (oscurecimiento de bordes) al video.
    """
    
    def __init__(self):
        super().__init__(
            nombre="Viñeta Visual", 
            descripcion="Aplica un oscurecimiento a los bordes del video (Vignette)"
        )
        
        # Estado interno del modulo
        self._vignette_mask = None
        self._last_shape = None
        
        # Parametros configurables
        self._config = {
            "intensidad": 0.8,   # 0.0 (nada) a 1.0 (maximo)
            "radio": 0.7         # Tamaño del centro claro
        }
        
    def _create_vignette_mask(self, width: int, height: int):
        """Genera y cachea la mascara de viñeta para el tamaño actual."""
        if self._last_shape == (height, width) and self._vignette_mask is not None:
            return self._vignette_mask
            
        # Crear mallas X e Y con centro en 0
        x = np.linspace(-1, 1, width)
        y = np.linspace(-1, 1, height)
        X, Y = np.meshgrid(x, y)
        
        # Calcular distancia al centro
        radius = np.sqrt(X**2 + Y**2)
        
        # Parámetros del efecto
        r_scale = max(0.1, self._config["radio"])
        intensity = self._config["intensidad"]
        
        # Generar mascara suave (1.0 en el centro, cayendo hacia los bordes)
        mask = 1.0 - np.clip((radius - r_scale) / (1.5 - r_scale), 0, 1)
        
        # Aplicar curva para suavidad
        mask = mask ** 2
        
        # Interpolar con intensidad
        mask = 1.0 - (1.0 - mask) * intensity
        
        # Expandir a 3 canales
        mask = np.dstack([mask, mask, mask]).astype(np.float32)
        
        self._last_shape = (height, width)
        self._vignette_mask = mask
        return mask

    def prepare_audio(self, audio_path: str, *args):
        """No requiere procesamiento de audio."""
    def render(self, frame: np.ndarray, tiempo: float, **kwargs) -> np.ndarray:
        """
        Aplica la viñeta al frame actual.
        """
        if not self.habilitado or self._config["intensidad"] <= 0.0:
            return frame
            
        h, w = frame.shape[:2]
        channels = frame.shape[2] if len(frame.shape) > 2 else 1
        
        try:
            mask = self._create_vignette_mask(w, h)
            
            if channels == 4:
                rgb = frame[:, :, :3].astype(np.float32)
                alpha = frame[:, :, 3:]
                rgb = (rgb * mask).astype(np.uint8)
                resultado = np.concatenate([rgb, alpha], axis=2)
            elif channels == 3:
                resultado = (frame.astype(np.float32) * mask).astype(np.uint8)
            else:
                return frame
                
            return resultado
        except Exception as e:
            print(f"Error en VignetteModule: {e}")
            return frame
            return resultado
        except Exception as e:
            print(f"Error en VignetteModule: {e}")
            return frame

    def get_config_widgets(self, parent, app) -> QWidget:
        """
        Devuelve el panel de configuracion para la GUI.
        """
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        # --- Slider de Intensidad ---
        layout.addWidget(QLabel("Intensidad:"))
        slider_int = QSlider(Qt.Orientation.Horizontal)
        slider_int.setRange(0, 100)
        slider_int.setValue(int(self._config["intensidad"] * 100))
        layout.addWidget(slider_int)
        
        val_int_lbl = QLabel(f"{int(self._config['intensidad'] * 100)}%")
        layout.addWidget(val_int_lbl)

        def on_int_changed(v):
            val = v / 100.0
            val_int_lbl.setText(f"{v}%")
            self._update_config("intensidad", val, app)
            # Invalidar mascara para forzar regeneracion
            self._last_shape = None
            
        slider_int.valueChanged.connect(on_int_changed)

        # --- Slider de Radio ---
        layout.addWidget(QLabel("Radio (Area central):"))
        slider_rad = QSlider(Qt.Orientation.Horizontal)
        slider_rad.setRange(10, 150)
        slider_rad.setValue(int(self._config["radio"] * 100))
        layout.addWidget(slider_rad)
        
        val_rad_lbl = QLabel(f"{int(self._config['radio'] * 100)}%")
        layout.addWidget(val_rad_lbl)

        def on_rad_changed(v):
            val = v / 100.0
            val_rad_lbl.setText(f"{v}%")
            self._update_config("radio", val, app)
            # Invalidar mascara para forzar regeneracion
            self._last_shape = None
            
        slider_rad.valueChanged.connect(on_rad_changed)

        return content