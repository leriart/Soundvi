#!/usr/bin/env python3
import os
import re

def find_emojis(directory):
    # Rango general de emojis (simplificado para buscar gráficos comunes)
    emoji_pattern = re.compile(r'[\U00010000-\U0010ffff\u2600-\u27BF]')
    
    # Excepciones que YA son símbolos de texto seguros (los que pusimos antes)
    safe_symbols = {'➡', '✓', '▶', '✦', '○', '●', 'ℹ', '✎', '☐', '☑'}
    
    found_emojis = set()
    file_matches = {}

    for root, dirs, files in os.walk(directory):
        if '__pycache__' in root or 'venv' in root or '.git' in root or 'build' in root or 'dist' in root:
            continue
            
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        
                    for i, line in enumerate(lines):
                        matches = emoji_pattern.findall(line)
                        for match in matches:
                            if match not in safe_symbols:
                                found_emojis.add(match)
                                if path not in file_matches:
                                    file_matches[path] = []
                                file_matches[path].append((i+1, match, line.strip()))
                except Exception as e:
                    pass
                    
    return found_emojis, file_matches

project_root = "/home/lerit/Documentos/Proyectos/Proyecto Soundvi/soundvi_project 4.8/Soundvi-main"
emojis, matches = find_emojis(project_root)

print(f"Encontrados {len(emojis)} emojis gráficos diferentes:\n")
for e in emojis:
    print(f"Emoji: {e} (U+{ord(e):04X})")

print("\nArchivos afectados:")
for path, lines in matches.items():
    rel_path = os.path.relpath(path, project_root)
    print(f"\n- {rel_path}:")
    for line_num, char, text in lines:
        print(f"  Línea {line_num}: {char} -> {text}")
