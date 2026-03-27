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
    python build.py --version 4.8.0       # Con version custom
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

VERSION_DEFECTO = "4.8.0"
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
        print(f"  [2713] PyInstaller {PyInstaller.__version__} encontrado.")
        return True
    except ImportError:
        print("  [!] PyInstaller no instalado. Instalando...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyinstaller>=6.0"],
            stdout=subprocess.DEVNULL
        )
        print("  [2713] PyInstaller instalado correctamente.")
        return True


def limpiar_build():
    """Limpia directorios de build previos."""
    for d in [_DIST, _BUILD]:
        if os.path.isdir(d):
            shutil.rmtree(d)
            print(f"  [2713] Limpiado: {d}")
    # Limpiar .spec files
    for spec in Path(_RAIZ).glob("*.spec"):
        spec.unlink()
        print(f"  [2713] Limpiado: {spec.name}")


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
    
    # Runtime hook SIMPLE para Unicode (sin Qt)
    runtime_hook = os.path.join(_RAIZ, "runtime_hook_simple.py")
    if os.path.isfile(runtime_hook):
        datos.append((runtime_hook, "."))

    return datos


def obtener_hidden_imports() -> list:
    """Retorna la lista de hidden imports para PyInstaller."""
    return [
        # Qt6 (todos los módulos necesarios)
        "PyQt6", "PyQt6.QtWidgets", "PyQt6.QtCore", "PyQt6.QtGui",
        "PyQt6.QtPrintSupport", "PyQt6.sip",
        # Componentes específicos de Qt que PyInstaller puede perder
        "PyQt6.QtGui.QAction", "PyQt6.QtGui.QActionGroup",
        "PyQt6.QtWidgets.QMenu", "PyQt6.QtWidgets.QMenuBar",
        "PyQt6.QtWidgets.QToolBar", "PyQt6.QtWidgets.QStatusBar",
        "PyQt6.QtWidgets.QDockWidget", "PyQt6.QtWidgets.QFileDialog",
        "PyQt6.QtWidgets.QMessageBox", "PyQt6.QtWidgets.QSplitter",
        "PyQt6.QtWidgets.QTabWidget",
        # Core
        "cv2", "numpy", "PIL", "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont",
        "PIL.ImageOps", "PIL.ImageFilter", "PIL.ImageEnhance",
        # Modulos internos
        "modules.core.base", "modules.core.registry", "modules.core.manager",
        "modules.video", "modules.audio", "modules.text",
        "modules.utility", "modules.export",
        # Audio (todos los módulos necesarios)
        "scipy", "scipy.signal", "scipy.fft", "scipy.io", "scipy.ndimage",
        "pydub", "soundfile", "librosa", "librosa.feature", "librosa.effects",
        # Procesamiento
        "threadpoolctl", "joblib", "moviepy", "moviepy.editor", "moviepy.video", "moviepy.audio",
        "numba", "sklearn", "sklearn.cluster", "sklearn.preprocessing",
        # Gui internos (TODOS los widgets)
        "gui.qt6", "gui.qt6.main_window", "gui.qt6.theme",
        "gui.qt6.profile_selector", "gui.qt6.base",
        "gui.qt6.toolbar_widget", "gui.qt6.sidebar_widget",
        "gui.qt6.preview_widget", "gui.qt6.timeline_widget",
        "gui.qt6.media_library_widget", "gui.qt6.inspector_widget",
        "gui.qt6.audio_mixer_widget", "gui.qt6.transitions_panel",
        "gui.qt6.theme_selector", "gui.qt6.welcome_wizard",
        "gui.qt6.scripting_panel", "gui.qt6.export_dialog",
        "gui.qt6.about_dialog", "gui.qt6.splash_screen",
        "gui.loading",
        # Encoding/Unicode
        "encodings", "encodings.utf_8", "encodings.latin_1",
        "codecs", "locale", "json",
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
    
    # Forzar UTF-8 para Unicode (importante para caracteres especiales)
    cmd.extend(["--runtime-hook", "runtime_hook_simple.py"])

    # Icono
    if os.path.isfile(icono):
        cmd.extend(["--icon", icono])
        print(f"  [2713] Icono: {os.path.basename(icono)}")

    # Datos adicionales
    datos = obtener_datos_adicionales()
    for src, dst in datos:
        separador = ";" if plataforma == "windows" else ":"
        cmd.extend(["--add-data", f"{src}{separador}{dst}"])
    print(f"  [2713] Datos adicionales: {len(datos)} entradas")

    # Hidden imports
    hidden = obtener_hidden_imports()
    for h in hidden:
        cmd.extend(["--hidden-import", h])
    print(f"  [2713] Hidden imports: {len(hidden)} módulos")

    # Exclusiones para reducir tamaño
    excludes = obtener_excludes()
    for ex in excludes:
        cmd.extend(["--exclude-module", ex])
    print(f"  [2713] Exclusiones: {len(excludes)} módulos")

    # Opciones especificas por plataforma
    if plataforma == "linux":
        cmd.extend(["--strip"])  # Strip symbols en Linux
        print("  [2713] Strip symbols habilitado (Linux)")

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
        print(f"\n  [2717] Build fallido con codigo {resultado.returncode}")
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

    # Generar checksums para todos los archivos en dist/
    checksums = {}
    if os.path.isdir(_DIST):
        for root, dirs, files in os.walk(_DIST):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, _DIST)
                if not file.endswith(('.json', '.txt')):  # No checksum para metadata
                    checksums[rel_path] = calcular_hash(file_path)
    
    info["checksums"] = checksums

    if os.path.isfile(exe_path):
        info["sha256"] = calcular_hash(exe_path)
        info["tamano"] = obtener_tamano_legible(exe_path)

    info_path = os.path.join(_DIST, "build_info.json")
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)
    
    # Crear archivo de checksums para releases (SHA256SUMS)
    if checksums:
        checksums_path = os.path.join(_DIST, "SHA256SUMS")
        with open(checksums_path, "w", encoding="utf-8") as f:
            for file_path, hash_value in checksums.items():
                f.write(f"{hash_value}  {file_path}\n")
        print(f"  [2713] Checksums generados: {checksums_path}")

    # Resumen
    print(f"\n{'='*60}")
    print(f"  2713 BUILD EXITOSO")
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

    # Limpiar AppDir previo si existe
    if os.path.isdir(appdir):
        shutil.rmtree(appdir)

    # Crear estructura AppDir
    os.makedirs(os.path.join(appdir, "usr", "bin"), exist_ok=True)
    os.makedirs(os.path.join(appdir, "usr", "share", "icons", "hicolor", "256x256", "apps"), exist_ok=True)
    os.makedirs(os.path.join(appdir, "usr", "share", "applications"), exist_ok=True)

    # Copiar ejecutable y dependencias
    print(f"  [*] Copiando {exe_dir} a AppDir...")
    shutil.copytree(exe_dir, os.path.join(appdir, "usr", "bin", NOMBRE_APP),
                    dirs_exist_ok=True)

    # Crear AppRun
    apprun = os.path.join(appdir, "AppRun")
    with open(apprun, "w") as f:
        f.write(f"""#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
export PATH="$HERE/usr/bin/{NOMBRE_APP}:$PATH"
export LD_LIBRARY_PATH="$HERE/usr/bin/{NOMBRE_APP}:$LD_LIBRARY_PATH"
cd "$HERE"
exec "$HERE/usr/bin/{NOMBRE_APP}/{NOMBRE_APP}-{version}" "$@"
""")
    os.chmod(apprun, 0o755)

    # Crear .desktop
    desktop = os.path.join(appdir, f"{NOMBRE_APP}.desktop")
    with open(desktop, "w") as f:
        f.write(f"""[Desktop Entry]
Type=Application
Name={NOMBRE_APP}
GenericName=Video Editor with Audio Visualization
Comment=Modular video editor with reactive audio visualization
Exec=AppRun
Icon=soundvi
Categories=AudioVideo;Video;AudioVideoEditing;
Terminal=false
StartupNotify=true
MimeType=video/mp4;video/avi;video/mkv;video/mov;
""")

    # Copiar icono
    icon_src = os.path.join(_RAIZ, "logos", "logo.png")
    if os.path.isfile(icon_src):
        icon_dest = os.path.join(appdir, "soundvi.png")
        shutil.copy2(icon_src, icon_dest)
        
        # También copiar a la estructura estándar
        hicolor_icon = os.path.join(appdir, "usr", "share", "icons", "hicolor", "256x256", "apps", "soundvi.png")
        shutil.copy2(icon_src, hicolor_icon)
        print(f"  [2713] Icono copiado: {os.path.basename(icon_src)}")

    # Descargar appimagetool si no está disponible
    appimagetool = shutil.which("appimagetool")
    if not appimagetool:
        print("  [*] Descargando appimagetool...")
        appimagetool_url = "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
        appimagetool_path = os.path.join(_DIST, "appimagetool-x86_64.AppImage")
        
        try:
            import urllib.request
            urllib.request.urlretrieve(appimagetool_url, appimagetool_path)
            os.chmod(appimagetool_path, 0o755)
            appimagetool = appimagetool_path
            print("  [2713] appimagetool descargado")
        except Exception as e:
            print(f"  [!] Error descargando appimagetool: {e}")
            print("  [*] Intentando con curl...")
            subprocess.run(["curl", "-L", appimagetool_url, "-o", appimagetool_path], check=False)
            if os.path.isfile(appimagetool_path):
                os.chmod(appimagetool_path, 0o755)
                appimagetool = appimagetool_path
                print("  [2713] appimagetool descargado via curl")

    if appimagetool:
        output = os.path.join(_DIST, f"{NOMBRE_APP}-{version}-x86_64.AppImage")
        print(f"  [*] Generando AppImage: {os.path.basename(output)}")
        
        # Ejecutar appimagetool
        cmd = [appimagetool, "--appimage-extract-and-run", appdir, output]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.isfile(output):
            os.chmod(output, 0o755)
            print(f"  [2713] AppImage generado: {output}")
            print(f"  [2713] Tamaño: {obtener_tamano_legible(output)}")
            
            # Crear symlink sin versión
            symlink = os.path.join(_DIST, f"{NOMBRE_APP}.AppImage")
            if os.path.exists(symlink):
                os.remove(symlink)
            os.symlink(os.path.basename(output), symlink)
            print(f"  [2713] Symlink creado: {NOMBRE_APP}.AppImage")
        else:
            print(f"  [!] Error generando AppImage:")
            print(f"      Exit code: {result.returncode}")
            print(f"      stderr: {result.stderr[:200]}")
    else:
        print("  [!] appimagetool no encontrado.")
        print("  [*] La estructura AppDir está lista en:")
        print(f"      {appdir}")
        print("  [*] Puedes generar el AppImage manualmente con:")
        print(f"      appimagetool {appdir} {NOMBRE_APP}-{version}.AppImage")


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
  python build.py --version 4.8.0         # Con versión específica
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
        print("[2713] Limpieza completada.")
        # NO return aquí - continuar con el build después de limpiar

    if args.appimage:
        construir_appimage(args.version)
        return

    plataforma = args.platform or detectar_plataforma()
    construir(plataforma, args.version, args.debug, args.onefile)


if __name__ == "__main__":
    main()
