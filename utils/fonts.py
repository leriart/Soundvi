#!/usr/bin/env python3
"""
Utilidades de fuentes para Soundvi.

Proporciona acceso a fuentes del sistema y maneja la fuente JetBrainsMonoNerdFont.
"""

import os
import sys
from typing import List, Optional

# Ruta a la fuente JetBrainsMonoNerdFont-Regular incluida en el proyecto
FONT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts", "JetBrainsMonoNerdFont-Regular.ttf")

def get_system_fonts() -> List[str]:
    """
    Devuelve una lista de fuentes disponibles en el sistema.
    
    Returns:
        Lista de nombres de fuentes.
    """
    fonts = []
    
    # Añadir la fuente JetBrainsMonoNerdFont primero
    if os.path.exists(FONT_PATH):
        fonts.append("JetBrainsMono Nerd Font")
    
    try:
        from tkinter import font as tkfont
        tk_fonts = list(tkfont.families())
        fonts.extend(sorted(tk_fonts))
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
    
    Args:
        font_name: Nombre de la fuente
        
    Returns:
        Ruta del archivo de fuente o None si no se encuentra
    """
    if font_name == "JetBrainsMono Nerd Font":
        return FONT_PATH if os.path.exists(FONT_PATH) else None
    
    # Para otras fuentes, intentar encontrarlas en el sistema
    try:
        import subprocess
        import platform
        
        system = platform.system()
        
        if system == "Windows":
            # Windows: buscar en Fonts directory
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
        
        elif system == "Darwin":  # macOS
            # macOS: buscar en /Library/Fonts y ~/Library/Fonts
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
            # Linux: buscar en directorios comunes de fuentes
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
    """
    Verifica si una fuente está disponible en el sistema.
    
    Args:
        font_name: Nombre de la fuente a verificar
        
    Returns:
        True si la fuente está disponible, False en caso contrario
    """
    if font_name == "JetBrainsMono Nerd Font":
        return os.path.exists(FONT_PATH)
    
    try:
        from tkinter import font as tkfont
        return font_name in tkfont.families()
    except Exception:
        return False

def get_default_font() -> str:
    """
    Devuelve la fuente predeterminada para Soundvi.
    
    Returns:
        Nombre de la fuente predeterminada (JetBrainsMono Nerd Font si está disponible)
    """
    if os.path.exists(FONT_PATH):
        return "JetBrainsMono Nerd Font"
    
    # Fallback a fuentes comunes
    common_fonts = ["Arial", "Helvetica", "DejaVu Sans", "Ubuntu"]
    for font in common_fonts:
        if is_font_available(font):
            return font
    
    return "TkDefaultFont"