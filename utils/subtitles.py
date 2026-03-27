#!/usr/bin/env python3
"""
Parseo de subtitulos SRT.
"""

from __future__ import annotations
from datetime import timedelta

def format_time(seconds: float) -> str:
    """Formatea segundos a tiempo SRT (HH:MM:SS,mmm)"""
    if seconds < 0:
        seconds = 0
    td = timedelta(seconds=seconds)
    total_seconds = td.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds_val = total_seconds % 60
    milliseconds = int((seconds_val - int(seconds_val)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(seconds_val):02d},{milliseconds:03d}"


def _srt_a_segundos(tiempo_srt: str) -> float:
    """Convierte ``HH:MM:SS,mmm`` a segundos."""
    partes = tiempo_srt.replace(",", ".").strip().split(":")
    if len(partes) == 3:
        h, m, s = partes
        return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0


def parse_srt(path: str) -> list[dict]:
    """
    Parsea un archivo SRT y devuelve una lista de entradas de subtitulos.
    Cada entrada es un dict con claves ``start``, ``end`` (float) y ``text``.
    """
    subtitulos: list[dict] = []
    try:
        import re
        with open(path, "r", encoding="utf-8-sig") as fh: # UTF-8-SIG para quitar BOM
            contenido = fh.read()
    except Exception as exc:
        print(f"[subtitulos] Error al leer archivo: {exc}")
        return subtitulos

    # Regex para parsear SRT de forma más robusta
    pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:.+\n?)+)')
    matches = pattern.findall(contenido + "\n")
    
    for m in matches:
        inicio = _srt_a_segundos(m[1])
        fin = _srt_a_segundos(m[2])
        texto = m[3].strip().replace("\n", " ")
        subtitulos.append({"start": inicio, "end": fin, "text": texto})

    return subtitulos


def split_text_lines(text: str, max_chars: int) -> list[str]:
    """Divide texto en lineas respetando limites de palabras."""
    if max_chars <= 0:
        return [text]

    palabras = text.split()
    if not palabras:
        return [""]

    total_texto = " ".join(palabras)
    if len(total_texto) <= max_chars:
        return [total_texto]

    # Alineado inteligente: buscar el punto medio por palabras
    # para repartir la carga entre las dos lineas de forma equilibrada.
    punto_medio = len(total_texto) // 2
    
    # Encontrar el espacio más cercano al punto medio
    espacios = [i for i, char in enumerate(total_texto) if char == ' ']
    if not espacios:
        return [total_texto]
        
    mejor_corte = min(espacios, key=lambda x: abs(x - punto_medio))
    
    linea1 = total_texto[:mejor_corte].strip()
    linea2 = total_texto[mejor_corte:].strip()
    
    return [linea1, linea2]
