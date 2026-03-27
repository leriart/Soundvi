#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestor de Proyecto -- Maneja el estado completo del proyecto Soundvi.

Coordina el timeline, clips, modulos, configuracion y archivos de medios.
Soporta guardar/cargar proyectos en formato .svproj (JSON).
"""

from __future__ import annotations
import os
import json
import time
from typing import Optional, Dict, Any, List
from pathlib import Path

from core.timeline import Timeline
from core.video_clip import VideoClip, detect_source_type
from core.commands import CommandManager


class MediaItem:
    """Elemento de la biblioteca de medios del proyecto."""

    def __init__(self, path: str, name: str = "", media_type: str = ""):
        self.path: str = path
        self.name: str = name or os.path.basename(path)
        self.media_type: str = media_type or detect_source_type(path)
        self.tags: List[str] = []
        self.favorite: bool = False
        self.added_at: float = time.time()
        
        # Metadatos del archivo
        self.file_size: int = 0
        self.duration: float = 0.0
        self.width: int = 0
        self.height: int = 0
        
        if os.path.exists(path):
            self.file_size = os.path.getsize(path)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "media_type": self.media_type,
            "tags": self.tags,
            "favorite": self.favorite,
            "added_at": self.added_at,
            "file_size": self.file_size,
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MediaItem':
        item = cls(
            path=data.get("path", ""),
            name=data.get("name", ""),
            media_type=data.get("media_type", ""),
        )
        item.tags = data.get("tags", [])
        item.favorite = data.get("favorite", False)
        item.added_at = data.get("added_at", time.time())
        item.file_size = data.get("file_size", 0)
        item.duration = data.get("duration", 0.0)
        item.width = data.get("width", 0)
        item.height = data.get("height", 0)
        return item


class ProjectManager:
    """
    Gestor principal del proyecto Soundvi.
    
    Coordina todos los subsistemas:
    - Timeline con tracks y clips
    - Biblioteca de medios
    - Sistema de comandos (undo/redo)
    - Configuracion del proyecto
    - Guardado/carga de proyectos
    """

    # Version del formato de proyecto
    PROJECT_VERSION = "4.2.0"

    def __init__(self):
        # -- Subsistemas --
        self.timeline: Timeline = Timeline()
        self.command_manager: CommandManager = CommandManager(max_history=100)
        
        # -- Biblioteca de medios --
        self.media_library: List[MediaItem] = []
        
        # -- Informacion del proyecto --
        self.project_name: str = "Sin titulo"
        self.project_path: str = ""  # Ruta del archivo .svproj
        self.created_at: float = time.time()
        self.modified_at: float = time.time()
        self.author: str = ""
        self.description: str = ""
        
        # -- Configuracion de renderizado --
        self.render_config: Dict[str, Any] = {
            "width": 1920,
            "height": 1080,
            "fps": 30,
            "codec": "libx264",
            "preset": "medium",
            "bitrate": "8M",
            "audio_codec": "aac",
            "audio_bitrate": "192k",
            "use_gpu": False,
            "gpu_codec": "h264_nvenc",
            "fade_duration": 3.0,
        }
        
        # -- Metadatos del video --
        self.video_metadata: Dict[str, str] = {
            "title": "",
            "description": "",
            "copyright": "",
            "artist": "",
        }
        
        # -- Estado de modificacion --
        self._is_modified: bool = False
        
        # Registrar callback para marcar modificaciones
        self.command_manager.on_change(self._mark_modified)

    # -- Biblioteca de Medios --

    def add_media(self, path: str) -> Optional[MediaItem]:
        """Agrega un archivo a la biblioteca de medios."""
        if not os.path.exists(path):
            return None
            
        # Verificar que no este duplicado
        for item in self.media_library:
            if item.path == path:
                return item
                
        item = MediaItem(path)
        self.media_library.append(item)
        self._mark_modified()
        return item

    def remove_media(self, path: str) -> bool:
        """Elimina un archivo de la biblioteca de medios."""
        for i, item in enumerate(self.media_library):
            if item.path == path:
                self.media_library.pop(i)
                self._mark_modified()
                return True
        return False

    def get_media_by_type(self, media_type: str) -> List[MediaItem]:
        """Filtra medios por tipo."""
        return [m for m in self.media_library if m.media_type == media_type]

    def search_media(self, query: str) -> List[MediaItem]:
        """Busca medios por nombre o tags."""
        query_lower = query.lower()
        return [m for m in self.media_library
                if query_lower in m.name.lower() or 
                any(query_lower in tag.lower() for tag in m.tags)]

    # -- Gestion de Clips --

    def create_clip_from_media(self, media_path: str, track_index: int = 0,
                                start_time: float = 0.0) -> Optional[VideoClip]:
        """
        Crea un clip a partir de un archivo de medios y lo agrega al timeline.
        
        Args:
            media_path: Ruta al archivo de medios
            track_index: Indice del track donde colocar el clip
            start_time: Tiempo de inicio en el timeline
            
        Returns:
            El VideoClip creado, o None si fallo
        """
        source_type = detect_source_type(media_path)
        clip = VideoClip(
            source_path=media_path,
            source_type=source_type,
            track_index=track_index,
            start_time=start_time,
        )
        
        if self.timeline.add_clip(clip, track_index):
            # Agregar tambien a la biblioteca si no esta
            self.add_media(media_path)
            self._mark_modified()
            return clip
        return None

    # -- Estado del proyecto --

    @property
    def is_modified(self) -> bool:
        """Indica si el proyecto tiene cambios sin guardar."""
        return self._is_modified

    def _mark_modified(self):
        """Marca el proyecto como modificado."""
        self._is_modified = True
        self.modified_at = time.time()

    def mark_saved(self):
        """Marca el proyecto como guardado."""
        self._is_modified = False

    # -- Nuevo proyecto --

    def new_project(self):
        """Crea un nuevo proyecto limpio."""
        self.timeline = Timeline()
        self.command_manager.clear()
        self.media_library.clear()
        self.project_name = "Sin titulo"
        self.project_path = ""
        self.created_at = time.time()
        self.modified_at = time.time()
        self.author = ""
        self.description = ""
        self.video_metadata = {
            "title": "", "description": "", "copyright": "", "artist": "",
        }
        self._is_modified = False

    # -- Guardar/Cargar Proyecto --

    def save_project(self, path: str = "") -> bool:
        """
        Guarda el proyecto en formato .svproj (JSON).
        
        Args:
            path: Ruta del archivo. Si vacia, usa la ruta anterior.
            
        Returns:
            True si se guardo exitosamente
        """
        if path:
            self.project_path = path
        elif not self.project_path:
            return False
            
        project_data = {
            "version": self.PROJECT_VERSION,
            "project_name": self.project_name,
            "created_at": self.created_at,
            "modified_at": time.time(),
            "author": self.author,
            "description": self.description,
            "render_config": self.render_config,
            "video_metadata": self.video_metadata,
            "timeline": self.timeline.to_dict(),
            "media_library": [m.to_dict() for m in self.media_library],
        }
        
        try:
            with open(self.project_path, "w", encoding="utf-8") as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
            self.mark_saved()
            print(f"[ProjectManager] Proyecto guardado: {self.project_path}")
            return True
        except Exception as e:
            print(f"[ProjectManager] Error al guardar: {e}")
            return False

    def load_project(self, path: str) -> bool:
        """
        Carga un proyecto desde archivo .svproj.
        
        Args:
            path: Ruta del archivo del proyecto
            
        Returns:
            True si se cargo exitosamente
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            self.project_path = path
            self.project_name = data.get("project_name", "Sin titulo")
            self.created_at = data.get("created_at", time.time())
            self.modified_at = data.get("modified_at", time.time())
            self.author = data.get("author", "")
            self.description = data.get("description", "")
            self.render_config = data.get("render_config", self.render_config)
            self.video_metadata = data.get("video_metadata", self.video_metadata)
            
            # Cargar timeline
            timeline_data = data.get("timeline", {})
            if timeline_data:
                self.timeline = Timeline.from_dict(timeline_data)
                
            # Cargar biblioteca de medios
            self.media_library.clear()
            for media_data in data.get("media_library", []):
                item = MediaItem.from_dict(media_data)
                self.media_library.append(item)
                
            self.command_manager.clear()
            self._is_modified = False
            
            print(f"[ProjectManager] Proyecto cargado: {path}")
            return True
            
        except Exception as e:
            print(f"[ProjectManager] Error al cargar: {e}")
            return False

    def get_project_summary(self) -> Dict[str, Any]:
        """Retorna un resumen del estado del proyecto."""
        total_clips = sum(len(t.clips) for t in self.timeline.tracks)
        return {
            "name": self.project_name,
            "path": self.project_path,
            "tracks": len(self.timeline.tracks),
            "clips": total_clips,
            "duration": self.timeline.duration,
            "media_items": len(self.media_library),
            "modified": self._is_modified,
            "resolution": f"{self.render_config['width']}x{self.render_config['height']}",
            "fps": self.render_config['fps'],
        }

    def __repr__(self):
        return (f"ProjectManager(name='{self.project_name}', "
                f"clips={sum(len(t.clips) for t in self.timeline.tracks)}, "
                f"media={len(self.media_library)})")
