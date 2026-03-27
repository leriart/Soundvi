#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VideoClip -- Clase para representar clips de video individuales en el timeline.

Soporta multiples archivos de video, imagenes y GIFs como fuentes.
Cada clip tiene posicion temporal, duracion, recortes (trim) y propiedades.
"""

from __future__ import annotations
import os
import uuid
import threading
from typing import Optional, Dict, Any, List, Tuple
from functools import lru_cache

import numpy as np
import cv2

from core.logger import get_logger
logger = get_logger(__name__)

logger = get_logger(__name__)
class VideoClip:
    """
    Representa un clip de video/imagen/GIF en el timeline.
    
    Atributos principales:
        clip_id: Identificador unico del clip
        source_path: Ruta al archivo fuente
        source_type: Tipo de fuente ('video', 'image', 'gif', 'color')
        track_index: Indice del track donde se ubica
        start_time: Tiempo de inicio en el timeline (segundos)
        duration: Duracion del clip en el timeline (segundos)
        trim_start: Punto de inicio del recorte en el archivo fuente
        trim_end: Punto de fin del recorte en el archivo fuente
        opacity: Opacidad del clip (0.0 - 1.0)
        volume: Volumen del audio del clip (0.0 - 2.0)
        enabled: Si el clip esta habilitado para renderizado
    """

    # -- Tipos de fuente soportados --
    SOURCE_TYPES = ('video', 'image', 'gif', 'color', 'audio')

    def __init__(
        self,
        source_path: str = "",
        source_type: str = "video",
        track_index: int = 0,
        start_time: float = 0.0,
        duration: float = 0.0,
        name: str = ""
    ):
        # Identificador unico
        self.clip_id: str = str(uuid.uuid4())[:8]
        
        # Fuente del clip
        self.source_path: str = source_path
        self.source_type: str = source_type if source_type in self.SOURCE_TYPES else "video"
        self.name: str = name or os.path.basename(source_path) if source_path else "Clip vacio"
        
        # Posicion en el timeline
        self.track_index: int = track_index
        self.start_time: float = start_time
        self.duration: float = duration
        
        # Recorte (trim) del contenido fuente
        self.trim_start: float = 0.0
        self.trim_end: float = 0.0  # 0 = usar duracion completa
        
        # Propiedades visuales
        self.opacity: float = 1.0
        self.volume: float = 1.0
        self.speed: float = 1.0
        self.enabled: bool = True
        
        # Color de fondo (para clips de tipo 'color')
        self.color: Tuple[int, int, int] = (0, 0, 0)
        
        # Cache de frames
        self._frames_cache: List[np.ndarray] = []
        self._thumbnail: Optional[np.ndarray] = None
        self._source_duration: float = 0.0
        self._source_fps: float = 30.0
        self._source_width: int = 0
        self._source_height: int = 0
        self._loaded: bool = False
        self._lock = threading.Lock()
        
        # Efectos aplicados al clip
        self.effects: List[Dict[str, Any]] = []
        
        # Metadatos
        self.metadata: Dict[str, Any] = {}
        
        # Cargar informacion del archivo fuente si existe
        if source_path and os.path.exists(source_path):
            self._load_source_info()


    def add_module(self, module):
        """Añade un modulo/efecto al clip."""
        if not hasattr(self, 'effects'):
            self.effects = []
        
        # Convertir modulo a diccionario
        module_dict = {}
        if hasattr(module, 'to_dict'):
            module_dict = module.to_dict()
        elif hasattr(module, '__dict__'):
            module_dict = module.__dict__.copy()
        else:
            module_dict = {"type": str(type(module).__name__)}
        
        # Añadir identificador
        if "id" not in module_dict:
            import uuid
            module_dict["id"] = str(uuid.uuid4())[:8]
        
        self.effects.append(module_dict)
        print(f"[VideoClip] Efecto añadido a '{self.name}': {module_dict.get('type', 'unknown')}")
    def _load_source_info(self):
        """Carga informacion basica del archivo fuente (sin cargar todos los frames)."""
        try:
            if self.source_type == 'image':
                img = cv2.imread(self.source_path)
                if img is not None:
                    self._source_height, self._source_width = img.shape[:2]
                    self._source_duration = 0.0
                    self._source_fps = 0.0
                    if self.duration <= 0:
                        self.duration = 5.0  # Duracion por defecto para imagenes
                    self._loaded = True
                    
            elif self.source_type in ('video', 'gif'):
                cap = cv2.VideoCapture(self.source_path)
                if cap.isOpened():
                    self._source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    self._source_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    self._source_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    self._source_duration = frame_count / self._source_fps if self._source_fps > 0 else 0
                    
                    if self.duration <= 0:
                        self.duration = self._source_duration
                    if self.trim_end <= 0:
                        self.trim_end = self._source_duration
                        
                    # Generar thumbnail del primer frame
                    ok, frame = cap.read()
                    if ok:
                        self._thumbnail = cv2.resize(frame, (160, 90))
                    cap.release()
                    self._loaded = True
                    
            elif self.source_type == 'audio':
                # Para archivos de audio, usar moviepy o pydub para obtener duracion
                try:
                    from moviepy.editor import AudioFileClip
                    audio = AudioFileClip(self.source_path)
                    self._source_duration = audio.duration
                    audio.close()
                except ImportError:
                    try:
                        from pydub import AudioSegment
                        audio = AudioSegment.from_file(self.source_path)
                        self._source_duration = audio.duration_seconds
                    except ImportError:
                        # Fallback: usar ffprobe si esta disponible
                        import subprocess
                        cmd = ['ffprobe', '-v', 'error', '-show_entries', 
                               'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', 
                               self.source_path]
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        if result.returncode == 0:
                            self._source_duration = float(result.stdout.strip())
                        else:
                            self._source_duration = 0.0
                
                if self.duration <= 0:
                    self.duration = self._source_duration if self._source_duration > 0 else 5.0
                if self.trim_end <= 0:
                    self.trim_end = self._source_duration
                    
                # Thumbnail para audio (icono de nota musical)
                self._thumbnail = self._create_audio_thumbnail()
                self._loaded = True
                    
            elif self.source_type == 'color':
                self._loaded = True
                if self.duration <= 0:
                    self.duration = 5.0
                    
        except Exception as e:
            logger.error(f"Error cargando info de {self.source_path}: {e}")

    def load_frames(self, target_width: int = 0, target_height: int = 0):
        """
        Carga frames del archivo fuente en cache.
        Para GIFs carga todos los frames, para videos solo los necesarios.
        """
        with self._lock:
            if self._frames_cache:
                return  # Ya cargado
                
            try:
                if self.source_type == 'image':
                    img = cv2.imread(self.source_path)
                    if img is not None:
                        if target_width > 0 and target_height > 0:
                            img = cv2.resize(img, (target_width, target_height))
                        self._frames_cache = [img]
                        
                elif self.source_type == 'gif':
                    cap = cv2.VideoCapture(self.source_path)
                    frames = []
                    while True:
                        ok, frame = cap.read()
                        if not ok:
                            break
                        if target_width > 0 and target_height > 0:
                            frame = cv2.resize(frame, (target_width, target_height))
                        frames.append(frame)
                    cap.release()
                    self._frames_cache = frames
                    
                elif self.source_type == 'video':
                    # Para video, no cargamos todos los frames en memoria
                    # Se usa get_frame_at_time() bajo demanda
                    pass
                    
            except Exception as e:
                logger.error(f"Error cargando frames: {e}")

    def get_frame_at_time(self, time_in_clip: float, width: int = 0, height: int = 0) -> Optional[np.ndarray]:
        """
        Obtiene el frame correspondiente a un tiempo dentro del clip.
        Usa cache global LRU para mejorar rendimiento de scrubbing/preview.
        
        Args:
            time_in_clip: Tiempo relativo dentro del clip (0.0 = inicio del clip)
            width: Ancho deseado (0 = original)
            height: Alto deseado (0 = original)
            
        Returns:
            Frame como numpy array BGR, o None si no disponible
        """
        if not self.enabled:
            return None
            
        # Import local para evitar dependencias circulares
        from core.video_cache import cached_get_frame
        return cached_get_frame(self, time_in_clip, width, height)
    
    def _get_frame_at_time_impl(self, time_in_clip: float, width: int = 0, height: int = 0) -> Optional[np.ndarray]:
        """
        Implementacion real para obtener un frame.
        Llamado por el sistema de cache si el frame no esta cacheado.
        """
        frame = None
        source_time = (time_in_clip * self.speed) + self.trim_start
        
        try:
            if self.source_type == 'color':
                h = height if height > 0 else 1080
                w = width if width > 0 else 1920
                frame = np.full((h, w, 3), self.color[::-1], dtype=np.uint8)
                
            elif self.source_type == 'image':
                # Las imagenes se muestran estaticas durante toda la duracion del clip
                if not self._frames_cache:
                    # Cargar imagen una vez y cachearla
                    img = cv2.imread(self.source_path)
                    if img is not None:
                        self._frames_cache = [img]
                
                if self._frames_cache:
                    frame = self._frames_cache[0].copy()
                    
            elif self.source_type == 'gif':
                if not self._frames_cache:
                    self.load_frames(width, height)
                if self._frames_cache:
                    fps = self._source_fps if self._source_fps > 0 else 10
                    gif_duration = len(self._frames_cache) / fps
                    
                    # Si el clip es mas largo que el GIF, hacer loop
                    if self.duration > gif_duration and gif_duration > 0:
                        # Calcular tiempo loopado
                        looped_time = source_time % gif_duration
                        idx = int(looped_time * fps) % len(self._frames_cache)
                    else:
                        # Si el clip es mas corto, escalar tiempo
                        if self.duration > 0:
                            scaled_time = source_time * (gif_duration / self.duration)
                            idx = min(int(scaled_time * fps), len(self._frames_cache) - 1)
                        else:
                            idx = 0
                    
                    frame = self._frames_cache[idx].copy()
                    
            elif self.source_type == 'video':
                cap = cv2.VideoCapture(self.source_path)
                if cap.isOpened():
                    # Posicionar en el tiempo correcto
                    cap.set(cv2.CAP_PROP_POS_MSEC, source_time * 1000)
                    ok, frame = cap.read()
                    cap.release()
                    if not ok:
                        frame = None
                        
        except Exception as e:
            logger.error(f"Error obteniendo frame en t={time_in_clip:.2f}: {e}")
            return None
            
        # Redimensionar si es necesario
        if frame is not None and width > 0 and height > 0:
            frame = cv2.resize(frame, (width, height))
            
        # Aplicar opacidad
        if frame is not None and self.opacity < 1.0:
            frame = (frame.astype(np.float32) * self.opacity).astype(np.uint8)
            
        # Aplicar efectos del clip
        if frame is not None and hasattr(self, 'effects') and self.effects:
            import cv2
            import numpy as np
            for effect in self.effects:
                try:
                    effect_type = effect.get('type', 'unknown')
                    
                    if effect_type == 'transition':
                        # Transicion simple (fade)
                        subtype = effect.get('subtype', 'fade_in')
                        if subtype == 'fade_in':
                            # Fade in al inicio del clip
                            clip_time = time_in_clip
                            duration = effect.get('duration', 1.0)
                            if clip_time < duration:
                                alpha = clip_time / duration
                                frame = (frame.astype(np.float32) * alpha).astype(np.uint8)
                        elif subtype == 'fade_out':
                            # Fade out al final del clip
                            clip_time = time_in_clip
                            duration = effect.get('duration', 1.0)
                            if clip_time > self.duration - duration:
                                alpha = (self.duration - clip_time) / duration
                                frame = (frame.astype(np.float32) * alpha).astype(np.uint8)
                    
                    elif effect_type == 'waveform':
                        # Efecto visual de waveform
                        h, w = frame.shape[:2]
                        overlay = np.zeros((h, w, 3), dtype=np.uint8)
                        for x in range(0, w, 15):
                            height = np.random.randint(20, h//3)
                            y1 = h//2 - height//2
                            y2 = h//2 + height//2
                            cv2.line(overlay, (x, y1), (x, y2), (0, 200, 255), 3)
                        frame = cv2.addWeighted(frame, 0.8, overlay, 0.2, 0)
                        
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Error en efecto: {e}")
        return frame
    def get_thumbnail(self, width: int = 160, height: int = 90) -> Optional[np.ndarray]:
        """Obtiene un thumbnail del clip para la interfaz."""
        if self._thumbnail is not None:
            return cv2.resize(self._thumbnail, (width, height))
            
        if self.source_type == 'color':
            thumb = np.full((height, width, 3), self.color[::-1], dtype=np.uint8)
            return thumb
            
        if self.source_path and os.path.exists(self.source_path):
            try:
                if self.source_type == 'image':
                    img = cv2.imread(self.source_path)
                    if img is not None:
                        self._thumbnail = cv2.resize(img, (width, height))
                        return self._thumbnail
                else:
                    cap = cv2.VideoCapture(self.source_path)
                    ok, frame = cap.read()
                    cap.release()
                    if ok:
                        self._thumbnail = cv2.resize(frame, (width, height))
                        return self._thumbnail
            except Exception:
                pass
                
        # Thumbnail por defecto (gris oscuro)
        return np.full((height, width, 3), (40, 40, 40), dtype=np.uint8)

    def _create_audio_thumbnail(self, width: int = 160, height: int = 90) -> np.ndarray:
        """Crea un thumbnail para archivos de audio (icono de nota musical)."""
        thumb = np.full((height, width, 3), (30, 60, 90), dtype=np.uint8)  # Azul oscuro
        
        # Dibujar icono simple de nota musical
        center_x, center_y = width // 2, height // 2
        radius = min(width, height) // 4
        
        # Circulo
        cv2.circle(thumb, (center_x, center_y), radius, (100, 180, 255), -1)
        
        # Linea vertical (asta)
        cv2.line(thumb, (center_x + radius, center_y - radius // 2),
                 (center_x + radius, center_y + radius), (255, 255, 255), 2)
        
        # Nota musical (ovalo)
        cv2.ellipse(thumb, (center_x - radius // 3, center_y - radius // 2),
                    (radius // 2, radius // 3), 0, 0, 360, (255, 255, 255), -1)
        
        return thumb

    # -- Operaciones de edicion --

    def split_at(self, split_time: float) -> Optional['VideoClip']:
        """
        Divide el clip en dos partes en el tiempo indicado.
        
        Args:
            split_time: Tiempo relativo dentro del clip donde dividir
            
        Returns:
            Nuevo clip con la segunda parte, o None si la division no es valida
        """
        if split_time <= 0 or split_time >= self.duration:
            return None
            
        # Crear segundo clip
        second_clip = VideoClip(
            source_path=self.source_path,
            source_type=self.source_type,
            track_index=self.track_index,
            start_time=self.start_time + split_time,
            duration=self.duration - split_time,
            name=f"{self.name} (2)"
        )
        
        # Ajustar trim del segundo clip
        second_clip.trim_start = self.trim_start + (split_time * self.speed)
        second_clip.trim_end = self.trim_end
        second_clip.opacity = self.opacity
        second_clip.volume = self.volume
        second_clip.speed = self.speed
        second_clip.color = self.color
        second_clip._source_duration = self._source_duration
        second_clip._source_fps = self._source_fps
        second_clip._source_width = self._source_width
        second_clip._source_height = self._source_height
        second_clip._loaded = self._loaded
        
        # Ajustar el clip actual (primera parte)
        self.duration = split_time
        effective_end = self.trim_start + (split_time * self.speed)
        self.trim_end = effective_end
        self.name = f"{self.name} (1)" if "(1)" not in self.name and "(2)" not in self.name else self.name
        
        return second_clip

    def trim(self, new_start: float = None, new_end: float = None):
        """
        Ajusta los puntos de trim del clip.
        
        Args:
            new_start: Nuevo punto de inicio en el fuente (segundos)
            new_end: Nuevo punto de fin en el fuente (segundos)
        """
        if new_start is not None:
            self.trim_start = max(0, new_start)
        if new_end is not None:
            max_end = self._source_duration if self._source_duration > 0 else float('inf')
            self.trim_end = min(new_end, max_end)
            
        # Recalcular duracion
        effective_end = self.trim_end if self.trim_end > 0 else self._source_duration
        if effective_end > self.trim_start:
            self.duration = (effective_end - self.trim_start) / self.speed

    def move_to(self, new_start_time: float, new_track: int = None):
        """Mueve el clip a una nueva posicion temporal y/o track."""
        self.start_time = max(0, new_start_time)
        if new_track is not None:
            self.track_index = max(0, new_track)

    @property
    def end_time(self) -> float:
        """Tiempo de finalizacion del clip en el timeline."""
        return self.start_time + self.duration

    @property
    def source_info(self) -> Dict[str, Any]:
        """Informacion resumida del archivo fuente."""
        return {
            "path": self.source_path,
            "type": self.source_type,
            "duration": self._source_duration,
            "fps": self._source_fps,
            "width": self._source_width,
            "height": self._source_height,
            "loaded": self._loaded,
        }

    # -- Serializacion --

    def to_dict(self) -> Dict[str, Any]:
        """Serializa el clip a un diccionario para guardado."""
        return {
            "clip_id": self.clip_id,
            "source_path": self.source_path,
            "source_type": self.source_type,
            "name": self.name,
            "track_index": self.track_index,
            "start_time": self.start_time,
            "duration": self.duration,
            "trim_start": self.trim_start,
            "trim_end": self.trim_end,
            "opacity": self.opacity,
            "volume": self.volume,
            "speed": self.speed,
            "enabled": self.enabled,
            "color": list(self.color),
            "effects": self.effects,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VideoClip':
        """Crea un VideoClip desde un diccionario serializado."""
        clip = cls(
            source_path=data.get("source_path", ""),
            source_type=data.get("source_type", "video"),
            track_index=data.get("track_index", 0),
            start_time=data.get("start_time", 0.0),
            duration=data.get("duration", 0.0),
            name=data.get("name", ""),
        )
        clip.clip_id = data.get("clip_id", clip.clip_id)
        clip.trim_start = data.get("trim_start", 0.0)
        clip.trim_end = data.get("trim_end", 0.0)
        clip.opacity = data.get("opacity", 1.0)
        clip.volume = data.get("volume", 1.0)
        clip.speed = data.get("speed", 1.0)
        clip.enabled = data.get("enabled", True)
        clip.color = tuple(data.get("color", [0, 0, 0]))
        clip.effects = data.get("effects", [])
        clip.metadata = data.get("metadata", {})
        return clip

    def __repr__(self):
        return (f"VideoClip(id={self.clip_id}, name='{self.name}', "
                f"track={self.track_index}, start={self.start_time:.2f}s, "
                f"dur={self.duration:.2f}s, type={self.source_type})")


def detect_source_type(filepath: str) -> str:
    """Detecta el tipo de fuente basado en la extension del archivo."""
    ext = os.path.splitext(filepath)[1].lower()
    video_exts = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.webm', '.flv'}
    image_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    gif_exts = {'.gif'}
    audio_exts = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac'}
    
    if ext in video_exts:
        return 'video'
    elif ext in image_exts:
        return 'image'
    elif ext in gif_exts:
        return 'gif'
    elif ext in audio_exts:
        return 'audio'
    return 'video'  # Por defecto
