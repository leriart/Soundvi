#!/usr/bin/env python3
"""
Módulo base para visualizadores inspirados en wav2bar-reborn.

Implementa la lógica común de procesamiento de audio y renderizado
basada en la arquitectura de wav2bar-reborn.
"""

import numpy as np
import cv2
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import interp1d
import librosa
from dataclasses import dataclass
from typing import Tuple, Optional, List, Dict, Any
import threading


@dataclass
class Wav2BarConfig:
    """Configuración común para visualizadores wav2bar."""
    # Parámetros de audio
    fft_size: int = 2048
    hop_length: int = 512
    low_freq: float = 50.0
    high_freq: float = 10000.0
    gamma: float = 0.3  # Compresión gamma para el espectro
    
    # Parámetros de renderizado
    num_bars: int = 64
    mirror: bool = True
    invert: bool = False
    
    # Física
    gravity: float = 0.2
    inertia: float = 0.8
    response: float = 0.5
    smoothing: float = 0.3
    max_velocity: float = 10.0
    bounce_factor: float = 0.3
    min_height: float = 0.01
    
    # Estilo
    color: Tuple[int, int, int] = (255, 255, 255)
    opacity: float = 1.0
    glow_intensity: float = 0.0
    shadow_enabled: bool = True
    gradient_enabled: bool = False
    corner_radius: int = 2
    
    # Posición y tamaño
    pos_x: float = 0.5
    pos_y: float = 0.9
    scale_y: float = 0.6
    bar_width_ratio: float = 0.98
    spacing_ratio: float = 0.1


class Wav2BarBase:
    """
    Clase base para visualizadores wav2bar.
    
    Implementa el procesamiento de audio y la física común
    basada en wav2bar-reborn.
    """
    
    def __init__(self, config: Optional[Wav2BarConfig] = None):
        self.config = config or Wav2BarConfig()
        
        # Estado del audio
        self.audio_data = None
        self.sample_rate = None
        self.duration = 0.0
        
        # Cache de espectrograma
        self.spectrogram_cache = None
        self.total_frames = 0
        
        # Estado de física
        self.current_heights = np.zeros(self.config.num_bars, dtype=np.float32)
        self.target_heights_cache = None
        self.velocities = np.zeros(self.config.num_bars, dtype=np.float32)
        
        # Lock para thread safety
        self._lock = threading.Lock()
        self._is_ready = False
        
    def load_audio(self, audio_path: str, fps: int = 30):
        """Carga y procesa audio usando la metodología de wav2bar-reborn."""
        try:
            # Cargar audio
            y, sr = librosa.load(audio_path, sr=44100, mono=True)
            self.audio_data = y
            self.sample_rate = sr
            self.duration = len(y) / sr
            
            # Calcular STFT (como en wav2bar-reborn)
            S = np.abs(librosa.stft(
                y, 
                n_fft=self.config.fft_size, 
                hop_length=self.config.hop_length
            ))
            
            # Crear bandas de frecuencia logarítmicas
            n_bars = self.config.num_bars
            bands = np.logspace(
                np.log10(self.config.low_freq),
                np.log10(self.config.high_freq),
                n_bars + 1
            )
            
            # Frecuencias del STFT
            freqs = librosa.fft_frequencies(sr=sr, n_fft=self.config.fft_size)
            
            # Promediar energía en cada banda (similar a wav2bar-reborn)
            energy = np.zeros((n_bars, S.shape[1]))
            for i in range(n_bars):
                idx = np.where((freqs >= bands[i]) & (freqs < bands[i+1]))[0]
                if len(idx) > 0:
                    energy[i] = np.mean(S[idx, :], axis=0)
                else:
                    # Si no hay bins, usar el más cercano
                    closest = np.argmin(np.abs(freqs - (bands[i] + bands[i+1]) / 2))
                    energy[i] = S[closest, :]
            
            # Aplicar compresión gamma (como en wav2bar-reborn)
            energy = np.power(energy, self.config.gamma)
            
            # Suavizado espacial
            energy = gaussian_filter1d(energy, sigma=1.0, axis=0)
            
            # Normalizar por banda
            for i in range(n_bars):
                max_val = np.max(energy[i])
                if max_val > 0:
                    energy[i] /= max_val
            
            # Interpolar a framerate de video
            n_frames = int(self.duration * fps)
            x_old = np.linspace(0, 1, energy.shape[1])
            x_new = np.linspace(0, 1, n_frames)
            
            self.target_heights_cache = np.zeros((n_frames, n_bars), dtype=np.float32)
            for i in range(n_bars):
                interp = interp1d(x_old, energy[i], kind='cubic', fill_value='extrapolate')
                self.target_heights_cache[:, i] = interp(x_new)
            
            self.total_frames = n_frames
            self._is_ready = True
            
            print(f"[Wav2BarBase] Audio cargado: {self.duration:.2f}s, {n_frames} frames, {n_bars} bandas")
            
        except Exception as e:
            print(f"[Wav2BarBase] Error cargando audio: {e}")
            self._is_ready = False
    
    def update_physics(self, frame_index: int):
        """Actualiza la física basada en wav2bar-reborn."""
        if not self._is_ready or frame_index >= self.total_frames:
            return
        
        with self._lock:
            # Obtener alturas objetivo del audio
            target = self.target_heights_cache[frame_index].copy()
            
            # Aplicar inversión si está activado
            if self.config.invert:
                target = target[::-1]
            
            # Calcular fuerza hacia el objetivo
            delta = target - self.current_heights
            
            # Aplicar respuesta (aceleración hacia el objetivo)
            acceleration = delta * self.config.response
            
            # Actualizar velocidades (con inercia)
            self.velocities = self.velocities * self.config.inertia + acceleration
            
            # Limitar velocidad máxima
            max_vel = self.config.max_velocity / 30.0  # Asumiendo 30 FPS
            self.velocities = np.clip(self.velocities, -max_vel, max_vel)
            
            # Aplicar gravedad (tira hacia abajo)
            self.velocities -= self.config.gravity / 30.0
            
            # Actualizar alturas
            self.current_heights += self.velocities
            
            # Limitar altura mínima
            self.current_heights = np.maximum(self.current_heights, self.config.min_height)
            
            # Aplicar rebote en el fondo (como en wav2bar)
            bounce_mask = self.current_heights < self.config.min_height
            if np.any(bounce_mask):
                self.current_heights[bounce_mask] = self.config.min_height
                self.velocities[bounce_mask] = -self.velocities[bounce_mask] * self.config.bounce_factor
            
            # Suavizado temporal final
            if self.config.smoothing > 0:
                self.current_heights = gaussian_filter1d(
                    self.current_heights, 
                    sigma=self.config.smoothing * 2
                )
    
    def get_heights(self, frame_index: int) -> np.ndarray:
        """Obtiene las alturas actuales de las barras."""
        self.update_physics(frame_index)
        return self.current_heights.copy()
    
    def is_ready(self) -> bool:
        """Verifica si el motor está listo para renderizar."""
        return self._is_ready
    
    def reset(self):
        """Reinicia el estado del motor."""
        self.current_heights.fill(0)
        self.velocities.fill(0)
    
    def update_config(self, **kwargs):
        """Actualiza la configuración."""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                    
                    # Si cambia el número de barras, recrear arrays
                    if key == "num_bars" and len(self.current_heights) != value:
                        self.current_heights = np.zeros(value, dtype=np.float32)
                        self.velocities = np.zeros(value, dtype=np.float32)
                        if self._is_ready:
                            # Recargar audio con nuevo número de barras
                            print(f"[Wav2BarBase] Número de barras cambiado a {value}, se requiere recargar audio")
                            self._is_ready = False