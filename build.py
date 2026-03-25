#!/usr/bin/env python3
"""
Build Script for Soundvi - Supports PyInstaller and PyOxidizer
Versión final: dependencias verificadas correctamente.
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
        """Verifica dependencias según el builder elegido."""
        config = self.configs[target_platform]
        missing = []
        
        for req in config["requirements"]:
            # Solo verificamos la dependencia que corresponde al builder actual
            if builder == "pyinstaller" and req != "pyinstaller":
                continue
            if builder == "pyoxidizer" and req != "pyoxidizer":
                continue
            
            if req == "pyinstaller":
                import_name = "PyInstaller"
                try:
                    __import__(import_name)
                except ImportError:
                    missing.append(req)
            elif req == "pyoxidizer":
                # PyOxidizer es un ejecutable, no un módulo Python
                if shutil.which("pyoxidizer") is None:
                    missing.append(req)
            else:
                # Otras dependencias (por si se añaden en el futuro)
                import_name = req.replace("-", "_")
                try:
                    __import__(import_name)
                except ImportError:
                    missing.append(req)
        
        if missing:
            print(f"[ERROR] Missing dependencies for {target_platform} with builder {builder}:")
            for dep in missing:
                print(f"   - {dep}")
            if builder == "pyoxidizer" and "pyoxidizer" in missing:
                print("\n[INFO] PyOxidizer must be installed with: pip install pyoxidizer")
            elif builder == "pyinstaller" and "pyinstaller" in missing:
                print("\n[INFO] PyInstaller must be installed with: pip install pyinstaller")
            else:
                print(f"\nInstall with: pip install {' '.join(missing)}")
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
                    print("[ERROR] Generated executable not found.")
            else:
                print(f"[ERROR] PyInstaller failed (code {result.returncode}):")
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
    # Builder: PyOxidizer (entorno limpio con main.py en src/ y recursos en disco)
    # --------------------------------------------------------------------------
    def build_with_pyoxidizer(self, target_platform):
        print(f"[PyOxidizer] Compilando para {target_platform}...")
        
        # Directorio temporal para código Python limpio
        temp_dir = self.project_dir / "pyoxidizer_temp"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir()
        
        # Directorios a ignorar
        ignore_dirs = {'build', 'dist', 'build_output', '__pycache__', '.git', 'pyoxidizer_temp'}
        # Paquetes a incluir (sin src porque lo manejamos aparte)
        packages = ["core", "gui", "modules", "utils"]
        
        print("[PyOxidizer] Copiando archivos .py al entorno limpio...")
        py_count = 0
        
        for root, dirs, files in os.walk(self.project_dir):
            # Evitar entrar en directorios ignorados
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            rel_path = Path(root).relative_to(self.project_dir)
            # Determinar destino: si el archivo es main.py, irá a src/
            for file in files:
                if file.endswith('.py'):
                    src = Path(root) / file
                    # Para main.py, irá a src/main.py
                    if file == "main.py" and rel_path == Path("."):
                        dst_dir = temp_dir / "src"
                    else:
                        dst_dir = temp_dir / rel_path
                    dst_dir.mkdir(parents=True, exist_ok=True)
                    dst = dst_dir / file
                    shutil.copy2(src, dst)
                    py_count += 1
        
        # Copiar requirements.txt
        req_src = self.project_dir / "requirements.txt"
        if req_src.exists():
            shutil.copy2(req_src, temp_dir / "requirements.txt")
            print("[PyOxidizer] Copiado requirements.txt.")
        else:
            print("[PyOxidizer] Advertencia: No se encontró requirements.txt.")
        
        # Crear __init__.py en los paquetes necesarios
        for pkg_dir in ["src"] + packages:
            pkg_path = temp_dir / pkg_dir
            if pkg_path.exists():
                init_file = pkg_path / "__init__.py"
                if not init_file.exists():
                    init_file.touch()
                    print(f"[PyOxidizer] Creado {init_file}")
        
        print(f"[PyOxidizer] Copiados {py_count} archivos .py.")
        
        try:
            # Generar pyoxidizer.bzl dentro del temporal
            self._create_pyoxidizer_config_temp(temp_dir, packages, target_platform)
            
            # Ejecutar pyoxidizer
            cmd = ["pyoxidizer", "build", "--release"]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir)
            
            if result.returncode == 0:
                # Buscar el ejecutable generado
                build_subdir = temp_dir / "build"
                if build_subdir.exists():
                    for root, dirs, files in os.walk(build_subdir):
                        for file in files:
                            if file == f"soundvi{self.configs[target_platform]['ext']}":
                                src_exe = Path(root) / file
                                dst_exe = self.dist_dir / file
                                shutil.copy2(src_exe, dst_exe)
                                size_mb = dst_exe.stat().st_size / (1024 * 1024)
                                print(f"[OK] Build exitoso: {dst_exe}")
                                print(f"[Size] {size_mb:.2f} MB")
                                return True
                print("[ERROR] PyOxidizer generated executable not found.")
            else:
                print(f"[ERROR] PyOxidizer failed (code {result.returncode}):")
                print("--- STDOUT ---")
                print(result.stdout)
                print("--- STDERR ---")
                print(result.stderr)
            return False
        finally:
            # Limpiar temporal
            shutil.rmtree(temp_dir)
            print("[PyOxidizer] Limpiado directorio temporal.")
    
    def _create_pyoxidizer_config_temp(self, temp_dir, packages, target_platform):
        """Genera pyoxidizer.bzl dentro del directorio temporal."""
        # Lista de paquetes para read_package_root
        pkg_list = ", ".join(f'"{pkg}"' for pkg in ["src"] + packages)
        config = f'''# pyoxidizer.bzl for Soundvi - main.py en src/, recursos en disco
def make_exe():
    dist = default_python_distribution()
    policy = dist.make_python_packaging_policy()
    policy.extension_module_filter = "all"
    policy.allow_in_memory_shared_library_loading = True
    # Cambiamos a filesystem para que __file__ funcione
    policy.resources_location = "filesystem-relative:prefix"
    policy.resources_location_fallback = "filesystem-relative:prefix"

    python_config = dist.make_python_interpreter_config()
    python_config.run_module = "src.main"   # main.py está en src/

    exe = dist.to_python_executable(
        name="soundvi",
        packaging_policy=policy,
        config=python_config,
    )

    # Instalar dependencias
    exe.add_python_resources(exe.pip_install(["-r", "requirements.txt"]))

    # Incluir los paquetes (src, core, gui, modules, utils)
    exe.add_python_resources(exe.read_package_root(
        path=".",
        packages=[{pkg_list}],
    ))

    # Configuración específica de plataforma
    target_triple = VARS.get("target_triple", "")
    if "windows" in target_triple:
        exe.windows_subsystem = "windows"
        exe.windows_runtime_dlls_mode = "when-present"

    return exe

def make_install(exe):
    files = FileManifest()
    files.add_python_resource(".", exe)
    return files

register_target("exe", make_exe)
register_target("install", make_install, depends=["exe"], default=True)
resolve_targets()
'''
        with open(temp_dir / "pyoxidizer.bzl", "w", encoding="utf-8") as f:
            f.write(config)
        print("[PyOxidizer] Archivo pyoxidizer.bzl generado en entorno temporal.")
    
    # --------------------------------------------------------------------------
    # Helper para encontrar el ejecutable (solo para PyInstaller)
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
        # Para PyOxidizer ya copiamos el ejecutable directamente
        return None
    
    # --------------------------------------------------------------------------
    # Empaquetado portable
    # --------------------------------------------------------------------------
    def package_portable(self, target_platform, builder):
        print(f"[Portable] Creando paquete portable para {target_platform}...")
        executable = self._find_executable(target_platform, builder)
        if not executable:
            # Para PyOxidizer, el ejecutable ya está en dist
            ext = self.configs[target_platform]["ext"]
            name = f"soundvi{ext}"
            executable = self.dist_dir / name
            if not executable.exists():
                print(f"[ERROR] Ejecutable no encontrado en {executable}.")
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
    # Main build
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
                       default="pyinstaller", help="Build tool")
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