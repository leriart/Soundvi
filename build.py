#!/usr/bin/env python3
"""
Build Script para Soundvi - Crea ejecutables para Windows/Linux/macOS
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
        
        # Configuraciones por plataforma
        self.configs = {
            "windows": {
                "ext": ".exe",
                "builder": "nuitka",  # o "pyinstaller"
                "icon": self.project_dir / "logos" / "Cagando.ico",
                "requirements": ["nuitka", "ordered-set", "zstandard"],
            },
            "linux": {
                "ext": ".AppImage",
                "builder": "nuitka",
                "icon": self.project_dir / "logos" / "Cagando.png",
                "requirements": ["nuitka", "ordered-set", "appimagetool"],
            },
            "macos": {
                "ext": ".app",
                "builder": "pyinstaller",  # Nuitka tiene issues en macOS
                "icon": self.project_dir / "logos" / "Cagando.icns",
                "requirements": ["pyinstaller"],
            }
        }
    
    def check_dependencies(self, target_platform):
        """Verificar dependencias necesarias."""
        config = self.configs[target_platform]
        missing = []
        
        for req in config["requirements"]:
            if req == "appimagetool":
                # Verificar si appimagetool está disponible
                result = subprocess.run(["which", "appimagetool"], 
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    missing.append("appimagetool (descargar de GitHub)")
            else:
                # Verificar paquete Python
                try:
                    __import__(req.replace("-", "_"))
                except ImportError:
                    missing.append(req)
        
        if missing:
            print(f"❌ Dependencias faltantes para {target_platform}:")
            for dep in missing:
                print(f"   - {dep}")
            print(f"\nInstalar con: pip install {' '.join(missing)}")
            return False
        
        return True
    
    def clean_build_dirs(self):
        """Limpiar directorios de build anteriores."""
        for dir_path in [self.build_dir, self.dist_dir]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"🧹 Limpiado: {dir_path}")
        
        self.build_dir.mkdir(exist_ok=True)
        self.dist_dir.mkdir(exist_ok=True)
    
    def build_with_nuitka(self, target_platform):
        """Build usando Nuitka (recomendado)."""
        print(f"🚀 Compilando con Nuitka para {target_platform}...")
        
        main_script = self.project_dir / "main.py"
        output_name = f"soundvi{self.configs[target_platform]['ext']}"
        output_path = self.dist_dir / output_name
        
        # Comando base Nuitka
        cmd = [
            sys.executable, "-m", "nuitka",
            "--standalone",
            "--onefile",
            "--remove-output",
            "--enable-plugin=tk-inter",
            "--output-dir", str(self.build_dir),
            "--output-filename", output_name,
        ]
        
        # Plataforma específica
        if target_platform == "windows":
            cmd.extend(["--windows-console-mode=disable"])
            if self.configs["windows"]["icon"].exists():
                cmd.extend(["--windows-icon-from-ico", str(self.configs["windows"]["icon"])])
        elif target_platform == "linux":
            cmd.extend(["--linux-icon", str(self.configs["linux"]["icon"])])
        
        # Incluir datos
        data_dirs = ["fonts", "logos", "core", "gui", "modules", "utils"]
        for data_dir in data_dirs:
            src = self.project_dir / data_dir
            if src.exists():
                cmd.extend(["--include-data-dir", f"{src}={data_dir}"])
        
        # Archivos individuales
        config_file = self.project_dir / "config.json"
        if config_file.exists():
            cmd.extend(["--include-data-file", f"{config_file}=config.json"])
        
        # Script principal
        cmd.append(str(main_script))
        
        print(f"📦 Comando: {' '.join(cmd[:10])}...")
        
        # Ejecutar
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_dir)
            if result.returncode == 0:
                # Mover a dist
                built_file = self.build_dir / output_name
                if built_file.exists():
                    shutil.move(built_file, output_path)
                    size_mb = output_path.stat().st_size / (1024 * 1024)
                    print(f"✅ Build exitoso: {output_path}")
                    print(f"📊 Tamaño: {size_mb:.2f} MB")
                    return True
                else:
                    print(f"❌ Archivo no creado: {built_file}")
            else:
                print(f"❌ Error en Nuitka:")
                print(result.stderr[:500])
        except Exception as e:
            print(f"❌ Error ejecutando Nuitka: {e}")
        
        return False
    
    def build_with_pyinstaller(self, target_platform):
        """Build usando PyInstaller (alternativa)."""
        print(f"🚀 Compilando con PyInstaller para {target_platform}...")
        
        # Crear spec file dinámico
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
                # PyInstaller crea en dist/soundvi/ o dist/soundvi.exe
                if target_platform == "windows":
                    output_path = self.dist_dir / "soundvi.exe"
                else:
                    output_path = self.dist_dir / "soundvi"
                
                if output_path.exists():
                    size_mb = output_path.stat().st_size / (1024 * 1024)
                    print(f"✅ Build exitoso: {output_path}")
                    print(f"📊 Tamaño: {size_mb:.2f} MB")
                    return True
            else:
                print(f"❌ Error en PyInstaller:")
                print(result.stderr[:500])
        except Exception as e:
            print(f"❌ Error ejecutando PyInstaller: {e}")
        
        return False
    
    def _create_pyinstaller_spec(self, target_platform):
        """Crear archivo .spec para PyInstaller."""
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
        'tkinter', 'ttk', '_tkinter',
        'PIL._imaging', 'PIL._imagingtk', 'PIL._tkinter_finder',
        'numpy.core._dtype_ctypes', 'numpy.lib.format',
        'scipy.interpolate', 'scipy.signal', 'scipy.fft',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
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
    strip=False,
    upx=True,
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

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='soundvi',
)
'''
    
    def create_appimage(self):
        """Crear AppImage para Linux."""
        print("📦 Creando AppImage...")
        
        # Requiere appimagetool
        appimagetool = shutil.which("appimagetool")
        if not appimagetool:
            # Descargar si no existe
            appimagetool = "/tmp/appimagetool-x86_64.AppImage"
            if not Path(appimagetool).exists():
                print("📥 Descargando appimagetool...")
                subprocess.run([
                    "wget", "-q", 
                    "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage",
                    "-O", appimagetool
                ], check=True)
                os.chmod(appimagetool, 0o755)
        
        # Crear estructura AppDir
        appdir = self.build_dir / "Soundvi.AppDir"
        if appdir.exists():
            shutil.rmtree(appdir)
        
        # Copiar ejecutable y recursos
        # (Esto es simplificado - en realidad necesitarías una estructura completa)
        
        print("⚠️  Creación de AppImage requiere estructura completa")
        print("   Usa Nuitka --onefile para Linux en su lugar")
        return False
    
    def package_portable(self, target_platform):
        """Crear paquete portable."""
        print(f"📦 Creando paquete portable para {target_platform}...")
        
        executable = self.dist_dir / f"soundvi{self.configs[target_platform]['ext']}"
        if not executable.exists():
            print(f"❌ Ejecutable no encontrado: {executable}")
            return False
        
        # Crear directorio portable
        portable_dir = self.dist_dir / f"Soundvi-Portable-{target_platform.capitalize()}"
        if portable_dir.exists():
            shutil.rmtree(portable_dir)
        
        portable_dir.mkdir()
        
        # Copiar ejecutable
        shutil.copy(executable, portable_dir / executable.name)
        
        # Copiar recursos
        for data_dir in ["fonts", "logos", "core", "gui", "modules", "utils"]:
            src = self.project_dir / data_dir
            if src.exists():
                shutil.copytree(src, portable_dir / data_dir)
        
        # Copiar archivos individuales
        for data_file in ["config.json", "README.md"]:
            src = self.project_dir / data_file
            if src.exists():
                shutil.copy(src, portable_dir / data_file)
        
        # Crear script de lanzamiento
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
        
        # Comprimir
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
        print(f"✅ Paquete portable creado: {size_mb:.2f} MB")
        
        return True
    
    def build(self, target_platform, create_portable=False):
        """Ejecutar build completo."""
        print(f"\n{'='*60}")
        print(f"🏗️  BUILD SOUNDVI - {target_platform.upper()}")
        print(f"{'='*60}")
        
        # 1. Verificar dependencias
        if not self.check_dependencies(target_platform):
            return False
        
        # 2. Limpiar
        self.clean_build_dirs()
        
        # 3. Build según plataforma
        config = self.configs[target_platform]
        success = False
        
        if config["builder"] == "nuitka":
            success = self.build_with_nuitka(target_platform)
        elif config["builder"] == "pyinstaller":
            success = self.build_with_pyinstaller(target_platform)
        
        # 4. Crear AppImage si es Linux
        if success and target_platform == "linux" and config["ext"] == ".AppImage":
            success = self.create_appimage()
        
        # 5. Crear paquete portable si se solicita
        if success and create_portable:
            self.package_portable(target_platform)
        
        return success

def main():
    parser = argparse.ArgumentParser(description="Build Soundvi para múltiples plataformas")
    parser.add_argument("--platform", choices=["windows", "linux", "macos", "all"], 
                       default=platform.system().lower(), help="Plataforma objetivo")
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
        success = builder.build(platform_name, args.portable)
        if not success:
            all_success = False
            print(f"❌ Build falló para {platform_name}")
    
    if all_success:
        print(f"\n{'🎉'*20}")
        print("¡BUILDS COMPLETADOS EXITOSAMENTE!")
        print(f"{'🎉'*20}")
        print(f"\n📁 Output en: {builder.dist_dir}")
        print("📦 Archivos creados:")
        for item in builder.dist_dir.iterdir():
            if item.is_file():
                size_mb = item.stat().st_size / (1024 * 1024)
                print(f"   • {item.name} ({size_mb:.1f} MB)")
    
    return 0 if all_success else 1

if __name__ == "__main__":
    sys.exit(main())