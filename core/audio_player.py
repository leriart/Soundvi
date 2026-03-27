#!/usr/bin/env python3
"""
Modulo simple de reproduccion de audio para Soundvi.
Usa pygame si esta disponible, sino pydub, sino muestra advertencia.
"""
import threading
import time
from typing import Optional

class AudioPlayer:
    """Reproductor de audio simple."""
    
    def __init__(self):
        self._playing = False
        self._current_position = 0.0
        self._duration = 0.0
        self._thread: Optional[threading.Thread] = None
        self._audio_data = None
        
    def play_audio(self, audio_path: str, start_time: float = 0.0):
        """Reproduce audio desde un archivo."""
        if self._playing:
            self.stop()
            
        self._playing = True
        self._current_position = start_time
        self._thread = threading.Thread(target=self._play_thread, args=(audio_path, start_time))
        self._thread.daemon = True
        self._thread.start()
        
    def _play_thread(self, audio_path: str, start_time: float):
        """Hilo de reproduccion de audio."""
        try:
            # Intentar con pygame primero
            try:
                import pygame
                pygame.mixer.init()
                sound = pygame.mixer.Sound(audio_path)
                self._duration = sound.get_length()
                sound.play(loops=0, start=start_time)
                
                # Esperar a que termine
                while self._playing and pygame.mixer.get_busy():
                    self._current_position = start_time + (pygame.mixer.get_pos() / 1000.0)
                    time.sleep(0.1)
                    
            except ImportError:
                # Intentar con pydub
                try:
                    from pydub import AudioSegment
                    from pydub.playback import play
                    
                    audio = AudioSegment.from_file(audio_path)
                    self._duration = len(audio) / 1000.0
                    
                    if start_time > 0:
                        audio = audio[int(start_time * 1000):]
                    
                    play(audio)
                    
                except ImportError:
                    print("[Audio] No se encontro biblioteca de reproduccion de audio")
                    print("[Audio] Instala: pip install pygame o pip install pydub")
                    
        except Exception as e:
            print(f"[Audio] Error reproduciendo audio: {e}")
        finally:
            self._playing = False
            
    def stop(self):
        """Detiene la reproduccion."""
        self._playing = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            
    def pause(self):
        """Pausa la reproduccion."""
        # TODO: Implementar pausa real
        self._playing = False
        
    def seek(self, time_seconds: float):
        """Salta a una posicion especifica."""
        # Para implementacion completa, necesitariamos recrear el thread
        pass
        
    @property
    def is_playing(self) -> bool:
        return self._playing
        
    @property
    def current_time(self) -> float:
        return self._current_position
        
    @property
    def duration(self) -> float:
        return self._duration

# Instancia global
audio_player = AudioPlayer()
