#!/usr/bin/env python3
"""
Deteccion de codificadores GPU -- prueba ffmpeg en busca de codecs acelerados.
"""

import subprocess
from utils.ffmpeg import get_ffmpeg_path

_GPU_CODECS = {
    "nvenc": "h264_nvenc",
    "qsv": "h264_qsv",
    "vaapi": "h264_vaapi",
    "videotoolbox": "h264_videotoolbox",
}


def detect_gpu_codecs() -> list[str]:
    """
    Devuelve una lista de codificadores GPU funcionales.
    """
    ffmpeg = get_ffmpeg_path()
    try:
        result = subprocess.run(
            [ffmpeg, "-encoders"],
            capture_output=True, text=True, timeout=5,
        )
        salida_lower = result.stdout.lower()
    except Exception:
        return []

    disponibles: list[str] = []
    for _corto, nombre_completo in _GPU_CODECS.items():
        if nombre_completo not in salida_lower:
            continue
        try:
            cmd_prueba = [
                ffmpeg,
                "-f", "lavfi",
                "-i", "testsrc=duration=1:size=320x240:rate=15",
                "-frames:v", "1",
                "-c:v", nombre_completo,
                "-f", "null", "-",
            ]
            subprocess.run(cmd_prueba, capture_output=True, timeout=5)
            disponibles.append(nombre_completo)
        except Exception:
            pass

    return disponibles
