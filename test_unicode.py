#!/usr/bin/env python3
"""
Script para diagnosticar problemas de Unicode en el ejecutable.
"""

import sys
import locale
import os

def check_unicode_support():
    """Verifica soporte Unicode del sistema."""
    print("=== Diagnóstico Unicode ===")
    
    # 1. Configuración del sistema
    print("\n1. Configuración del sistema:")
    print(f"   Python version: {sys.version}")
    print(f"   Platform: {sys.platform}")
    print(f"   Filesystem encoding: {sys.getfilesystemencoding()}")
    print(f"   Default encoding: {sys.getdefaultencoding()}")
    print(f"   Stdout encoding: {sys.stdout.encoding}")
    
    # 2. Locale
    print("\n2. Configuración locale:")
    try:
        print(f"   LC_ALL: {os.environ.get('LC_ALL', 'No establecido')}")
        print(f"   LANG: {os.environ.get('LANG', 'No establecido')}")
        print(f"   LC_CTYPE: {os.environ.get('LC_CTYPE', 'No establecido')}")
        
        # Obtener locale actual
        current_locale = locale.getlocale()
        print(f"   Locale actual: {current_locale}")
        
        # Verificar si es UTF-8
        for var in ['LC_ALL', 'LANG', 'LC_CTYPE']:
            value = os.environ.get(var, '')
            if 'UTF-8' in value.upper() or 'UTF8' in value.upper():
                print(f"   ✅ {var} contiene UTF-8: {value}")
            elif value:
                print(f"   ⚠️  {var} NO contiene UTF-8: {value}")
    except Exception as e:
        print(f"   ❌ Error obteniendo locale: {e}")
    
    # 3. Probar caracteres Unicode
    print("\n3. Prueba de caracteres Unicode:")
    test_chars = [
        ("Emojis", "🎉 🦀 🚀 ✅ ❌ ⚠️"),
        ("Acentos español", "á é í ó ú ñ Á É Í Ó Ú Ñ"),
        ("Símbolos", "• → ← ↑ ↓ © ® ™"),
        ("Caracteres especiales", "α β γ δ ε π σ μ ∞ ≠ ≈"),
    ]
    
    for name, chars in test_chars:
        try:
            print(f"   {name}: {chars}")
        except UnicodeEncodeError as e:
            print(f"   ❌ {name}: ERROR de encoding - {e}")
    
    # 4. Probar escritura a stdout
    print("\n4. Prueba de escritura stdout:")
    test_strings = [
        "Hola mundo con acentos: café, niño, acción",
        "Emojis: 🎵 🎨 🎭 🎬",
        "Símbolos matemáticos: ∑ ∫ √ ∞",
    ]
    
    for test in test_strings:
        try:
            sys.stdout.write(f"   {test}\n")
            sys.stdout.flush()
        except Exception as e:
            print(f"   ❌ Error escribiendo: {test[:30]}... - {e}")
    
    # 5. Verificar variables de entorno importantes
    print("\n5. Variables de entorno importantes:")
    env_vars = ['TERM', 'COLORTERM', 'WT_SESSION', 'WT_PROFILE_ID']
    for var in env_vars:
        value = os.environ.get(var, 'No establecido')
        print(f"   {var}: {value}")
    
    # 6. Recomendaciones
    print("\n6. Recomendaciones:")
    if 'UTF-8' not in os.environ.get('LANG', '').upper():
        print("   ⚠️  Configurar LANG con UTF-8:")
        print("     export LANG=es_MX.UTF-8")
        print("     export LC_ALL=es_MX.UTF-8")
    
    if not sys.stdout.encoding or sys.stdout.encoding.upper() != 'UTF-8':
        print("   ⚠️  Stdout no está en UTF-8")
        print("     Revisar configuración de terminal")
    
    print("\n=== Fin del diagnóstico ===")

def check_pyinstaller_unicode():
    """Verifica problemas específicos de PyInstaller con Unicode."""
    print("\n=== Diagnóstico PyInstaller Unicode ===")
    
    # PyInstaller puede tener problemas con:
    # 1. Archivos .spec con encoding incorrecto
    # 2. Hook files que no manejan Unicode
    # 3. Recursos embebidos con encoding incorrecto
    
    # Verificar si estamos en un ejecutable PyInstaller
    if getattr(sys, 'frozen', False):
        print("✅ Ejecutando desde PyInstaller bundle")
        print(f"   _MEIPASS: {getattr(sys, '_MEIPASS', 'No disponible')}")
    else:
        print("⚠️  No ejecutando desde PyInstaller bundle")
    
    # Probar importación de módulos que usan Unicode
    modules_to_test = ['json', 'csv', 'xml.etree.ElementTree']
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"✅ Módulo {module_name} importado correctamente")
        except Exception as e:
            print(f"❌ Error importando {module_name}: {e}")

if __name__ == "__main__":
    print("🔧 Diagnóstico de problemas Unicode/Encoding\n")
    check_unicode_support()
    check_pyinstaller_unicode()
    
    # Prueba final
    print("\n🎯 Prueba final - Caracteres problemáticos comunes:")
    problem_chars = "áéíóúñÁÉÍÓÚÑ©®™🎵🎨→←"
    print(f"   Cadena de prueba: {problem_chars}")
    print(f"   Longitud: {len(problem_chars)} caracteres")
    print(f"   Bytes (UTF-8): {problem_chars.encode('utf-8')}")
    
    # Sugerencia para terminal
    print("\n💡 Si ves números/letras en vez de caracteres:")
    print("   1. Verifica que tu terminal soporte UTF-8")
    print("   2. Prueba con: echo -e '\\xf0\\x9f\\x8e\\x89' (debería mostrar 🎉)")
    print("   3. Configura: export LC_ALL=en_US.UTF-8")
    print("   4. O usa: export PYTHONIOENCODING=utf-8")