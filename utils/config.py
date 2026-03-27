#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Soundvi -- Sistema de configuracion persistente.

Gestiona la carga, guardado y validacion de ajustes para Soundvi.
Los archivos de configuracion se almacenan en una ubicacion apropiada
del sistema operativo del usuario (AppData en Windows, ~/.config en Linux,
~/Library en macOS), NO dentro del ejecutable.

Al iniciar, si no existe el archivo de configuracion, se crea automaticamente
con valores por defecto. Soporta ejecucion tanto en desarrollo como empaquetado.
"""

import json
import os
import sys
import platform
import logging
from pathlib import Path
from typing import Any, Dict, Optional

log = logging.getLogger("soundvi.config")

# ---------------------------------------------------------------------------
#  Valores por defecto
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: Dict[str, Any] = {
    # -- Aplicacion --
    "version": "4.8",
    "video_library": "moviepy",
    "theme": "darkly",
    "idioma": "Espanol",

    # -- FFmpeg --
    "ffmpeg_path": "",
    "cpu_threads": 4,
    "ffmpeg_preset": "medium",
    "ffmpeg_codec": "libx264",
    "use_gpu": False,
    "gpu_codec": "h264_nvenc",

    # -- Comportamiento --
    "auto_save": True,
    "autosave_intervalo": 300,
    "preview_quality": "medium",
    "log_level": "info",

    # -- Apariencia de barras --
    "bar_color_r": 51,
    "bar_color_g": 255,
    "bar_color_b": 255,
    "bar_height_ratio": 0.60,
    "bar_width_px": 20,
    "bar_spacing_px": 5,
    "bar_center_offset": 0.5,

    # -- Volumen --
    "final_volume": 100,
    "volume_protection": True,
    "normalize_audio": True,
    "max_safe_volume": 150,

    # -- Subtitulos --
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

    # -- Modulos activos --
    "subtitles_enabled": False,

    # -- Salida de video --
    "width": 1920,
    "height": 1080,
    "fps": 30,
    "fade": 3.0,

    # -- Rutas de archivos --
    "media_path": "",
    "audio_path": "",
    "output_path": "",
    "subtitle_path": "",
    "carpeta_proyectos": "",
    "ultima_carpeta_abierta": "",

    # -- Timeline --
    "snap_habilitado": True,
    "snap_sensibilidad": 10,
    "track_height_default": 60,
    "mostrar_waveforms": True,
    "mostrar_thumbnails": True,

    # -- Performance --
    "gpu_aceleracion": False,
    "cache_size_mb": 512,
    "threads": 0,

    # -- Shortcuts --
    "shortcuts": {
        "Nuevo proyecto":    "Ctrl+N",
        "Abrir proyecto":    "Ctrl+O",
        "Guardar proyecto":  "Ctrl+S",
        "Importar medios":   "Ctrl+I",
        "Exportar video":    "Ctrl+E",
        "Deshacer":          "Ctrl+Z",
        "Rehacer":           "Ctrl+Y",
        "Dividir clip":      "Ctrl+Shift+X",
        "Eliminar clip":     "Delete",
        "Play/Pause":        "Space",
        "Stop":              "S",
        "Zoom acercar":      "Ctrl++",
        "Zoom alejar":       "Ctrl+-",
    },
}

# Valores por defecto para preferencias de usuario (perfil, tema, wizard, etc.)
DEFAULT_USER_PREFS: Dict[str, Any] = {
    "perfil": "creador",
    "tema": "darkly",
    "recordar": False,
    "wizard_completado": False,
    "ultima_carpeta_abierta": "",
    "ultimo_volumen": 100,
}


# ---------------------------------------------------------------------------
#  Rutas de configuracion del sistema
# ---------------------------------------------------------------------------

def _is_frozen() -> bool:
    """Retorna True si se ejecuta dentro de un ejecutable empaquetado."""
    return getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS') or hasattr(sys, 'oxidized')


def get_config_dir() -> Path:
    """
    Retorna la ruta del directorio de configuracion de Soundvi.
    
    - Windows:  %APPDATA%/Soundvi/
    - macOS:    ~/Library/Application Support/Soundvi/
    - Linux:    ~/.config/Soundvi/
    
    Si el directorio no existe, lo crea automaticamente.
    """
    sistema = platform.system()
    
    if sistema == "Windows":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        config_dir = Path(base) / "Soundvi"
    elif sistema == "Darwin":
        config_dir = Path.home() / "Library" / "Application Support" / "Soundvi"
    else:
        # Linux y otros Unix
        xdg_config = os.environ.get("XDG_CONFIG_HOME", "")
        if xdg_config:
            config_dir = Path(xdg_config) / "Soundvi"
        else:
            config_dir = Path.home() / ".config" / "Soundvi"
    
    # Crear directorio si no existe
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        log.warning("No se pudo crear directorio de configuracion %s: %s", config_dir, e)
        # Fallback: usar directorio del proyecto
        config_dir = Path(__file__).resolve().parent.parent
    
    return config_dir


def get_config_path() -> Path:
    """Retorna la ruta del archivo de configuracion principal."""
    return get_config_dir() / "config.json"


def get_user_prefs_path() -> Path:
    """Retorna la ruta del archivo de preferencias de usuario."""
    return get_config_dir() / "user_preferences.json"


def get_settings_path() -> Path:
    """Retorna la ruta del archivo de settings del dialogo."""
    return get_config_dir() / "soundvi_settings.json"


# ---------------------------------------------------------------------------
#  Carga y guardado de configuracion principal
# ---------------------------------------------------------------------------

def load_config() -> dict:
    """
    Carga la configuracion principal desde JSON.
    Si el archivo no existe, lo crea con valores por defecto.
    Fusiona con DEFAULT_CONFIG para asegurar que todas las claves existan.
    """
    config_path = get_config_path()
    try:
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as fh:
                config = json.load(fh)
            # Fusionar con defaults para claves nuevas
            changed = False
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
                    changed = True
            if changed:
                save_config(config)
            return config
        else:
            log.info("Archivo de configuracion no encontrado. Creando con valores por defecto: %s", config_path)
            save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("No se pudo cargar la configuracion desde %s: %s", config_path, exc)
        return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> bool:
    """
    Guarda la configuracion en JSON.
    Limpia valores que tengan metodo .get() (tkinter variables).
    """
    config_path = get_config_path()
    try:
        # Fusionar con defaults para claves faltantes
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value

        cleaned = {}
        for key, value in config.items():
            if isinstance(value, dict):
                # Para diccionarios, guardar el diccionario completo
                cleaned[key] = value
            elif hasattr(value, "get") and callable(value.get):
                # Para objetos con método get() (como defaultdict)
                try:
                    cleaned[key] = value.get()
                except TypeError:
                    # Si get() necesita argumentos, guardar el objeto tal cual
                    cleaned[key] = value
            else:
                cleaned[key] = value

        with open(config_path, "w", encoding="utf-8") as fh:
            json.dump(cleaned, fh, indent=2, ensure_ascii=False)
        log.debug("Configuracion guardada en %s", config_path)
        return True
    except OSError as exc:
        log.warning("No se pudo guardar la configuracion en %s: %s", config_path, exc)
        return False


# ---------------------------------------------------------------------------
#  Carga y guardado de preferencias de usuario
# ---------------------------------------------------------------------------

def load_user_prefs() -> dict:
    """
    Carga las preferencias de usuario desde JSON.
    Si el archivo no existe, lo crea con valores por defecto.
    """
    prefs_path = get_user_prefs_path()
    try:
        if prefs_path.exists():
            with open(prefs_path, "r", encoding="utf-8") as fh:
                prefs = json.load(fh)
            # Fusionar con defaults
            for key, value in DEFAULT_USER_PREFS.items():
                if key not in prefs:
                    prefs[key] = value
            return prefs
        else:
            log.info("Preferencias de usuario no encontradas. Creando: %s", prefs_path)
            save_user_prefs(DEFAULT_USER_PREFS)
            return DEFAULT_USER_PREFS.copy()
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("No se pudo cargar preferencias de usuario: %s", exc)
        return DEFAULT_USER_PREFS.copy()


def save_user_prefs(prefs: dict) -> bool:
    """Guarda las preferencias de usuario en JSON."""
    prefs_path = get_user_prefs_path()
    try:
        with open(prefs_path, "w", encoding="utf-8") as fh:
            json.dump(prefs, fh, indent=2, ensure_ascii=False)
        log.debug("Preferencias de usuario guardadas en %s", prefs_path)
        return True
    except OSError as exc:
        log.warning("No se pudo guardar preferencias de usuario: %s", exc)
        return False


def is_first_launch() -> bool:
    """Retorna True si es el primer inicio (no existe archivo de preferencias)."""
    return not get_user_prefs_path().exists()


# ---------------------------------------------------------------------------
#  Carga y guardado de settings del dialogo
# ---------------------------------------------------------------------------

def load_settings() -> dict:
    """Carga los settings del dialogo de configuracion."""
    settings_path = get_settings_path()
    try:
        if settings_path.exists():
            with open(settings_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("No se pudo cargar settings: %s", exc)
    return {}


def save_settings(settings: dict) -> bool:
    """Guarda los settings del dialogo de configuracion."""
    settings_path = get_settings_path()
    try:
        with open(settings_path, "w", encoding="utf-8") as fh:
            json.dump(settings, fh, indent=2, ensure_ascii=False)
        return True
    except OSError as exc:
        log.warning("No se pudo guardar settings: %s", exc)
        return False


# ---------------------------------------------------------------------------
#  Inicializacion del sistema de configuracion
# ---------------------------------------------------------------------------

def inicializar_configuracion():
    """
    Inicializa el sistema de configuracion:
    - Crea el directorio de configuracion si no existe
    - Crea archivos por defecto si no existen
    - Migra configuracion legacy si es necesario
    
    Debe llamarse al inicio de la aplicacion.
    """
    config_dir = get_config_dir()
    log.info("Directorio de configuracion: %s", config_dir)
    
    # Crear archivos por defecto si no existen
    if not get_config_path().exists():
        save_config(DEFAULT_CONFIG)
        log.info("Configuracion por defecto creada")
    
    if not get_user_prefs_path().exists():
        save_user_prefs(DEFAULT_USER_PREFS)
        log.info("Preferencias de usuario por defecto creadas")
    
    # Migrar archivos legacy del directorio del proyecto
    _migrar_config_legacy()


def _migrar_config_legacy():
    """
    Migra archivos de configuracion del directorio del proyecto
    a la nueva ubicacion del sistema.
    """
    raiz = Path(__file__).resolve().parent.parent
    config_dir = get_config_dir()
    
    archivos_legacy = {
        "config.json": get_config_path(),
        "user_preferences.json": get_user_prefs_path(),
        "soundvi_settings.json": get_settings_path(),
    }
    
    for nombre_legacy, ruta_nueva in archivos_legacy.items():
        ruta_legacy = raiz / nombre_legacy
        if ruta_legacy.exists() and not ruta_nueva.exists():
            try:
                with open(ruta_legacy, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                with open(ruta_nueva, "w", encoding="utf-8") as f:
                    json.dump(datos, f, indent=2, ensure_ascii=False)
                log.info("Migrado %s -> %s", ruta_legacy, ruta_nueva)
            except Exception as e:
                log.warning("Error migrando %s: %s", nombre_legacy, e)


# ---------------------------------------------------------------------------
#  Utilidades
# ---------------------------------------------------------------------------

def hex_to_rgb(hex_color: str) -> tuple:
    """Convierte hex a (R, G, B)."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    elif len(hex_color) == 3:
        return tuple(int(c * 2, 16) for c in hex_color)
    return (51, 255, 255)


def get_value(config: dict, key: str, default: Any = None) -> Any:
    """Obtiene un valor de configuracion con fallback a default."""
    val = config.get(key, default)
    if val is None:
        val = DEFAULT_CONFIG.get(key, default)
    return val
