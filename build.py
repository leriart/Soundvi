#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Soundvi -- Script de empaquetado multiplataforma mejorado.

Genera ejecutables standalone para Windows, Linux y macOS usando PyInstaller.
Soporta construccion de multiples plataformas en una sola ejecucion.

Uso:
    python build.py                                # Build para la plataforma actual
    python build.py --platform windows             # Build para Windows
    python build.py --platform linux               # Build para Linux
    python build.py --platform windows linux macos # Build para todas las indicadas
    python build.py --platform all                 # Build para TODAS las plataformas
    python build.py --version 4.8.0                # Con version custom
    python build.py --onefile                      # Ejecutable unico
    python build.py --clean                        # Limpiar build previos
    python build.py --appimage                     # (Linux) Generar AppImage
"""

import os
import sys
import io
import shutil
import platform
import subprocess
import argparse
import json
import hashlib
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
#  Configuracion de codificacion multiplataforma
# ---------------------------------------------------------------------------
# En Windows, la consola usa cp1252 por defecto, lo cual no soporta
# caracteres Unicode como U+2713 (checkmark). Forzamos UTF-8 en stdout/stderr
# para evitar UnicodeEncodeError en cualquier plataforma.

def _configurar_codificacion():
    """Configura stdout/stderr para usar UTF-8 con fallback seguro."""
    if sys.stdout.encoding and sys.stdout.encoding.lower().replace('-', '') != 'utf8':
        try:
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True
            )
        except Exception:
            pass
    if sys.stderr.encoding and sys.stderr.encoding.lower().replace('-', '') != 'utf8':
        try:
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True
            )
        except Exception:
            pass
    # Variable de entorno para subprocesos Python
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    # En Windows 10+, habilitar UTF-8 en la consola si es posible
    if platform.system() == 'Windows':
        os.environ.setdefault('PYTHONUTF8', '1')
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleOutputCP(65001)
            kernel32.SetConsoleCP(65001)
        except Exception:
            pass

_configurar_codificacion()

# ---------------------------------------------------------------------------
#  Simbolos seguros multiplataforma (ASCII puro)
# ---------------------------------------------------------------------------
# Usamos alternativas ASCII para garantizar compatibilidad con cualquier
# codificacion de consola (cp1252 en Windows, UTF-8 en Linux/macOS).

OK = "[OK]"       # En lugar de U+2713 (checkmark)
FAIL = "[FAIL]"   # En lugar de U+2717 (cross mark)
INFO = "[*]"       # En lugar de asteriscos u otros simbolos
WARN = "[!]"       # Advertencia

_RAIZ = os.path.dirname(os.path.abspath(__file__))
_DIST = os.path.join(_RAIZ, "dist")
_BUILD = os.path.join(_RAIZ, "build")

VERSION_DEFECTO = "4.8.0"
NOMBRE_APP = "Soundvi"
PLATAFORMAS_VALIDAS = ["windows", "linux", "macos"]

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
        print(f"  {OK} PyInstaller {PyInstaller.__version__} encontrado.")
        return True
    except ImportError:
        print(f"  {WARN} PyInstaller no instalado. Instalando...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyinstaller>=6.0"],
            stdout=subprocess.DEVNULL
        )
        print(f"  {OK} PyInstaller instalado correctamente.")
        return True


def limpiar_build():
    """Limpia directorios de build previos."""
    for d in [_DIST, _BUILD]:
        if os.path.isdir(d):
            shutil.rmtree(d)
            print(f"  {OK} Limpiado: {d}")
    # Limpiar .spec files
    for spec in Path(_RAIZ).glob("*.spec"):
        spec.unlink()
        print(f"  {OK} Limpiado: {spec.name}")


def calcular_hash(ruta: str) -> str:
    """Calcula SHA256 del archivo."""
    sha256 = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(8192), b""):
            sha256.update(bloque)
    return sha256.hexdigest()


def obtener_tamano_legible(ruta: str) -> str:
    """Retorna el tamano del archivo en formato legible."""
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
        # Qt6 (todos los modulos necesarios)
        "PyQt6", "PyQt6.QtWidgets", "PyQt6.QtCore", "PyQt6.QtGui",
        "PyQt6.QtPrintSupport", "PyQt6.sip",
        # Componentes especificos de Qt que PyInstaller puede perder
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
        # Audio (todos los modulos necesarios)
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
    """Modulos a excluir para reducir tamano."""
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
              onefile: bool = False, dist_dir: str = None):
    """Ejecuta PyInstaller para construir el ejecutable.
    
    Args:
        plataforma: Plataforma objetivo (windows, linux, macos).
        version: Version del build.
        modo_debug: Si True, build en modo debug.
        onefile: Si True, genera ejecutable unico.
        dist_dir: Directorio de salida. Si None, usa dist/<plataforma>/.
    
    Returns:
        True si el build fue exitoso, False en caso contrario.
    """
    # Directorio de salida por plataforma
    if dist_dir is None:
        dist_dir = os.path.join(_DIST, plataforma)
    
    build_dir = os.path.join(_BUILD, plataforma)
    
    print(f"\n{'='*60}")
    print(f"  Soundvi Build System v3.0 (Multi-Platform)")
    print(f"{'='*60}")
    print(f"  App:        {NOMBRE_APP} v{version}")
    print(f"  Plataforma: {plataforma}")
    print(f"  Modo:       {'onefile' if onefile else 'onedir'}")
    print(f"  Debug:      {'Si' if modo_debug else 'No'}")
    print(f"  Salida:     {dist_dir}")
    print(f"  Fecha:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Python:     {sys.version.split()[0]}")
    print(f"  OS:         {platform.platform()}")
    print(f"{'='*60}\n")

    print("[1/5] Verificando dependencias...")
    verificar_pyinstaller()

    print("\n[2/5] Limpiando builds previos de esta plataforma...")
    for d in [dist_dir, build_dir]:
        if os.path.isdir(d):
            shutil.rmtree(d)
            print(f"  {OK} Limpiado: {d}")
    # Limpiar .spec files de esta plataforma
    for spec in Path(_RAIZ).glob("*.spec"):
        spec.unlink()
        print(f"  {OK} Limpiado: {spec.name}")

    print("\n[3/5] Preparando configuracion...")

    # Icono segun plataforma
    if plataforma == "windows":
        icono = os.path.join(_RAIZ, "logos", "logo.ico")
    elif plataforma == "macos":
        icono = os.path.join(_RAIZ, "logos", "logo.icns")
        if not os.path.isfile(icono):
            icono = os.path.join(_RAIZ, "logos", "logo.png")
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
        "--distpath", dist_dir,
        "--workpath", build_dir,
        "--log-level", "WARN" if not modo_debug else "DEBUG",
    ]
    
    # Forzar UTF-8 para Unicode (importante para caracteres especiales)
    runtime_hook_path = os.path.join(_RAIZ, "runtime_hook_simple.py")
    if os.path.isfile(runtime_hook_path):
        cmd.extend(["--runtime-hook", runtime_hook_path])

    # Icono
    if os.path.isfile(icono):
        cmd.extend(["--icon", icono])
        print(f"  {OK} Icono: {os.path.basename(icono)}")

    # Datos adicionales
    datos = obtener_datos_adicionales()
    for src, dst in datos:
        separador = ";" if plataforma == "windows" else ":"
        cmd.extend(["--add-data", f"{src}{separador}{dst}"])
    print(f"  {OK} Datos adicionales: {len(datos)} entradas")

    # Hidden imports
    hidden = obtener_hidden_imports()
    for h in hidden:
        cmd.extend(["--hidden-import", h])
    print(f"  {OK} Hidden imports: {len(hidden)} modulos")
    
    # FORZAR inclusion de modulos criticos (solucion agresiva)
    # Esto asegura que PyInstaller incluya los modulos aunque no los detecte
    cmd.extend(["--collect-all", "gui.qt6"])
    cmd.extend(["--collect-all", "modules"])
    cmd.extend(["--collect-all", "core"])

    # Exclusiones para reducir tamano
    excludes = obtener_excludes()
    for ex in excludes:
        cmd.extend(["--exclude-module", ex])
    print(f"  {OK} Exclusiones: {len(excludes)} modulos")

    # Opciones especificas por plataforma
    if plataforma == "linux":
        cmd.extend(["--strip"])  # Strip symbols en Linux
        print(f"  {OK} Strip symbols habilitado (Linux)")

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
        print(f"\n  {FAIL} Build fallido para '{plataforma}' con codigo {resultado.returncode}")
        print("  Sugerencias:")
        print("    - Ejecuta con --debug para mas informacion")
        print("    - Verifica que todas las dependencias esten instaladas")
        print("    - Revisa que no haya errores de importacion")
        return False

    print(f"\n[5/5] Finalizando build ({plataforma})...")

    # Buscar ejecutable generado
    if onefile:
        exe_path = os.path.join(dist_dir, nombre_exe_full)
    else:
        exe_dir_path = os.path.join(dist_dir, nombre_exe)
        if plataforma == "windows":
            exe_path = os.path.join(exe_dir_path, f"{nombre_exe}.exe")
        else:
            exe_path = os.path.join(exe_dir_path, nombre_exe)

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

    # Generar checksums para todos los archivos en dist_dir
    checksums = {}
    if os.path.isdir(dist_dir):
        for root, dirs, files in os.walk(dist_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, dist_dir)
                if not file.endswith(('.json', '.txt')):  # No checksum para metadata
                    checksums[rel_path] = calcular_hash(file_path)
    
    info["checksums"] = checksums

    if os.path.isfile(exe_path):
        info["sha256"] = calcular_hash(exe_path)
        info["tamano"] = obtener_tamano_legible(exe_path)

    info_path = os.path.join(dist_dir, "build_info.json")
    os.makedirs(dist_dir, exist_ok=True)
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)
    
    # Crear archivo de checksums para releases (SHA256SUMS)
    if checksums:
        checksums_path = os.path.join(dist_dir, "SHA256SUMS")
        with open(checksums_path, "w", encoding="utf-8") as f:
            for file_path_rel, hash_value in checksums.items():
                f.write(f"{hash_value}  {file_path_rel}\n")
        print(f"  {OK} Checksums generados: {checksums_path}")

    # Resumen
    print(f"\n{'='*60}")
    print(f"  {OK} BUILD EXITOSO -- {plataforma}")
    print(f"{'='*60}")
    print(f"  Ejecutable: {dist_dir}")
    if os.path.isfile(exe_path):
        print(f"  Tamano:     {info.get('tamano', 'N/A')}")
        print(f"  SHA256:     {info.get('sha256', 'N/A')[:16]}...")
    print(f"  Duracion:   {duracion:.1f}s")
    print(f"  Info:       {info_path}")
    print(f"{'='*60}\n")
    return True


# ---------------------------------------------------------------------------
#  Multi-platform builder
# ---------------------------------------------------------------------------

def construir_multiple(plataformas: list, version: str, modo_debug: bool = False,
                       onefile: bool = False):
    """Construye para multiples plataformas secuencialmente.
    
    Si una plataforma falla, continua con las siguientes y reporta
    un resumen al final.
    
    Args:
        plataformas: Lista de plataformas a construir.
        version: Version del build.
        modo_debug: Si True, build en modo debug.
        onefile: Si True, genera ejecutable unico.
    """
    total = len(plataformas)
    resultados = {}  # plataforma -> True/False
    
    print(f"\n{'#'*60}")
    print(f"  MULTI-PLATFORM BUILD")
    print(f"  Plataformas: {', '.join(plataformas)} ({total} total)")
    print(f"  Version:     {version}")
    print(f"  Modo:        {'onefile' if onefile else 'onedir'}")
    print(f"{'#'*60}")
    
    for idx, plat in enumerate(plataformas, 1):
        print(f"\n{'#'*60}")
        print(f"  [{idx}/{total}] Construyendo para: {plat.upper()}")
        print(f"{'#'*60}")
        
        try:
            exito = construir(plat, version, modo_debug, onefile)
            resultados[plat] = exito
        except Exception as e:
            print(f"\n  {FAIL} Excepcion durante build de '{plat}': {e}")
            resultados[plat] = False
    
    # ---------------------------------------------------------------------------
    #  Reporte final multi-plataforma
    # ---------------------------------------------------------------------------
    exitosos = [p for p, ok in resultados.items() if ok]
    fallidos = [p for p, ok in resultados.items() if not ok]
    
    print(f"\n{'#'*60}")
    print(f"  RESUMEN MULTI-PLATFORM BUILD")
    print(f"{'#'*60}")
    print(f"  Total:    {total}")
    print(f"  Exitosos: {len(exitosos)}")
    print(f"  Fallidos: {len(fallidos)}")
    print()
    
    for plat, ok in resultados.items():
        estado = f"{OK}" if ok else f"{FAIL}"
        dist_plat = os.path.join(_DIST, plat)
        print(f"  {estado} {plat:10s}  ->  {dist_plat}")
    
    if fallidos:
        print(f"\n  {WARN} Plataformas fallidas: {', '.join(fallidos)}")
        print(f"  {INFO} Ejecuta con --debug para mas informacion sobre los errores.")
    
    print(f"\n  Directorio de salida: {_DIST}/")
    print(f"  Estructura:")
    if os.path.isdir(_DIST):
        for plat in plataformas:
            plat_dir = os.path.join(_DIST, plat)
            if os.path.isdir(plat_dir):
                n_files = sum(len(files) for _, _, files in os.walk(plat_dir))
                print(f"    dist/{plat}/  ({n_files} archivos)")
            else:
                print(f"    dist/{plat}/  (no generado)")
    
    print(f"{'#'*60}\n")
    
    # Codigo de salida: falla si TODAS las plataformas fallaron
    if not exitosos:
        sys.exit(1)


# ---------------------------------------------------------------------------
#  AppImage builder (Linux)
# ---------------------------------------------------------------------------

def construir_appimage(version: str):
    """Genera un AppImage para Linux despues del build onedir."""
    print("\n[+] Generando AppImage para Linux...")

    appdir = os.path.join(_DIST, f"{NOMBRE_APP}.AppDir")
    exe_dir = os.path.join(_DIST, f"{NOMBRE_APP}-{version}")

    if not os.path.isdir(exe_dir):
        print(f"{WARN} Primero ejecuta el build onedir antes de generar AppImage.")
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
    print(f"  {INFO} Copiando {exe_dir} a AppDir...")
    shutil.copytree(exe_dir, os.path.join(appdir, "usr", "bin", NOMBRE_APP),
                    dirs_exist_ok=True)

    # Crear AppRun
    apprun = os.path.join(appdir, "AppRun")
    with open(apprun, "w", newline='\n') as f:
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
    with open(desktop, "w", newline='\n') as f:
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
        
        # Tambien copiar a la estructura estandar
        hicolor_icon = os.path.join(appdir, "usr", "share", "icons", "hicolor", "256x256", "apps", "soundvi.png")
        shutil.copy2(icon_src, hicolor_icon)
        print(f"  {OK} Icono copiado: {os.path.basename(icon_src)}")

    # Descargar appimagetool si no esta disponible
    appimagetool = shutil.which("appimagetool")
    if not appimagetool:
        print(f"  {INFO} Descargando appimagetool...")
        appimagetool_url = "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
        appimagetool_path = os.path.join(_DIST, "appimagetool-x86_64.AppImage")
        
        try:
            import urllib.request
            urllib.request.urlretrieve(appimagetool_url, appimagetool_path)
            os.chmod(appimagetool_path, 0o755)
            appimagetool = appimagetool_path
            print(f"  {OK} appimagetool descargado")
        except Exception as e:
            print(f"  {WARN} Error descargando appimagetool: {e}")
            print(f"  {INFO} Intentando con curl...")
            subprocess.run(["curl", "-L", appimagetool_url, "-o", appimagetool_path], check=False)
            if os.path.isfile(appimagetool_path):
                os.chmod(appimagetool_path, 0o755)
                appimagetool = appimagetool_path
                print(f"  {OK} appimagetool descargado via curl")

    if appimagetool:
        output = os.path.join(_DIST, f"{NOMBRE_APP}-{version}-x86_64.AppImage")
        print(f"  {INFO} Generando AppImage: {os.path.basename(output)}")
        
        # Ejecutar appimagetool
        cmd = [appimagetool, "--appimage-extract-and-run", appdir, output]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.isfile(output):
            os.chmod(output, 0o755)
            print(f"  {OK} AppImage generado: {output}")
            print(f"  {OK} Tamano: {obtener_tamano_legible(output)}")
            
            # Crear symlink sin version
            symlink = os.path.join(_DIST, f"{NOMBRE_APP}.AppImage")
            if os.path.exists(symlink):
                os.remove(symlink)
            os.symlink(os.path.basename(output), symlink)
            print(f"  {OK} Symlink creado: {NOMBRE_APP}.AppImage")
        else:
            print(f"  {WARN} Error generando AppImage:")
            print(f"      Exit code: {result.returncode}")
            print(f"      stderr: {result.stderr[:200]}")
    else:
        print(f"  {WARN} appimagetool no encontrado.")
        print(f"  {INFO} La estructura AppDir esta lista en:")
        print(f"      {appdir}")
        print(f"  {INFO} Puedes generar el AppImage manualmente con:")
        print(f"      appimagetool {appdir} {NOMBRE_APP}-{version}.AppImage")


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------

def _resolver_plataformas(valores: list) -> list:
    """Resuelve la lista de plataformas a partir de los valores del CLI.
    
    Soporta:
      - Un solo valor: ['windows'] -> ['windows']
      - Varios valores: ['windows', 'linux'] -> ['windows', 'linux']
      - 'all': ['all'] -> ['windows', 'linux', 'macos']
    
    Elimina duplicados manteniendo orden.
    """
    if not valores:
        return [detectar_plataforma()]
    
    # Si alguno de los valores es 'all', devolver todas las plataformas
    if "all" in valores:
        return list(PLATAFORMAS_VALIDAS)
    
    # Eliminar duplicados preservando orden
    vistos = set()
    resultado = []
    for v in valores:
        if v not in vistos:
            vistos.add(v)
            resultado.append(v)
    return resultado


def main():
    parser = argparse.ArgumentParser(
        description=f"{NOMBRE_APP} -- Script de empaquetado multiplataforma",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python build.py                                  # Build para tu plataforma
  python build.py --platform windows               # Build para Windows
  python build.py --platform linux                 # Build para Linux
  python build.py --platform windows linux macos   # Build para las 3 plataformas
  python build.py --platform all                   # Build para TODAS las plataformas
  python build.py --onefile                        # Ejecutable unico
  python build.py --appimage                       # Generar AppImage (Linux)
  python build.py --version 4.8.0                  # Con version especifica
  python build.py --clean                          # Solo limpiar
        """
    )
    parser.add_argument("--platform", nargs="+",
                        choices=["windows", "linux", "macos", "all"],
                        default=None,
                        help="Plataforma(s) objetivo. Usa 'all' para todas. "
                             "Ejemplo: --platform windows linux")
    parser.add_argument("--version", default=VERSION_DEFECTO,
                        help=f"Version del build (default: {VERSION_DEFECTO})")
    parser.add_argument("--debug", action="store_true",
                        help="Build en modo debug")
    parser.add_argument("--onefile", action="store_true",
                        help="Generar ejecutable unico (--onefile)")
    parser.add_argument("--clean", action="store_true",
                        help="Solo limpiar directorios de build")
    parser.add_argument("--appimage", action="store_true",
                        help="Generar AppImage (solo Linux)")

    args = parser.parse_args()

    if args.clean:
        print(f"{INFO} Limpiando directorios de build...")
        limpiar_build()
        print(f"{OK} Limpieza completada.")
        # NO return aqui - continuar con el build despues de limpiar

    if args.appimage:
        construir_appimage(args.version)
        return

    plataformas = _resolver_plataformas(args.platform)
    
    if len(plataformas) == 1:
        # Build de una sola plataforma (comportamiento clasico)
        exito = construir(plataformas[0], args.version, args.debug, args.onefile)
        if not exito:
            sys.exit(1)
    else:
        # Build multi-plataforma con reporte
        construir_multiple(plataformas, args.version, args.debug, args.onefile)


if __name__ == "__main__":
    main()
