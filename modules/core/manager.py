#!/usr/bin/env python3
from __future__ import annotations
"""
CategorizedModuleManager -- Gestor de m\u00f3dulos con categorizaci\u00f3n por tipo.

Escanea m\u00f3dulos organizados por tipo/categor\u00eda desde la estructura:
  modules/audio/visualization/
  modules/video/effects/
  modules/text/subtitles/
  etc.

Mantiene compatibilidad con la estructura legacy (m\u00f3dulos en modules/).
"""

import os
import sys
import importlib.util
import inspect
import json
import uuid
import numpy as np
from typing import List, Dict, Type, Optional

from modules.core.base import Module
from modules.core.registry import ModuleRegistry, MODULE_TYPES


class CategorizedModuleManager:
    """Gestor de m\u00f3dulos con categorizaci\u00f3n por tipo."""

    def __init__(self, modules_root: str | None = None):
        self._modules: List[Module] = []
        self._module_types: Dict[str, Type[Module]] = {}
        self._modules_dir = modules_root or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self._config_dir = os.path.join(
            os.path.dirname(self._modules_dir), "modules_config")
        self.registry = ModuleRegistry()

        if not os.path.exists(self._config_dir):
            os.makedirs(self._config_dir)

        # Cargar m\u00f3dulos de estructura nueva
        self._scan_modules_by_type()
        # Compatibilidad: cargar m\u00f3dulos legacy del directorio raiz
        self._load_legacy_modules()

    def _scan_modules_by_type(self):
        """Escanea m\u00f3dulos organizados por tipo."""
        type_folders = list(MODULE_TYPES.keys())  # ["video", "audio", "text", "utility", "export"]
        for type_folder in type_folders:
            type_path = os.path.join(self._modules_dir, type_folder)
            if os.path.exists(type_path):
                self._load_modules_from_type(type_folder, type_path)

    def _load_modules_from_type(self, module_type: str, type_path: str):
        """Carga m\u00f3dulos de una categor\u00eda espec\u00edfica."""
        for root, dirs, files in os.walk(type_path):
            relative_path = os.path.relpath(root, type_path)
            category = "general" if relative_path == "." else os.path.basename(root)

            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    filepath = os.path.join(root, file)
                    self._load_module_with_metadata(
                        filepath=filepath,
                        module_type=module_type,
                        category=category
                    )

    def _load_legacy_modules(self):
        """Carga m\u00f3dulos legacy del directorio ra\u00edz modules/."""
        # Nombres de clases ya cargadas desde la estructura nueva
        loaded_class_names = {cls.__name__ for cls in self._module_types.values()}
        loaded_file_names = set()
        for k in self._module_types:
            # type_key es "module_file_ClassName", extraer nombre de archivo
            parts = k.rsplit('_', 1)
            if len(parts) >= 1:
                loaded_file_names.add(parts[0])

        for filename in os.listdir(self._modules_dir):
            if (filename.endswith('.py') and
                filename not in ('__init__.py', 'base.py', 'manager.py', 'TEMPLATE.py')):
                filepath = os.path.join(self._modules_dir, filename)
                if os.path.isfile(filepath):
                    mod_name = os.path.splitext(filename)[0]
                    # Saltar si ya existe una versi\u00f3n categorizada
                    if mod_name in loaded_file_names:
                        print(f"[manager] Saltando legacy '{mod_name}' (ya cargado como categorizado)")
                        continue
                    self._load_module_with_metadata(
                        filepath=filepath,
                        module_type=None,
                        category=None
                    )

    def _load_module_with_metadata(self, filepath: str, module_type: str | None, category: str | None):
        """Carga un m\u00f3dulo y extrae sus metadatos."""
        module_name = os.path.splitext(os.path.basename(filepath))[0]
        unique_name = f"soundvi_mod_{module_name}_{id(filepath)}"
        try:
            spec = importlib.util.spec_from_file_location(unique_name, filepath)
            if spec is None or spec.loader is None:
                return
            mod = importlib.util.module_from_spec(spec)
            sys.modules[unique_name] = mod
            spec.loader.exec_module(mod)

            for name, obj in inspect.getmembers(mod, inspect.isclass):
                if issubclass(obj, Module) and obj is not Module and obj.__module__ == unique_name:
                    # Inyectar metadatos si no los tiene y los conocemos
                    if module_type and getattr(obj, 'module_type', 'uncategorized') == 'uncategorized':
                        obj.module_type = module_type
                    if category and getattr(obj, 'module_category', 'general') == 'general':
                        obj.module_category = category

                    type_key = f"{module_name}_{name}"
                    self._module_types[type_key] = obj
                    self.registry.register_module(obj)
                    print(f"[manager] M\u00f3dulo '{type_key}' [{getattr(obj, 'module_type', '?')}/{getattr(obj, 'module_category', '?')}] cargado")
        except Exception as e:
            print(f"[manager] Error cargando m\u00f3dulo {module_name}: {e}")

    # -- Creaci\u00f3n e instancias ------------------------------------------------

    def create_module_instance(self, module_type: str, **kwargs) -> Optional[Module]:
        if module_type not in self._module_types:
            print(f"[manager] Tipo '{module_type}' no encontrado")
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
        if module not in self._modules:
            self._modules.append(module)
            self._modules.sort()
            print(f"[manager] M\u00f3dulo '{module.nombre}' a\u00f1adido (capa {module.capa})")

    def remove_module_instance(self, module: Module):
        if module in self._modules:
            self._modules.remove(module)
            if hasattr(module, "mod_id"):
                config_file = os.path.join(self._config_dir, f"{module.mod_id}.json")
                if os.path.exists(config_file):
                    try:
                        os.remove(config_file)
                    except: pass
            print(f"[manager] M\u00f3dulo '{module.nombre}' eliminado")

    # -- Acceso ---------------------------------------------------------------

    def get_module_types(self) -> List[str]:
        return list(self._module_types.keys())

    def get_module_types_by_category(self) -> Dict[str, Dict[str, List[str]]]:
        """Devuelve tipos de m\u00f3dulo organizados por tipo/categor\u00eda."""
        result = {}
        for type_key, module_class in self._module_types.items():
            mod_type = getattr(module_class, 'module_type', 'uncategorized')
            mod_cat = getattr(module_class, 'module_category', 'general')
            if mod_type not in result:
                result[mod_type] = {}
            if mod_cat not in result[mod_type]:
                result[mod_type][mod_cat] = []
            result[mod_type][mod_cat].append(type_key)
        return result

    def get_modules(self) -> List[Module]:
        return list(self._modules)

    def get_active_modules(self) -> List[Module]:
        return sorted([m for m in self._modules if m.habilitado])

    def get_inactive_modules(self) -> List[Module]:
        return sorted([m for m in self._modules if not m.habilitado])

    def get_module_by_name(self, nombre: str) -> Module | None:
        for m in self._modules:
            if m.nombre == nombre:
                return m
        return None

    def search_modules(self, query: str) -> List[str]:
        """Busca tipos de m\u00f3dulo por query."""
        results = []
        query_lower = query.lower()
        for type_key, module_class in self._module_types.items():
            if query_lower in type_key.lower():
                results.append(type_key)
                continue
            tags = getattr(module_class, 'module_tags', [])
            if any(query_lower in t.lower() for t in tags):
                results.append(type_key)
                continue
            mod_type = getattr(module_class, 'module_type', '')
            if query_lower in mod_type.lower():
                results.append(type_key)
        return results

    # -- Renderizado ----------------------------------------------------------

    def render_all(self, frame: np.ndarray, tiempo: float, **kwargs) -> np.ndarray:
        resultado = frame.copy()
        for mod in self.get_active_modules():
            try:
                resultado = mod.render(resultado, tiempo, **kwargs)
            except Exception as e:
                print(f"[manager] Error en m\u00f3dulo '{mod.nombre}': {e}")
        return resultado

    # -- Persistencia ---------------------------------------------------------

    def save_all_modules(self):
        for mod in self._modules:
            if not hasattr(mod, "mod_id"):
                mod.mod_id = str(uuid.uuid4())[:8]
            mod_type = None
            for t_name, t_class in self._module_types.items():
                if isinstance(mod, t_class):
                    mod_type = t_name
                    break
            if not mod_type:
                continue
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
                    if not mod_type:
                        continue
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
                    print(f"[manager] Error cargando m\u00f3dulo {file}: {e}")
        return loaded

    def __len__(self):
        return len(self._modules)

    def __repr__(self):
        activos = len(self.get_active_modules())
        return f"<CategorizedModuleManager: {len(self._modules)} m\u00f3dulos ({activos} activos), {len(self._module_types)} tipos>"