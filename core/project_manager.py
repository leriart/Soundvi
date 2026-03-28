#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestor de Proyecto -- Maneja el estado completo del proyecto Soundvi.

Coordina el timeline, clips, módulos, configuración y archivos de medios.
Soporta guardar/cargar proyectos en formato .soundvi (comprimido+cifrado) y .svproj (JSON legacy).
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
        self.embedded: bool = False
        self.embedded_path: str = ""

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
            "embedded": self.embedded,
            "embedded_path": self.embedded_path,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MediaItem:
        item = cls(
            path=data.get("path", ""),
            name=data.get("name", ""),
            media_type=data.get("media_type", data.get("type", ""))
        )
        item.tags = data.get("tags", [])
        item.favorite = data.get("favorite", False)
        item.added_at = data.get("added_at", time.time())
        item.file_size = data.get("file_size", data.get("size", 0))
        item.duration = data.get("duration", 0.0)
        item.width = data.get("width", 0)
        item.height = data.get("height", 0)
        item.embedded = data.get("embedded", False)
        item.embedded_path = data.get("embedded_path", "")
        return item


class ProjectManager:
    """
    Gestor principal del proyecto Soundvi.

    Coordina todos los subsistemas:
    - Timeline con tracks y clips
    - Biblioteca de medios
    - Sistema de comandos (undo/redo)
    - Configuración del proyecto
    - Módulos activos
    - Guardado/carga de proyectos
    """

    # Versión del formato de proyecto
    PROJECT_VERSION = "5.0.0"

    def __init__(self):
        # -- Subsistemas --
        self.timeline: Timeline = Timeline()
        self.command_manager: CommandManager = CommandManager(max_history=100)

        # -- Biblioteca de medios --
        self.media_library: List[MediaItem] = []

        # -- Configuración del proyecto --
        self.project_path: str = ""
        self.project_name: str = "Nuevo proyecto"
        self.created_at: float = time.time()
        self.modified_at: float = time.time()
        self.author: str = ""
        self.description: str = ""

        # -- Configuración de render --
        self.render_config: Dict[str, Any] = {
            "resolution": "1920x1080",
            "fps": 30,
            "codec": "h264",
            "bitrate": "10M",
            "audio_bitrate": "192k",
            "output_format": "mp4"
        }

        # -- Metadatos de video --
        self.video_metadata: Dict[str, Any] = {}

        # -- Estado de módulos (serializable) --
        self.modules_state: List[Dict[str, Any]] = []

        # -- Estado interno --
        self._is_modified: bool = False

    # -------------------------------------------------------------------------
    # Nuevo proyecto
    # -------------------------------------------------------------------------
    def new_project(self):
        """Crea un proyecto completamente nuevo, limpiando todo el estado."""
        self.clear()
        print("[ProjectManager] Nuevo proyecto creado")

    # -------------------------------------------------------------------------
    # Guardado
    # -------------------------------------------------------------------------
    def save_project(self, path: str = "", embed_media: bool = False) -> bool:
        """
        Guarda el proyecto en formato .soundvi (comprimido/cifrado) o .svproj (legacy).

        Args:
            path: Ruta del archivo. Si vacía, usa la ruta anterior.
            embed_media: Si True, incrusta archivos de medios en el proyecto

        Returns:
            True si se guardó exitosamente
        """
        if path:
            self.project_path = path
        elif not self.project_path:
            return False

        is_soundvi = self.project_path.endswith(".soundvi")

        try:
            if is_soundvi:
                return self._save_soundvi(embed_media)
            else:
                return self._save_json_legacy()
        except Exception as e:
            print(f"[ProjectManager] Error al guardar proyecto: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _save_soundvi(self, embed_media: bool = False) -> bool:
        """Guarda en formato .soundvi con cifrado."""
        from core.soundvi_project import create_soundvi_project

        project_data = {
            "project_name": self.project_name,
            "author": self.author,
            "description": self.description,
            "project_config": {
                "version": self.PROJECT_VERSION,
                "created_at": self.created_at,
                "modified_at": time.time(),
                "video_metadata": self.video_metadata,
            },
            "render_config": self.render_config,
            "timeline": self.timeline.to_dict(),
            "modules": self.modules_state,
            "media_library": [m.to_dict() for m in self.media_library],
            "undo_stack": [],
            "redo_stack": [],
            "last_action": self._get_last_action(),
            "action_count": 0,
        }

        success = create_soundvi_project(
            project_data,
            self.project_path,
            password=None,  # Usa contraseña por defecto
            embed_media=embed_media
        )

        if success:
            self._is_modified = False
            self.modified_at = time.time()
            file_size = os.path.getsize(self.project_path) if os.path.exists(self.project_path) else 0
            print(f"[ProjectManager] Proyecto .soundvi guardado: {self.project_path} "
                  f"({file_size / 1024:.1f} KB, medios embebidos: {embed_media})")
        else:
            print("[ProjectManager] Error guardando .soundvi, intentando fallback JSON...")
            return self._save_json_fallback()

        return success

    def _save_json_legacy(self) -> bool:
        """Guarda en formato JSON legacy (.svproj)."""
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
            "modules": self.modules_state,
            "media_library": [m.to_dict() for m in self.media_library],
        }

        try:
            with open(self.project_path, "w", encoding="utf-8") as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False, default=str)
            self._is_modified = False
            print(f"[ProjectManager] Proyecto JSON guardado: {self.project_path}")
            return True
        except Exception as e:
            print(f"[ProjectManager] Error al guardar JSON: {e}")
            return False

    def _save_json_fallback(self) -> bool:
        """Fallback: guarda como JSON si el .soundvi falla."""
        json_path = self.project_path.replace(".soundvi", ".svproj")
        old_path = self.project_path
        self.project_path = json_path
        result = self._save_json_legacy()
        if not result:
            self.project_path = old_path
        return result

    # -------------------------------------------------------------------------
    # Carga
    # -------------------------------------------------------------------------
    def load_project(self, path: str) -> bool:
        """
        Carga un proyecto desde archivo .soundvi o .svproj (legacy).

        Args:
            path: Ruta del archivo

        Returns:
            True si se cargó exitosamente
        """
        if not os.path.exists(path):
            print(f"[ProjectManager] Archivo no encontrado: {path}")
            return False

        is_soundvi = path.endswith(".soundvi")

        try:
            if is_soundvi:
                return self._load_soundvi(path)
            else:
                return self._load_json_legacy(path)
        except Exception as e:
            print(f"[ProjectManager] Error al cargar proyecto: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _load_soundvi(self, path: str) -> bool:
        """Carga un proyecto .soundvi."""
        from core.soundvi_project import load_soundvi_project

        project_data = load_soundvi_project(path, password=None)
        if not project_data:
            print(f"[ProjectManager] Error cargando .soundvi: {path}")
            return False

        manifest = project_data.get("manifest", {})
        config = project_data.get("project_config", {})
        timeline_data = project_data.get("timeline", {})
        modules_data = project_data.get("modules", [])
        media_library_data = project_data.get("media_library", [])
        history_data = project_data.get("history", {})
        render_config = project_data.get("render_config", {})

        # Restaurar datos básicos
        self.project_path = path
        self.project_name = manifest.get("project_name", "Sin nombre")
        self.created_at = config.get("created_at", time.time())
        self.modified_at = config.get("modified_at", time.time())
        self.author = manifest.get("author", "")
        self.description = manifest.get("description", "")
        self.video_metadata = config.get("video_metadata", {})

        if render_config:
            self.render_config.update(render_config)

        # Restaurar timeline
        if timeline_data:
            self.timeline = Timeline.from_dict(timeline_data)

        # Restaurar módulos
        self.modules_state = modules_data if isinstance(modules_data, list) else []

        # Restaurar biblioteca de medios
        self.media_library.clear()
        for media_data in media_library_data:
            item = MediaItem.from_dict(media_data)
            self.media_library.append(item)

        # Limpiar undo/redo
        self.command_manager.clear()
        self._is_modified = False

        print(f"[ProjectManager] Proyecto .soundvi cargado: {path}")
        print(f"  Nombre: {self.project_name}")
        print(f"  Módulos: {len(self.modules_state)}")
        print(f"  Medios: {len(self.media_library)}")
        return True

    def _load_json_legacy(self, path: str) -> bool:
        """Carga un proyecto JSON legacy (.svproj o .json)."""
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

            # Timeline
            timeline_data = data.get("timeline", {})
            if timeline_data:
                self.timeline = Timeline.from_dict(timeline_data)

            # Módulos
            self.modules_state = data.get("modules", [])

            # Medios
            self.media_library.clear()
            for media_data in data.get("media_library", []):
                item = MediaItem.from_dict(media_data)
                self.media_library.append(item)

            self.command_manager.clear()
            self._is_modified = False

            print(f"[ProjectManager] Proyecto JSON cargado: {path}")
            return True

        except Exception as e:
            print(f"[ProjectManager] Error cargando JSON: {e}")
            return False

    # -------------------------------------------------------------------------
    # Estado de módulos
    # -------------------------------------------------------------------------
    def set_modules_state(self, modules_state: List[Dict[str, Any]]):
        """Establece el estado serializable de los módulos."""
        self.modules_state = modules_state
        self.mark_modified()

    def get_modules_state(self) -> List[Dict[str, Any]]:
        """Obtiene el estado serializable de los módulos."""
        return self.modules_state

    # -------------------------------------------------------------------------
    # Métodos auxiliares
    # -------------------------------------------------------------------------
    def _get_last_action(self):
        """Obtiene la última acción realizada."""
        if hasattr(self.command_manager, 'get_last_action'):
            return self.command_manager.get_last_action()
        return ""

    # -------------------------------------------------------------------------
    # Utilidades
    # -------------------------------------------------------------------------
    def mark_modified(self):
        self._is_modified = True
        self.modified_at = time.time()

    def mark_saved(self):
        self._is_modified = False

    @property
    def is_modified(self) -> bool:
        return self._is_modified

    def get_project_summary(self) -> Dict[str, Any]:
        total_clips = sum(len(t.clips) for t in self.timeline.tracks)
        return {
            "name": self.project_name,
            "path": self.project_path,
            "tracks": len(self.timeline.tracks),
            "clips": total_clips,
            "media_items": len(self.media_library),
            "modules": len(self.modules_state),
            "modified": self._is_modified,
            "created": time.strftime("%Y-%m-%d %H:%M", time.localtime(self.created_at)),
            "modified_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(self.modified_at)),
        }

    def add_media(self, path: str, name: str = "") -> MediaItem:
        item = MediaItem(path, name)
        self.media_library.append(item)
        self.mark_modified()
        return item

    def remove_media(self, item: MediaItem):
        if item in self.media_library:
            self.media_library.remove(item)
            self.mark_modified()

    def find_media_by_path(self, path: str) -> Optional[MediaItem]:
        for item in self.media_library:
            if item.path == path:
                return item
        return None

    def clear(self):
        """Limpia todo el proyecto (nuevo proyecto)."""
        self.timeline = Timeline()
        self.command_manager.clear()
        self.media_library.clear()
        self.modules_state.clear()
        self.project_path = ""
        self.project_name = "Nuevo proyecto"
        self.created_at = time.time()
        self.modified_at = time.time()
        self.author = ""
        self.description = ""
        self._is_modified = False
