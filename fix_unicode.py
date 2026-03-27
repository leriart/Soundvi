#!/usr/bin/env python3
"""
Script para arreglar problemas de Unicode en el proyecto.
Reemplaza códigos hexadecimales por caracteres Unicode reales.
"""

import os
import re

def fix_file(filepath):
    """Arregla problemas de Unicode en un archivo."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Reemplazos comunes
    replacements = {
        '"2713 ': '"✓ ',  # check mark
        ' 2713"': ' ✓"',
        '"25B6"': '"▶"',  # play/triangle right
        '"2726"': '"✦"',  # black four pointed star
        '"25CB"': '"○"',  # white circle
        '"25CF"': '"●"',  # black circle
        '"2139"': '"ℹ"',  # information source
        '"270E"': '"✎"',  # lower right pencil
        '27A1': '➡',      # rightwards arrow
        '\\u27A1': '➡',
        '\\u25B6': '▶',
        '\\u2726': '✦',
        '\\u25CB': '○',
        '\\u25CF': '●',
        '\\u2139': 'ℹ',
        '\\u270E': '✎',
        '\\u2713': '✓',
    }
    
    original = content
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    print("🔧 Arreglando problemas de Unicode en el proyecto...")
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    fixed_files = []
    
    # Archivos a verificar
    files_to_check = [
        "gui/qt6/profile_selector.py",
        "gui/qt6/welcome_wizard.py",
        "gui/qt6/scripting_panel.py",
        "gui/qt6/about_dialog.py",
        "gui/qt6/sidebar_widget.py",
        "gui/qt6/base.py",
        "gui/qt6/transitions_panel.py",
        "gui/qt6/media_library_widget.py",
        "gui/qt6/toolbar_widget.py",
        "gui/qt6/export_dialog.py",
    ]
    
    for rel_path in files_to_check:
        filepath = os.path.join(project_root, rel_path)
        if os.path.exists(filepath):
            if fix_file(filepath):
                print(f"  ✅ Arreglado: {rel_path}")
                fixed_files.append(rel_path)
            else:
                print(f"  ✓ OK: {rel_path}")
        else:
            print(f"  ⚠ No encontrado: {rel_path}")
    
    print(f"\n📊 Resumen: {len(fixed_files)} archivos arreglados")
    if fixed_files:
        print("Archivos modificados:")
        for f in fixed_files:
            print(f"  - {f}")
    
    print("\n🎯 Problemas comunes arreglados:")
    print("  2713 → ✓ (check mark)")
    print("  25B6 → ▶ (play/triangle right)")
    print("  2726 → ✦ (black four pointed star)")
    print("  25CB → ○ (white circle)")
    print("  25CF → ● (black circle)")
    print("  2139 → ℹ (information source)")
    print("  270E → ✎ (lower right pencil)")
    print("  27A1 → ➡ (rightwards arrow)")

if __name__ == "__main__":
    main()