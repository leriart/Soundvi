#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de reproducción de audio sincronizada para Soundvi.
Usa pygame.mixer para reproducción con seek y sincronización precisa.
Soporta múltiples formatos: mp3, wav, ogg, flac, m4a, aac.
"""
import os
import time
import threading
from typing import Optional, List, Tuple

from core.logger import get_logger
logger = get_logger(__name__)

_pygame_available = False
_mixer_initialized = False

try:
    import pygame
    _pygame_available = True
except ImportError:
    logger.warning("pygame no disponible. Audio deshabilitado. Instala: pip install pygame")


def _ensure_mixer():
    """Inicializa pygame.mixer si no está inicializado."""
    global _mixer_initialized
    if not _pygame_available:
        return False
    if not _mixer_initialized:
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            _mixer_initialized = True
        except Exception as e:
            logger.error("Error inicializando pygame.mixer: %s", e)
            return False
    return True


class AudioPlayer:
    """
    Reproductor de audio con sincronización precisa para preview.
    
    Soporta:
    - Reproducción sincronizada con el timeline
    - Seek (saltar a posición)
    - Volumen por clip
    - Múltiples clips de audio simultáneos (hasta 8 canales)
    - Fade in/out de audio
    """

    MAX_CHANNELS = 8

    def __init__(self):
        self._playing = False
        self._current_position = 0.0
        self._duration = 0.0
        self._volume = 1.0
        self._active_channels: List[Tuple[object, str, float]] = []  # (channel, path, offset)
        self._lock = threading.Lock()
        self._sync_timer: Optional[threading.Timer] = None
        self._start_wall_time = 0.0
        self._start_position = 0.0
        # Cache de sonidos cargados para evitar recargas
        self._sound_cache = {}

    def _get_sound(self, audio_path: str):
        """Obtiene o carga un sonido en cache."""
        if not _ensure_mixer():
            return None
        if audio_path not in self._sound_cache:
            try:
                sound = pygame.mixer.Sound(audio_path)
                self._sound_cache[audio_path] = sound
            except Exception as e:
                logger.error("Error cargando audio '%s': %s", audio_path, e)
                return None
        return self._sound_cache.get(audio_path)

    def play_audio(self, audio_path: str, start_time: float = 0.0,
                   volume: float = 1.0, fade_in_ms: int = 0):
        """
        Reproduce un archivo de audio desde una posición específica.
        
        Args:
            audio_path: Ruta al archivo de audio
            start_time: Posición de inicio en segundos
            volume: Volumen (0.0 - 1.0)
            fade_in_ms: Duración del fade in en milisegundos
        """
        if not os.path.exists(audio_path):
            logger.warning("Archivo de audio no encontrado: %s", audio_path)
            return

        if not _ensure_mixer():
            return

        try:
            # --- FIX: Si necesita seek, usar SOLO pygame.mixer.music ---
            # Antes se reproducía primero en un channel (desde t=0) y luego
            # también en mixer.music (desde start_time), causando audio duplicado.
            if start_time > 0.01:
                self._play_with_seek(audio_path, start_time, volume, fade_in_ms)
                return

            sound = self._get_sound(audio_path)
            if sound is None:
                return

            self._duration = sound.get_length()

            # Buscar canal libre
            channel = pygame.mixer.find_channel()
            if channel is None:
                # Forzar un canal
                channel = pygame.mixer.Channel(0)

            channel.set_volume(volume * self._volume)

            if fade_in_ms > 0:
                channel.play(sound, fade_ms=fade_in_ms)
            else:
                channel.play(sound)

            with self._lock:
                self._active_channels.append((channel, audio_path, start_time))
                self._playing = True
                self._start_wall_time = time.monotonic()
                self._start_position = start_time
                self._current_position = start_time

        except Exception as e:
            logger.error("Error reproduciendo audio: %s", e)

    def _play_with_seek(self, audio_path: str, start_time: float,
                        volume: float, fade_in_ms: int):
        """Reproduce con seek usando pygame.mixer.music."""
        try:
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.set_volume(volume * self._volume)
            pygame.mixer.music.play(start=start_time)
            with self._lock:
                self._playing = True
                self._start_wall_time = time.monotonic()
                self._start_position = start_time
                self._current_position = start_time
        except Exception as e:
            logger.error("Error en play_with_seek: %s", e)

    def play_clips_at_time(self, clips_info: list, playhead_time: float):
        """
        Reproduce múltiples clips de audio sincronizados con el playhead.
        
        Args:
            clips_info: Lista de dicts con {path, clip_start, clip_duration, volume, trim_start}
            playhead_time: Tiempo actual del playhead en el timeline
        """
        self.stop()
        
        if not _ensure_mixer():
            return

        for info in clips_info:
            path = info.get('path', '')
            clip_start = info.get('clip_start', 0.0)
            clip_duration = info.get('clip_duration', 0.0)
            volume = info.get('volume', 1.0)
            trim_start = info.get('trim_start', 0.0)

            if not os.path.exists(path):
                continue

            # Calcular posición dentro del archivo de audio
            offset_in_clip = playhead_time - clip_start
            if offset_in_clip < 0 or offset_in_clip > clip_duration:
                continue

            audio_position = trim_start + offset_in_clip

            # Reproducir
            self.play_audio(path, start_time=audio_position, volume=volume)

        with self._lock:
            self._playing = True
            self._start_wall_time = time.monotonic()
            self._start_position = playhead_time

    def stop(self, fade_out_ms: int = 0):
        """Detiene toda la reproducción de audio."""
        with self._lock:
            self._playing = False

        if _pygame_available and _mixer_initialized:
            try:
                if fade_out_ms > 0:
                    pygame.mixer.fadeout(fade_out_ms)
                else:
                    pygame.mixer.stop()
                try:
                    pygame.mixer.music.stop()
                except Exception:
                    pass
            except Exception:
                pass

        with self._lock:
            self._active_channels.clear()

    def pause(self):
        """Pausa la reproducción."""
        with self._lock:
            if self._playing:
                self._playing = False
                self._current_position = self._start_position + (
                    time.monotonic() - self._start_wall_time
                )
        if _pygame_available and _mixer_initialized:
            try:
                pygame.mixer.pause()
                try:
                    pygame.mixer.music.pause()
                except Exception:
                    pass
            except Exception:
                pass

    def resume(self):
        """Reanuda la reproducción pausada."""
        if _pygame_available and _mixer_initialized:
            try:
                pygame.mixer.unpause()
                try:
                    pygame.mixer.music.unpause()
                except Exception:
                    pass
            except Exception:
                pass
        with self._lock:
            self._playing = True
            self._start_wall_time = time.monotonic()
            self._start_position = self._current_position

    def set_volume(self, volume: float):
        """Establece el volumen maestro (0.0 - 1.0)."""
        self._volume = max(0.0, min(1.0, volume))
        if _pygame_available and _mixer_initialized:
            try:
                pygame.mixer.music.set_volume(self._volume)
            except Exception:
                pass

    def seek(self, time_seconds: float):
        """Salta a una posición específica."""
        with self._lock:
            self._current_position = time_seconds
            self._start_position = time_seconds
            self._start_wall_time = time.monotonic()

    def get_current_time(self) -> float:
        """Retorna la posición actual de reproducción."""
        with self._lock:
            if self._playing:
                return self._start_position + (time.monotonic() - self._start_wall_time)
            return self._current_position

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def current_time(self) -> float:
        return self.get_current_time()

    @property
    def duration(self) -> float:
        return self._duration

    def clear_cache(self):
        """Limpia el cache de sonidos."""
        self._sound_cache.clear()

    def get_audio_fade_volume(self, clip_time: float, clip_duration: float,
                              fade_in_duration: float = 0.0,
                              fade_out_duration: float = 0.0) -> float:
        """
        Calcula el volumen de fade para un punto temporal dado.
        
        Args:
            clip_time: Tiempo dentro del clip
            clip_duration: Duración total del clip
            fade_in_duration: Duración del fade in
            fade_out_duration: Duración del fade out
            
        Returns:
            Factor de volumen (0.0 - 1.0)
        """
        vol = 1.0
        if fade_in_duration > 0 and clip_time < fade_in_duration:
            vol *= clip_time / fade_in_duration
        if fade_out_duration > 0 and clip_time > (clip_duration - fade_out_duration):
            remaining = clip_duration - clip_time
            vol *= max(0.0, remaining / fade_out_duration)
        return max(0.0, min(1.0, vol))


# Instancia global
audio_player = AudioPlayer()
