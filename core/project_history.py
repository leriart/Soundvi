#!/usr/bin/env python3
"""
Gestor de historial de proyectos recientes para Soundvi.
Guarda los últimos proyectos abiertos y permite cargarlos automáticamente.
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

class ProjectHistory:
    """Maneja el historial de proyectos recientes."""
    
    def __init__(self, max_history: int = 10, history_file: str = "project_history.json"):
        """
        Args:
            max_history: Máximo número de proyectos en el historial
            history_file: Nombre del archivo de historial (en ~/.config/Soundvi/)
        """
        self.max_history = max_history
        self.history_file = history_file
        self._history: List[Dict] = []
        self._load_history()
    
    def _get_history_path(self) -> str:
        """Retorna la ruta completa al archivo de historial."""
        config_dir = os.path.join(os.path.expanduser("~"), ".config", "Soundvi")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, self.history_file)
    
    def _load_history(self):
        """Carga el historial desde el archivo."""
        history_path = self._get_history_path()
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self._history = data[-self.max_history:]  # Mantener solo los más recientes
            except (json.JSONDecodeError, IOError):
                self._history = []
        else:
            self._history = []
    
    def _save_history(self):
        """Guarda el historial al archivo."""
        history_path = self._get_history_path()
        try:
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(self._history, f, indent=2, ensure_ascii=False)
        except IOError:
            pass  # Silencioso si no se puede guardar
    
    def add_project(self, project_path: str, project_name: str = None):
        """
        Agrega un proyecto al historial.
        
        Args:
            project_path: Ruta completa al archivo .svproj
            project_name: Nombre del proyecto (si None, se extrae del path)
        """
        if not project_path:
            return
        
        # Extraer nombre si no se proporciona
        if project_name is None:
            project_name = os.path.splitext(os.path.basename(project_path))[0]
        
        # Crear entrada del proyecto
        project_entry = {
            "path": project_path,
            "name": project_name,
            "last_opened": datetime.now().isoformat(),
            "size": os.path.getsize(project_path) if os.path.exists(project_path) else 0
        }
        
        # Remover si ya existe (para evitar duplicados)
        self._history = [p for p in self._history if p.get("path") != project_path]
        
        # Agregar al inicio (más reciente primero)
        self._history.insert(0, project_entry)
        
        # Limitar tamaño del historial
        if len(self._history) > self.max_history:
            self._history = self._history[:self.max_history]
        
        self._save_history()
    
    def get_recent_projects(self, limit: int = None) -> List[Dict]:
        """
        Retorna la lista de proyectos recientes.
        
        Args:
            limit: Límite de proyectos a retornar (None = todos)
        
        Returns:
            Lista de diccionarios con información de proyectos
        """
        if limit is None:
            return self._history.copy()
        return self._history[:limit]
    
    def get_last_project(self) -> Optional[Dict]:
        """Retorna el último proyecto abierto, si existe."""
        if self._history:
            # Verificar que el archivo aún existe
            for project in self._history:
                if os.path.exists(project.get("path", "")):
                    return project
        return None
    
    def remove_project(self, project_path: str) -> bool:
        """Elimina un proyecto del historial."""
        initial_len = len(self._history)
        self._history = [p for p in self._history if p.get("path") != project_path]
        
        if len(self._history) != initial_len:
            self._save_history()
            return True
        return False
    
    def clear_history(self):
        """Limpia todo el historial."""
        self._history = []
        self._save_history()
    
    def project_exists(self, project_path: str) -> bool:
        """Verifica si un proyecto está en el historial."""
        return any(p.get("path") == project_path for p in self._history)

# Instancia global
project_history = ProjectHistory(max_history=15)
