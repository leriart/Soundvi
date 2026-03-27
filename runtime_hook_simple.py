#!/usr/bin/env python3
"""
Runtime hook SIMPLE para PyInstaller - Solo configuración básica de encoding.

Este hook se ejecuta al inicio del ejecutable. Mantenlo MUY simple.
NO intentes importar Qt u otros módulos complejos aquí.
"""

import sys
import os
import locale

# Solo configurar encoding básico - nada de Qt
def setup_basic_encoding():
    """Configuración mínima de encoding para evitar segmentation faults."""
    
    # 1. Configurar variables de entorno para UTF-8
    # Esto es seguro y no causa segmentation faults
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    os.environ.setdefault('PYTHONUTF8', '1')
    
    # 2. Configurar locale básico (sin forzar demasiado)
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error:
        # Si falla, intentar locale simple
        try:
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        except locale.Error:
            # Si todo falla, al menos configurar variables
            pass
    
    # 3. Configurar LANG/LC_ALL si no están definidos
    if 'LANG' not in os.environ:
        os.environ['LANG'] = 'C.UTF-8'
    if 'LC_ALL' not in os.environ:
        os.environ['LC_ALL'] = 'C.UTF-8'
    
    # 4. Forzar encoding UTF-8 en stdout/stderr (seguro)
    # Esto es necesario para que los caracteres Unicode se muestren correctamente
    try:
        # Reabrir stdout/stderr con encoding UTF-8
        if sys.stdout and hasattr(sys.stdout, 'buffer'):
            sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
        if sys.stderr and hasattr(sys.stderr, 'buffer'):
            sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)
    except Exception:
        # Si falla, continuar sin cambios (no es crítico)
        pass
    
    # 5. Debug info (solo si variable está definida)
    if os.environ.get('SOUNDVI_DEBUG_RUNTIME'):
        print(f"[RUNTIME HOOK SIMPLE] Encoding configurado")
        print(f"  PYTHONIOENCODING: {os.environ.get('PYTHONIOENCODING')}")
        print(f"  LANG: {os.environ.get('LANG')}")
        print(f"  LC_ALL: {os.environ.get('LC_ALL')}")

# Ejecutar SOLO la configuración básica
setup_basic_encoding()

# NOTA CRÍTICA: Este hook se ejecuta ANTES de que Qt se inicialice.
# NO importes PyQt6 aquí - causará segmentation faults.
# La configuración de fuentes debe hacerse en main.py después de que
# QApplication esté creada.