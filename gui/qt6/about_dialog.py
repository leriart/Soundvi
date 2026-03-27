# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- About Dialog con Zoundvi.

Dialogo satirico "Acerca de" que muestra al zombie en el inodoro
y texto grosero/comico sobre el programa. Porque hasta el About
tiene que tener personalidad.
"""

from __future__ import annotations

import os
import sys
import random

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QTabWidget
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QFont, QColor, QPalette, QIcon

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ZOUNDVI_DIR = os.path.join(_RAIZ, "multimedia", "zoundvi")


class AboutDialog(QDialog):
    """Dialogo 'Acerca de Soundvi' con Zoundvi y humor satirico."""

    _FRASES_CIERRE = [
        "Cerrar esta mierda",
        "Ya leí suficiente",
        "Siguiente ventana inútil",
        "Volver al trabajo (jaja)",
        "Entendido, jefe",
        "Ok, como sea",
        "Me vale, cierra",
        "Adiós, Zoundvi culero",
        "Skip intro",
        "TL;DR: cerrar",
        "No one cares, close",
        "Entendí todo (mentira)",
        "Gracias por la info que no pedí",
        "Understandable, have a nice day",
        "Ya sé wey, cierra",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Acerca de Soundvi -- Y del zombie que lo habita")
        self.setMinimumSize(600, 520)
        self.setMaximumSize(750, 680)
        self._construir_ui()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 15, 20, 15)

        # === Header con logo ===
        header = QHBoxLayout()

        # Logo Zoundvi
        logo_path = os.path.join(_ZOUNDVI_DIR, "zoundvi_logo.png")
        if os.path.isfile(logo_path):
            lbl_logo = QLabel()
            pixmap = QPixmap(logo_path).scaled(
                100, 100,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            lbl_logo.setPixmap(pixmap)
            header.addWidget(lbl_logo)

        # Titulo y version
        info_layout = QVBoxLayout()
        lbl_titulo = QLabel("SOUNDVI")
        lbl_titulo.setFont(QFont("Arial Black", 26, QFont.Weight.Bold))
        lbl_titulo.setStyleSheet("color: #E8842C;")
        info_layout.addWidget(lbl_titulo)

        lbl_version = QLabel("v4.8 — Edición 'It compiles, ship it' 27A1")
        lbl_version.setFont(QFont("Consolas", 10))
        lbl_version.setStyleSheet("color: #8CD47E;")
        info_layout.addWidget(lbl_version)

        lbl_desc = QLabel("Editor de video para masoquistas con buen gusto musical")
        lbl_desc.setFont(QFont("Arial", 9))
        lbl_desc.setStyleSheet("color: #AAA;")
        info_layout.addWidget(lbl_desc)

        header.addLayout(info_layout)
        header.addStretch()
        layout.addLayout(header)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #333;")
        layout.addWidget(sep)

        # === Tabs ===
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #333; border-radius: 5px; }
            QTabBar::tab { padding: 8px 16px; margin-right: 2px; }
            QTabBar::tab:selected { background: #E8842C; color: white; border-radius: 4px 4px 0 0; }
        """)

        # Tab 1: Acerca de (con la imagen del toilet)
        tabs.addTab(self._crear_tab_about(), "Acerca de")
        # Tab 2: Creditos
        tabs.addTab(self._crear_tab_creditos(), "Creditos")
        # Tab 3: Zoundvi
        tabs.addTab(self._crear_tab_zoundvi(), "Zoundvi")

        layout.addWidget(tabs)

        # === Boton de cierre ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cerrar = QPushButton(random.choice(self._FRASES_CIERRE))
        btn_cerrar.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        btn_cerrar.setMinimumSize(220, 40)
        btn_cerrar.setStyleSheet("""
            QPushButton {
                background-color: #E8842C;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 24px;
            }
            QPushButton:hover {
                background-color: #FF9944;
            }
            QPushButton:pressed {
                background-color: #C66A1A;
            }
        """)
        btn_cerrar.clicked.connect(self.accept)
        btn_layout.addWidget(btn_cerrar)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _crear_tab_about(self) -> QWidget:
        """Tab principal con imagen del zombie en el inodoro."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Imagen del zombie en el inodoro
        content_layout = QHBoxLayout()

        toilet_path = os.path.join(_ZOUNDVI_DIR, "zoundvi_toilet.png")
        if os.path.isfile(toilet_path):
            lbl_img = QLabel()
            pixmap = QPixmap(toilet_path).scaled(
                200, 200,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            lbl_img.setPixmap(pixmap)
            lbl_img.setAlignment(Qt.AlignmentFlag.AlignTop)
            content_layout.addWidget(lbl_img)

        # Texto satirico
        texto = QLabel()
        texto.setWordWrap(True)
        texto.setFont(QFont("Arial", 10))
        texto.setStyleSheet("color: #CCC; line-height: 1.5;")
        texto.setText(
            "<b>Soundvi</b> es un editor de video que literalmente nadie pidió pero que "
            "alguien construyó porque tenía demasiado tiempo libre (o muy poco sentido común).<br><br>"
            "Nació de la frustración de usar editores 'profesionales' que te cobran "
            "un riñón y medio solo para darte la oportunidad de crashear el software "
            "cada 5 minutos. Aquí crasheamos gratis y con estilo. ;)<br><br>"
            "Cuenta con un sistema de módulos 'Plug and Play' que permite "
            "agregar funcionalidad sin romper todo (jaja, buena esa... en teoría).<br><br>"
            "Perfiles de usuario: <b>Básico</b> (para mortales), <b>Creador</b> "
            "(para gente que cree que sabe), <b>Profesional</b> (RIP tu PC), "
            "y <b>Personalizado</b> (para indecis@s crónicos).<br><br>"
            "<i>\"It's not a bug, it's a feature™\"</i><br>"
            "<i>\"Works on my machine\"</i><br>"
            "<i>\"Si no funciona, reinicia. Si sigue sin funcionar... F\"</i><br>"
            "<small>-- Zoundvi, profeta de los bugs, 2026</small>"
        )
        content_layout.addWidget(texto, 1)
        layout.addLayout(content_layout)
        layout.addStretch()

        return widget

    def _crear_tab_creditos(self) -> QWidget:
        """Tab de creditos."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        creditos = QLabel()
        creditos.setWordWrap(True)
        creditos.setFont(QFont("Consolas", 10))
        creditos.setStyleSheet("color: #8CD47E;")
        creditos.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        creditos.setText(
            "<b>== CRÉDITOS (por si alguien pregunta) ==</b><br><br>"
            "<b>Desarrollo:</b> Un wey con más café que neuronas funcionales<br>"
            "<b>Diseño UI:</b> El mismo wey, pero con 3 Red Bulls encima<br>"
            "<b>QA/Testing:</b> Los usuarios (beta testers sin saberlo lmao)<br>"
            "<b>Mascota Oficial:</b> Zoundvi (el zombie que no firmó para esto)<br>"
            "<b>Documentación:</b> ChatGPT + StackOverflow + 'Ctrl+C Ctrl+V'<br>"
            "<b>Soporte Emocional:</b> Memes de programación a las 3 AM<br>"
            "<b>Motivación:</b> Pura terquedad y despecho<br><br>"
            "<b>== TECNOLOGÍAS (aka: duct tape digital) ==</b><br><br>"
            "Python 3.10+ (porque 2.7 ya valió madres)<br>"
            "PyQt6 (para UI bonitas que sí crashean bonito)<br>"
            "OpenCV + NumPy (magia negra de procesamiento)<br>"
            "FFmpeg (el héroe sin capa que hace TODO)<br>"
            "librosa + Vosk (IA que a veces funciona)<br>"
            "Y un chingo de librerías que ni recordamos<br><br>"
            "<b>== AGRADECIMIENTOS ESPECIALES ==</b><br><br>"
            "2605 A Stack Overflow: MVP del año, todos los años<br>"
            "2615 Al café: Sin ti, esto sería Visual Basic<br>"
            "2697 A los beta testers: Gracias por no demandar (todavía)<br>"
            "2699 A Git: Por dejarme hacer 'git revert' cada 5 minutos<br>"
            "2639 A mi RAM: Sorry por los memory leaks, bro<br>"
            "266B A Spotify: Por la playlist 'Coding in the Dark'<br>"
            "2022 A la pizza fría de las 4 AM: Real one<br><br>"
            "<b>== LICENCIA ==</b><br><br>"
            "MIT License -- Úsalo, modifícalo, véndelo, nos vale.<br>"
            "Si truena algo: not my problem ¯\\_(ツ)_/¯<br>"
            "Si le haces millones: invita las chelas<br>"
            "Disclaimer: El software viene 'as is' aka 'aguántese'"
        )
        layout.addWidget(creditos)
        layout.addStretch()

        return widget

    def _crear_tab_zoundvi(self) -> QWidget:
        """Tab dedicado al personaje Zoundvi."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Scroll area para el contenido
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        content = QWidget()
        content_layout = QVBoxLayout(content)

        # Titulo
        titulo = QLabel("Conoce a Zoundvi")
        titulo.setFont(QFont("Arial Black", 16, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #E8842C;")
        content_layout.addWidget(titulo)

        # Descripcion
        desc = QLabel()
        desc.setWordWrap(True)
        desc.setFont(QFont("Arial", 10))
        desc.setStyleSheet("color: #CCC;")
        desc.setText(
            "Zoundvi es un zombie verde con ojos más saltones que chapulín, pelo más "
            "desalineado que tu vida, y una camiseta naranja que ya no se acuerda "
            "cuándo fue su último día de lavado. Es la mascota no oficial (y definitivamente "
            "no solicitada) de Soundvi. Básicamente, el espíritu animal de todos los devs.<br><br>"
            "Aparece en diferentes situaciones del programa:<br>"
            "25B6 Editando video con tijeras (herramientas digitales? para qué?)<br>"
            "2022 Esperando renders con cara de 'me quiero morir' (relatable)<br>"
            "2605 Celebrando exports como si hubiera ganado el mundial<br>"
            "2620 Aterrándose con BSoDs y crashes épicos<br>"
            "2615 Tomando café (o lo que sea que tomen los zombies)<br>"
            "2022 Filosofando en el trono (porque hasta los zombies necesitan su tiempo)<br><br>"
            "<b>Frases célebres de Zoundvi:</b><br>"
            "<i>\"PUTO EL QUE LO LEA\"</i> (spoiler: ya caíste)<br>"
            "<i>\"¿Feature o bug? Sí\"</i><br>"
            "<i>\"El código funciona, no toques nada\"</i><br>"
            "<i>\"Ctrl+Z es mi mejor amigo\"</i><br>"
            "<i>\"Si compila, envíalo\"</i><br><br>"
            "<small>Nota: Zoundvi no se hace responsable por tus traumas con FFmpeg</small>"
        )
        content_layout.addWidget(desc)

        # Galeria de imagenes
        galeria_titulo = QLabel("Galeria de Zoundvi")
        galeria_titulo.setFont(QFont("Arial Black", 12))
        galeria_titulo.setStyleSheet("color: #8CD47E; margin-top: 10px;")
        content_layout.addWidget(galeria_titulo)

        # Mostrar imagenes en grid
        imagenes_info = [
            ("zoundvi_logo.png", "Zombie VHS (logo)"),
            ("zoundvi_toilet.png", "En el trono filosofando"),
            ("zoundvi_coffee.png", "Odio liquido (cafe)"),
        ]

        row_layout = None
        for i, (archivo, titulo_img) in enumerate(imagenes_info):
            if i % 3 == 0:
                row_layout = QHBoxLayout()
                content_layout.addLayout(row_layout)

            img_widget = QVBoxLayout()
            ruta = os.path.join(_ZOUNDVI_DIR, archivo)
            if os.path.isfile(ruta):
                lbl = QLabel()
                px = QPixmap(ruta).scaled(
                    120, 120,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                lbl.setPixmap(px)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                img_widget.addWidget(lbl)

            lbl_t = QLabel(titulo_img)
            lbl_t.setFont(QFont("Arial", 8))
            lbl_t.setStyleSheet("color: #999;")
            lbl_t.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_widget.addWidget(lbl_t)

            row_layout.addLayout(img_widget)

        # Rellenar ultima fila si es necesario
        if row_layout and len(imagenes_info) % 3 != 0:
            for _ in range(3 - len(imagenes_info) % 3):
                row_layout.addStretch()

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        return widget


def mostrar_about(parent=None):
    """Funcion helper para mostrar el dialogo About."""
    dlg = AboutDialog(parent)
    dlg.exec()
