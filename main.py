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
import signal
import socket
import atexit
import tkinter as tk

# -----------------------------------------------------------------------------
# Detección de entorno empaquetado (PyInstaller, PyOxidizer)
# -----------------------------------------------------------------------------
def is_frozen():
    return getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS') or hasattr(sys, 'oxidized')

def resource_path(relative_path):
    if is_frozen():
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# -- Asegurar ruta del proyecto -----------------------------------------------
if not is_frozen():
    _RAIZ_PROYECTO = os.path.dirname(os.path.abspath(__file__))
    if _RAIZ_PROYECTO not in sys.path:
        sys.path.insert(0, _RAIZ_PROYECTO)

# =============================================================================
# PARCHE: Instancia única y manejo de señales
# =============================================================================

def setup_single_instance():
    try:
        lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        lock_socket.bind('\0soundvi_single_instance_lock')
        print("[*] Soundvi iniciado (instancia única)")
        return lock_socket
    except socket.error:
        print("[!] ERROR: Ya hay una instancia de Soundvi ejecutándose")
        print("[!] Cierra la ventana existente antes de abrir otra.")
        sys.exit(1)

def cleanup_single_instance(lock_socket):
    if lock_socket:
        try:
            lock_socket.close()
        except:
            pass

def signal_handler(signum, frame):
    print("\n[*] Recibida señal de terminación. Cerrando Soundvi...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

lock_socket = setup_single_instance()
atexit.register(lambda: cleanup_single_instance(lock_socket))

# =============================================================================
# FIN DEL PARCHE
# =============================================================================

def optimize_python_settings():
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
    faltantes = []
    for pkg in ("ttkbootstrap", "numpy", "cv2", "PIL", "librosa"):
        try:
            __import__(pkg)
        except ImportError:
            faltantes.append(pkg)

    if faltantes:
        print("[!] DEPENDENCIAS FALTANTES:")
        for pkg in faltantes:
            print(f"    - {pkg}")
        print("\nInstala con:")
        print("    pip install -r requirements.txt")
        sys.exit(1)

def main():
    optimize_python_settings()
    check_dependencies()

    try:
        from gui.app import SoundviApp
    except ImportError as e:
        print(f"[!] Error importando GUI: {e}")
        print("[!] Asegúrate de que la estructura de carpetas sea correcta.")
        sys.exit(1)

    print("[*] Iniciando interfaz gráfica...")
    root = tk.Tk()
    # Forzar carga del paquete msgcat antes de usar ttkbootstrap
    root.tk.call('package', 'require', 'msgcat')
    app = SoundviApp(root)
    app.run()

if __name__ == "__main__":
    main()