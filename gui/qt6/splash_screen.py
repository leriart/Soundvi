# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- Splash Screen con Zoundvi.

Muestra el logo de Zoundvi al iniciar la aplicacion con barra de progreso
y texto satirico. Duracion: ~2-3 segundos.
"""

from __future__ import annotations

import os
import sys

from PyQt6.QtWidgets import QSplashScreen, QApplication, QProgressBar, QLabel
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QPixmap, QPainter, QFont, QColor, QLinearGradient

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ruta de imagenes de Zoundvi
_ZOUNDVI_DIR = os.path.join(_RAIZ, "multimedia", "zoundvi")
_LOGO_PATH = os.path.join(_ZOUNDVI_DIR, "zoundvi_logo.png")


class SoundviSplashScreen(QSplashScreen):
    """Splash screen con logo de Zoundvi, barra de progreso y texto satirico."""

    _FRASES = [
        "Cargando módulos de dudosa procedencia...",
        "Invocando al zombie editor (espero que esté sobrio)...",
        "Preparando el café virtual... ☕ (no juzgues)",
        "Calibrando el desastre visual...",
        "Despertando neuronas zombies (si es que hay alguna)...",
        "Compilando excusas creativas para los bugs...",
        "Cargando interfaz (recen para que funcione)...",
        "Inicializando motor de render (F por tu RAM)...",
        "Verificando que nadie rompió nada (sorpresa: sí rompieron)...",
        "Buscando los frames perdidos en el Triángulo de las Bermudas...",
        "Leyendo la documentación... jaja, buena esa ",
        "Optimizando el caos existencial...",
        "Cargando plugins experimentales (yolo)...",
        "Reviviendo procesos muertos (ctrl+shift+esc)...",
        "Haciendo magia negra con FFmpeg...",
        "Rogando que los módulos cooperen hoy...",
        "Abriendo la dimensión de los codecs perdidos...",
        "Esperando que Python no se tilte...",
        "Calentando los ventiladores de tu PC...",
        "Importando librerías que ni conoces...",
        "Midiendo tu paciencia (spoiler: es poca)...",
        "Ejecutando código legacy del 2015...",
        "Pidiéndole a Stack Overflow que nos salve...",
        "Cargando memes de programación...",
    ]

    def __init__(self):
        # Crear pixmap base
        splash_pixmap = self._crear_splash_pixmap()
        super().__init__(splash_pixmap)

        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        # Progreso interno
        self._progreso = 0
        self._frase_idx = 0
        self._frases_mostradas = []

        # Timer para animar progreso
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._avanzar_progreso)

    def _crear_splash_pixmap(self) -> QPixmap:
        """Crea el pixmap del splash screen con el logo de Zoundvi."""
        ancho, alto = 520, 420

        pixmap = QPixmap(ancho, alto)
        pixmap.fill(QColor(26, 26, 46))  # Fondo oscuro

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Borde con gradiente
        grad = QLinearGradient(0, 0, ancho, alto)
        grad.setColorAt(0, QColor(232, 132, 44))   # Naranja Zoundvi
        grad.setColorAt(1, QColor(75, 158, 58))     # Verde zombie
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawRoundedRect(0, 0, ancho, alto, 15, 15)

        # Fondo interior
        painter.setBrush(QColor(26, 26, 46))
        painter.drawRoundedRect(3, 3, ancho - 6, alto - 6, 13, 13)

        # Logo de Zoundvi
        if os.path.isfile(_LOGO_PATH):
            logo = QPixmap(_LOGO_PATH)
            if not logo.isNull():
                logo_scaled = logo.scaled(
                    180, 180,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                x_logo = (ancho - logo_scaled.width()) // 2
                painter.drawPixmap(x_logo, 20, logo_scaled)

        # Titulo
        font_titulo = QFont("Arial Black", 28, QFont.Weight.Bold)
        painter.setFont(font_titulo)
        painter.setPen(QColor(232, 132, 44))
        painter.drawText(QRect(0, 205, ancho, 45), Qt.AlignmentFlag.AlignCenter, "SOUNDVI")

        # Subtitulo
        import random
        subtitulos = [
            "v4.8 -- Editor de video para zombies con buen gusto",
            "v4.8 -- Donde los bugs son features™",
            "v4.8 -- Probablemente funcione (no garantizado)",
            "v4.8 -- Hecho con café y desesperación",
            "v4.8 -- 'It compiles, ship it' Edition",
            "v4.8 -- May contain traces of sanity",
        ]
        font_sub = QFont("Arial", 11)
        painter.setFont(font_sub)
        painter.setPen(QColor(180, 180, 180))
        painter.drawText(
            QRect(0, 250, ancho, 25),
            Qt.AlignmentFlag.AlignCenter,
            random.choice(subtitulos)
        )

        # Linea separadora
        painter.setPen(QColor(60, 60, 80))
        painter.drawLine(40, 285, ancho - 40, 285)

        # Espacio para texto dinamico (se dibuja en drawContents)

        # Barra de progreso (fondo)
        painter.setBrush(QColor(40, 40, 60))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(40, 370, ancho - 80, 20, 5, 5)

        # Credito
        creditos_zoundvi = [
            "Zoundvi dice: 'Editar video nunca fue tan... cuestionable'",
            "Zoundvi: 'Si crashea, no fui yo' ☠",
            "Zoundvi promete bugs al mejor estilo 2020",
            "Warning: Zombie inside, proceed with caution 26A0",
            "Powered by café, pizza fría y Stack Overflow",
            "Zoundvi: 'Trust me bro, funciona'",
        ]
        font_credito = QFont("Arial", 8)
        painter.setFont(font_credito)
        painter.setPen(QColor(100, 100, 120))
        painter.drawText(
            QRect(0, 395, ancho, 20),
            Qt.AlignmentFlag.AlignCenter,
            random.choice(creditos_zoundvi)
        )

        painter.end()
        return pixmap

    def drawContents(self, painter: QPainter):
        """Dibuja contenido dinamico sobre el splash."""
        ancho = self.pixmap().width()

        # Texto de carga
        font_msg = QFont("Consolas", 10)
        painter.setFont(font_msg)
        painter.setPen(QColor(140, 212, 126))  # Verde terminal

        if self._frase_idx < len(self._FRASES):
            frase = self._FRASES[self._frase_idx]
        else:
            frase = "Listo. Que comience la locura."

        painter.drawText(QRect(40, 295, ancho - 80, 25), Qt.AlignmentFlag.AlignLeft, f"> {frase}")

        # Porcentaje
        font_pct = QFont("Arial Black", 9)
        painter.setFont(font_pct)
        painter.setPen(QColor(232, 132, 44))
        painter.drawText(
            QRect(40, 345, ancho - 80, 20),
            Qt.AlignmentFlag.AlignRight,
            f"{self._progreso}%"
        )

        # Barra de progreso (relleno)
        if self._progreso > 0:
            barra_ancho = int((ancho - 80) * self._progreso / 100)
            grad = QLinearGradient(40, 0, 40 + barra_ancho, 0)
            grad.setColorAt(0, QColor(75, 158, 58))
            grad.setColorAt(1, QColor(140, 212, 126))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(grad)
            painter.drawRoundedRect(40, 370, barra_ancho, 20, 5, 5)

    def iniciar(self, callback_fin=None):
        """Inicia la animacion del splash screen."""
        self._callback_fin = callback_fin
        self._progreso = 0
        self._frase_idx = 0
        self.show()
        self._timer.start(120)  # ~2.5 segundos total (120ms * ~21 pasos)

    def _avanzar_progreso(self):
        """Avanza la barra de progreso y cambia frases."""
        self._progreso += 5
        if self._progreso % 15 == 0:
            self._frase_idx = min(self._frase_idx + 1, len(self._FRASES) - 1)

        self.repaint()

        if self._progreso >= 100:
            self._timer.stop()
            self.showMessage(
                "Carga completa. Buena suerte.",
                Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
                QColor(140, 212, 126)
            )
            # Cerrar splash despues de 300ms
            QTimer.singleShot(300, self._finalizar)

    def _finalizar(self):
        """Cierra el splash y ejecuta callback."""
        self.close()
        if hasattr(self, '_callback_fin') and self._callback_fin:
            self._callback_fin()


def mostrar_splash(app: QApplication, callback_fin=None) -> SoundviSplashScreen:
    """Funcion helper para mostrar el splash screen."""
    splash = SoundviSplashScreen()
    splash.iniciar(callback_fin)
    return splash
