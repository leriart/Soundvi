#!/usr/bin/env python3
"""
ModuleRegistry -- Registro central de m\u00f3dulos disponibles por tipo/categor\u00eda.
"""

from typing import List, Dict, Type, Optional
from modules.core.base import Module


# Definicion de tipos de modulos
MODULE_TYPES = {
    "video": {
        "name": "Video",
        "icon": "\U0001f3ac",
        "description": "Procesamiento y efectos de video",
        "categories": ["effects", "filters", "generators", "transitions"]
    },
    "audio": {
        "name": "Audio",
        "icon": "\U0001f50a",
        "description": "Procesamiento y visualizaci\u00f3n de audio",
        "categories": ["visualization", "effects", "analysis", "enhancement"]
    },
    "text": {
        "name": "Texto",
        "icon": "\U0001f4dd",
        "description": "Subt\u00edtulos, t\u00edtulos y texto en pantalla",
        "categories": ["subtitles", "titles", "captions", "lower-thirds"]
    },
    "utility": {
        "name": "Utilidad",
        "icon": "\u2699\ufe0f",
        "description": "Herramientas y utilidades",
        "categories": ["watermark", "timestamp", "metadata", "utility"]
    },
    "export": {
        "name": "Exportaci\u00f3n",
        "icon": "\U0001f4e4",
        "description": "Formatos y opciones de exportaci\u00f3n",
        "categories": ["social", "streaming", "archive", "optimization"]
    }
}


class ModuleRegistry:
    """Registro central de m\u00f3dulos disponibles."""

    def __init__(self):
        self.modules_by_type: Dict[str, List[Type[Module]]] = {}
        self.modules_by_category: Dict[str, List[Type[Module]]] = {}
        self.modules_by_tag: Dict[str, List[Type[Module]]] = {}
        self.all_modules: List[Type[Module]] = []

    def register_module(self, module_class: Type[Module]):
        """Registra un m\u00f3dulo en el sistema."""
        module_type = getattr(module_class, 'module_type', 'uncategorized')
        category = getattr(module_class, 'module_category', 'general')
        tags = getattr(module_class, 'module_tags', [])

        self.modules_by_type.setdefault(module_type, []).append(module_class)
        self.modules_by_category.setdefault(category, []).append(module_class)

        for tag in tags:
            self.modules_by_tag.setdefault(tag, []).append(module_class)

        self.all_modules.append(module_class)

    def get_by_type(self, module_type: str) -> List[Type[Module]]:
        return self.modules_by_type.get(module_type, [])

    def get_by_category(self, category: str) -> List[Type[Module]]:
        return self.modules_by_category.get(category, [])

    def search(self, query: str) -> List[Type[Module]]:
        """Busca m\u00f3dulos por nombre, descripcion o tags."""
        results = []
        query_lower = query.lower()
        for mc in self.all_modules:
            # Buscar en nombre de clase
            if query_lower in mc.__name__.lower():
                results.append(mc)
                continue
            # Buscar en tags
            tags = getattr(mc, 'module_tags', [])
            if any(query_lower in t.lower() for t in tags):
                results.append(mc)
                continue
            # Buscar en tipo
            if query_lower in getattr(mc, 'module_type', '').lower():
                results.append(mc)
        return results

    def get_types_summary(self) -> Dict[str, int]:
        """Devuelve cantidad de m\u00f3dulos por tipo."""
        return {t: len(mods) for t, mods in self.modules_by_type.items()}

    def __len__(self):
        return len(self.all_modules)

    def __repr__(self):
        return f"<ModuleRegistry: {len(self.all_modules)} tipos registrados>"
