# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- Wizard de Bienvenida para usuarios novatos.

Guia paso a paso que enseña al usuario:
  1. Importar medios (video/audio/imagen)
  2. Agregar clips al timeline
  3. Aplicar un efecto
  4. Exportar el video final

Se muestra al inicio cuando el nivel es Novato y es primer uso,
o cuando el usuario lo solicita desde el panel de Primeros Pasos.
"""

from __future__ import annotations

import os
import sys
import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QStackedWidget, QWidget, QSizePolicy, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _RAIZ) if _RAIZ not in sys.path else None

log = logging.getLogger("soundvi.qt6.welcome_wizard")


# ---------------------------------------------------------------------------
#  Datos de los pasos del wizard
# ---------------------------------------------------------------------------
PASOS_WIZARD = [
    {
        "titulo": "¡Bienvenido a Soundvi! 🎬",
        "icono": "🎉",
        "descripcion": (
            "Soundvi es un editor de video audio-reactivo que te permite\n"
            "crear videos increíbles sincronizados con tu música.\n\n"
            "Este asistente te guiará en tus primeros pasos.\n"
            "¡Vamos a crear tu primer video juntos!"
        ),
        "tip": "💡 Puedes volver a ver este asistente desde el menú Help > Asistente de Bienvenida.",
    },
    {
        "titulo": "Paso 1: Importar medios 📁",
        "icono": "📁",
        "descripcion": (
            "Lo primero es agregar tu contenido a la Biblioteca de Medios.\n\n"
            "Puedes importar:\n"
            "  • Videos (.mp4, .avi, .mov)\n"
            "  • Audio (.mp3, .wav, .flac)\n"
            "  • Imágenes (.png, .jpg, .gif)\n\n"
            "Usa Ctrl+I o el botón 'Importar' en la barra de herramientas."
        ),
        "tip": "💡 También puedes arrastrar archivos directamente desde tu explorador de archivos.",
    },
    {
        "titulo": "Paso 2: Agregar al Timeline 📋",
        "icono": "📋",
        "descripcion": (
            "El Timeline es donde organizas tu video.\n\n"
            "Desde la Biblioteca, arrastra un clip hacia\n"
            "el timeline en la parte inferior de la pantalla.\n\n"
            "Los clips se colocan en pistas (tracks):\n"
            "  • Pista de Video: para clips de video e imágenes\n"
            "  • Pista de Audio: para música y sonidos"
        ),
        "tip": "💡 Puedes mover clips arrastrándolos y redimensionarlos desde los bordes.",
    },
    {
        "titulo": "Paso 3: Aplicar un efecto ✨",
        "icono": "✨",
        "descripcion": (
            "En el panel de Módulos (izquierda) encontrarás\n"
            "efectos para aplicar a tus clips.\n\n"
            "Para aplicar un efecto:\n"
            "  1. Selecciona un clip en el timeline\n"
            "  2. Haz doble clic en el módulo deseado\n\n"
            "Los efectos audio-reactivos responden a la\n"
            "música automáticamente. ¡Es como magia! 🎵"
        ),
        "tip": "💡 Usa el Inspector (derecha) para ajustar las propiedades del efecto.",
    },
    {
        "titulo": "Paso 4: Exportar tu video 🎬",
        "icono": "🎬",
        "descripcion": (
            "Cuando estés listo, exporta tu creación:\n\n"
            "  1. Ve a File > Exportar video (Ctrl+E)\n"
            "  2. Elige la calidad y formato\n"
            "  3. Selecciona dónde guardar\n"
            "  4. ¡Presiona Exportar!\n\n"
            "Soundvi se encarga del resto. 🚀"
        ),
        "tip": "💡 Para empezar, usa '1080p H.264' — es compatible con casi todo.",
    },
    {
        "titulo": "¡Listo para crear! 🎊",
        "icono": "🚀",
        "descripcion": (
            "Ya conoces lo básico de Soundvi.\n\n"
            "Recuerda:\n"
            "  • Ctrl+Z para deshacer cualquier error\n"
            "  • Ctrl+S para guardar tu proyecto\n"
            "  • Los tooltips tienen información útil\n\n"
            "¡Diviértete creando! Zoundvi cree en ti. 🐾"
        ),
        "tip": "💡 Puedes cambiar tu nivel de experiencia en Modules > Cambiar perfil.",
    },
]


# ---------------------------------------------------------------------------
#  PaginaWizard -- una pagina individual del wizard
# ---------------------------------------------------------------------------
class PaginaWizard(QWidget):
    """Widget que representa un paso individual del wizard."""

    def __init__(self, datos: dict, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        # Icono grande
        icono = QLabel(datos["icono"])
        icono.setFont(QFont("Segoe UI", 48))
        icono.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icono)

        # Titulo
        titulo = QLabel(datos["titulo"])
        titulo.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setStyleSheet("color: #00BC8C;")
        layout.addWidget(titulo)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #495057; max-height: 1px;")
        layout.addWidget(sep)

        # Descripcion
        desc = QLabel(datos["descripcion"])
        desc.setFont(QFont("Segoe UI", 12))
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignLeft)
        desc.setStyleSheet("color: #DEE2E6; line-height: 1.5;")
        layout.addWidget(desc)

        layout.addStretch()

        # Tip
        tip = QLabel(datos["tip"])
        tip.setWordWrap(True)
        tip.setStyleSheet("""
            QLabel {
                background-color: #1a3a2a;
                color: #00BC8C;
                border: 1px solid #00BC8C;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 11px;
            }
        """)
        layout.addWidget(tip)


# ---------------------------------------------------------------------------
#  WelcomeWizard -- dialogo principal del wizard
# ---------------------------------------------------------------------------
class WelcomeWizard(QDialog):
    """
    Wizard de bienvenida paso a paso para usuarios novatos.
    Muestra una secuencia de pasos explicando el flujo basico de trabajo.
    """

    wizard_completado = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Bienvenido a Soundvi")
        self.setMinimumSize(QSize(560, 520))
        self.resize(600, 560)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #212529;
            }
        """)

        self._paso_actual = 0
        self._total_pasos = len(PASOS_WIZARD)

        self._construir_ui()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Stacked widget con las paginas
        self._stack = QStackedWidget()
        for datos in PASOS_WIZARD:
            self._stack.addWidget(PaginaWizard(datos))
        layout.addWidget(self._stack)

        # Barra inferior: progreso + navegacion
        barra = QFrame()
        barra.setStyleSheet("""
            QFrame {
                background-color: #2B3035;
                border-top: 1px solid #495057;
                padding: 8px;
            }
        """)
        barra_layout = QVBoxLayout(barra)
        barra_layout.setContentsMargins(16, 8, 16, 8)

        # Barra de progreso
        self._progress = QProgressBar()
        self._progress.setRange(0, self._total_pasos - 1)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(6)
        self._progress.setStyleSheet("""
            QProgressBar {
                background-color: #495057;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #00BC8C;
                border-radius: 3px;
            }
        """)
        barra_layout.addWidget(self._progress)

        # Indicador de paso
        self._lbl_paso = QLabel()
        self._lbl_paso.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_paso.setStyleSheet("color: #6C757D; font-size: 10px;")
        barra_layout.addWidget(self._lbl_paso)

        # Botones
        btn_layout = QHBoxLayout()

        self._btn_omitir = QPushButton("Omitir todo")
        self._btn_omitir.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #6C757D;
                border: none;
                font-size: 11px;
                padding: 6px 12px;
            }
            QPushButton:hover { color: #ADB5BD; }
        """)
        self._btn_omitir.clicked.connect(self._omitir)
        btn_layout.addWidget(self._btn_omitir)

        btn_layout.addStretch()

        self._btn_anterior = QPushButton("← Anterior")
        self._btn_anterior.setStyleSheet("""
            QPushButton {
                background-color: #495057;
                color: #DEE2E6;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #6C757D; }
        """)
        self._btn_anterior.clicked.connect(self._anterior)
        btn_layout.addWidget(self._btn_anterior)

        self._btn_siguiente = QPushButton("Siguiente →")
        self._btn_siguiente.setStyleSheet("""
            QPushButton {
                background-color: #00BC8C;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #00D6A1; }
        """)
        self._btn_siguiente.clicked.connect(self._siguiente)
        btn_layout.addWidget(self._btn_siguiente)

        barra_layout.addLayout(btn_layout)
        layout.addWidget(barra)

        self._actualizar_estado()

    def _actualizar_estado(self):
        """Actualiza botones y progreso segun el paso actual."""
        self._stack.setCurrentIndex(self._paso_actual)
        self._progress.setValue(self._paso_actual)
        self._lbl_paso.setText(
            f"Paso {self._paso_actual + 1} de {self._total_pasos}"
        )
        self._btn_anterior.setEnabled(self._paso_actual > 0)

        if self._paso_actual == self._total_pasos - 1:
            self._btn_siguiente.setText("¡Empezar! 🚀")
        else:
            self._btn_siguiente.setText("Siguiente →")

    def _siguiente(self):
        if self._paso_actual < self._total_pasos - 1:
            self._paso_actual += 1
            self._actualizar_estado()
        else:
            self._finalizar()

    def _anterior(self):
        if self._paso_actual > 0:
            self._paso_actual -= 1
            self._actualizar_estado()

    def _omitir(self):
        self._finalizar()

    def _finalizar(self):
        self.wizard_completado.emit()
        self.accept()
        log.info("Wizard de bienvenida completado.")


# ---------------------------------------------------------------------------
#  Panel de Primeros Pasos (embebido en la ventana principal)
# ---------------------------------------------------------------------------
class PanelPrimerosPasos(QFrame):
    """
    Panel que se muestra en la ventana principal para usuarios novatos.
    Ofrece accesos directos a las acciones principales con descripciones.
    """

    accion_solicitada = pyqtSignal(str)  # nombre de la accion

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #1B2631;
                border: 2px solid #00BC8C;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Titulo
        titulo = QLabel("🚀 Primeros Pasos")
        titulo.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #00BC8C; border: none;")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(titulo)

        subtitulo = QLabel("¿Por dónde empezar? Sigue estos pasos:")
        subtitulo.setStyleSheet("color: #ADB5BD; font-size: 11px; border: none;")
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitulo)

        # Pasos como botones
        pasos = [
            ("1️⃣", "Importar medios", "Agrega tus archivos de video y audio", "import_media"),
            ("2️⃣", "Agregar al timeline", "Arrastra clips al timeline para organizarlos", "add_to_timeline"),
            ("3️⃣", "Aplicar un efecto", "Haz doble clic en un módulo para aplicarlo", "open_modules"),
            ("4️⃣", "Exportar video", "Genera tu video final listo para compartir", "export_video"),
        ]

        for icono, nombre, desc, accion in pasos:
            btn = QPushButton(f"{icono}  {nombre}")
            btn.setToolTip(desc)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2B3035;
                    color: #DEE2E6;
                    border: 1px solid #495057;
                    border-radius: 6px;
                    padding: 10px 16px;
                    font-size: 12px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #375A7F;
                    border-color: #00BC8C;
                }
            """)
            btn.clicked.connect(lambda checked, a=accion: self.accion_solicitada.emit(a))
            layout.addWidget(btn)

        # Boton para ver wizard
        btn_wizard = QPushButton("📖 Ver tutorial completo")
        btn_wizard.setStyleSheet("""
            QPushButton {
                background-color: #00BC8C;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #00D6A1; }
        """)
        btn_wizard.clicked.connect(lambda: self.accion_solicitada.emit("show_wizard"))
        layout.addWidget(btn_wizard)

        # Link para cerrar
        btn_cerrar = QPushButton("✕ Ocultar este panel")
        btn_cerrar.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #6C757D;
                border: none;
                font-size: 10px;
                padding: 4px;
            }
            QPushButton:hover { color: #ADB5BD; }
        """)
        btn_cerrar.clicked.connect(self.hide)
        layout.addWidget(btn_cerrar)
