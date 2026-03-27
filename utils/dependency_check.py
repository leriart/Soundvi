#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Soundvi -- Verificador de dependencias.

Verifica las dependencias del sistema y proporciona mensajes claros
sobre qué falta y cómo instalarlo. Diferencia entre dependencias
críticas (obligatorias) y opcionales.
"""

import sys
import os
import importlib
import subprocess
from typing import Dict, List, Tuple, Optional

# Dependencias: (nombre_import, nombre_pip, es_critica, descripcion)
DEPENDENCIAS: List[Tuple[str, str, bool, str]] = [
    # Críticas (sin estas no arranca)
    ("PyQt6", "PyQt6>=6.5.0", True, "Interfaz gráfica"),
    ("numpy", "numpy>=1.24.0", True, "Procesamiento numérico"),
    ("cv2", "opencv-python>=4.8.0", True, "Procesamiento de video"),
    ("PIL", "pillow>=10.0.0", True, "Procesamiento de imágenes"),
    ("scipy", "scipy>=1.11.0", True, "Procesamiento de audio"),
    
    # Importantes (funcionalidad reducida sin estas)
    ("pydub", "pydub>=0.25.1", False, "Manipulación de audio"),
    ("soundfile", "soundfile>=0.12.0", False, "Lectura de archivos de audio"),
    ("threadpoolctl", "threadpoolctl>=3.2.0", False, "Control de paralelismo"),
    ("joblib", "joblib>=1.3.0", False, "Procesamiento paralelo"),
    
    # Opcionales (funciones avanzadas)
    ("librosa", "librosa>=0.10.0", False, "Análisis avanzado de audio"),
    ("vosk", "vosk>=0.3.45", False, "Subtítulos con IA (offline)"),
    ("moviepy", "moviepy>=1.0.3", False, "Edición de video avanzada"),
    ("numba", "numba>=0.58.0", False, "Aceleración JIT"),
    ("matplotlib", "matplotlib>=3.7.0", False, "Visualizaciones"),
]


def verificar_dependencia(nombre_import: str) -> Tuple[bool, Optional[str]]:
    """Verifica si un módulo está instalado y retorna la versión."""
    try:
        mod = importlib.import_module(nombre_import)
        version = getattr(mod, "__version__", getattr(mod, "VERSION", "?"))
        return True, str(version)
    except ImportError:
        return False, None


def verificar_ffmpeg() -> Tuple[bool, Optional[str]]:
    """Verifica si FFmpeg está disponible en el sistema."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            # Extraer version de la primera línea
            first_line = result.stdout.split("\n")[0]
            return True, first_line
        return False, None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, None


def verificar_todas() -> Dict[str, dict]:
    """Verifica todas las dependencias y retorna un informe."""
    informe = {}
    
    for nombre_import, nombre_pip, critica, descripcion in DEPENDENCIAS:
        instalado, version = verificar_dependencia(nombre_import)
        informe[nombre_import] = {
            "instalado": instalado,
            "version": version,
            "pip": nombre_pip,
            "critica": critica,
            "descripcion": descripcion,
        }
    
    # FFmpeg
    ff_ok, ff_ver = verificar_ffmpeg()
    informe["ffmpeg"] = {
        "instalado": ff_ok,
        "version": ff_ver,
        "pip": "N/A (instalar desde sistema)",
        "critica": False,
        "descripcion": "Codificación/decodificación de video",
    }
    
    return informe


def imprimir_informe():
    """Imprime un informe de dependencias en la consola."""
    informe = verificar_todas()
    
    print("\n" + "=" * 60)
    print("  Soundvi — Verificación de dependencias")
    print("=" * 60)
    
    criticas_ok = True
    
    for nombre, info in informe.items():
        estado = "✓" if info["instalado"] else "✗"
        tipo = "CRÍTICA" if info["critica"] else "opcional"
        version = info["version"] or "no instalado"
        
        if info["instalado"]:
            print(f"  [{estado}] {nombre:<20} v{version:<15} ({info['descripcion']})")
        else:
            marker = "!!" if info["critica"] else "  "
            print(f"  [{estado}]{marker} {nombre:<18} {version:<15} ({info['descripcion']})")
            if info["critica"]:
                criticas_ok = False
    
    print("=" * 60)
    
    if not criticas_ok:
        faltantes = [info["pip"] for info in informe.values()
                     if info["critica"] and not info["instalado"]]
        print(f"\n  [!] Dependencias críticas faltantes:")
        print(f"      pip install {' '.join(faltantes)}")
    else:
        print(f"\n  [✓] Todas las dependencias críticas están instaladas.")
    
    opcionales = [info["pip"] for info in informe.values()
                  if not info["critica"] and not info["instalado"] 
                  and info["pip"] != "N/A (instalar desde sistema)"]
    if opcionales:
        print(f"\n  [i] Dependencias opcionales no instaladas:")
        for p in opcionales[:5]:
            print(f"      pip install {p}")
    
    print()
    return criticas_ok


if __name__ == "__main__":
    ok = imprimir_informe()
    sys.exit(0 if ok else 1)
