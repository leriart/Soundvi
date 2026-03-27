#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Soundvi -- Generador de Video con Visualizador Modular
------------------------------------------------------
Aplicacion de escritorio para generar videos reactivos al audio.
Disenado con arquitectura de modulos "Plug and Play".

Modos de ejecucion:
    python main.py                              # Modo por defecto (PyQt6)
    python main.py --profile basico             # Con perfil especifico
    python main.py --profile creador
    python main.py --profile profesional
    python main.py --profile personalizado
"""

import sys
import os
import argparse
import multiprocessing as mp
import atexit
import platform
import tempfile
import time
import logging

# -- Asegurar ruta del proyecto -----------------------------------------------
_RAIZ_PROYECTO = os.path.dirname(os.path.abspath(__file__))
if _RAIZ_PROYECTO not in sys.path:
    sys.path.insert(0, _RAIZ_PROYECTO)

# -----------------------------------------------------------------------------
# Deteccion de entorno empaquetado
# -----------------------------------------------------------------------------
def is_frozen():
    """Retorna True si el codigo se ejecuta dentro de un ejecutable empaquetado."""
    return getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS') or hasattr(sys, 'oxidized')

# -----------------------------------------------------------------------------
# Instancia unica robusta (funciona en desarrollo y empaquetado)
# -----------------------------------------------------------------------------
_LOCK_FD = None

def single_instance_lock():
    """Evita que se ejecuten multiples instancias de la aplicacion."""
    global _LOCK_FD
    lock_dir = tempfile.gettempdir()
    lock_file = os.path.join(lock_dir, "soundvi_instance.lock")

    if platform.system() == 'Windows':
        try:
            if os.path.exists(lock_file):
                os.remove(lock_file)
            _LOCK_FD = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        except OSError:
            print("[!] ERROR: Ya hay otra instancia de Soundvi ejecutandose.")
            sys.exit(1)
    else:
        import fcntl
        try:
            _LOCK_FD = os.open(lock_file, os.O_CREAT | os.O_RDWR)
            fcntl.flock(_LOCK_FD, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (IOError, OSError):
            print("[!] ERROR: Ya hay otra instancia de Soundvi ejecutandose.")
            sys.exit(1)

    def release_lock():
        global _LOCK_FD
        if _LOCK_FD is not None:
            try:
                if platform.system() != 'Windows':
                    import fcntl
                    fcntl.flock(_LOCK_FD, fcntl.LOCK_UN)
                os.close(_LOCK_FD)
            except:
                pass

    atexit.register(release_lock)

# -----------------------------------------------------------------------------
# Optimizacion y dependencias
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
    """Verifica dependencias criticas para PyQt6."""
    faltantes = []
    for pkg in ("PyQt6", "numpy", "cv2", "PIL"):
        try:
            __import__(pkg)
        except ImportError:
            faltantes.append(pkg)
    if faltantes:
        print("[!] ERROR -- Dependencias faltantes:")
        for m in faltantes: print(f"  - {m}")
        print("\nInstale con: pip install PyQt6 opencv-python numpy pillow")
        sys.exit(1)

# -----------------------------------------------------------------------------
# Aplicacion principal (PyQt6)
# -----------------------------------------------------------------------------
def run_app(perfil: str = ""):
    """Punto de entrada de la GUI PyQt6."""
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QIcon

    from core.profiles import ProfileManager
    from gui.qt6.theme import AdministradorTemas
    from gui.qt6.main_window import VentanaPrincipalQt6
    from gui.qt6.splash_screen import SoundviSplashScreen
    from gui.qt6.profile_selector import (
        es_primer_inicio, mostrar_selector_perfil,
        cargar_preferencias, obtener_tema_guardado
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Soundvi")
    app.setApplicationVersion("5.1")
    app.setOrganizationName("Soundvi")

    # Icono de aplicacion (Zoundvi logo)
    zoundvi_logo = os.path.join(_RAIZ_PROYECTO, "multimedia", "zoundvi", "zoundvi_logo.png")
    logo_path = os.path.join(_RAIZ_PROYECTO, "logos", "logo.png")
    icon_path = zoundvi_logo if os.path.isfile(zoundvi_logo) else logo_path
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Aplicar tema desde preferencias guardadas (o darkly por defecto)
    temas = AdministradorTemas()
    tema_inicial = obtener_tema_guardado()
    temas.aplicar_tema(tema_inicial, app)

    # Inicializar ProfileManager
    pm = ProfileManager()
    pm.cargar()

    # Detectar primer inicio o perfil via CLI
    primer_inicio = es_primer_inicio()
    prefs = cargar_preferencias()
    recordar = prefs.get("recordar", False)

    if perfil and perfil in pm.perfiles_disponibles:
        # Perfil via linea de comandos: aplicar directamente
        pm.seleccionar_perfil(perfil)
        print(f"[*] Perfil seleccionado via CLI: {perfil}")
    elif primer_inicio or not recordar:
        # Primer inicio o usuario no marco "recordar": mostrar selector
        resultado = mostrar_selector_perfil(pm, primer_inicio=primer_inicio)
        if resultado is None:
            print("[*] Seleccion de perfil cancelada. Usando perfil por defecto.")
            pm.seleccionar_perfil("creador")
        else:
            # Aplicar el tema que el usuario eligio en el selector
            tema_elegido = obtener_tema_guardado()
            if tema_elegido != temas.tema_actual:
                temas.aplicar_tema(tema_elegido, app)
    else:
        # Restaurar perfil guardado
        perfil_guardado = prefs.get("perfil", "")
        if perfil_guardado and perfil_guardado in pm.perfiles_disponibles:
            pm.seleccionar_perfil(perfil_guardado)
            print(f"[*] Perfil restaurado desde preferencias: {perfil_guardado}")

    # Splash Screen con Zoundvi
    splash = SoundviSplashScreen()
    splash.show()
    app.processEvents()

    # Crear ventana principal
    ventana = VentanaPrincipalQt6(pm)

    # Funcion para mostrar ventana al terminar splash
    def _mostrar_ventana():
        ventana.show()
        print(f"[*] Soundvi iniciado (perfil: {pm.perfil_activo.nombre})")

    # Iniciar animacion del splash
    splash.iniciar(callback_fin=_mostrar_ventana)

    sys.exit(app.exec())

# -----------------------------------------------------------------------------
# Argumentos CLI
# -----------------------------------------------------------------------------
def parse_args():
    """Parsea argumentos de linea de comandos."""
    parser = argparse.ArgumentParser(
        description="Soundvi -- Editor de Video Modular con Visualizacion de Audio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python main.py                              # Iniciar Soundvi
  python main.py --profile basico             # Con perfil basico
  python main.py --profile profesional        # Con todo activado
        """
    )
    parser.add_argument("--profile", type=str, default="",
                        choices=["basico", "creador", "profesional", "personalizado", ""],
                        help="Perfil de usuario")
    parser.add_argument("--theme", type=str, default="darkly",
                        choices=["darkly", "claro"],
                        help="Tema visual")
    parser.add_argument("--version", action="version",
                        version="Soundvi v5.1")
    return parser.parse_args()

# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------
def main():
    args = parse_args()

    # Evitar multiples instancias
    single_instance_lock()

    # Optimizar
    optimize_python_settings()

    # Verificar dependencias
    print("[*] Modo: PyQt6")
    check_dependencies()
    run_app(perfil=args.profile)


if __name__ == "__main__":
    main()
