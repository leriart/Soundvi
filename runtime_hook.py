#!/usr/bin/env python3
"""
Runtime hook para PyInstaller - Configuración Unicode/Encoding

Este archivo se ejecuta al inicio del ejecutable generado por PyInstaller
para configurar correctamente el encoding y soporte Unicode.
"""

import sys
import os
import locale

def setup_unicode():
    """Configura el sistema para soporte Unicode correcto."""
    
    # 1. Forzar encoding UTF-8 para stdin/stdout/stderr
    if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding is None:
        sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
    
    if hasattr(sys.stderr, 'encoding') and sys.stderr.encoding is None:
        sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)
    
    if hasattr(sys.stdin, 'encoding') and sys.stdin.encoding is None:
        sys.stdin = open(sys.stdin.fileno(), mode='r', encoding='utf-8', buffering=1)
    
    # 2. Configurar locale para UTF-8
    try:
        # Intentar configurar locale a UTF-8
        locale.setlocale(locale.LC_ALL, '')
        
        # Si el locale no es UTF-8, forzarlo
        current_locale = locale.getlocale()
        if current_locale[1] is None or 'UTF-8' not in current_locale[1].upper():
            # Intentar diferentes locales UTF-8
            for loc in ['C.UTF-8', 'en_US.UTF-8', 'es_MX.UTF-8', 'es_ES.UTF-8']:
                try:
                    locale.setlocale(locale.LC_ALL, loc)
                    break
                except locale.Error:
                    continue
    except locale.Error as e:
        # Si falla locale, al menos configurar encoding
        pass
    
    # 3. Configurar variables de entorno para UTF-8
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    os.environ.setdefault('PYTHONUTF8', '1')
    
    if 'LANG' not in os.environ:
        os.environ['LANG'] = 'C.UTF-8'
    if 'LC_ALL' not in os.environ:
        os.environ['LC_ALL'] = 'C.UTF-8'
    
    # 4. Configurar sys para UTF-8
    if hasattr(sys, 'setdefaultencoding'):
        sys.setdefaultencoding('utf-8')
    
    # 5. Log de configuración (solo en modo debug)
    if os.environ.get('SOUNDVI_DEBUG'):
        print(f"[RUNTIME HOOK] Unicode configurado")
        print(f"  stdout encoding: {sys.stdout.encoding}")
        print(f"  stderr encoding: {sys.stderr.encoding}")
        print(f"  filesystem encoding: {sys.getfilesystemencoding()}")
        print(f"  LANG: {os.environ.get('LANG')}")
        print(f"  LC_ALL: {os.environ.get('LC_ALL')}")

def setup_fonts():
    """Configura rutas de fuentes para el ejecutable."""
    
    # PyInstaller almacena datos en sys._MEIPASS
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        meipass = sys._MEIPASS
        
        # Añadir directorio de fuentes al PATH si existe
        fonts_dir = os.path.join(meipass, 'fonts')
        if os.path.isdir(fonts_dir):
            # Esto ayuda a bibliotecas como PIL/Pillow a encontrar fuentes
            os.environ.setdefault('FONTCONFIG_PATH', fonts_dir)
            
            # Para Qt, necesitamos configurar QFontDatabase
            try:
                from PyQt6.QtGui import QFontDatabase
                db = QFontDatabase()
                for font_file in os.listdir(fonts_dir):
                    if font_file.lower().endswith(('.ttf', '.otf')):
                        font_path = os.path.join(fonts_dir, font_file)
                        db.addApplicationFont(font_path)
            except ImportError:
                pass  # Qt no está disponible

# Ejecutar configuración al importar
setup_unicode()
setup_fonts()

# Nota: Este archivo debe ser simple y no depender de otros módulos
# ya que se ejecuta muy temprano en el proceso de inicio.