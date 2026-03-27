# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- Panel de Scripting Python para usuarios profesionales.

Permite ejecutar scripts Python para automatizar tareas en Soundvi.
Incluye:
  - Editor de código con resaltado basico
  - Consola de salida
  - Historial de comandos
  - Acceso a objetos internos (timeline, clips, módulos)
"""

from __future__ import annotations

import os
import sys
import io
import logging
import traceback
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTextEdit, QPlainTextEdit, QSplitter, QSizePolicy,
    QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QSyntaxHighlighter

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _RAIZ) if _RAIZ not in sys.path else None

log = logging.getLogger("soundvi.qt6.scripting")


# ---------------------------------------------------------------------------
#  Snippets predefinidos
# ---------------------------------------------------------------------------
SNIPPETS = {
    "-- Seleccionar snippet --": "",
    "Listar tracks": (
        "# Listar todos los tracks del timeline\n"
        "for i, track in enumerate(timeline.tracks):\n"
        "    print(f'Track {i}: {track.name} ({track.track_type})')\n"
    ),
    "Listar clips": (
        "# Listar todos los clips\n"
        "for track in timeline.tracks:\n"
        "    for clip in track.clips:\n"
        "        print(f'{track.name} > {clip.name}: {clip.start_time:.2f}s - {clip.duration:.2f}s')\n"
    ),
    "Silenciar todos los clips": (
        "# Silenciar volumen de todos los clips\n"
        "for track in timeline.tracks:\n"
        "    for clip in track.clips:\n"
        "        clip.volume = 0.0\n"
        "print('Todos los clips silenciados.')\n"
    ),
    "Restaurar volumen": (
        "# Restaurar volumen a 1.0\n"
        "for track in timeline.tracks:\n"
        "    for clip in track.clips:\n"
        "        clip.volume = 1.0\n"
        "print('Volumen restaurado a 1.0')\n"
    ),
    "Info del proyecto": (
        "# Información del proyecto\n"
        "print(f'Total tracks: {len(timeline.tracks)}')\n"
        "total_clips = sum(len(t.clips) for t in timeline.tracks)\n"
        "print(f'Total clips: {total_clips}')\n"
        "print(f'Duración: {timeline.duration:.2f}s')\n"
        "print(f'Playhead: {timeline.playhead:.2f}s')\n"
    ),
    "Ajustar opacidad": (
        "# Ajustar opacidad de todos los clips de video\n"
        "nueva_opacidad = 0.8\n"
        "for track in timeline.tracks:\n"
        "    if track.track_type == 'video':\n"
        "        for clip in track.clips:\n"
        "            clip.opacity = nueva_opacidad\n"
        "print(f'Opacidad ajustada a {nueva_opacidad}')\n"
    ),
}


# ---------------------------------------------------------------------------
#  Resaltado de sintaxis basico para Python
# ---------------------------------------------------------------------------
class PythonHighlighter(QSyntaxHighlighter):
    """Resaltado de sintaxis Python muy basico."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules = []

        # Keywords
        kw_format = QTextCharFormat()
        kw_format.setForeground(QColor("#F39C12"))
        kw_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            "and", "as", "assert", "break", "class", "continue", "def",
            "del", "elif", "else", "except", "finally", "for", "from",
            "global", "if", "import", "in", "is", "lambda", "not",
            "or", "pass", "raise", "return", "try", "while", "with",
            "yield", "True", "False", "None",
        ]
        import re
        for kw in keywords:
            pattern = re.compile(rf"\b{kw}\b")
            self._rules.append((pattern, kw_format))

        # Strings
        str_format = QTextCharFormat()
        str_format.setForeground(QColor("#00BC8C"))
        self._rules.append((re.compile(r'"[^"]*"'), str_format))
        self._rules.append((re.compile(r"'[^']*'"), str_format))

        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6C757D"))
        comment_format.setFontItalic(True)
        self._rules.append((re.compile(r"#.*$"), comment_format))

        # Numbers
        num_format = QTextCharFormat()
        num_format.setForeground(QColor("#E74C3C"))
        self._rules.append((re.compile(r"\b\d+\.?\d*\b"), num_format))

        # Builtins
        builtin_format = QTextCharFormat()
        builtin_format.setForeground(QColor("#3498DB"))
        builtins_list = ["print", "len", "range", "enumerate", "sum", "max", "min",
                         "list", "dict", "set", "str", "int", "float", "type"]
        for b in builtins_list:
            self._rules.append((re.compile(rf"\b{b}\b"), builtin_format))

    def highlightBlock(self, text: str):
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


# ---------------------------------------------------------------------------
#  ScriptingPanel -- Panel de consola Python
# ---------------------------------------------------------------------------
class ScriptingPanel(QWidget):
    """
    Panel de scripting Python para automatizar tareas en Soundvi.
    Solo visible para usuarios profesionales.
    """

    script_ejecutado = pyqtSignal(str)  # resultado de la ejecucion

    def __init__(self, contexto: Optional[Dict[str, Any]] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._contexto = contexto or {}
        self._historial: list = []
        self._idx_historial = -1

        self._construir_ui()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #2B3035;
                border-bottom: 2px solid #E74C3C;
                padding: 4px;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)

        titulo = QLabel("🐍 Consola Python")
        titulo.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #E74C3C;")
        header_layout.addWidget(titulo)

        header_layout.addStretch()

        # Combo de snippets
        self._combo_snippets = QComboBox()
        self._combo_snippets.addItems(list(SNIPPETS.keys()))
        self._combo_snippets.setStyleSheet("""
            QComboBox {
                background-color: #3B4148;
                color: #DEE2E6;
                border: 1px solid #495057;
                border-radius: 3px;
                padding: 2px 8px;
                min-width: 160px;
            }
        """)
        self._combo_snippets.currentTextChanged.connect(self._insertar_snippet)
        header_layout.addWidget(self._combo_snippets)

        btn_limpiar = QPushButton("🗑 Limpiar")
        btn_limpiar.setStyleSheet("""
            QPushButton {
                background-color: #495057; color: #DEE2E6;
                border: none; border-radius: 3px;
                padding: 4px 10px; font-size: 11px;
            }
            QPushButton:hover { background-color: #6C757D; }
        """)
        btn_limpiar.clicked.connect(self._limpiar_salida)
        header_layout.addWidget(btn_limpiar)

        layout.addWidget(header)

        # Splitter: editor arriba, salida abajo
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Editor de codigo
        self._editor = QPlainTextEdit()
        self._editor.setFont(QFont("Consolas", 11))
        self._editor.setPlaceholderText(
            "# Escribe tu código Python aquí...\n"
            "# Objetos disponibles: timeline, clips, modules\n"
            "# Presiona Ctrl+Enter para ejecutar"
        )
        self._editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1a1d21;
                color: #DEE2E6;
                border: none;
                selection-background-color: #375A7F;
            }
        """)
        self._highlighter = PythonHighlighter(self._editor.document())
        splitter.addWidget(self._editor)

        # Salida / consola
        self._salida = QTextEdit()
        self._salida.setReadOnly(True)
        self._salida.setFont(QFont("Consolas", 10))
        self._salida.setStyleSheet("""
            QTextEdit {
                background-color: #0d1117;
                color: #8B949E;
                border: none;
                border-top: 1px solid #495057;
            }
        """)
        self._salida.setPlaceholderText("La salida aparecerá aquí...")
        splitter.addWidget(self._salida)

        splitter.setSizes([300, 200])
        layout.addWidget(splitter)

        # Barra inferior: ejecutar
        barra = QFrame()
        barra.setStyleSheet("QFrame { background-color: #2B3035; border-top: 1px solid #495057; }")
        barra_layout = QHBoxLayout(barra)
        barra_layout.setContentsMargins(8, 4, 8, 4)

        lbl_info = QLabel("Ctrl+Enter para ejecutar")
        lbl_info.setStyleSheet("color: #6C757D; font-size: 10px;")
        barra_layout.addWidget(lbl_info)

        barra_layout.addStretch()

        btn_ejecutar = QPushButton("▶ Ejecutar")
        btn_ejecutar.setStyleSheet("""
            QPushButton {
                background-color: #00BC8C;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #00D6A1; }
        """)
        btn_ejecutar.clicked.connect(self._ejecutar)
        barra_layout.addWidget(btn_ejecutar)

        layout.addWidget(barra)

    def keyPressEvent(self, event):
        """Ctrl+Enter para ejecutar."""
        from PyQt6.QtCore import Qt
        if (event.modifiers() & Qt.KeyboardModifier.ControlModifier and
                event.key() == Qt.Key.Key_Return):
            self._ejecutar()
        else:
            super().keyPressEvent(event)

    def _insertar_snippet(self, nombre: str):
        """Inserta un snippet en el editor."""
        codigo = SNIPPETS.get(nombre, "")
        if codigo:
            self._editor.setPlainText(codigo)
            self._combo_snippets.setCurrentIndex(0)  # Reset selector

    def _limpiar_salida(self):
        """Limpia la consola de salida."""
        self._salida.clear()

    def _ejecutar(self):
        """Ejecuta el codigo del editor en un entorno sandbox."""
        codigo = self._editor.toPlainText().strip()
        if not codigo:
            return

        self._historial.append(codigo)
        self._idx_historial = len(self._historial)

        # Capturar stdout
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        buffer_out = io.StringIO()
        buffer_err = io.StringIO()

        try:
            sys.stdout = buffer_out
            sys.stderr = buffer_err

            # Contexto de ejecucion con objetos de Soundvi
            exec_context = dict(self._contexto)
            exec_context["__builtins__"] = __builtins__

            exec(codigo, exec_context)

            salida = buffer_out.getvalue()
            errores = buffer_err.getvalue()

            if salida:
                self._agregar_salida(salida, "#00BC8C")
            if errores:
                self._agregar_salida(errores, "#F39C12")
            if not salida and not errores:
                self._agregar_salida("✓ Ejecutado sin errores.", "#6C757D")

        except Exception as e:
            tb = traceback.format_exc()
            self._agregar_salida(f"❌ Error:\n{tb}", "#E74C3C")

        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        self.script_ejecutado.emit(codigo)

    def _agregar_salida(self, texto: str, color: str = "#DEE2E6"):
        """Agrega texto a la consola de salida con color."""
        self._salida.append(
            f'<span style="color: {color}; font-family: Consolas;">{texto}</span>'
        )

    # -- API publica -----------------------------------------------------------
    def set_contexto(self, contexto: Dict[str, Any]):
        """Establece el contexto de ejecucion (timeline, clips, etc.)."""
        self._contexto = contexto

    def actualizar_contexto(self, clave: str, valor: Any):
        """Actualiza una clave del contexto."""
        self._contexto[clave] = valor
