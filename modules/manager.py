#!/usr/bin/env python3
from __future__ import annotations
"""
ModuleManager -- gestiona los modulos activos de Soundvi.

Proporciona una interfaz centralizada para registrar, activar/desactivar
y renderizar modulos en orden.

Ahora con deteccion automatica de modulos en la carpeta modules/.
Soporta multiples instancias del mismo tipo de modulo.
"""


import os
import sys
import importlib.util
import inspect
import os
import sys
import importlib.util
import inspect
import numpy as np
import json
import uuid
from typing import List, Dict, Type, Optional

from modules.base import Module


class ModuleManager:
    """
    Gestor de modulos de Soundvi.

    Mantiene un registro ordenado de modulos y se encarga de
    aplicarlos secuencialmente sobre cada frame.
    """

    def __init__(self, modules_dir: str | None = None):
        self._modules: List[Module] = []
        self._module_types: Dict[str, Type[Module]] = {}
        self._modules_dir = modules_dir or os.path.dirname(os.path.abspath(__file__))
        self._config_dir = os.path.join(os.path.dirname(self._modules_dir), "modules_config")
        
        # Crear carpeta de configs si no existe
        if not os.path.exists(self._config_dir):
            os.makedirs(self._config_dir)
            
        # Cargar tipos de modulos automaticamente
        self._load_module_types_from_dir()

    # -- Carga automatica de tipos de modulos ---------------------------------

    def _load_module_types_from_dir(self):
        """Carga todos los tipos de modulos validos del directorio modules/."""
        if not os.path.isdir(self._modules_dir):
            print(f"[manager] Directorio de modulos no encontrado: {self._modules_dir}")
            return
        
        # Obtener archivos .py en el directorio (excluyendo __init__.py y base.py)
        for filename in os.listdir(self._modules_dir):
            if filename.endswith('.py') and filename not in ('__init__.py', 'base.py', 'manager.py', 'TEMPLATE.py'):
                module_name = filename[:-3]  # Sin .py
                self._load_module_type_from_file(module_name, os.path.join(self._modules_dir, filename))
    
    def _load_module_type_from_file(self, module_name: str, filepath: str):
        """Carga un tipo de modulo desde un archivo Python."""
        try:
            # Importar el modulo dinamicamente
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            if spec is None or spec.loader is None:
                print(f"[manager] No se pudo cargar especificacion para {module_name}")
                return
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Buscar clases que hereden de Module (y no sean la clase base misma)
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, Module) and obj != Module and 
                    obj.__module__ == module_name):
                    
                    # Registrar el tipo de modulo
                    type_name = f"{module_name}_{name}"
                    self._module_types[type_name] = obj
                    print(f"[manager] Tipo de modulo '{type_name}' cargado desde {os.path.basename(filepath)}")
                    
        except Exception as e:
            print(f"[manager] Error cargando tipo de modulo {module_name}: {e}")

    # -- Registro y creacion de modulos ---------------------------------------

    def create_module_instance(self, module_type: str, **kwargs) -> Optional[Module]:
        """
        Crea una nueva instancia de un modulo.
        
        Args:
            module_type: Nombre del tipo de modulo (ej: "subtitles_module_SubtitlesModule")
            **kwargs: Argumentos para el constructor del modulo
            
        Returns:
            Instancia del modulo o None si no se pudo crear
        """
        if module_type not in self._module_types:
            print(f"[manager] Tipo de modulo '{module_type}' no encontrado")
            return None
        
        try:
            module_class = self._module_types[module_type]
            instance = module_class(**kwargs)
            if not hasattr(instance, "mod_id"):
                instance.mod_id = str(uuid.uuid4())[:8]
            return instance
        except Exception as e:
            print(f"[manager] Error creando instancia de '{module_type}': {e}")
            return None

    def add_module_instance(self, module: Module):
        """Añade una instancia de modulo al gestor."""
        if module not in self._modules:
            self._modules.append(module)
            # Ordenar por capa
            self._modules.sort()
            print(f"[manager] Modulo '{module.nombre}' añadido (capa {module.capa})")

    def remove_module_instance(self, module: Module):
        """Elimina una instancia de modulo del gestor."""
        if module in self._modules:
            self._modules.remove(module)
            
            # Borrar archivo de configuracion si existe
            if hasattr(module, "mod_id"):
                config_file = os.path.join(self._config_dir, f"{module.mod_id}.json")
                if os.path.exists(config_file):
                    try:
                        os.remove(config_file)
                        print(f"[manager] Configuración de '{module.nombre}' eliminada")
                    except Exception as e:
                        print(f"[manager] Error al borrar archivo {config_file}: {e}")
            
            print(f"[manager] Modulo '{module.nombre}' eliminado")

    def duplicate_module(self, module: Module) -> Optional[Module]:
        """
        Duplica un modulo existente.
        
        Args:
            module: Modulo a duplicar
            
        Returns:
            Nueva instancia del modulo o None si no se pudo duplicar
        """
        # Buscar el tipo de modulo
        for type_name, module_class in self._module_types.items():
            if isinstance(module, module_class):
                try:
                    # Crear nueva instancia con misma configuracion
                    new_module = module_class()
                    new_module.set_config(module.get_config())
                    new_module.capa = module.capa + 1  # Una capa mas arriba
                    new_module.nombre = f"{module.nombre} (copia)"
                    return new_module
                except Exception as e:
                    print(f"[manager] Error duplicando modulo '{module.nombre}': {e}")
                    return None
        return None

    # -- Acceso ---------------------------------------------------------------

    def get_module_types(self) -> List[str]:
        """Devuelve la lista de tipos de modulos disponibles."""
        return list(self._module_types.keys())

    def get_modules(self) -> List[Module]:
        """Devuelve la lista completa de modulos registrados."""
        return list(self._modules)

    def get_active_modules(self) -> List[Module]:
        """Devuelve solo los modulos habilitados, ordenados por capa."""
        return sorted([m for m in self._modules if m.habilitado])

    def get_inactive_modules(self) -> List[Module]:
        """Devuelve solo los modulos deshabilitados, ordenados por capa."""
        return sorted([m for m in self._modules if not m.habilitado])

    def get_module_by_name(self, nombre: str) -> Module | None:
        """Busca un modulo por nombre."""
        for m in self._modules:
            if m.nombre == nombre:
                return m
        return None

    def get_modules_by_type(self, module_type: str) -> List[Module]:
        """Devuelve todos los modulos de un tipo especifico."""
        modules = []
        for type_name, module_class in self._module_types.items():
            if type_name == module_type:
                for module in self._modules:
                    if isinstance(module, module_class):
                        modules.append(module)
                break
        return modules

    # -- Renderizado ----------------------------------------------------------

    def render_all(
        self,
        frame: np.ndarray,
        tiempo: float,
        **kwargs,
    ) -> np.ndarray:
        """
        Aplica todos los modulos activos sobre el frame, en orden de capa.

        Parametros
        ----------
        frame : np.ndarray
            Frame BGR de OpenCV.
        tiempo : float
            Tiempo actual en segundos.
        **kwargs :
            Datos adicionales pasados a cada modulo.

        Devuelve
        --------
        np.ndarray : Frame con todos los modulos renderizados.
        """
        resultado = frame.copy()
        
        # Renderizar modulos activos ordenados por capa
        for mod in self.get_active_modules():
            try:
                resultado = mod.render(resultado, tiempo, **kwargs)
            except Exception as e:
                print(f"[manager] Error en modulo '{mod.nombre}': {e}")
        
        return resultado

    def __len__(self):
        return len(self._modules)

    def __repr__(self):
        activos = len(self.get_active_modules())
        inactivos = len(self.get_inactive_modules())
        tipos = len(self._module_types)
        return f"<ModuleManager: {len(self._modules)} modulos ({activos} activos, {inactivos} inactivos), {tipos} tipos>"

    def save_all_modules(self):
        """Guarda la configuracion de cada modulo en su propio archivo."""
        for mod in self._modules:
            if not hasattr(mod, "mod_id"):
                mod.mod_id = str(uuid.uuid4())[:8]
                
            # Identificar el tipo real del modulo
            mod_type = None
            for t_name, t_class in self._module_types.items():
                if isinstance(mod, t_class):
                    mod_type = t_name
                    break
                    
            if not mod_type: continue
            
            data = {
                "type": mod_type,
                "name": mod.nombre,
                "enabled": mod.habilitado,
                "layer": mod.capa,
                "config": mod.get_config()
            }
            if hasattr(mod, "current_srt_path"):
                data["srt_path"] = mod.current_srt_path
                
            config_file = os.path.join(self._config_dir, f"{mod.mod_id}.json")
            try:
                with open(config_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            except Exception as e:
                print(f"[manager] Error guardando config de {mod.nombre}: {e}")

    def load_saved_modules(self) -> List[Module]:
        """Carga los modulos guardados y devuelve las instancias creadas."""
        loaded = []
        if not os.path.exists(self._config_dir):
            return loaded
            
        for file in os.listdir(self._config_dir):
            if file.endswith(".json"):
                mod_id = file.replace(".json", "")
                try:
                    with open(os.path.join(self._config_dir, file), "r", encoding="utf-8") as f:
                        data = json.load(f)
                        
                    mod_type = data.get("type")
                    if not mod_type: continue
                    
                    mod = self.create_module_instance(mod_type)
                    if mod:
                        mod.mod_id = mod_id
                        mod.nombre = data.get("name", mod.nombre)
                        mod.habilitado = data.get("enabled", False)
                        mod.capa = data.get("layer", mod.capa)
                        mod.set_config(data.get("config", {}))
                        
                        if "srt_path" in data and hasattr(mod, "set_subtitles"):
                            srt_path = data.get("srt_path")
                            if srt_path and os.path.exists(srt_path):
                                from utils.subtitles import parse_srt
                                mod.set_subtitles(parse_srt(srt_path))
                                if hasattr(mod, 'current_srt_path'):
                                    mod.current_srt_path = srt_path
                                
                        loaded.append(mod)
                        self.add_module_instance(mod)
                except Exception as e:
                    print(f"[manager] Error cargando archivo de modulo {file}: {e}")
        return loaded