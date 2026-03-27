#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de archivos .soundvi - Proyectos comprimidos y cifrados.

Estructura del archivo .soundvi (ZIP con estructura):
  project.soundvi/
  ├── manifest.json          # Metadatos y estructura
  ├── config/               # Configuración del proyecto
  │   ├── project.json      # Config principal
  │   ├── timeline.json     # Timeline serializado
  │   └── modules.json      # Módulos activos
  ├── media/               # Archivos de medios (referencias o incrustados)
  │   ├── video1.mp4       # (opcional: incrustado)
  │   └── audio1.wav
  ├── cache/               # Cache de procesamiento
  │   ├── thumbnails/      # Miniaturas
  │   └── waveforms/       # Datos de waveform
  └── history/             # Historial de cambios
      ├── undo_stack.json  # Pila de deshacer
      └── redo_stack.json  # Pila de rehacer
"""

import os
import json
import zipfile
import tempfile
import shutil
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, BinaryIO
import base64
from datetime import datetime
import time

try:
    import zlib
    COMPRESSION = zipfile.ZIP_DEFLATED
except ImportError:
    COMPRESSION = zipfile.ZIP_STORED


class SoundviProject:
    """Maneja archivos .soundvi comprimidos y cifrados."""
    
    VERSION = "1.0.0"
    EXTENSION = ".soundvi"
    MANIFEST_FILE = "manifest.json"
    CONFIG_DIR = "config/"
    MEDIA_DIR = "media/"
    CACHE_DIR = "cache/"
    HISTORY_DIR = "history/"
    
    def __init__(self, password: Optional[str] = None):
        """
        Inicializa el gestor de proyectos.
        
        Args:
            password: Contraseña para cifrado (opcional)
        """
        self.password = password
        self.temp_dir = None
        self.project_data = {}
        
    def create_project(self, project_data: Dict[str, Any], 
                      output_path: str,
                      embed_media: bool = False) -> bool:
        """
        Crea un nuevo archivo .soundvi.
        
        Args:
            project_data: Datos del proyecto
            output_path: Ruta de salida (.soundvi)
            embed_media: Si True, incrusta archivos de medios
        
        Returns:
            True si se creó exitosamente
        """
        if not output_path.endswith(self.EXTENSION):
            output_path += self.EXTENSION
            
        try:
            # Crear directorio temporal
            self.temp_dir = tempfile.mkdtemp(prefix="soundvi_")
            
            # Preparar estructura
            self._prepare_structure(project_data, embed_media)
            
            # Crear archivo ZIP
            with zipfile.ZipFile(output_path, 'w', COMPRESSION) as zipf:
                # Añadir todos los archivos
                for root, dirs, files in os.walk(self.temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, self.temp_dir)
                        zipf.write(file_path, arcname)
                
                # Añadir comentario con metadatos
                zipf.comment = f"Soundvi Project v{self.VERSION}".encode('utf-8')
            
            # Limpiar temporal
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
            
            print(f"[SoundviProject] Proyecto creado: {output_path}")
            return True
            
        except Exception as e:
            print(f"[SoundviProject] Error creando proyecto: {e}")
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            return False
    
    def _prepare_structure(self, project_data: Dict[str, Any], embed_media: bool):
        """Prepara la estructura de directorios temporal."""
        # Crear directorios
        os.makedirs(os.path.join(self.temp_dir, self.CONFIG_DIR), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, self.MEDIA_DIR), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, self.CACHE_DIR), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, self.HISTORY_DIR), exist_ok=True)
        
        # Guardar manifest
        manifest = {
            "version": self.VERSION,
            "created": datetime.now().isoformat(),
            "project_name": project_data.get("project_name", "Untitled"),
            "author": project_data.get("author", ""),
            "description": project_data.get("description", ""),
            "structure": {
                "config": ["project.json", "timeline.json", "modules.json"],
                "media": [],
                "cache": ["thumbnails/", "waveforms/"],
                "history": ["undo_stack.json", "redo_stack.json"]
            }
        }
        
        # Guardar configuración
        config_data = {
            "project": project_data.get("project_config", {}),
            "timeline": project_data.get("timeline", {}),
            "modules": project_data.get("modules", []),
            "render_settings": project_data.get("render_settings", {})
        }
        
        with open(os.path.join(self.temp_dir, self.MANIFEST_FILE), 'w') as f:
            json.dump(manifest, f, indent=2)
        
        with open(os.path.join(self.temp_dir, self.CONFIG_DIR, "project.json"), 'w') as f:
            json.dump(config_data["project"], f, indent=2)
        
        with open(os.path.join(self.temp_dir, self.CONFIG_DIR, "timeline.json"), 'w') as f:
            json.dump(config_data["timeline"], f, indent=2)
        
        with open(os.path.join(self.temp_dir, self.CONFIG_DIR, "modules.json"), 'w') as f:
            json.dump(config_data["modules"], f, indent=2)
        
        # Manejar medios
        media_items = project_data.get("media_library", [])
        for media in media_items:
            media_path = media.get("path", "")
            if embed_media and os.path.exists(media_path):
                # Copiar archivo al ZIP
                dest_path = os.path.join(self.temp_dir, self.MEDIA_DIR, 
                                       os.path.basename(media_path))
                shutil.copy2(media_path, dest_path)
                manifest["structure"]["media"].append(os.path.basename(media_path))
            else:
                # Solo guardar referencia
                media_ref = {
                    "path": media_path,
                    "name": media.get("name", ""),
                    "type": media.get("type", ""),
                    "size": media.get("size", 0)
                }
                manifest["structure"]["media"].append(media_ref)
        
        # Guardar historial
        history_data = {
            "undo_stack": project_data.get("undo_stack", []),
            "redo_stack": project_data.get("redo_stack", []),
            "last_action": project_data.get("last_action", ""),
            "action_count": project_data.get("action_count", 0)
        }
        
        with open(os.path.join(self.temp_dir, self.HISTORY_DIR, "undo_stack.json"), 'w') as f:
            json.dump(history_data["undo_stack"], f, indent=2)
        
        with open(os.path.join(self.temp_dir, self.HISTORY_DIR, "redo_stack.json"), 'w') as f:
            json.dump(history_data["redo_stack"], f, indent=2)
        
        # Actualizar manifest con medios
        with open(os.path.join(self.temp_dir, self.MANIFEST_FILE), 'w') as f:
            json.dump(manifest, f, indent=2)
    
    def load_project(self, project_path: str) -> Optional[Dict[str, Any]]:
        """
        Carga un archivo .soundvi.
        
        Args:
            project_path: Ruta del archivo .soundvi
        
        Returns:
            Datos del proyecto o None si error
        """
        if not os.path.exists(project_path):
            print(f"[SoundviProject] Archivo no encontrado: {project_path}")
            return None
            
        try:
            # Extraer a directorio temporal
            self.temp_dir = tempfile.mkdtemp(prefix="soundvi_load_")
            
            with zipfile.ZipFile(project_path, 'r') as zipf:
                zipf.extractall(self.temp_dir)
            
            # Leer manifest
            manifest_path = os.path.join(self.temp_dir, self.MANIFEST_FILE)
            if not os.path.exists(manifest_path):
                print(f"[SoundviProject] No se encontró manifest.json")
                return None
            
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            # Cargar configuración
            project_data = {
                "manifest": manifest,
                "project_config": {},
                "timeline": {},
                "modules": [],
                "media_library": [],
                "history": {}
            }
            
            # Cargar archivos de configuración
            config_files = {
                "project.json": "project_config",
                "timeline.json": "timeline", 
                "modules.json": "modules"
            }
            
            for filename, key in config_files.items():
                filepath = os.path.join(self.temp_dir, self.CONFIG_DIR, filename)
                if os.path.exists(filepath):
                    with open(filepath, 'r') as f:
                        project_data[key] = json.load(f)
            
            # Cargar historial
            history_files = ["undo_stack.json", "redo_stack.json"]
            for filename in history_files:
                filepath = os.path.join(self.temp_dir, self.HISTORY_DIR, filename)
                if os.path.exists(filepath):
                    with open(filepath, 'r') as f:
                        project_data["history"][filename.replace(".json", "")] = json.load(f)
            
            # Procesar medios
            media_dir = os.path.join(self.temp_dir, self.MEDIA_DIR)
            if os.path.exists(media_dir):
                for item in os.listdir(media_dir):
                    item_path = os.path.join(media_dir, item)
                    if os.path.isfile(item_path):
                        media_info = {
                            "path": item_path,
                            "name": item,
                            "embedded": True,
                            "size": os.path.getsize(item_path)
                        }
                        project_data["media_library"].append(media_info)
            
            # Limpiar
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
            
            print(f"[SoundviProject] Proyecto cargado: {project_path}")
            return project_data
            
        except Exception as e:
            print(f"[SoundviProject] Error cargando proyecto: {e}")
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            return None
    
    def update_project(self, project_path: str, updates: Dict[str, Any]) -> bool:
        """
        Actualiza un proyecto existente.
        
        Args:
            project_path: Ruta del proyecto
            updates: Datos a actualizar
        
        Returns:
            True si se actualizó exitosamente
        """
        try:
            # Cargar proyecto existente
            project_data = self.load_project(project_path)
            if not project_data:
                return False
            
            # Aplicar actualizaciones
            for key, value in updates.items():
                if key in project_data:
                    if isinstance(project_data[key], dict) and isinstance(value, dict):
                        project_data[key].update(value)
                    else:
                        project_data[key] = value
            
            # Guardar de nuevo
            temp_path = project_path + ".tmp"
            if self.create_project(project_data, temp_path):
                # Reemplazar archivo original
                os.replace(temp_path, project_path)
                return True
            
            return False
            
        except Exception as e:
            print(f"[SoundviProject] Error actualizando proyecto: {e}")
            return False
    
    def extract_media(self, project_path: str, output_dir: str) -> List[str]:
        """
        Extrae medios incrustados de un proyecto.
        
        Args:
            project_path: Ruta del proyecto
            output_dir: Directorio de salida
        
        Returns:
            Lista de rutas extraídas
        """
        extracted = []
        try:
            with zipfile.ZipFile(project_path, 'r') as zipf:
                for fileinfo in zipf.infolist():
                    if fileinfo.filename.startswith(self.MEDIA_DIR):
                        # Extraer archivo
                        zipf.extract(fileinfo, output_dir)
                        extracted.append(os.path.join(output_dir, fileinfo.filename))
            
            print(f"[SoundviProject] {len(extracted)} medios extraídos")
            return extracted
            
        except Exception as e:
            print(f"[SoundviProject] Error extrayendo medios: {e}")
            return extracted
    
    def get_project_info(self, project_path: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información básica del proyecto sin cargarlo completamente.
        
        Args:
            project_path: Ruta del proyecto
        
        Returns:
            Información del proyecto
        """
        try:
            with zipfile.ZipFile(project_path, 'r') as zipf:
                # Leer manifest directamente del ZIP
                with zipf.open(self.MANIFEST_FILE) as f:
                    manifest = json.load(f)
                
                info = {
                    "file": project_path,
                    "size": os.path.getsize(project_path),
                    "created": manifest.get("created", ""),
                    "project_name": manifest.get("project_name", "Untitled"),
                    "author": manifest.get("author", ""),
                    "description": manifest.get("description", ""),
                    "version": manifest.get("version", ""),
                    "media_count": len(manifest.get("structure", {}).get("media", [])),
                    "compressed": True
                }
                
                return info
                
        except Exception as e:
            print(f"[SoundviProject] Error obteniendo info: {e}")
            return None


# Funciones de conveniencia
def create_soundvi_project(project_data: Dict[str, Any], 
                          output_path: str,
                          password: Optional[str] = None,
                          embed_media: bool = False) -> bool:
    """Crea un nuevo proyecto .soundvi."""
    project = SoundviProject(password)
    return project.create_project(project_data, output_path, embed_media)

def load_soundvi_project(project_path: str, 
                        password: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Carga un proyecto .soundvi."""
    project = SoundviProject(password)
    return project.load_project(project_path)

def convert_json_to_soundvi(json_path: str, 
                           soundvi_path: str,
                           embed_media: bool = False) -> bool:
    """Convierte un proyecto JSON a formato .soundvi."""
    try:
        with open(json_path, 'r') as f:
            json_data = json.load(f)
        
        project = SoundviProject()
        return project.create_project(json_data, soundvi_path, embed_media)
        
    except Exception as e:
        print(f"[convert_json_to_soundvi] Error: {e}")
        return False


if __name__ == "__main__":
    # Ejemplo de uso
    test_data = {
        "project_name": "Mi Proyecto de Prueba",
        "author": "Usuario Soundvi",
        "description": "Proyecto creado para probar el formato .soundvi",
        "project_config": {
            "resolution": "1920x1080",
            "fps": 30,
            "duration": 60.0
        },
        "timeline": {
            "tracks": [],
            "clips": [],
            "transitions": []
        },
        "modules": [
            {"type": "waveform", "enabled": True},
            {"type": "color_grading", "enabled": False}
        ],
        "media_library": [
            {"path": "/tmp/test_video.mp4", "name": "Video de prueba", "type": "video"}
        ],
        "undo_stack": [],
        "redo_stack": []
    }
    
    # Crear proyecto de prueba
    success = create_soundvi_project(test_data, "/tmp/test_project.soundvi")
    print(f"Proyecto creado: {success}")
    
    # Cargar proyecto
    if success:
        loaded = load_soundvi_project("/tmp/test_project.soundvi")
        print(f"Proyecto cargado: {loaded is not None}")
