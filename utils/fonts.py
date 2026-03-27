#!/usr/bin/env python3
"""
Utilidades de fuentes para Soundvi.

Proporciona acceso a fuentes del sistema y maneja la fuente JetBrainsMonoNerdFont.
Usa PyQt6 en lugar de tkinter para deteccion de fuentes del sistema.
"""

import os
import sys
from typing import List, Optional

# Ruta a la fuente JetBrainsMonoNerdFont-Regular incluida en el proyecto
FONT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts", "JetBrainsMonoNerdFont-Regular.ttf")

def get_system_fonts() -> List[str]:
    """
    Devuelve una lista de fuentes disponibles en el sistema.
    Usa PyQt6 QFontDatabase para deteccion.
    """
    fonts = []

    # Anadir la fuente JetBrainsMonoNerdFont primero
    if os.path.exists(FONT_PATH):
        fonts.append("JetBrainsMono Nerd Font")

    try:
        from PyQt6.QtGui import QFontDatabase
        qt_fonts = QFontDatabase.families()
        fonts.extend(sorted(qt_fonts))
    except Exception:
        # Fallback: fuentes comunes
        common_fonts = [
            "Arial", "Helvetica", "Times New Roman", "Courier New",
            "Verdana", "Georgia", "Trebuchet MS", "Comic Sans MS",
            "Impact", "Lucida Console", "Tahoma", "Palatino"
        ]
        fonts.extend(common_fonts)

    # Eliminar duplicados manteniendo el orden
    seen = set()
    unique_fonts = []
    for font in fonts:
        if font not in seen:
            seen.add(font)
            unique_fonts.append(font)

    return unique_fonts

def get_font_path(font_name: str) -> Optional[str]:
    """
    Devuelve la ruta del archivo de fuente para un nombre de fuente dado.
    """
    if font_name == "JetBrainsMono Nerd Font":
        return FONT_PATH if os.path.exists(FONT_PATH) else None

    try:
        import platform

        system = platform.system()

        if system == "Windows":
            fonts_dir = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
            possible_names = [
                f"{font_name}.ttf",
                f"{font_name}.ttc",
                f"{font_name.replace(' ', '')}.ttf",
                f"{font_name.replace(' ', '')}.ttc",
            ]
            for name in possible_names:
                path = os.path.join(fonts_dir, name)
                if os.path.exists(path):
                    return path

        elif system == "Darwin":
            font_dirs = [
                "/Library/Fonts",
                "/System/Library/Fonts",
                os.path.expanduser("~/Library/Fonts")
            ]
            for font_dir in font_dirs:
                if os.path.exists(font_dir):
                    for root, dirs, files in os.walk(font_dir):
                        for file in files:
                            if file.lower().endswith(('.ttf', '.ttc', '.otf')):
                                if font_name.lower() in file.lower():
                                    return os.path.join(root, file)

        elif system == "Linux":
            font_dirs = [
                "/usr/share/fonts",
                "/usr/local/share/fonts",
                os.path.expanduser("~/.fonts"),
                os.path.expanduser("~/.local/share/fonts")
            ]
            for font_dir in font_dirs:
                if os.path.exists(font_dir):
                    for root, dirs, files in os.walk(font_dir):
                        for file in files:
                            if file.lower().endswith(('.ttf', '.ttc', '.otf')):
                                if font_name.lower() in file.lower():
                                    return os.path.join(root, file)

    except Exception:
        pass

    return None

def is_font_available(font_name: str) -> bool:
    """Verifica si una fuente esta disponible en el sistema."""
    if font_name == "JetBrainsMono Nerd Font":
        return os.path.exists(FONT_PATH)
    try:
        from PyQt6.QtGui import QFontDatabase
        return font_name in QFontDatabase.families()
    except Exception:
        return False

def get_default_font() -> str:
    """Devuelve la fuente predeterminada para Soundvi."""
    if os.path.exists(FONT_PATH):
        return "JetBrainsMono Nerd Font"

    common_fonts = ["Arial", "Helvetica", "DejaVu Sans", "Ubuntu"]
    for font in common_fonts:
        if is_font_available(font):
            return font

    return "Sans Serif"
