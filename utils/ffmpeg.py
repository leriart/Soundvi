#!/usr/bin/env python3
"""
Resolucion del binario FFmpeg -- encuentra el mejor ffmpeg disponible.

Soporta ruta personalizada almacenada en config.json (clave ``ffmpeg_path``).
"""

import os
import shutil
import platform
import subprocess
from pathlib import Path


# Variable global para ruta personalizada (se establece desde la config)
_ruta_personalizada: str | None = None


def set_custom_ffmpeg_path(ruta: str | None):
    """Establece una ruta personalizada de FFmpeg."""
    global _ruta_personalizada
    _ruta_personalizada = ruta


def validate_ffmpeg_path(ruta: str) -> bool:
    """
    Valida que la ruta apunta a un ejecutable FFmpeg funcional.
    Devuelve True si funciona correctamente.
    """
    if not ruta or not os.path.isfile(ruta):
        return False
    try:
        result = subprocess.run(
            [ruta, "-version"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0 and "ffmpeg" in result.stdout.lower()
    except Exception:
        return False


def get_ffmpeg_path() -> str:
    """
    Localiza el binario de ffmpeg con la siguiente prioridad:

    1. Ruta personalizada configurada por el usuario.
    2. Un binario ``ffmpeg-static`` incluido junto a la raiz del proyecto.
    3. El binario del sistema encontrado via PATH.
    4. Ubicaciones comunes codificadas como ultimo recurso.
    """
    # -- 1. Ruta personalizada --
    if _ruta_personalizada and os.path.isfile(_ruta_personalizada):
        if validate_ffmpeg_path(_ruta_personalizada):
            print(f"[ffmpeg] Usando ruta personalizada -> {_ruta_personalizada}")
            return _ruta_personalizada

    # -- 2. Binario estatico incluido --
    raiz_proyecto = Path(__file__).resolve().parent.parent
    binario_estatico = raiz_proyecto / "ffmpeg-static"
    if binario_estatico.exists():
        if not os.access(str(binario_estatico), os.X_OK):
            try:
                os.chmod(str(binario_estatico), 0o755)
            except OSError:
                pass
        print(f"[ffmpeg] Usando binario incluido -> {binario_estatico}")
        return str(binario_estatico)

    # -- 3. Binario del sistema en PATH --
    ffmpeg_sistema = shutil.which("ffmpeg")
    if ffmpeg_sistema:
        print(f"[ffmpeg] Usando binario del sistema -> {ffmpeg_sistema}")
        return ffmpeg_sistema

    # -- 4. Ubicaciones comunes --
    sistema = platform.system()
    candidatos = []
    if sistema == "Windows":
        candidatos = [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        ]
    elif sistema == "Darwin":
        candidatos = ["/usr/local/bin/ffmpeg", "/opt/homebrew/bin/ffmpeg"]
    else:
        candidatos = ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]

    for candidato in candidatos:
        if os.path.isfile(candidato):
            print(f"[ffmpeg] Encontrado en ubicacion de respaldo -> {candidato}")
            return candidato

    print("[ffmpeg] Advertencia: no se localizo ningun binario; usando 'ffmpeg' por defecto")
    return "ffmpeg"
