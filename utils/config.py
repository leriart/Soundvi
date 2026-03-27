#!/usr/bin/env python3
"""
Gestion de configuracion -- cargar, guardar y validar ajustes para Soundvi.
"""

import json
from pathlib import Path

# -- Valores por defecto ------------------------------------------------------

DEFAULT_CONFIG = {
    # Libreria de video
    "video_library": "moviepy",
    "theme": "darkly",

    # FFmpeg
    "ffmpeg_path": "",  # Ruta personalizada de FFmpeg (vacio = auto-detectar)
    "cpu_threads": 4,
    "ffmpeg_preset": "medium",
    "ffmpeg_codec": "libx264",
    "use_gpu": False,
    "gpu_codec": "h264_nvenc",
    "auto_save": True,
    "preview_quality": "medium",
    "log_level": "info",

    # Apariencia de barras
    "bar_color_r": 51,
    "bar_color_g": 255,
    "bar_color_b": 255,
    "bar_height_ratio": 0.60,
    "bar_width_px": 20,
    "bar_spacing_px": 5,
    "bar_center_offset": 0.5,

    # Volumen
    "final_volume": 100,
    "volume_protection": True,
    "normalize_audio": True,
    "max_safe_volume": 150,

    # Subtitulos
    "subtitle_enabled": False,
    "subtitle_font": "Arial",
    "subtitle_size": 36,
    "subtitle_color_r": 255,
    "subtitle_color_g": 255,
    "subtitle_color_b": 255,
    "subtitle_opacity": 1.0,
    "subtitle_x": 50,
    "subtitle_y": 90,
    "subtitle_layer": "above",
    "subtitle_line_break": 40,

    # Modulos activos
    "subtitles_enabled": False,

    # Salida de video
    "width": 1920,
    "height": 1080,
    "fps": 30,
    "fade": 3.0,

    # Rutas de archivos
    "media_path": "",
    "audio_path": "",
    "output_path": "",
    "subtitle_path": "",
}

def get_config_path() -> Path:
    """Devuelve la ruta del archivo de configuracion."""
    return Path(__file__).resolve().parent.parent / "config.json"


def load_config() -> dict:
    """Carga la configuracion desde JSON."""
    config_path = get_config_path()
    try:
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as fh:
                config = json.load(fh)
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
        else:
            save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
    except Exception as exc:
        print(f"[config] Advertencia: no se pudo cargar la configuracion -- {exc}")
        return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> bool:
    """Guarda la configuracion en JSON."""
    config_path = get_config_path()
    try:
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value

        cleaned = {}
        for key, value in config.items():
            if hasattr(value, "get"):
                cleaned[key] = value.get()
            else:
                cleaned[key] = value

        with open(config_path, "w", encoding="utf-8") as fh:
            json.dump(cleaned, fh, indent=2, ensure_ascii=False)
        return True
    except Exception as exc:
        print(f"[config] Advertencia: no se pudo guardar la configuracion -- {exc}")
        return False


def hex_to_rgb(hex_color: str) -> tuple:
    """Convierte hex a (R, G, B)."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    elif len(hex_color) == 3:
        return tuple(int(c * 2, 16) for c in hex_color)
    return (51, 255, 255)



