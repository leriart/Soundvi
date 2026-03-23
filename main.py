#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Soundvi - Generador de Video con Visualizador Modular
------------------------------------------------------
Aplicación de escritorio para generar videos reactivos al audio.
Diseñado con arquitectura de módulos "Plug and Play".

Uso:
    python main.py

Requisitos:
    - Python 3.10+
    - FFmpeg (en el sistema o provisto en la UI)
"""

import sys
import os
import multiprocessing as mp
import threading

# -- Asegurar ruta del proyecto -----------------------------------------------
_RAIZ_PROYECTO = os.path.dirname(os.path.abspath(__file__))
if _RAIZ_PROYECTO not in sys.path:
    sys.path.insert(0, _RAIZ_PROYECTO)

def optimize_python_settings():
    """Optimiza configuraciones de Python para mejor rendimiento."""
    print("=== INICIANDO SOUNDVI (MODO OPTIMIZADO) ===")
    num_cores = max(1, mp.cpu_count() - 1)
    os.environ['OMP_NUM_THREADS'] = str(num_cores)
    os.environ['MKL_NUM_THREADS'] = str(num_cores)
    os.environ['NUMEXPR_NUM_THREADS'] = str(num_cores)
    
    try:
        import numba
        numba.set_num_threads(num_cores)
        print(f"[*] Numba threads set: {num_cores}")
    except ImportError:
        pass
    print(f"[*] Optimizacion activada. Nucleos: {num_cores}\n")

def check_dependencies():
    """Verifica dependencias críticas."""
    faltantes = []
    for pkg in ("ttkbootstrap", "numpy", "cv2", "PIL", "librosa"):
        try:
            __import__(pkg)
        except ImportError:
            faltantes.append(pkg)
    if faltantes:
        print("[!] ERROR -- Dependencias faltantes:")
        for m in faltantes: print(f"  - {m}")
        print("\nInstale con: pip install -r requirements.txt")
        sys.exit(1)

def run_app():
    """Punto de entrada de la GUI."""
    import tkinter as tk
    import ttkbootstrap as tb
    from gui.app import SoundviApp
    import shutil

    if not shutil.which("ffmpeg"):
        print("[!] ADVERTENCIA: ffmpeg no encontrado en PATH.")
        print("  Configure una ruta en la pestaña Ajustes de la aplicación.")

    root = tb.Window(themename="darkly")
    
    logo_png = os.path.join(_RAIZ_PROYECTO, "logos", "logo.png")
    logo_ico = os.path.join(_RAIZ_PROYECTO, "logos", "logo.ico")
    
    if os.path.exists(logo_ico):
        try: root.iconbitmap(logo_ico)
        except Exception: pass
    elif os.path.exists(logo_png):
        try:
            logo_img = tk.PhotoImage(file=logo_png)
            root.iconphoto(False, logo_img)
        except Exception: pass

    app = SoundviApp(root)
    app.mainloop()

def main():
    optimize_python_settings()
    check_dependencies()
    # Ejecutamos la app de manera segura, el hilo principal en GUI
    run_app()

if __name__ == "__main__":
    main()