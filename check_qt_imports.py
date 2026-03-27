#!/usr/bin/env python3
"""
Script para verificar TODAS las importaciones de PyQt6 en el proyecto.
Busca problemas con QAction/QActionGroup en QtWidgets vs QtGui.
"""

import os
import re
import sys

def check_file(filepath):
    """Verifica un archivo Python en busca de imports problemáticos de Qt."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        lines = content.split('\n')
        problems = []
        
        for i, line in enumerate(lines, 1):
            # Buscar imports de QAction/QActionGroup desde QtWidgets
            if 'from PyQt6.QtWidgets import' in line and ('QAction' in line or 'QActionGroup' in line):
                problems.append(f"  Línea {i}: {line.strip()}")
            
            # Buscar imports individuales problemáticos
            if 'import' in line and 'PyQt6.QtWidgets' in line:
                # Verificar si después hay referencia a QAction/QActionGroup
                next_lines = lines[i:i+5] if i < len(lines) else []
                for j, next_line in enumerate(next_lines):
                    if 'QAction' in next_line or 'QActionGroup' in next_line:
                        problems.append(f"  Línea {i}+{j+1}: Posible problema en {line.strip()}")
        
        return problems
    
    except Exception as e:
        return [f"  ERROR al leer archivo: {e}"]

def main():
    print("[*] Verificando TODOS los imports de PyQt6 en el proyecto...")
    print("=" * 80)
    
    # Buscar todos los archivos .py
    project_root = os.path.dirname(os.path.abspath(__file__))
    python_files = []
    
    for root, dirs, files in os.walk(project_root):
        # Excluir directorios
        dirs[:] = [d for d in dirs if d not in ['__pycache__', 'test_venv', 'build_venv', '.git']]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    print(f"Encontrados {len(python_files)} archivos Python.")
    print()
    
    all_problems = []
    
    for filepath in python_files:
        rel_path = os.path.relpath(filepath, project_root)
        problems = check_file(filepath)
        
        if problems:
            print(f"⚠️  PROBLEMAS en {rel_path}:")
            for problem in problems:
                print(problem)
            print()
            all_problems.extend([(rel_path, p) for p in problems])
    
    if not all_problems:
        print("[✓] ¡No se encontraron problemas con imports de QAction/QActionGroup!")
        print("Todos los imports parecen correctos (QAction/QActionGroup en QtGui).")
    else:
        print(f"[✗] Se encontraron {len(all_problems)} problemas.")
        print("\nResumen de problemas:")
        for filepath, problem in all_problems:
            print(f"  {filepath}: {problem}")
    
    print("\n" + "=" * 80)
    print("Recomendaciones:")
    print("1. QAction y QActionGroup deben importarse desde PyQt6.QtGui")
    print("2. Ejemplo correcto: from PyQt6.QtGui import QAction, QActionGroup")
    print("3. Ejemplo incorrecto: from PyQt6.QtWidgets import ..., QAction, ...")
    
    return len(all_problems)

if __name__ == "__main__":
    sys.exit(main())