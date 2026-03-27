#!/usr/bin/env python3
"""
Script para reemplazar TODOS los emojis gráficos por símbolos Unicode de texto.
Analiza todo el proyecto y reemplaza automáticamente.
"""

import os
import re
import sys

# Mapeo de emojis gráficos a símbolos Unicode de texto
EMOJI_REPLACEMENTS = {
    # Emojis gráficos comunes encontrados
    "[•]": "[•]",  # Mantener como está (es aceptable)
    "[▶]": "[▶]",  # Mantener como está
    "[✎]": "[✎]",  # Mantener como está
    "[*]": "[*]",  # Mantener como está
    "[*]": "[*]",  # Mantener como está
    "[*]": "[*]",  # Mantener como está
    "[★]": "[★]",  # Mantener como está
    "[▶]": "[▶]",  # Mantener como está
    "[✓]": "[✓]",  # Mantener como está
    "[*]": "[*]",  # Mantener como está
    "": "",  # Mantener como está
    "[♫]": "[♫]",  # Mantener como está
    "⚠": "⚠",    # Mantener como está (ya es símbolo de advertencia)
    "[*]": "[*]",  # Mantener como está
    "[✗]": "[✗]",  # Mantener como está
    
    # Símbolos que YA convertimos (mantener)
    "➡": "➡",    # Rightwards arrow (U+27A1)
    "✓": "✓",    # Check mark (U+2713)
    "▶": "▶",    # Play/triangle right (U+25B6)
    "✦": "✦",    # Black four pointed star (U+2726)
    "○": "○",    # White circle (U+25CB)
    "●": "●",    # Black circle (U+25CF)
    "ℹ": "ℹ",    # Information source (U+2139)
    "✎": "✎",    # Lower right pencil (U+270E)
    
    # Símbolos de texto seguros (mantener)
    "☐": "☐",    # Ballot box (U+2610)
    "☑": "☑",    # Ballot box with check (U+2611)
    "☒": "☒",    # Ballot box with X (U+2612)
    "★": "★",    # Black star (U+2605)
    "☆": "☆",    # White star (U+2606)
    "⚫": "⚫",   # Black circle (U+26AB)
    "⚪": "⚪",   # White circle (U+26AA)
    "⬤": "⬤",   # Black large circle (U+2B24)
    "○": "○",    # White circle (U+25CB)
    "●": "●",    # Black circle (U+25CF)
    "◯": "◯",    # Large circle (U+25EF)
    "⬢": "⬢",   # Black hexagon (U+2B22)
    "⬡": "⬡",   # White hexagon (U+2B21)
    "■": "■",    # Black square (U+25A0)
    "□": "□",    # White square (U+25A1)
    "▢": "▢",    # White square with rounded corners (U+25A2)
    "▣": "▣",    # White square containing black small square (U+25A3)
    "▤": "▤",    # Square with horizontal fill (U+25A4)
    "▥": "▥",    # Square with vertical fill (U+25A5)
    "▦": "▦",    # Square with orthogonal crosshatch fill (U+25A6)
    "▧": "▧",    # Square with upper left to lower right fill (U+25A7)
    "▨": "▨",    # Square with upper right to lower left fill (U+25A8)
    "▩": "▩",    # Square with diagonal crosshatch fill (U+25A9)
    "▪": "▪",    # Black small square (U+25AA)
    "▫": "▫",    # White small square (U+25AB)
    "▶": "▶",    # Black right-pointing triangle (U+25B6)
    "▷": "▷",    # White right-pointing triangle (U+25B7)
    "◀": "◀",    # Black left-pointing triangle (U+25C0)
    "◁": "◁",    # White left-pointing triangle (U+25C1)
    "▼": "▼",    # Black down-pointing triangle (U+25BC)
    "▽": "▽",    # White down-pointing triangle (U+25BD)
    "▲": "▲",    # Black up-pointing triangle (U+25B2)
    "△": "△",    # White up-pointing triangle (U+25B3)
    "◆": "◆",    # Black diamond (U+25C6)
    "◇": "◇",    # White diamond (U+25C7)
    "◈": "◈",    # White diamond containing black small diamond (U+25C8)
    "○": "○",    # White circle (U+25CB)
    "●": "●",    # Black circle (U+25CF)
    "◐": "◐",    # Circle with left half black (U+25D0)
    "◑": "◑",    # Circle with right half black (U+25D1)
    "◒": "◒",    # Circle with lower half black (U+25D2)
    "◓": "◓",    # Circle with upper half black (U+25D3)
    "◔": "◔",    # Circle with upper right quadrant black (U+25D4)
    "◕": "◕",    # Circle with all but upper left quadrant black (U+25D5)
    "◖": "◖",    # Left half black circle (U+25D6)
    "◗": "◗",    # Right half black circle (U+25D7)
    "◘": "◘",    # Inverse bullet (U+25D8)
    "◙": "◙",    # Inverse white circle (U+25D9)
    "◚": "◚",    # Upper half inverse white circle (U+25DA)
    "◛": "◛",    # Lower half inverse white circle (U+25DB)
    "◜": "◜",    # Upper left quadrant circular arc (U+25DC)
    "◝": "◝",    # Upper right quadrant circular arc (U+25DD)
    "◞": "◞",    # Lower right quadrant circular arc (U+25DE)
    "◟": "◟",    # Lower left quadrant circular arc (U+25DF)
    "◠": "◠",    # Upper half circle (U+25E0)
    "◡": "◡",    # Lower half circle (U+25E1)
    "◢": "◢",    # Black lower right triangle (U+25E2)
    "◣": "◣",    # Black lower left triangle (U+25E3)
    "◤": "◤",    # Black upper left triangle (U+25E4)
    "◥": "◥",    # Black upper right triangle (U+25E5)
    "◦": "◦",    # White bullet (U+25E6)
    "◧": "◧",    # Square with left half black (U+25E7)
    "◨": "◨",    # Square with right half black (U+25E8)
    "◩": "◩",    # Square with upper left diagonal half black (U+25E9)
    "◪": "◪",    # Square with lower right diagonal half black (U+25EA)
    "◫": "◫",    # Square with upper right diagonal half black (U+25EB)
    "◬": "◬",    # Square with lower left diagonal half black (U+25EC)
    "◭": "◭",    # Diamond with left half black (U+25ED)
    "◮": "◮",    # Diamond with right half black (U+25EE)
    "◯": "◯",    # Large circle (U+25EF)
    "◰": "◰",    # White square with upper left quadrant (U+25F0)
    "◱": "◱",    # White square with lower left quadrant (U+25F1)
    "◲": "◲",    # White square with lower right quadrant (U+25F2)
    "◳": "◳",    # White square with upper right quadrant (U+25F3)
    "◴": "◴",    # White circle with upper left quadrant (U+25F4)
    "◵": "◵",    # White circle with lower left quadrant (U+25F5)
    "◶": "◶",    # White circle with lower right quadrant (U+25F6)
    "◷": "◷",    # White circle with upper right quadrant (U+25F7)
    "◸": "◸",    # Upper left triangle (U+25F8)
    "◹": "◹",    # Upper right triangle (U+25F9)
    "◺": "◺",    # Lower left triangle (U+25FA)
    "◻": "◻",    # White medium square (U+25FB)
    "◼": "◼",    # Black medium square (U+25FC)
    "◽": "◽",    # White medium small square (U+25FD)
    "◾": "◾",    # Black medium small square (U+25FE)
    "◿": "◿",    # Lower right triangle (U+25FF)
}

# Símbolos que son SEGUROS (no cambiar)
SAFE_SYMBOLS = {
    "➡", "✓", "▶", "✦", "○", "●", "ℹ", "✎", "☐", "☑", "☒",
    "★", "☆", "⚫", "⚪", "⬤", "◯", "⬢", "⬡", "■", "□", "▢",
    "▣", "▤", "▥", "▦", "▧", "▨", "▩", "▪", "▫", "▷", "◀",
    "◁", "▼", "▽", "▲", "△", "◆", "◇", "◈", "◐", "◑", "◒",
    "◓", "◔", "◕", "◖", "◗", "◘", "◙", "◚", "◛", "◜", "◝",
    "◞", "◟", "◠", "◡", "◢", "◣", "◤", "◥", "◦", "◧", "◨",
    "◩", "◪", "◫", "◬", "◭", "◮", "◰", "◱", "◲", "◳", "◴",
    "◵", "◶", "◷", "◸", "◹", "◺", "◻", "◼", "◽", "◾", "◿"
}

def analyze_file(filepath):
    """Analiza un archivo y encuentra todos los caracteres Unicode."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Encontrar todos los caracteres Unicode fuera del rango ASCII básico
        unicode_chars = set()
        for char in content:
            code = ord(char)
            if code > 127:  # Fuera de ASCII
                unicode_chars.add(char)
        
        return unicode_chars, content
    except Exception as e:
        return set(), ""

def replace_emojis_in_file(filepath):
    """Reemplaza emojis gráficos en un archivo."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        replacements = []
        
        # Reemplazar cada carácter
        for i, char in enumerate(content):
            if ord(char) > 127 and char not in SAFE_SYMBOLS:
                # Verificar si es un emoji gráfico (rango de emojis)
                code = ord(char)
                if (0x1F300 <= code <= 0x1F9FF) or (0x2600 <= code <= 0x27BF):
                    # Es un emoji gráfico, buscar reemplazo
                    if char in EMOJI_REPLACEMENTS:
                        new_char = EMOJI_REPLACEMENTS[char]
                        if new_char != char:
                            # Reemplazar en el contenido
                            content = content[:i] + new_char + content[i+1:]
                            replacements.append((char, new_char, i))
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, replacements
        return False, []
    
    except Exception as e:
        return False, []

def main():
    print("[*] ANALIZANDO TODO EL PROYECTO PARA EMOJIS GRÁFICOS")
    print("=" * 80)
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Excluir directorios
    exclude_dirs = {'__pycache__', '.git', 'venv', 'build', 'dist', 'test_venv', 'build_venv'}
    
    all_unicode_chars = set()
    files_with_unicode = []
    files_modified = []
    total_replacements = []
    
    # Analizar todos los archivos .py
    for root, dirs, files in os.walk(project_root):
        # Excluir directorios
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                unicode_chars, _ = analyze_file(filepath)
                
                if unicode_chars:
                    rel_path = os.path.relpath(filepath, project_root)
                    files_with_unicode.append(rel_path)
                    all_unicode_chars.update(unicode_chars)
    
    print(f"[*] Encontrados {len(all_unicode_chars)} caracteres Unicode diferentes:")
    for char in sorted(all_unicode_chars, key=lambda x: ord(x)):
        print(f"  U+{ord(char):04X}: '{char}'")
    
    print(f"\n {len(files_with_unicode)} archivos contienen caracteres Unicode")
    
    # Ahora reemplazar emojis gráficos
    print("\n REEMPLAZANDO EMOJIS GRÁFICOS")
    print("=" * 80)
    
    for rel_path in files_with_unicode:
        filepath = os.path.join(project_root, rel_path)
        modified, replacements = replace_emojis_in_file(filepath)
        
        if modified:
            files_modified.append(rel_path)
            total_replacements.extend([(rel_path, old, new, pos) for old, new, pos in replacements])
            print(f"  [✓] Modificado: {rel_path}")
            for old, new, pos in replacements:
                print(f"     {old} (U+{ord(old):04X}) → {new} (U+{ord(new):04X})")
    
    print(f"\n[*] RESUMEN:")
    print(f"  Archivos modificados: {len(files_modified)}")
    print(f"  Reemplazos totales: {len(total_replacements)}")
    
    if total_replacements:
        print("\n DETALLE DE REEMPLAZOS:")
        for filepath, old, new, pos in total_replacements:
            print(f"  {filepath}: {old} → {new}")
    
    # Crear reporte
    with open(os.path.join(project_root, "unicode_analysis_report.txt"), "w", encoding="utf-8") as f:
        f.write("ANÁLISIS DE UNICODE - SOUNDVI\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Caracteres Unicode encontrados: {len(all_unicode_chars)}\n")
        for char in sorted(all_unicode_chars, key=lambda x: ord(x)):
            f.write(f"U+{ord(char):04X}: '{char}'\n")
        
        f.write(f"\nArchivos modificados: {len(files_modified)}\n")
        for file in files_modified:
            f.write(f"- {file}\n")
        
        f.write(f"\nReemplazos realizados: {len(total_replacements)}\n")
