#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Soundvi - Generador de Video con Visualizador Modular
------------------------------------------------------
Aplicación de escritorio para generar videos reactivos al audio.
Diseñado con arquitectura de módulos "Plug and Play".
"""

import sys
import os
import multiprocessing as mp
import atexit
import platform
import tempfile
import fcntl
import time
import logging

# -- Asegurar ruta del proyecto -----------------------------------------------
_RAIZ_PROYECTO = os.path.dirname(os.path.abspath(__file__))
if _RAIZ_PROYECTO not in sys.path:
    sys.path.insert(0, _RAIZ_PROYECTO)

# -----------------------------------------------------------------------------
# Instancia única robusta (funciona en desarrollo y empaquetado)
# -----------------------------------------------------------------------------
_LOCK_FILE = None
_LOCK_FD = -1

def single_instance_lock():
    """
    Evita múltiples instancias del programa usando un archivo de bloqueo.
    Funciona en Linux/macOS con fcntl.flock y en Windows con archivo exclusivo.
    Solo se ejecuta en el proceso principal y una sola vez.
    """
    # Solo ejecutar en el proceso principal
    if mp.current_process().name != 'MainProcess':
        return

    # Evitar ejecución repetida dentro del mismo proceso
    if hasattr(single_instance_lock, '_done') and single_instance_lock._done:
        return
    single_instance_lock._done = True

    global _LOCK_FILE, _LOCK_FD

    system = platform.system()
    lock_path = os.path.join(tempfile.gettempdir(), f"soundvi_{os.getenv('USER', 'user')}.lock")

    if system == "Windows":
        # Windows: usar archivo con O_EXCL
        try:
            _LOCK_FD = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.close(_LOCK_FD)   # Solo necesitamos que el archivo exista
            # Marcar como no heredable (opcional)
            os.set_inheritable(_LOCK_FD, False) if _LOCK_FD != -1 else None
        except FileExistsError:
            print("[!] Ya hay una instancia de Soundvi ejecutándose.")
            sys.exit(1)
        atexit.register(lambda: os.unlink(lock_path) if os.path.exists(lock_path) else None)
    else:
        # Linux/macOS: usar fcntl.flock (bloqueo exclusivo)
        try:
            _LOCK_FD = os.open(lock_path, os.O_CREAT | os.O_RDWR)
            fcntl.flock(_LOCK_FD, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Marcar descriptor como no heredable para que los hijos no lo retengan
            os.set_inheritable(_LOCK_FD, False)
        except (IOError, OSError):
            print("[!] Ya hay una instancia de Soundvi ejecutándose.")
            sys.exit(1)
        atexit.register(lambda: (fcntl.flock(_LOCK_FD, fcntl.LOCK_UN), os.close(_LOCK_FD)) if _LOCK_FD != -1 else None)

# -----------------------------------------------------------------------------
# Optimización y dependencias
# -----------------------------------------------------------------------------
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
    # Evitar múltiples instancias
    single_instance_lock()
    # Optimizar y comprobar dependencias
    optimize_python_settings()
    check_dependencies()
    # Ejecutar la GUI
    run_app()

if __name__ == "__main__":
    main()