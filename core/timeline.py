#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Timeline Multi-Track -- Sistema de timeline con multiples pistas.

Soporta tracks de video, audio, subtitulos y efectos.
Cada track puede contener multiples clips organizados temporalmente.
"""

from __future__ import annotations
import uuid
from typing import Optional, Dict, Any, List, Tuple

import numpy as np

from core.video_clip import VideoClip


class Track:
    """
    Representa una pista individual en el timeline.
    
    Tipos de track:
        'video'     - Pistas de video/imagenes
        'audio'     - Pistas de audio
        'subtitle'  - Pistas de subtitulos
        'effect'    - Pistas de efectos/modulos
    """

    TRACK_TYPES = ('video', 'audio', 'subtitle', 'effect')

    def __init__(self, track_type: str = "video", name: str = "", index: int = 0):
        self.track_id: str = str(uuid.uuid4())[:8]
        self.track_type: str = track_type if track_type in self.TRACK_TYPES else "video"
        self.name: str = name or f"{track_type.capitalize()} {index + 1}"
        self.index: int = index
        self.clips: List[VideoClip] = []
        self.muted: bool = False
        self.locked: bool = False
        self.visible: bool = True
        self.solo: bool = False
        self.height: int = 60  # Altura visual en pixeles
        self.color: str = self._default_color()
        self.volume: float = 1.0  # Solo para tracks de audio
        self.pan: float = 0.0    # Panorama: -1.0 (izq) a 1.0 (der)

    def _default_color(self) -> str:
        """Color por defecto segun tipo de track."""
        colors = {
            'video': '#3498db',
            'audio': '#2ecc71',
            'subtitle': '#e67e22',
            'effect': '#9b59b6',
        }
        return colors.get(self.track_type, '#95a5a6')

    def add_clip(self, clip: VideoClip) -> bool:
        """
        Agrega un clip al track verificando que no se superponga.
        
        Returns:
            True si se agrego exitosamente
        """
        if self.locked:
            return False
            
        clip.track_index = self.index
        
        # Verificar superposicion
        for existing in self.clips:
            if self._clips_overlap(clip, existing):
                return False
                
        self.clips.append(clip)
        self._sort_clips()
        return True

    def remove_clip(self, clip_id: str) -> Optional[VideoClip]:
        """Elimina un clip del track por su ID."""
        if self.locked:
            return None
        for i, clip in enumerate(self.clips):
            if clip.clip_id == clip_id:
                return self.clips.pop(i)
        return None

    def get_clip_at_time(self, time: float) -> Optional[VideoClip]:
        """Obtiene el clip activo en un tiempo dado."""
        for clip in self.clips:
            if clip.start_time <= time < clip.end_time and clip.enabled:
                return clip
        return None

    def get_clips_in_range(self, start: float, end: float) -> List[VideoClip]:
        """Obtiene todos los clips que se encuentran en un rango temporal."""
        result = []
        for clip in self.clips:
            if clip.end_time > start and clip.start_time < end:
                result.append(clip)
        return result

    def _clips_overlap(self, clip_a: VideoClip, clip_b: VideoClip) -> bool:
        """Verifica si dos clips se superponen temporalmente."""
        return clip_a.start_time < clip_b.end_time and clip_b.start_time < clip_a.end_time

    def _sort_clips(self):
        """Ordena clips por tiempo de inicio."""
        self.clips.sort(key=lambda c: c.start_time)

    @property
    def total_duration(self) -> float:
        """Duracion total del track (hasta el fin del ultimo clip)."""
        if not self.clips:
            return 0.0
        return max(c.end_time for c in self.clips)

    def to_dict(self) -> Dict[str, Any]:
        """Serializa el track."""
        return {
            "track_id": self.track_id,
            "track_type": self.track_type,
            "name": self.name,
            "index": self.index,
            "muted": self.muted,
            "locked": self.locked,
            "visible": self.visible,
            "solo": self.solo,
            "height": self.height,
            "color": self.color,
            "volume": self.volume,
            "pan": self.pan,
            "clips": [c.to_dict() for c in self.clips],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Track':
        """Crea un Track desde un diccionario."""
        track = cls(
            track_type=data.get("track_type", "video"),
            name=data.get("name", ""),
            index=data.get("index", 0),
        )
        track.track_id = data.get("track_id", track.track_id)
        track.muted = data.get("muted", False)
        track.locked = data.get("locked", False)
        track.visible = data.get("visible", True)
        track.solo = data.get("solo", False)
        track.height = data.get("height", 60)
        track.color = data.get("color", track.color)
        track.volume = data.get("volume", 1.0)
        track.pan = data.get("pan", 0.0)
        for clip_data in data.get("clips", []):
            clip = VideoClip.from_dict(clip_data)
            track.clips.append(clip)
        track._sort_clips()
        return track


class Timeline:
    """
    Timeline multi-track principal de Soundvi.
    
    Gestiona todas las pistas y proporciona metodos para:
    - Agregar/eliminar tracks y clips
    - Navegar temporalmente
    - Renderizar el frame compuesto para un tiempo dado
    - Zoom y scroll del timeline
    """

    def __init__(self):
        self.tracks: List[Track] = []
        self.playhead: float = 0.0       # Posicion actual del cabezal
        self.duration: float = 0.0        # Duracion total del proyecto
        self.zoom_level: float = 1.0      # Nivel de zoom (pixeles por segundo)
        self.scroll_offset: float = 0.0   # Offset de scroll horizontal
        self.snap_enabled: bool = True     # Snap a otros clips
        self.snap_threshold: float = 0.1   # Umbral de snap en segundos
        self.selection: List[str] = []     # IDs de clips seleccionados
        self.loop_start: float = 0.0       # Inicio de region de loop
        self.loop_end: float = 0.0         # Fin de region de loop
        self.loop_enabled: bool = False    # Loop activado
        
        # Crear tracks por defecto
        self._create_default_tracks()

    def _create_default_tracks(self):
        """Crea las pistas por defecto del timeline."""
        default_tracks = [
            ("video", "Video 1"),
            ("audio", "Audio 1"),
            ("subtitle", "Subtitulos"),
            ("effect", "Efectos"),
        ]
        for i, (track_type, name) in enumerate(default_tracks):
            track = Track(track_type=track_type, name=name, index=i)
            self.tracks.append(track)

    # -- Gestion de Tracks --

    def add_track(self, track_type: str = "video", name: str = "") -> Track:
        """Agrega un nuevo track al timeline."""
        index = len(self.tracks)
        track = Track(track_type=track_type, name=name, index=index)
        self.tracks.append(track)
        self._update_duration()
        return track

    def remove_track(self, track_id: str) -> bool:
        """Elimina un track por su ID."""
        for i, track in enumerate(self.tracks):
            if track.track_id == track_id:
                self.tracks.pop(i)
                # Reindexar tracks
                for j, t in enumerate(self.tracks):
                    t.index = j
                self._update_duration()
                return True
        return False

    def get_track(self, index: int) -> Optional[Track]:
        """Obtiene un track por su indice."""
        if 0 <= index < len(self.tracks):
            return self.tracks[index]
        return None

    def get_tracks_by_type(self, track_type: str) -> List[Track]:
        """Obtiene todos los tracks de un tipo especifico."""
        return [t for t in self.tracks if t.track_type == track_type]

    # -- Gestion de Clips --

    def add_clip(self, clip: VideoClip, track_index: int = 0) -> bool:
        """Agrega un clip a un track especifico."""
        track = self.get_track(track_index)
        if track is None:
            return False
        result = track.add_clip(clip)
        if result:
            self._update_duration()
        return result

    def remove_clip(self, clip_id: str) -> Optional[VideoClip]:
        """Busca y elimina un clip en todos los tracks."""
        for track in self.tracks:
            clip = track.remove_clip(clip_id)
            if clip is not None:
                self._update_duration()
                return clip
        return None

    def find_clip(self, clip_id: str) -> Optional[Tuple[VideoClip, Track]]:
        """Busca un clip por ID y retorna el clip y su track."""
        for track in self.tracks:
            for clip in track.clips:
                if clip.clip_id == clip_id:
                    return (clip, track)
        return None

    def get_all_clips(self) -> List[VideoClip]:
        """Obtiene todos los clips de todos los tracks."""
        clips = []
        for track in self.tracks:
            clips.extend(track.clips)
        return clips

    def move_clip(self, clip_id: str, new_start: float, new_track_index: int = None) -> bool:
        """Mueve un clip a una nueva posicion y/o track."""
        result = self.find_clip(clip_id)
        if result is None:
            return False
            
        clip, current_track = result
        
        # Snap a otros clips si esta habilitado
        if self.snap_enabled:
            new_start = self._snap_time(new_start, clip_id)
        
        if new_track_index is not None and new_track_index != current_track.index:
            # Mover a otro track
            current_track.remove_clip(clip_id)
            clip.start_time = new_start
            target_track = self.get_track(new_track_index)
            if target_track is None:
                current_track.add_clip(clip)
                return False
            if not target_track.add_clip(clip):
                current_track.add_clip(clip)
                return False
        else:
            clip.start_time = new_start
            current_track._sort_clips()
            
        self._update_duration()
        return True

    def split_clip(self, clip_id: str, split_time: float) -> Optional[VideoClip]:
        """Divide un clip en el tiempo indicado del timeline."""
        result = self.find_clip(clip_id)
        if result is None:
            return None
            
        clip, track = result
        # Convertir tiempo del timeline a tiempo relativo del clip
        relative_time = split_time - clip.start_time
        new_clip = clip.split_at(relative_time)
        
        if new_clip is not None:
            track.add_clip(new_clip)
            self._update_duration()
            
        return new_clip

    # -- Snap --

    def _snap_time(self, time: float, exclude_clip_id: str = "") -> float:
        """Ajusta el tiempo al borde mas cercano de otro clip (snap)."""
        closest = time
        min_dist = self.snap_threshold
        
        for track in self.tracks:
            for clip in track.clips:
                if clip.clip_id == exclude_clip_id:
                    continue
                # Snap al inicio del clip
                dist_start = abs(time - clip.start_time)
                if dist_start < min_dist:
                    min_dist = dist_start
                    closest = clip.start_time
                # Snap al fin del clip
                dist_end = abs(time - clip.end_time)
                if dist_end < min_dist:
                    min_dist = dist_end
                    closest = clip.end_time
                    
        return closest

    # -- Renderizado --

    def get_composite_frame(self, time: float, width: int, height: int) -> np.ndarray:
        """
        Genera el frame compuesto para un tiempo dado.
        Combina todos los clips activos de los tracks de video.
        
        Args:
            time: Tiempo en el timeline (segundos)
            width: Ancho del frame de salida
            height: Alto del frame de salida
            
        Returns:
            Frame compuesto como numpy array BGR
        """
        # Frame base negro
        composite = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Recorrer tracks de video de abajo hacia arriba (el indice mas alto se dibuja encima)
        video_tracks = [t for t in self.tracks if t.track_type == 'video' and t.visible and not t.muted]
        
        for track in video_tracks:
            clip = track.get_clip_at_time(time)
            if clip is None:
                continue
                
            # Tiempo relativo dentro del clip
            clip_time = time - clip.start_time
            frame = clip.get_frame_at_time(clip_time, width, height)
            
            if frame is not None:
                if clip.opacity >= 1.0:
                    composite = frame
                else:
                    # Mezclar con opacidad
                    alpha = clip.opacity
                    composite = cv2.addWeighted(frame, alpha, composite, 1.0 - alpha, 0)
                    
        return composite

    # -- Navegacion --

    def set_playhead(self, time: float):
        """Establece la posicion del cabezal de reproduccion."""
        self.playhead = max(0.0, min(time, self.duration))

    def move_playhead(self, delta: float):
        """Mueve el cabezal relativamente."""
        self.set_playhead(self.playhead + delta)

    def goto_next_clip_edge(self):
        """Mueve el cabezal al borde del siguiente clip."""
        edges = set()
        for track in self.tracks:
            for clip in track.clips:
                if clip.start_time > self.playhead + 0.01:
                    edges.add(clip.start_time)
                if clip.end_time > self.playhead + 0.01:
                    edges.add(clip.end_time)
        if edges:
            self.playhead = min(edges)

    def goto_prev_clip_edge(self):
        """Mueve el cabezal al borde del clip anterior."""
        edges = set()
        for track in self.tracks:
            for clip in track.clips:
                if clip.start_time < self.playhead - 0.01:
                    edges.add(clip.start_time)
                if clip.end_time < self.playhead - 0.01:
                    edges.add(clip.end_time)
        if edges:
            self.playhead = max(edges)

    # -- Zoom --

    def zoom_in(self, factor: float = 1.5):
        """Aumenta el zoom del timeline."""
        self.zoom_level = min(self.zoom_level * factor, 500.0)

    def zoom_out(self, factor: float = 1.5):
        """Disminuye el zoom del timeline."""
        self.zoom_level = max(self.zoom_level / factor, 0.1)

    def zoom_to_fit(self, canvas_width: int):
        """Ajusta el zoom para que todo el timeline quepa en el canvas."""
        if self.duration > 0 and canvas_width > 0:
            self.zoom_level = canvas_width / self.duration
            self.scroll_offset = 0.0

    # -- Utilidades --

    def _update_duration(self):
        """Recalcula la duracion total del timeline."""
        max_end = 0.0
        for track in self.tracks:
            track_dur = track.total_duration
            if track_dur > max_end:
                max_end = track_dur
        self.duration = max_end

    def time_to_pixels(self, time: float) -> float:
        """Convierte tiempo a posicion en pixeles."""
        return (time - self.scroll_offset) * self.zoom_level

    def pixels_to_time(self, pixels: float) -> float:
        """Convierte posicion en pixeles a tiempo."""
        if self.zoom_level <= 0:
            return 0.0
        return (pixels / self.zoom_level) + self.scroll_offset

    def clear(self):
        """Limpia todo el timeline."""
        for track in self.tracks:
            track.clips.clear()
        self.playhead = 0.0
        self.duration = 0.0
        self.selection.clear()

    # -- Serializacion --

    def to_dict(self) -> Dict[str, Any]:
        """Serializa el timeline completo."""
        return {
            "tracks": [t.to_dict() for t in self.tracks],
            "playhead": self.playhead,
            "duration": self.duration,
            "zoom_level": self.zoom_level,
            "snap_enabled": self.snap_enabled,
            "loop_start": self.loop_start,
            "loop_end": self.loop_end,
            "loop_enabled": self.loop_enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Timeline':
        """Crea un Timeline desde un diccionario."""
        timeline = cls()
        timeline.tracks.clear()
        for track_data in data.get("tracks", []):
            track = Track.from_dict(track_data)
            timeline.tracks.append(track)
        timeline.playhead = data.get("playhead", 0.0)
        timeline.duration = data.get("duration", 0.0)
        timeline.zoom_level = data.get("zoom_level", 1.0)
        timeline.snap_enabled = data.get("snap_enabled", True)
        timeline.loop_start = data.get("loop_start", 0.0)
        timeline.loop_end = data.get("loop_end", 0.0)
        timeline.loop_enabled = data.get("loop_enabled", False)
        return timeline

    def __repr__(self):
        total_clips = sum(len(t.clips) for t in self.tracks)
        return f"Timeline(tracks={len(self.tracks)}, clips={total_clips}, dur={self.duration:.1f}s)"
