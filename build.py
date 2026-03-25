#!/usr/bin/env python3
"""
Build Script para Soundvi - Soporta PyInstaller y PyOxidizer (CORREGIDO)
Versión final con sintaxis Starlark válida y sin condicionales globales.
"""

import os
import sys
import shutil
import argparse
import subprocess
import platform
from pathlib import Path
import zipfile
import tarfile

class SoundviBuilder:
    def __init__(self, project_dir=None):
        self.project_dir = Path(project_dir or os.getcwd())
        self.build_dir = self.project_dir / "build_output"
        self.dist_dir = self.project_dir / "dist"
        
        self.configs = {
            "windows": {
                "ext": ".exe",
                "icon": self.project_dir / "logos" / "logo.ico",
                "requirements": ["pyinstaller", "pyoxidizer"],
            },
            "linux": {
                "ext": "",
                "icon": self.project_dir / "logos" / "logo.png",
                "requirements": ["pyinstaller", "pyoxidizer"],
            },
            "macos": {
                "ext": ".app",
                "icon": self.project_dir / "logos" / "logo.icns",
                "requirements": ["pyinstaller", "pyoxidizer"],
            }
        }
    
    def check_dependencies(self, target_platform, builder):
        """Verificar dependencias según el builder elegido."""
        config = self.configs[target_platform]
        missing = []
        
        for req in config["requirements"]:
            if builder == "pyoxidizer" and req == "pyoxidizer":
                if shutil.which("pyoxidizer") is None:
                    missing.append(req)
                continue
            
            if builder != "pyoxidizer" or req != "pyoxidizer":
                import_name = req.replace("-", "_")
                if req == "pyinstaller":
                    import_name = "PyInstaller"
                try:
                    __import__(import_name)
                except ImportError:
                    missing.append(req)
        
        if missing:
            print(f"[ERROR] Dependencias faltantes para {target_platform} con builder {builder}:")
            for dep in missing:
                print(f"   - {dep}")
            if builder == "pyoxidizer" and "pyoxidizer" in missing:
                print("\n[INFO] PyOxidizer debe instalarse con: pip install pyoxidizer")
            else:
                print(f"\nInstalar con: pip install {' '.join(missing)}")
            return False
        return True
    
    def clean_build_dirs(self):
        for dir_path in [self.build_dir, self.dist_dir]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"[Clean] Limpiado: {dir_path}")
        self.build_dir.mkdir(exist_ok=True)
        self.dist_dir.mkdir(exist_ok=True)
    
    # --------------------------------------------------------------------------
    # Builder: PyInstaller
    # --------------------------------------------------------------------------
    def build_with_pyinstaller(self, target_platform):
        print(f"[PyInstaller] Compilando para {target_platform}...")
        spec_content = self._create_pyinstaller_spec(target_platform)
        spec_path = self.project_dir / "soundvi.spec"
        spec_path.write_text(spec_content)
        
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "--noconfirm",
            str(spec_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_dir)
            if result.returncode == 0:
                output_path = self._find_executable(target_platform)
                if output_path:
                    size_mb = output_path.stat().st_size / (1024 * 1024)
                    print(f"[OK] Build exitoso: {output_path}")
                    print(f"[Size] {size_mb:.2f} MB")
                    return True
                else:
                    print("[ERROR] No se encontró el ejecutable generado.")
            else:
                print(f"[ERROR] PyInstaller falló (código {result.returncode}):")
                print("--- STDOUT ---")
                print(result.stdout)
                print("--- STDERR ---")
                print(result.stderr)
        except Exception as e:
            print(f"[ERROR] Error ejecutando PyInstaller: {e}")
        return False
    
    def _create_pyinstaller_spec(self, target_platform):
        use_upx = True
        excludes = [
            'matplotlib', 'sklearn', 'scikit-learn', 'imageio_ffmpeg',
            'PyQt5', 'PySide2', 'PyQt6', 'IPython', 'jupyter',
            'tensorflow', 'torch', 'pandas', 'notebook',
        ]
        return f'''# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.json', '.'),
        ('fonts', 'fonts'),
        ('logos', 'logos'),
        ('core', 'core'),
        ('gui', 'gui'),
        ('modules', 'modules'),
        ('utils', 'utils'),
    ],
    hiddenimports=[
        'numpy', 'cv2', 'librosa', 'moviepy', 'ttkbootstrap',
        'PIL', 'scipy', 'pygame', 'pydub', 'soundfile',
        'tkinter', '_tkinter',
        'PIL._imaging', 'PIL._imagingtk',
        'numpy.core._dtype_ctypes', 'numpy.lib.format',
        'scipy.interpolate', 'scipy.signal', 'scipy.fft',
        'librosa.core.fft', 'librosa.core.audio', 'librosa.util',
        'librosa.core.spectrum', 'librosa.core.constantq',
        'librosa.feature', 'librosa.effects',
        'scipy.signal.spectral', 'scipy.signal.windows',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes={excludes},
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='soundvi',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx={use_upx},
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='{self.configs[target_platform]["icon"]}' if os.path.exists('{self.configs[target_platform]["icon"]}') else None,
)

# Sin COLLECT para generar un solo ejecutable
'''
    
    # --------------------------------------------------------------------------
    # Builder: PyOxidizer (con Starlark válido)
    # --------------------------------------------------------------------------
    def build_with_pyoxidizer(self, target_platform):
        print(f"[PyOxidizer] Compilando para {target_platform}...")
        self._create_pyoxidizer_config(target_platform)
        
        cmd = ["pyoxidizer", "build", "--release"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_dir)
            if result.returncode == 0:
                output_path = self._find_executable(target_platform, builder="pyoxidizer")
                if output_path:
                    size_mb = output_path.stat().st_size / (1024 * 1024)
                    print(f"[OK] Build exitoso: {output_path}")
                    print(f"[Size] {size_mb:.2f} MB")
                    return True
                else:
                    print("[ERROR] No se encontró el ejecutable generado por PyOxidizer.")
            else:
                print(f"[ERROR] PyOxidizer falló (código {result.returncode}):")
                print("--- STDOUT ---")
                print(result.stdout)
                print("--- STDERR ---")
                print(result.stderr)
        except Exception as e:
            print(f"[ERROR] Error ejecutando PyOxidizer: {e}")
        return False
    
    def _create_pyoxidizer_config(self, target_platform):
        """Genera pyoxidizer.bzl con sintaxis Starlark válida (sin condicionales globales)."""
        ext = self.configs[target_platform]["ext"]
        exe_name = f"soundvi{ext}"
        
        # Contenido sin espacios iniciales y sin if global
        config = '''# pyoxidizer.bzl para Soundvi - Generador de Video con Visualizador
# Configuración específica para el proyecto Soundvi de https://github.com/leriart/Soundvi

def make_exe():
    """Crea un ejecutable para Soundvi."""
    
    # Usar la distribución de Python por defecto
    dist = default_python_distribution()
    
    # Configurar política de empaquetado
    policy = dist.make_python_packaging_policy()
    
    # Configurar ubicación de recursos (en memoria para mejor rendimiento)
    policy.resources_location_fallback = "in-memory"
    
    # Excluir módulos pesados que no son necesarios
    policy.excluded_module_names.update([
        "matplotlib", "sklearn", "scikit-learn", "imageio_ffmpeg",
        "PyQt5", "PySide2", "PyQt6", "IPython", "jupyter",
        "tensorflow", "torch", "pandas", "notebook",
    ])
    
    # Configuración del intérprete Python
    python_config = dist.make_python_interpreter_config()
    
    # Ejecutar el módulo main al iniciar
    python_config.run_module = "main"
    
    # Configurar para usar el intérprete embebido
    python_config.use_module_runner = True
    
    # Crear ejecutable
    exe = dist.to_python_executable(
        name="%s",
        packaging_policy=policy,
        config=python_config,
    )
    
    # Instalar dependencias desde requirements.txt
    print("[PyOxidizer] Instalando dependencias desde requirements.txt...")
    exe.add_python_resources(exe.pip_install(["-r", "requirements.txt"]))
    
    # Incluir módulos de código fuente como paquetes Python
    print("[PyOxidizer] Incluyendo módulos de código fuente...")
    
    # Core - motor de procesamiento
    exe.add_python_resources(exe.read_package_root(
        path="core",
        packages=["core"],
        excludes=["**/__pycache__", "**/*.pyc"],
    ))
    
    # GUI - interfaz gráfica
    exe.add_python_resources(exe.read_package_root(
        path="gui",
        packages=["gui"],
        excludes=["**/__pycache__", "**/*.pyc"],
    ))
    
    # Modules - sistema modular plug-and-play
    exe.add_python_resources(exe.read_package_root(
        path="modules",
        packages=["modules"],
        excludes=["**/__pycache__", "**/*.pyc"],
    ))
    
    # Utils - utilidades
    exe.add_python_resources(exe.read_package_root(
        path="utils",
        packages=["utils"],
        excludes=["**/__pycache__", "**/*.pyc"],
    ))
    
    # Incluir main.py como módulo principal
    exe.add_python_resources(exe.read_file("main.py", dest="main.py"))
    
    # Incluir archivos de configuración
    exe.add_python_resources(exe.read_file("config.json", dest="config.json"))
    exe.add_python_resources(exe.read_file("README.md", dest="README.md"))
    
    # Incluir directorios de recursos
    exe.add_python_resources(exe.read_directory("fonts", dest="fonts"))
    exe.add_python_resources(exe.read_directory("logos", dest="logos"))
    
    # Incluir directorios de configuración de módulos
    exe.add_python_resources(exe.read_directory("modules_config", dest="modules_config"))
    
    # Configuración específica de plataforma (icono asignado directamente)
    if VARS.get("TARGET_TRIPLE", "").endswith("-windows-msvc"):
        # Configuración para Windows
        exe.windows_runtime_dlls_mode = "always"
        exe.windows_subsystem = "windows"  # O "console" para aplicaciones de consola
        # Configurar icono (se asume que el archivo existe)
        exe.icon = "logos/logo.ico"
        print("[PyOxidizer] Icono configurado: logos/logo.ico")
            
    elif VARS.get("TARGET_TRIPLE", "").endswith("-linux-"):
        # Configuración para Linux
        exe.icon = "logos/logo.png"
        print("[PyOxidizer] Icono configurado: logos/logo.png")
            
    elif VARS.get("TARGET_TRIPLE", "").endswith("-darwin"):
        # Configuración para macOS
        exe.icon = "logos/logo.icns"
        print("[PyOxidizer] Icono configurado: logos/logo.icns")
    
    return exe

def make_embedded_resources(exe):
    """Crea recursos embebidos a partir del ejecutable."""
    return exe.to_embedded_resources()

def make_install(exe):
    """Crea un manifiesto de instalación."""
    files = FileManifest()
    files.add_python_resource(".", exe)
    
    # Agregar archivos adicionales si es necesario
    for extra_file in ["README.md", "LICENSE"]:
        # En Starlark, read_file devuelve el contenido o None si no existe
        if read_file(extra_file):
            files.add_file(extra_file)
    
    return files

def make_windows_installer(exe):
    """Crea un instalador MSI para Windows."""
    return exe.to_wix_msi_builder(
        id_prefix="soundvi",
        product_name="Soundvi",
        product_version="1.0.0",
        product_manufacturer="Lerit",
        arch="x64" if "x86_64" in VARS.get("TARGET_TRIPLE", "") else "x86",
    )

def make_macos_app_bundle(exe):
    """Crea un bundle de aplicación para macOS."""
    bundle = MacOsApplicationBundleBuilder("Soundvi")
    bundle.set_info_plist_required_keys(
        display_name="Soundvi",
        identifier="com.leriart.soundvi",
        version="1.0.0",
        signature="????",  # Necesita un código de firma real
        executable="soundvi",
    )
    
    m = FileManifest()
    m.add_python_resource(".", exe)
    bundle.add_macos_manifest(m)
    
    return bundle

# Registrar todos los targets (sin condicionales globales)
register_target("exe", make_exe)
register_target("resources", make_embedded_resources, depends=["exe"])
register_target("install", make_install, depends=["exe"], default=True)
register_target("msi_installer", make_windows_installer, depends=["exe"])
register_target("macos_bundle", make_macos_app_bundle, depends=["exe"])

resolve_targets()
''' % exe_name
        
        with open(self.project_dir / "pyoxidizer.bzl", "w") as f:
            f.write(config)
        print("[PyOxidizer] Archivo de configuración pyoxidizer.bzl generado (Starlark válido).")
    
    # --------------------------------------------------------------------------
    # Helper para encontrar el ejecutable
    # --------------------------------------------------------------------------
    def _find_executable(self, target_platform, builder="pyinstaller"):
        ext = self.configs[target_platform]["ext"]
        name = f"soundvi{ext}"
        
        if builder == "pyinstaller":
            candidates = [
                self.dist_dir / name,
                self.dist_dir / "soundvi" / name,
            ]
            for cand in candidates:
                if cand.exists():
                    return cand
        elif builder == "pyoxidizer":
            build_dir = self.project_dir / "build"
            if build_dir.exists():
                for root, dirs, files in os.walk(build_dir):
                    if name in files:
                        return Path(root) / name
        return None
    
    # --------------------------------------------------------------------------
    # Empaquetado portable
    # --------------------------------------------------------------------------
    def package_portable(self, target_platform, builder):
        print(f"[Portable] Creando paquete portable para {target_platform}...")
        executable = self._find_executable(target_platform, builder)
        if not executable:
            print(f"[ERROR] Ejecutable no encontrado para empaquetar.")
            return False
        
        portable_dir = self.dist_dir / f"Soundvi-Portable-{target_platform.capitalize()}"
        if portable_dir.exists():
            shutil.rmtree(portable_dir)
        portable_dir.mkdir()
        
        shutil.copy(executable, portable_dir / executable.name)
        
        for data_dir in ["fonts", "logos", "core", "gui", "modules", "utils"]:
            src = self.project_dir / data_dir
            if src.exists():
                shutil.copytree(src, portable_dir / data_dir)
        
        for data_file in ["config.json", "README.md"]:
            src = self.project_dir / data_file
            if src.exists():
                shutil.copy(src, portable_dir / data_file)
        
        if target_platform == "windows":
            launcher = portable_dir / "Run-Soundvi.bat"
            launcher.write_text('''@echo off
echo Soundvi Portable para Windows
echo.
soundvi.exe
pause
''')
        else:
            launcher = portable_dir / "run-soundvi.sh"
            launcher.write_text('''#!/bin/bash
echo "Soundvi Portable para Linux"
echo ""
./soundvi
''')
            os.chmod(launcher, 0o755)
        
        if target_platform == "windows":
            zip_path = self.dist_dir / f"Soundvi-Portable-{target_platform}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(portable_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, portable_dir)
                        zipf.write(file_path, f"Soundvi-Portable/{arcname}")
        else:
            tar_path = self.dist_dir / f"Soundvi-Portable-{target_platform}.tar.gz"
            with tarfile.open(tar_path, 'w:gz') as tar:
                tar.add(portable_dir, arcname=f"Soundvi-Portable-{target_platform}")
        
        size_mb = Path(zip_path if target_platform == "windows" else tar_path).stat().st_size / (1024 * 1024)
        print(f"[OK] Paquete portable creado: {size_mb:.2f} MB")
        return True
    
    # --------------------------------------------------------------------------
    # Construcción principal
    # --------------------------------------------------------------------------
    def build(self, target_platform, builder, create_portable=False):
        print(f"\n{'='*60}")
        print(f"BUILD SOUNDVI - {target_platform.upper()} (builder: {builder})")
        print(f"{'='*60}")
        
        if not self.check_dependencies(target_platform, builder):
            return False
        
        self.clean_build_dirs()
        
        success = False
        if builder == "pyinstaller":
            success = self.build_with_pyinstaller(target_platform)
        elif builder == "pyoxidizer":
            success = self.build_with_pyoxidizer(target_platform)
        else:
            print(f"[ERROR] Builder '{builder}' no soportado.")
            return False
        
        if success and create_portable:
            self.package_portable(target_platform, builder)
        
        return success

def main():
    parser = argparse.ArgumentParser(description="Build Soundvi con PyInstaller o PyOxidizer")
    parser.add_argument("--platform", choices=["windows", "linux", "macos", "all"], 
                       default=platform.system().lower(), help="Plataforma objetivo")
    parser.add_argument("--builder", choices=["pyinstaller", "pyoxidizer"], 
                       default="pyinstaller", help="Herramienta de construcción")
    parser.add_argument("--portable", action="store_true", help="Crear paquete portable")
    parser.add_argument("--output-dir", help="Directorio de salida")
    parser.add_argument("--clean", action="store_true", help="Limpiar antes de build")
    
    args = parser.parse_args()
    
    builder = SoundviBuilder()
    
    if args.output_dir:
        builder.dist_dir = Path(args.output_dir)
    if args.clean:
        builder.clean_build_dirs()
    
    platforms = []
    if args.platform == "all":
        platforms = ["windows", "linux", "macos"]
    else:
        platforms = [args.platform]
    
    all_success = True
    for platform_name in platforms:
        success = builder.build(platform_name, args.builder, args.portable)
        if not success:
            all_success = False
            print(f"[ERROR] Build falló para {platform_name} con {args.builder}")
    
    if all_success:
        print(f"\n{'*'*20}")
        print("BUILDS COMPLETADOS EXITOSAMENTE")
        print(f"{'*'*20}")
        print(f"\nOutput en: {builder.dist_dir}")
        print("Archivos creados:")
        for item in builder.dist_dir.iterdir():
            if item.is_file():
                size_mb = item.stat().st_size / (1024 * 1024)
                print(f"   - {item.name} ({size_mb:.1f} MB)")
    
    return 0 if all_success else 1

if __name__ == "__main__":
    sys.exit(main())
