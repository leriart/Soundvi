#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Audio Reactivo Universal.

Permite vincular CUALQUIER parametro de modulo o clip a frecuencias de audio.
Analiza el audio en bandas de frecuencia y genera valores normalizados
que pueden controlar opacidad, posicion, tamano, color, etc.

Uso:
    reactor = AudioReactor()
    reactor.load_audio("cancion.mp3")
    
    # Vincular un parametro a bajos (20-200 Hz)
    binding = AudioBinding("opacity", band="bass", intensity=1.5)
    reactor.add_binding(binding)
    
    # En cada frame:
    values = reactor.get_values_at(current_time)
    # values = {"opacity": 0.85}
"""

from __future__ import annotations
import numpy as np
from typing import Optional, Dict, Any, List, Tuple


# -- Bandas de frecuencia predefinidas --
FREQUENCY_BANDS = {
    "sub_bass":   (20, 60),
    "bass":       (60, 250),
    "low_mid":    (250, 500),
    "mid":        (500, 2000),
    "high_mid":   (2000, 4000),
    "high":       (4000, 8000),
    "brilliance": (8000, 20000),
    "full":       (20, 20000),
}

# -- Modos de respuesta --
RESPONSE_MODES = {
    "instant":    "Respuesta instantanea",
    "smooth":     "Suavizado (promedio movil)",
    "peak_hold":  "Retener picos",
    "attack":     "Solo ataques (onsets)",
    "envelope":   "Envolvente (follow)",
}


class AudioBinding:
    """
    Vinculacion de un parametro a una banda de frecuencia de audio.
    
    Atributos:
        parameter: Nombre del parametro a controlar
        band: Banda de frecuencia ("bass", "mid", "high", etc.)
        intensity: Multiplicador de intensidad (0.0 - 5.0)
        offset: Valor base al que se suma la reactividad
        min_value: Valor minimo permitido
        max_value: Valor maximo permitido
        response_mode: Modo de respuesta temporal
        smoothing: Factor de suavizado (0.0 = sin suavizado, 1.0 = maximo)
        invert: Invertir la respuesta (1 - valor)
    """

    def __init__(self, parameter: str, band: str = "bass",
                 intensity: float = 1.0, offset: float = 0.0,
                 min_value: float = 0.0, max_value: float = 1.0,
                 response_mode: str = "smooth", smoothing: float = 0.3,
                 invert: bool = False):
        self.parameter: str = parameter
        self.band: str = band if band in FREQUENCY_BANDS else "bass"
        self.intensity: float = max(0.0, min(5.0, intensity))
        self.offset: float = offset
        self.min_value: float = min_value
        self.max_value: float = max_value
        self.response_mode: str = response_mode
        self.smoothing: float = max(0.0, min(1.0, smoothing))
        self.invert: bool = invert
        self.enabled: bool = True
        
        # Estado interno para suavizado
        self._prev_value: float = 0.0
        self._peak_value: float = 0.0

    def process_value(self, raw_energy: float) -> float:
        """
        Procesa el valor crudo de energia en el valor final del parametro.
        
        Args:
            raw_energy: Energia cruda de la banda de frecuencia (0.0 - 1.0)
            
        Returns:
            Valor procesado para el parametro
        """
        if not self.enabled:
            return self.offset
        
        # Aplicar intensidad
        value = raw_energy * self.intensity
        
        # Aplicar modo de respuesta
        if self.response_mode == "smooth":
            value = self._prev_value * self.smoothing + value * (1.0 - self.smoothing)
        elif self.response_mode == "peak_hold":
            if value > self._peak_value:
                self._peak_value = value
            else:
                self._peak_value *= 0.95  # Decaimiento lento
            value = self._peak_value
        elif self.response_mode == "attack":
            # Solo responde a incrementos
            delta = value - self._prev_value
            value = max(0, delta) * self.intensity
        elif self.response_mode == "envelope":
            # Ataque rapido, decaimiento lento
            if value > self._prev_value:
                value = self._prev_value * 0.3 + value * 0.7
            else:
                value = self._prev_value * 0.9 + value * 0.1
        
        self._prev_value = value
        
        # Invertir si es necesario
        if self.invert:
            value = 1.0 - value
        
        # Mapear al rango [min_value, max_value] y aplicar offset
        range_size = self.max_value - self.min_value
        value = self.min_value + value * range_size + self.offset
        value = max(self.min_value, min(self.max_value, value))
        
        return value

    def reset(self):
        """Resetea el estado interno."""
        self._prev_value = 0.0
        self._peak_value = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter": self.parameter,
            "band": self.band,
            "intensity": self.intensity,
            "offset": self.offset,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "response_mode": self.response_mode,
            "smoothing": self.smoothing,
            "invert": self.invert,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AudioBinding':
        binding = cls(
            parameter=data.get("parameter", ""),
            band=data.get("band", "bass"),
            intensity=data.get("intensity", 1.0),
            offset=data.get("offset", 0.0),
            min_value=data.get("min_value", 0.0),
            max_value=data.get("max_value", 1.0),
            response_mode=data.get("response_mode", "smooth"),
            smoothing=data.get("smoothing", 0.3),
            invert=data.get("invert", False),
        )
        binding.enabled = data.get("enabled", True)
        return binding


class AudioReactor:
    """
    Motor de audio reactivo universal.
    
    Analiza el audio y proporciona valores de energia por banda de frecuencia
    que pueden vincularse a cualquier parametro de modulos o clips.
    """

    def __init__(self):
        # Datos de analisis de audio
        self._band_energies: Dict[str, np.ndarray] = {}  # {band_name: array_of_energies}
        self._fps: float = 30.0
        self._duration: float = 0.0
        self._total_frames: int = 0
        self._loaded: bool = False
        
        # Vinculaciones activas
        self.bindings: List[AudioBinding] = []
        
        # Datos de beat detection
        self._beat_times: np.ndarray = np.array([])
        self._onset_strength: np.ndarray = np.array([])

    def load_audio(self, audio_path: str, fps: float = 30.0):
        """
        Carga y analiza un archivo de audio.
        
        Extrae la energia por banda de frecuencia para cada frame de video.
        
        Args:
            audio_path: Ruta al archivo de audio
            fps: Frames por segundo del video
        """
        try:
            import librosa
            
            # Cargar audio
            y, sr = librosa.load(audio_path, sr=22050, mono=True)
            self._fps = fps
            self._duration = len(y) / sr
            self._total_frames = int(self._duration * fps)
            
            # Calcular STFT
            hop_length = int(sr / fps)
            stft = np.abs(librosa.stft(y, hop_length=hop_length, n_fft=2048))
            freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
            
            # Extraer energia por banda de frecuencia
            for band_name, (low_freq, high_freq) in FREQUENCY_BANDS.items():
                # Encontrar indices de frecuencia para esta banda
                freq_mask = (freqs >= low_freq) & (freqs <= high_freq)
                if not np.any(freq_mask):
                    self._band_energies[band_name] = np.zeros(self._total_frames)
                    continue
                    
                # Sumar energia en la banda
                band_energy = np.sum(stft[freq_mask, :], axis=0)
                
                # Normalizar a 0-1
                max_energy = np.max(band_energy) if np.max(band_energy) > 0 else 1.0
                band_energy = band_energy / max_energy
                
                # Interpolar al numero de frames de video
                from scipy.interpolate import interp1d
                x_original = np.linspace(0, self._duration, len(band_energy))
                x_target = np.linspace(0, self._duration, self._total_frames)
                interpolator = interp1d(x_original, band_energy, 
                                       kind='linear', fill_value=0, bounds_error=False)
                self._band_energies[band_name] = interpolator(x_target)
            
            # Beat detection
            try:
                tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)
                self._beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop_length)
                self._onset_strength = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
            except Exception:
                self._beat_times = np.array([])
                self._onset_strength = np.array([])
            
            self._loaded = True
            print(f"[AudioReactor] Audio analizado: {self._duration:.1f}s, {self._total_frames} frames")
            
        except ImportError:
            print("[AudioReactor] librosa no disponible. Instalar con: pip install librosa")
        except Exception as e:
            print(f"[AudioReactor] Error analizando audio: {e}")

    def get_band_energy(self, band: str, time: float) -> float:
        """
        Obtiene la energia de una banda de frecuencia en un tiempo dado.
        
        Args:
            band: Nombre de la banda ("bass", "mid", "high", etc.)
            time: Tiempo en segundos
            
        Returns:
            Energia normalizada (0.0 - 1.0)
        """
        if not self._loaded or band not in self._band_energies:
            return 0.0
            
        frame_idx = int(time * self._fps)
        frame_idx = max(0, min(frame_idx, len(self._band_energies[band]) - 1))
        return float(self._band_energies[band][frame_idx])

    def get_all_bands_at(self, time: float) -> Dict[str, float]:
        """Obtiene la energia de todas las bandas en un tiempo dado."""
        result = {}
        for band_name in FREQUENCY_BANDS:
            result[band_name] = self.get_band_energy(band_name, time)
        return result

    def is_beat_at(self, time: float, tolerance: float = 0.05) -> bool:
        """Verifica si hay un beat en el tiempo dado."""
        if len(self._beat_times) == 0:
            return False
        distances = np.abs(self._beat_times - time)
        return float(np.min(distances)) < tolerance

    def get_beat_intensity(self, time: float, decay: float = 0.15) -> float:
        """
        Obtiene la intensidad del beat mas cercano con decaimiento.
        
        Args:
            time: Tiempo en segundos
            decay: Tiempo de decaimiento en segundos
            
        Returns:
            Intensidad del beat (0.0 - 1.0)
        """
        if len(self._beat_times) == 0:
            return 0.0
        
        # Buscar beats recientes
        recent = self._beat_times[self._beat_times <= time]
        if len(recent) == 0:
            return 0.0
            
        last_beat = recent[-1]
        elapsed = time - last_beat
        
        if elapsed > decay:
            return 0.0
        return 1.0 - (elapsed / decay)

    # -- Gestion de vinculaciones --

    def add_binding(self, binding: AudioBinding):
        """Agrega una vinculacion audio-parametro."""
        # Evitar duplicados del mismo parametro
        self.bindings = [b for b in self.bindings if b.parameter != binding.parameter]
        self.bindings.append(binding)

    def remove_binding(self, parameter: str):
        """Elimina la vinculacion de un parametro."""
        self.bindings = [b for b in self.bindings if b.parameter != parameter]

    def get_binding(self, parameter: str) -> Optional[AudioBinding]:
        """Obtiene la vinculacion de un parametro."""
        for b in self.bindings:
            if b.parameter == parameter:
                return b
        return None

    def get_values_at(self, time: float) -> Dict[str, float]:
        """
        Obtiene todos los valores de parametros vinculados en un tiempo dado.
        
        Returns:
            Diccionario {nombre_parametro: valor_procesado}
        """
        values = {}
        for binding in self.bindings:
            if not binding.enabled:
                continue
            energy = self.get_band_energy(binding.band, time)
            values[binding.parameter] = binding.process_value(energy)
        return values

    def reset_all_bindings(self):
        """Resetea el estado interno de todas las vinculaciones."""
        for binding in self.bindings:
            binding.reset()

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def available_bands(self) -> List[str]:
        return list(FREQUENCY_BANDS.keys())

    # -- Serializacion --

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bindings": [b.to_dict() for b in self.bindings],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AudioReactor':
        reactor = cls()
        for binding_data in data.get("bindings", []):
            binding = AudioBinding.from_dict(binding_data)
            reactor.bindings.append(binding)
        return reactor
