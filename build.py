#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Soundvi -- Script de empaquetado multiplataforma mejorado.

Genera ejecutables standalone para Windows y Linux usando PyInstaller.
Incluye optimizaciones para reducir tamaño y dependencias externas.

Uso:
    python build.py                       # Build para la plataforma actual
    python build.py --platform windows    # Build para Windows
    python build.py --platform linux      # Build para Linux
    python build.py --version 5.1.0       # Con version custom
    python build.py --onefile             # Ejecutable unico
    python build.py --clean               # Limpiar build previos
    python build.py --appimage            # (Linux) Generar AppImage
"""

import os
import sys
import shutil
import platform
import subprocess
import argparse
import json
import hashlib
from datetime import datetime
from pathlib import Path

_RAIZ = os.path.dirname(os.path.abspath(__file__))
_DIST = os.path.join(_RAIZ, "dist")
_BUILD = os.path.join(_RAIZ, "build")

VERSION_DEFECTO = "5.1.0"
NOMBRE_APP = "Soundvi"

# ---------------------------------------------------------------------------
#  Utilidades
# ---------------------------------------------------------------------------

def detectar_plataforma() -> str:
    """Detecta la plataforma actual."""
    sistema = platform.system().lower()
    if sistema == "windows":
        return "windows"
    elif sistema == "darwin":
        return "macos"
    return "linux"


def verificar_pyinstaller() -> bool:
    """Verifica que PyInstaller esta instalado."""
    try:
        import PyInstaller
        print(f"  [✓] PyInstaller {PyInstaller.__version__} encontrado.")
        return True
    except ImportError:
        print("  [!] PyInstaller no instalado. Instalando...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyinstaller>=6.0"],
            stdout=subprocess.DEVNULL
        )
        print("  [✓] PyInstaller instalado correctamente.")
        return True


def limpiar_build():
    """Limpia directorios de build previos."""
    for d in [_DIST, _BUILD]:
        if os.path.isdir(d):
            shutil.rmtree(d)
            print(f"  [✓] Limpiado: {d}")
    # Limpiar .spec files
    for spec in Path(_RAIZ).glob("*.spec"):
        spec.unlink()
        print(f"  [✓] Limpiado: {spec.name}")


def calcular_hash(ruta: str) -> str:
    """Calcula SHA256 del archivo."""
    sha256 = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(8192), b""):
            sha256.update(bloque)
    return sha256.hexdigest()


def obtener_tamano_legible(ruta: str) -> str:
    """Retorna el tamaño del archivo en formato legible."""
    size = os.path.getsize(ruta)
    for unidad in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unidad}"
        size /= 1024
    return f"{size:.1f} TB"


# ---------------------------------------------------------------------------
#  Datos para el build
# ---------------------------------------------------------------------------

def obtener_datos_adicionales() -> list:
    """Retorna la lista de datos adicionales para PyInstaller."""
    datos = []
    dirs_incluir = ["logos", "multimedia", "modules", "fonts"]
    for d in dirs_incluir:
        ruta = os.path.join(_RAIZ, d)
        if os.path.isdir(ruta):
            datos.append((ruta, d))

    # Archivos de configuracion
    for cfg in ["config.json", "profiles.json"]:
        ruta = os.path.join(_RAIZ, cfg)
        if os.path.isfile(ruta):
            datos.append((ruta, "."))

    return datos


def obtener_hidden_imports() -> list:
    """Retorna la lista de hidden imports para PyInstaller."""
    return [
        # Qt6
        "PyQt6", "PyQt6.QtWidgets", "PyQt6.QtCore", "PyQt6.QtGui",
        "PyQt6.sip",
        # Core
        "cv2", "numpy", "PIL", "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont",
        # Modulos internos
        "modules.core.base", "modules.core.registry", "modules.core.manager",
        "modules.video", "modules.audio", "modules.text",
        "modules.utility", "modules.export",
        # Audio
        "scipy", "scipy.signal", "scipy.fft",
        "pydub", "soundfile",
        # Procesamiento
        "threadpoolctl", "joblib",
        # Gui internos
        "gui.qt6", "gui.qt6.main_window", "gui.qt6.theme",
        "gui.qt6.profile_selector", "gui.qt6.base",
        "core.profiles", "core.timeline", "core.commands",
        "core.keyframes", "core.video_clip",
        # Utils
        "utils.config", "utils.ffmpeg", "utils.fonts",
    ]


def obtener_excludes() -> list:
    """Modulos a excluir para reducir tamaño."""
    return [
        "tkinter", "_tkinter", "tcl", "tk",
        "unittest", "test", "tests",
        "matplotlib", "matplotlib.backends",
        "IPython", "jupyter",
        "sphinx", "docutils",
        "setuptools", "pip", "wheel",
        "xml.etree.ElementTree",
    ]


# ---------------------------------------------------------------------------
#  Builder principal
# ---------------------------------------------------------------------------

def construir(plataforma: str, version: str, modo_debug: bool = False,
              onefile: bool = False):
    """Ejecuta PyInstaller para construir el ejecutable."""
    print(f"\n{'='*60}")
    print(f"  Soundvi Build System v2.0")
    print(f"{'='*60}")
    print(f"  App:        {NOMBRE_APP} v{version}")
    print(f"  Plataforma: {plataforma}")
    print(f"  Modo:       {'onefile' if onefile else 'onedir'}")
    print(f"  Debug:      {'Sí' if modo_debug else 'No'}")
    print(f"  Fecha:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Python:     {sys.version.split()[0]}")
    print(f"  OS:         {platform.platform()}")
    print(f"{'='*60}\n")

    print("[1/5] Verificando dependencias...")
    verificar_pyinstaller()

    print("\n[2/5] Limpiando builds previos...")
    limpiar_build()

    print("\n[3/5] Preparando configuración...")

    # Icono segun plataforma
    if plataforma == "windows":
        icono = os.path.join(_RAIZ, "logos", "logo.ico")
    else:
        icono = os.path.join(_RAIZ, "logos", "logo.png")

    # Nombre del ejecutable
    nombre_exe = f"{NOMBRE_APP}-{version}"
    if plataforma == "windows":
        nombre_exe_full = f"{nombre_exe}.exe"
    else:
        nombre_exe_full = nombre_exe

    # Construir comando PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", nombre_exe,
        "--onefile" if onefile else "--onedir",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--log-level", "WARN" if not modo_debug else "DEBUG",
    ]

    # Icono
    if os.path.isfile(icono):
        cmd.extend(["--icon", icono])
        print(f"  [✓] Icono: {os.path.basename(icono)}")

    # Datos adicionales
    datos = obtener_datos_adicionales()
    for src, dst in datos:
        separador = ";" if plataforma == "windows" else ":"
        cmd.extend(["--add-data", f"{src}{separador}{dst}"])
    print(f"  [✓] Datos adicionales: {len(datos)} entradas")

    # Hidden imports
    hidden = obtener_hidden_imports()
    for h in hidden:
        cmd.extend(["--hidden-import", h])
    print(f"  [✓] Hidden imports: {len(hidden)} módulos")

    # Exclusiones para reducir tamaño
    excludes = obtener_excludes()
    for ex in excludes:
        cmd.extend(["--exclude-module", ex])
    print(f"  [✓] Exclusiones: {len(excludes)} módulos")

    # Opciones especificas por plataforma
    if plataforma == "linux":
        cmd.extend(["--strip"])  # Strip symbols en Linux
        print("  [✓] Strip symbols habilitado (Linux)")

    if modo_debug:
        cmd.append("--debug=all")

    # Entry point
    cmd.append(os.path.join(_RAIZ, "main.py"))

    print(f"\n[4/5] Ejecutando PyInstaller...")
    print(f"  Comando: {' '.join(cmd[:8])}...")

    inicio = datetime.now()
    resultado = subprocess.run(cmd, cwd=_RAIZ)
    duracion = (datetime.now() - inicio).total_seconds()

    if resultado.returncode != 0:
        print(f"\n  [✗] Build fallido con codigo {resultado.returncode}")
        print("  Sugerencias:")
        print("    - Ejecuta con --debug para más información")
        print("    - Verifica que todas las dependencias estén instaladas")
        print("    - Revisa que no haya errores de importación")
        sys.exit(1)

    print(f"\n[5/5] Finalizando build...")

    # Buscar ejecutable generado
    if onefile:
        exe_path = os.path.join(_DIST, nombre_exe_full)
    else:
        exe_dir = os.path.join(_DIST, nombre_exe)
        if plataforma == "windows":
            exe_path = os.path.join(exe_dir, f"{nombre_exe}.exe")
        else:
            exe_path = os.path.join(exe_dir, nombre_exe)

    # Crear archivo de version/info
    info = {
        "nombre": NOMBRE_APP,
        "version": version,
        "plataforma": plataforma,
        "modo": "onefile" if onefile else "onedir",
        "fecha_build": datetime.now().isoformat(),
        "python": sys.version.split()[0],
        "duracion_build_seg": round(duracion, 1),
        "os": platform.platform(),
    }

    if os.path.isfile(exe_path):
        info["sha256"] = calcular_hash(exe_path)
        info["tamano"] = obtener_tamano_legible(exe_path)

    info_path = os.path.join(_DIST, "build_info.json")
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)

    # Resumen
    print(f"\n{'='*60}")
    print(f"  ✅ BUILD EXITOSO")
    print(f"{'='*60}")
    print(f"  Ejecutable: {_DIST}")
    if os.path.isfile(exe_path):
        print(f"  Tamaño:     {info.get('tamano', 'N/A')}")
        print(f"  SHA256:     {info.get('sha256', 'N/A')[:16]}...")
    print(f"  Duración:   {duracion:.1f}s")
    print(f"  Info:       {info_path}")
    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
#  AppImage builder (Linux)
# ---------------------------------------------------------------------------

def construir_appimage(version: str):
    """Genera un AppImage para Linux después del build onedir."""
    print("\n[+] Generando AppImage para Linux...")

    appdir = os.path.join(_DIST, f"{NOMBRE_APP}.AppDir")
    exe_dir = os.path.join(_DIST, f"{NOMBRE_APP}-{version}")

    if not os.path.isdir(exe_dir):
        print("[!] Primero ejecuta el build onedir antes de generar AppImage.")
        print("    Uso: python build.py --platform linux && python build.py --appimage")
        return

    # Crear estructura AppDir
    os.makedirs(os.path.join(appdir, "usr", "bin"), exist_ok=True)
    os.makedirs(os.path.join(appdir, "usr", "share", "icons"), exist_ok=True)
    os.makedirs(os.path.join(appdir, "usr", "share", "applications"), exist_ok=True)

    # Copiar ejecutable
    shutil.copytree(exe_dir, os.path.join(appdir, "usr", "bin", NOMBRE_APP),
                    dirs_exist_ok=True)

    # Crear AppRun
    apprun = os.path.join(appdir, "AppRun")
    with open(apprun, "w") as f:
        f.write(f"""#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${{SELF%/*}}
exec "$HERE/usr/bin/{NOMBRE_APP}/{NOMBRE_APP}-{version}" "$@"
""")
    os.chmod(apprun, 0o755)

    # Crear .desktop
    desktop = os.path.join(appdir, f"{NOMBRE_APP}.desktop")
    with open(desktop, "w") as f:
        f.write(f"""[Desktop Entry]
Type=Application
Name={NOMBRE_APP}
Exec=AppRun
Icon=soundvi
Categories=AudioVideo;Video;
Comment=Editor de Video Modular con Audio Reactivo
Terminal=false
""")

    # Copiar icono
    icon_src = os.path.join(_RAIZ, "logos", "logo.png")
    if os.path.isfile(icon_src):
        shutil.copy2(icon_src, os.path.join(appdir, "soundvi.png"))
        shutil.copy2(icon_src,
                     os.path.join(appdir, "usr", "share", "icons", "soundvi.png"))

    # Verificar si appimagetool está disponible
    appimagetool = shutil.which("appimagetool")
    if appimagetool:
        output = os.path.join(_DIST, f"{NOMBRE_APP}-{version}-x86_64.AppImage")
        subprocess.run([appimagetool, appdir, output])
        if os.path.isfile(output):
            print(f"  [✓] AppImage generado: {output}")
            print(f"  [✓] Tamaño: {obtener_tamano_legible(output)}")
        else:
            print("  [!] Error generando AppImage")
    else:
        print("  [!] appimagetool no encontrado.")
        print("  Descárgalo de: https://github.com/AppImage/AppImageKit/releases")
        print(f"  La estructura AppDir está lista en: {appdir}")
        print("  Ejecuta manualmente: appimagetool {appdir} {NOMBRE_APP}-{version}.AppImage")


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=f"{NOMBRE_APP} -- Script de empaquetado multiplataforma",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python build.py                         # Build para tu plataforma
  python build.py --platform windows      # Build para Windows
  python build.py --platform linux        # Build para Linux
  python build.py --onefile               # Ejecutable único
  python build.py --appimage              # Generar AppImage (Linux)
  python build.py --version 5.1.0         # Con versión específica
  python build.py --clean                 # Solo limpiar
        """
    )
    parser.add_argument("--platform", choices=["windows", "linux", "macos"],
                        default=None, help="Plataforma objetivo")
    parser.add_argument("--version", default=VERSION_DEFECTO,
                        help=f"Versión del build (default: {VERSION_DEFECTO})")
    parser.add_argument("--debug", action="store_true",
                        help="Build en modo debug")
    parser.add_argument("--onefile", action="store_true",
                        help="Generar ejecutable único (--onefile)")
    parser.add_argument("--clean", action="store_true",
                        help="Solo limpiar directorios de build")
    parser.add_argument("--appimage", action="store_true",
                        help="Generar AppImage (solo Linux)")

    args = parser.parse_args()

    if args.clean:
        print("[*] Limpiando directorios de build...")
        limpiar_build()
        print("[✓] Limpieza completada.")
        return

    if args.appimage:
        construir_appimage(args.version)
        return

    plataforma = args.platform or detectar_plataforma()
    construir(plataforma, args.version, args.debug, args.onefile)


if __name__ == "__main__":
    main()
