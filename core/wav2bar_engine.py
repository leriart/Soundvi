#!/usr/bin/env python3
"""
Motor de visualizacion de audio inspirado en Wav2Bar.

Implementa un sistema de visualizacion flexible con:
- Multiple modos de visualizacion (barras, waveform, particulas, etc.)
- Fisica realista (gravedad, inercia, rebote)
- Configuracion en tiempo real
- Renderizado eficiente con OpenCV
"""

import numpy as np
import cv2
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import interp1d
import threading
from dataclasses import dataclass
from typing import List, Tuple, Optional, Callable


@dataclass
class BarPhysics:
    """Configuracion de fisica para barras de audio."""
    gravity: float = 0.2           # Fuerza de gravedad (0-1)
    inertia: float = 0.8           # Conservacion de momentum (0-1)
    response: float = 0.5          # Velocidad de respuesta al audio (0-1)
    smoothing: float = 0.3         # Suavizado temporal (0-1)
    max_velocity: float = 10.0     # Velocidad maxima de movimiento
    bounce_factor: float = 0.3     # Factor de rebote (0-1)
    min_height: float = 0.01       # Altura minima relativa


@dataclass
class VisualStyle:
    """Estilo visual para la visualizacion."""
    # Colores
    primary_color: Tuple[int, int, int] = (255, 255, 255)
    secondary_color: Tuple[int, int, int] = (100, 100, 255)
    background_color: Tuple[int, int, int] = (0, 0, 0)
    
    # Efectos
    glow_intensity: float = 0.0    # Intensidad de brillo (0-1)
    shadow_enabled: bool = True
    gradient_enabled: bool = False
    round_corners: bool = True
    
    # Dimensiones
    bar_width_ratio: float = 0.98  # Ancho relativo de las barras
    spacing_ratio: float = 0.1     # Espacio entre barras
    # Efectos
    glow_intensity: float = 0.0    # Intensidad de brillo (0-1)
    shadow_enabled: bool = True
    gradient_enabled: bool = False
    round_corners: bool = True
    
    # Dimensiones
    bar_width_ratio: float = 0.98  # Ancho relativo de las barras
    spacing_ratio: float = 0.1     # Espacio entre barras
    corner_radius: int = 2         # Radio de esquinas redondeadas
    
    # Posicion y Tamaño
    pos_x: float = 0.5             # Posicion X relativa (0-1)
    pos_y: float = 0.9             # Posicion Y relativa (0-1)
    scale_y: float = 0.6           # Escala vertical relativa (0-1)


class Wav2BarEngine:
    """
    Motor principal de visualizacion Wav2Bar.
    
    Procesa datos de audio y genera frames de visualizacion con fisica
    en tiempo real y multiples modos de renderizado.
    """
    
    def __init__(self, 
                 num_bars: int = 64,
                 framerate: int = 30,
                 width: int = 1280,
                 height: int = 720):
        
        self.num_bars = num_bars
        self.framerate = framerate
        self.width = width
        self.height = height
        
        # Estado del motor
        self.audio_data = None
        self.sample_rate = None
        self.duration = 0.0
        self.total_frames = 0
        
        # Parametros configurables
        self.physics = BarPhysics()
        self.style = VisualStyle()
        
        # Estado de renderizado
        self.current_heights = np.zeros(num_bars, dtype=np.float32)
        self.target_heights = np.zeros(num_bars, dtype=np.float32)
        self.velocities = np.zeros(num_bars, dtype=np.float32)
        
        # Cache para rendimiento
        self.bar_positions = None
        self.bar_widths = None
        self._update_layout()
        
        # Modo de visualizacion
        self.mode = "bars"  # "bars", "waveform", "particles", "spectrum"
        self.mirror = True
        self.invert = False
        
        # Hilo de procesamiento
        self._lock = threading.Lock()
        self._is_ready = False
    
    def set_config(self, **kwargs):
        with self._lock:
            needs_layout = False
            for k, v in kwargs.items():
                if k == "mode":
                    self.mode = v
                elif k == "mirror":
                    self.mirror = v
                elif k == "invert":
                    self.invert = v
                elif hasattr(self.physics, k):
                    setattr(self.physics, k, v)
                elif hasattr(self.style, k):
                    setattr(self.style, k, v)
                    if k in ("bar_width_ratio", "spacing_ratio", "pos_x", "pos_y", "scale_y"):
                        needs_layout = True
                elif k == "color" and isinstance(v, (tuple, list)):
                    self.style.primary_color = v
                elif hasattr(self, k):
                    setattr(self, k, v)
                    if k in ("num_bars", "width", "height"):
                        needs_layout = True
                        
            if needs_layout:
                # Si num_bars cambió, recrear arrays
                if len(self.current_heights) != self.num_bars:
                    import numpy as np
                    self.current_heights = np.zeros(self.num_bars, dtype=np.float32)
                    self.target_heights = np.zeros(self.num_bars, dtype=np.float32)
                    self.velocities = np.zeros(self.num_bars, dtype=np.float32)
                self._update_layout()
                    
    def _update_layout(self):
        """Calcula posiciones y dimensiones de las barras."""
        if self.width <= 0 or self.height <= 0:
            return
        
        # Calcular ancho total disponible
        total_width = self.width * self.style.bar_width_ratio
        
        # Calcular ancho de barra y espacio
        total_spacing = self.style.spacing_ratio * total_width
        bar_width = (total_width - total_spacing) / self.num_bars
        spacing = total_spacing / (self.num_bars - 1) if self.num_bars > 1 else 0
        
        # Calcular posiciones
        self.bar_widths = bar_width
        start_x = (self.width - total_width) / 2
        
        self.bar_positions = []
        for i in range(self.num_bars):
            x = start_x + i * (bar_width + spacing)
            self.bar_positions.append(x)
        
        self.bar_positions = np.array(self.bar_positions, dtype=np.float32)
    
    def load_audio(self, audio_path: str):
        """Carga y preprocesa archivo de audio."""
        try:
            import librosa
            from scipy import signal
            
            # Cargar audio
            y, sr = librosa.load(audio_path, sr=44100, mono=True)
            self.audio_data = y
            self.sample_rate = sr
            self.duration = len(y) / sr
            
            # Calcular espectrograma para las barras
            n_fft = 2048
            hop_length = n_fft // 4
            
            # STFT
            S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop_length))
            
            # Bandas de frecuencia logaritmicas
            n_bars = self.num_bars
            low_freq = 50
            high_freq = 10000
            
            # Frecuencias del STFT
            freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
            
            # Crear bandas logaritmicas
            bands = np.logspace(np.log10(low_freq), np.log10(high_freq), n_bars + 1)
            
            # Promediar energia en cada banda
            energy = np.zeros((n_bars, S.shape[1]))
            for i in range(n_bars):
                idx = np.where((freqs >= bands[i]) & (freqs < bands[i+1]))[0]
                if len(idx) > 0:
                    energy[i] = np.mean(S[idx, :], axis=0)
                else:
                    # Si no hay bins, usar el mas cercano
                    closest = np.argmin(np.abs(freqs - (bands[i] + bands[i+1]) / 2))
                    energy[i] = S[closest, :]
            
            # Normalizar y suavizar
            energy = np.power(energy, 0.3)  # Compresion gamma
            energy = gaussian_filter1d(energy, sigma=1.0, axis=0)
            
            # Normalizar por banda
            for i in range(n_bars):
                max_val = np.max(energy[i])
                if max_val > 0:
                    energy[i] /= max_val
            
            # Interpolar a framerate de video
            n_frames = int(self.duration * self.framerate)
            x_old = np.linspace(0, 1, energy.shape[1])
            x_new = np.linspace(0, 1, n_frames)
            
            self.target_heights_cache = np.zeros((n_frames, n_bars), dtype=np.float32)
            for i in range(n_bars):
                interp = interp1d(x_old, energy[i], kind='cubic', fill_value='extrapolate')
                self.target_heights_cache[:, i] = interp(x_new)
            
            self.total_frames = n_frames
            self._is_ready = True
            
            print(f"[Wav2Bar] Audio cargado: {self.duration:.2f}s, {n_frames} frames")
            
        except Exception as e:
            print(f"[Wav2Bar] Error cargando audio: {e}")
            self._is_ready = False
    
    def update_physics(self, frame_index: int):
        """Actualiza la fisica de las barras para el frame actual."""
        if not self._is_ready or frame_index >= self.total_frames:
            return
        
        with self._lock:
            # Obtener alturas objetivo del audio
            target = self.target_heights_cache[frame_index].copy()
            
            # Aplicar inversion si esta activado
            if self.invert:
                target = target[::-1]
            
            # Calcular fuerza hacia el objetivo
            delta = target - self.current_heights
            
            # Aplicar respuesta (aceleracion hacia el objetivo)
            acceleration = delta * self.physics.response
            
            # Actualizar velocidades
            self.velocities = self.velocities * self.physics.inertia + acceleration
            
            # Limitar velocidad maxima
            max_vel = self.physics.max_velocity / self.framerate
            self.velocities = np.clip(self.velocities, -max_vel, max_vel)
            
            # Aplicar gravedad (tira hacia abajo)
            self.velocities -= self.physics.gravity / self.framerate
            
            # Actualizar alturas
            self.current_heights += self.velocities
            
            # Limitar altura minima
            self.current_heights = np.maximum(self.current_heights, self.physics.min_height)
            
            # Aplicar rebote en el fondo
            bounce_mask = self.current_heights < self.physics.min_height
            if np.any(bounce_mask):
                self.current_heights[bounce_mask] = self.physics.min_height
                self.velocities[bounce_mask] = -self.velocities[bounce_mask] * self.physics.bounce_factor
            
            # Suavizado final
            if self.physics.smoothing > 0:
                self.current_heights = gaussian_filter1d(self.current_heights, 
                                                       sigma=self.physics.smoothing * 2)
    
    def get_heights(self, frame_index: int) -> np.ndarray:
        """Obtiene las alturas actuales de las barras."""
        self.update_physics(frame_index)
        return self.current_heights.copy()
    
    def render_frame(self, frame_index: int, background: Optional[np.ndarray] = None) -> np.ndarray:
        """Renderiza un frame completo."""
        if background is None:
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            frame[:] = self.style.background_color
        else:
            frame = background.copy()
        
        heights = self.get_heights(frame_index)
        
        if self.mode == "bars":
            frame = self._render_bars(frame, heights)
        elif self.mode == "waveform":
            frame = self._render_waveform(frame, heights)
        elif self.mode == "spectrum":
            frame = self._render_spectrum(frame, heights)
        
        return frame
    
    def _render_bars(self, frame: np.ndarray, heights: np.ndarray) -> np.ndarray:
        """Renderiza barras tradicionales."""
        max_h = self.height * self.style.scale_y
        base_y = int(self.height * self.style.pos_y)
        offset_x = int(self.width * (self.style.pos_x - 0.5))
        
        # Si espejo esta activado, duplicar y reflejar
        if self.mirror:
            heights = np.concatenate([heights[::-1], heights])
            if self.bar_positions is not None and len(self.bar_positions) > 0:
                # Ajustar posiciones para modo espejo
                mirrored_positions = np.concatenate([
                    self.bar_positions[::-1] - self.bar_widths,
                    self.bar_positions
                ])
            else:
                return frame
        else:
            mirrored_positions = self.bar_positions
        
        if mirrored_positions is None or len(mirrored_positions) != len(heights):
            return frame
        
        for i, (x, h) in enumerate(zip(mirrored_positions, heights)):
            # Calcular altura en pixeles
            h_px = int(h * max_h)
            if h_px < 2:
                continue
            
            # Posicion Y (desde abajo)
            y_bottom = base_y
            y_top = y_bottom - h_px
            
            # Coordenadas del rectangulo
            x1, y1 = int(x), int(y_top)
            x2, y2 = int(x + self.bar_widths), y_bottom
            
            # Dibujar barra
            if self.style.round_corners and self.style.corner_radius > 0:
                # Rectangulo con esquinas redondeadas
                radius = min(self.style.corner_radius, h_px // 2)
                if radius > 0:
                    # Dibujar rectangulo principal
                    cv2.rectangle(frame, (x1 + radius, y1), 
                                 (x2 - radius, y2), self.style.primary_color, -1)
                    cv2.rectangle(frame, (x1, y1 + radius), 
                                 (x2, y2 - radius), self.style.primary_color, -1)
                    
                    # Dibujar semicirculos para esquinas
                    cv2.ellipse(frame, (x1 + radius, y1 + radius), 
                               (radius, radius), 180, 0, 90, self.style.primary_color, -1)
                    cv2.ellipse(frame, (x2 - radius, y1 + radius), 
                               (radius, radius), 270, 0, 90, self.style.primary_color, -1)
                else:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), 
                                self.style.primary_color, -1)
            else:
                cv2.rectangle(frame, (x1, y1), (x2, y2), 
                            self.style.primary_color, -1)
            
            # Sombra si esta activada
            if self.style.shadow_enabled and h_px > 5:
                shadow_color = tuple(max(0, c - 40) for c in self.style.primary_color)
                cv2.rectangle(frame, (x1, y2 - 2), (x2, y2), 
                            shadow_color, -1)
        
        return frame
    
    def _render_waveform(self, frame: np.ndarray, heights: np.ndarray) -> np.ndarray:
        """Renderiza como waveform continuo."""
        if len(heights) < 2:
            return frame
        
        bar_height = self.height * 0.4
        center_y = self.height // 2
        
        # Crear puntos para la linea
        points = []
        for i, (x, h) in enumerate(zip(self.bar_positions, heights)):
            y = center_y - (h - 0.5) * bar_height
            points.append((int(x + self.bar_widths / 2), int(y)))
        
        # Dibujar linea suave
        if len(points) > 1:
            pts = np.array(points, dtype=np.int32)
            cv2.polylines(frame, [pts], False, self.style.primary_color, 2)
        
        return frame
    
    def _render_spectrum(self, frame: np.ndarray, heights: np.ndarray) -> np.ndarray:
        """Renderiza como espectro (area fill)."""
        if len(heights) < 2:
            return frame
        
        bar_height = self.height * 0.5
        base_y = self.height
        
        # Crear puntos para el poligono
        points = []
        
        # Punto inicial en la esquina inferior izquierda
        x0 = self.bar_positions[0]
        points.append((int(x0), base_y))
        
        # Puntos superiores
        for i, (x, h) in enumerate(zip(self.bar_positions, heights)):
            y = base_y - h * bar_height
            points.append((int(x + self.bar_widths / 2), int(y)))
        
        # Punto final en la esquina inferior derecha
        x_last = self.bar_positions[-1] + self.bar_widths
        points.append((int(x_last), base_y))
        
        # Rellenar poligono
        if len(points) >= 3:
            pts = np.array(points, dtype=np.int32)
            cv2.fillPoly(frame, [pts], self.style.primary_color)
        
        return frame
    
    def set_style(self, **kwargs):
        """Actualiza el estilo visual."""
        for key, value in kwargs.items():
            if hasattr(self.style, key):
                setattr(self.style, key, value)
        
        # Si cambian dimensiones relacionadas con layout, actualizar
        layout_keys = ['bar_width_ratio', 'spacing_ratio']
        if any(key in layout_keys for key in kwargs.keys()):
            self._update_layout()
    
    def set_physics(self, **kwargs):
        """Actualiza parametros de fisica."""
        for key, value in kwargs.items():
            if hasattr(self.physics, key):
                setattr(self.physics, key, value)
    
    def is_ready(self) -> bool:
        """Verifica si el motor esta listo para renderizar."""
        return self._is_ready
    
    def reset(self):
        """Reinicia el estado del motor."""
        self.current_heights.fill(0)
        self.target_heights.fill(0)
        self.velocities.fill(0)
    def _render_particles(self, frame: np.ndarray, heights: np.ndarray) -> np.ndarray:
        """Renderiza como particulas saltarinas."""
        max_h = self.height * self.style.scale_y
        base_y = int(self.height * self.style.pos_y)
        offset_x = int(self.width * (self.style.pos_x - 0.5))
        
        # Modo espejo
        if self.mirror:
            h_array = np.concatenate([heights[::-1], heights])
            if self.bar_positions is not None and len(self.bar_positions) * 2 == len(h_array):
                # Generar posiciones para espejo (solo si las originales existen)
                pass # Por brevedad, simplificado
        else:
            h_array = heights
            
        color = (int(self.style.primary_color[0]), int(self.style.primary_color[1]), int(self.style.primary_color[2]))
        
        # Render particles
        for i, h in enumerate(h_array):
            if i >= len(self.bar_positions) and not self.mirror: continue
            
            pos = self.bar_positions[i % len(self.bar_positions)]
            if self.mirror and i < len(heights):
                pos = self.width / 2 - (pos - self.width / 2) # Espejo izquierdo
                
            x = int(pos) + offset_x
            h_px = int(h * max_h)
            y = base_y - h_px
            
            # Dibujar un circulo brillante en la punta
            cv2.circle(frame, (x, y), int(self.bar_widths/2) + 2, color, -1)
            if self.style.glow_intensity > 0:
                cv2.circle(frame, (x, y), int(self.bar_widths) + 4, color, 1)
                
        return frame

    def _render_spectrum(self, frame: np.ndarray, heights: np.ndarray) -> np.ndarray:
        """Renderiza como linea continua de espectro rellenado (estilo area)."""
        max_h = self.height * self.style.scale_y
        base_y = int(self.height * self.style.pos_y)
        offset_x = int(self.width * (self.style.pos_x - 0.5))
        
        pts = []
        pts.append([0 + offset_x, base_y])
        
        # Modo espejo
        if self.mirror:
            h_array = np.concatenate([heights[::-1], heights])
        else:
            h_array = heights
            
        color = (int(self.style.primary_color[0]), int(self.style.primary_color[1]), int(self.style.primary_color[2]))
        
        for i, h in enumerate(h_array):
            if i >= len(self.bar_positions) and not self.mirror: continue
            pos = self.bar_positions[i % len(self.bar_positions)]
            if self.mirror and i < len(heights):
                pos = self.width / 2 - (pos - self.width / 2)
            
            x = int(pos) + offset_x
            y = base_y - int(h * max_h)
            pts.append([x, y])
            
        if pts:
            pts.append([pts[-1][0], base_y])
            poly_pts = np.array([pts], dtype=np.int32)
            
            # Crear overlay para semitransparencia
            overlay = frame.copy()
            cv2.fillPoly(overlay, poly_pts, color)
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
            
            # Borde
            cv2.polylines(frame, poly_pts, False, color, 2)
            
        return frame