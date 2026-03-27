#!/usr/bin/env python3
"""
Test mínimo para verificar que el runtime hook no causa segmentation fault.
"""

import sys
import os

# Simular que estamos en un ejecutable PyInstaller
sys.frozen = True
sys._MEIPASS = os.path.dirname(os.path.abspath(__file__))

# Importar el runtime hook simple
import runtime_hook_simple

print("[✓] Test exitoso: runtime_hook_simple.py no causa segmentation fault")
print(f"   PYTHONIOENCODING: {os.environ.get('PYTHONIOENCODING')}")
print(f"   LANG: {os.environ.get('LANG')}")
print(f"   LC_ALL: {os.environ.get('LC_ALL')}")