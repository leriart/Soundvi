# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- Widgets auxiliares reutilizables.

Contiene widgets personalizados de uso comun en toda la interfaz:
  - ColorPickerWidget    Selector de color con preview
  - SliderWithLabel      Slider con etiqueta y valor numerico
  - TimeCodeEdit         Editor de timecode (HH:MM:SS:FF)
  - ThumbnailWidget      Widget para mostrar thumbnail de clip
  - PropertyGroup        Grupo colapsable de propiedades
"""

from __future__ import annotations

from typing import Optional, Callable

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QSlider, QLineEdit, QFrame, QSizePolicy, QColorDialog,
    QGroupBox, QToolButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont, QPixmap, QPainter, QImage

import numpy as np


# ---------------------------------------------------------------------------
#  ColorPickerWidget -- Selector de color con preview
# ---------------------------------------------------------------------------
class ColorPickerWidget(QWidget):
    """Selector de color con boton de preview y dialogo de seleccion."""

    color_changed = pyqtSignal(str)  # emite color en formato '#RRGGBB'

    def __init__(self, label: str = "Color", color_inicial: str = "#FFFFFF",
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._color = color_inicial

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        lbl = QLabel(label)
        lbl.setMinimumWidth(80)
        layout.addWidget(lbl)

        # Boton de muestra de color
        self._btn_color = QPushButton()
        self._btn_color.setFixedSize(28, 28)
        self._btn_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_color.setToolTip("Seleccionar color")
        self._btn_color.clicked.connect(self._abrir_selector)
        layout.addWidget(self._btn_color)

        # Etiqueta con valor hex
        self._lbl_hex = QLabel(color_inicial)
        self._lbl_hex.setFont(QFont("Consolas", 10))
        self._lbl_hex.setMinimumWidth(65)
        layout.addWidget(self._lbl_hex)

        layout.addStretch()
        self._actualizar_muestra()

    def _abrir_selector(self):
        """Abre el dialogo nativo de seleccion de color."""
        color = QColorDialog.getColor(QColor(self._color), self, "Seleccionar color")
        if color.isValid():
            self._color = color.name()
            self._actualizar_muestra()
            self.color_changed.emit(self._color)

    def _actualizar_muestra(self):
        self._btn_color.setStyleSheet(
            f"QPushButton {{ background-color: {self._color}; "
            f"border: 2px solid #495057; border-radius: 4px; }}"
            f"QPushButton:hover {{ border-color: #00BC8C; }}"
        )
        self._lbl_hex.setText(self._color)

    def get_color(self) -> str:
        return self._color

    def set_color(self, color: str):
        self._color = color
        self._actualizar_muestra()


# ---------------------------------------------------------------------------
#  SliderWithLabel -- Slider con etiqueta y valor numerico
# ---------------------------------------------------------------------------
class SliderWithLabel(QWidget):
    """Slider horizontal con etiqueta, valor numerico y rango configurable."""

    value_changed = pyqtSignal(float)

    def __init__(self, label: str, minimo: float = 0.0, maximo: float = 1.0,
                 valor: float = 0.5, decimales: int = 2, paso: int = 100,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._min = minimo
        self._max = maximo
        self._decimales = decimales
        self._paso = paso  # pasos internos del slider

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        lbl = QLabel(label)
        lbl.setMinimumWidth(80)
        layout.addWidget(lbl)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, paso)
        self._slider.setValue(self._valor_a_slider(valor))
        self._slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self._slider)

        self._lbl_valor = QLabel(f"{valor:.{decimales}f}")
        self._lbl_valor.setMinimumWidth(45)
        self._lbl_valor.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._lbl_valor.setFont(QFont("Consolas", 10))
        layout.addWidget(self._lbl_valor)

    def _valor_a_slider(self, val: float) -> int:
        if self._max == self._min:
            return 0
        return int(((val - self._min) / (self._max - self._min)) * self._paso)

    def _slider_a_valor(self, pos: int) -> float:
        return self._min + (pos / self._paso) * (self._max - self._min)

    def _on_slider_changed(self, pos: int):
        val = self._slider_a_valor(pos)
        self._lbl_valor.setText(f"{val:.{self._decimales}f}")
        self.value_changed.emit(val)

    def get_value(self) -> float:
        return self._slider_a_valor(self._slider.value())

    def set_value(self, val: float):
        self._slider.blockSignals(True)
        self._slider.setValue(self._valor_a_slider(val))
        self._lbl_valor.setText(f"{val:.{self._decimales}f}")
        self._slider.blockSignals(False)


# ---------------------------------------------------------------------------
#  TimeCodeEdit -- Editor de timecode (HH:MM:SS:FF)
# ---------------------------------------------------------------------------
class TimeCodeEdit(QWidget):
    """Editor de timecode con formato HH:MM:SS.mmm."""

    time_changed = pyqtSignal(float)  # emite tiempo en segundos

    def __init__(self, label: str = "Tiempo", valor: float = 0.0,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._valor = valor

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        lbl = QLabel(label)
        lbl.setMinimumWidth(80)
        layout.addWidget(lbl)

        self._edit = QLineEdit(self._formato(valor))
        self._edit.setFont(QFont("Consolas", 10))
        self._edit.setFixedWidth(100)
        self._edit.setToolTip("Formato: HH:MM:SS.mmm")
        self._edit.editingFinished.connect(self._on_edit)
        layout.addWidget(self._edit)

        layout.addStretch()

    @staticmethod
    def _formato(segundos: float) -> str:
        """Convierte segundos a formato HH:MM:SS.mmm."""
        h = int(segundos // 3600)
        m = int((segundos % 3600) // 60)
        s = int(segundos % 60)
        ms = int((segundos % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

    @staticmethod
    def _parsear(texto: str) -> float:
        """Parsea texto en formato HH:MM:SS.mmm a segundos."""
        try:
            partes = texto.strip().split(":")
            if len(partes) == 3:
                h = int(partes[0])
                m = int(partes[1])
                s_parts = partes[2].split(".")
                s = int(s_parts[0])
                ms = int(s_parts[1]) if len(s_parts) > 1 else 0
                return h * 3600 + m * 60 + s + ms / 1000.0
            elif len(partes) == 2:
                m = int(partes[0])
                s_parts = partes[1].split(".")
                s = int(s_parts[0])
                ms = int(s_parts[1]) if len(s_parts) > 1 else 0
                return m * 60 + s + ms / 1000.0
        except (ValueError, IndexError):
            pass
        return 0.0

    def _on_edit(self):
        val = self._parsear(self._edit.text())
        if val != self._valor:
            self._valor = val
            self._edit.setText(self._formato(val))
            self.time_changed.emit(val)

    def get_time(self) -> float:
        return self._valor

    def set_time(self, val: float):
        self._valor = val
        self._edit.setText(self._formato(val))


# ---------------------------------------------------------------------------
#  ThumbnailWidget -- Widget para mostrar thumbnail de clip
# ---------------------------------------------------------------------------
class ThumbnailWidget(QLabel):
    """Muestra un thumbnail de un clip con nombre superpuesto."""

    clicked = pyqtSignal()

    def __init__(self, width: int = 120, height: int = 68,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._w = width
        self._h = height
        self.setFixedSize(width, height)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: #2B3035;
                border: 1px solid #495057;
                border-radius: 4px;
                color: #6C757D;
                font-size: 10px;
            }
        """)
        self.setText("Sin thumbnail")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_thumbnail_numpy(self, frame: np.ndarray, nombre: str = ""):
        """Establece el thumbnail desde un numpy array BGR."""
        if frame is None:
            return
        try:
            import cv2
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w = frame_rgb.shape[:2]
            qimg = QImage(frame_rgb.data, w, h, w * 3, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg).scaled(
                self._w, self._h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.setPixmap(pixmap)
        except Exception:
            self.setText(nombre or "Error")

    def set_color(self, color: str, nombre: str = ""):
        """Muestra un color solido como thumbnail."""
        pixmap = QPixmap(self._w, self._h)
        pixmap.fill(QColor(color))
        self.setPixmap(pixmap)
        if nombre:
            self.setToolTip(nombre)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
#  PropertyGroup -- Grupo colapsable de propiedades
# ---------------------------------------------------------------------------
class PropertyGroup(QFrame):
    """Grupo de propiedades colapsable con header clickeable."""

    toggled = pyqtSignal(bool)  # emite True si esta expandido

    def __init__(self, titulo: str, expandido: bool = True,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._expandido = expandido
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # Header clickeable
        icono_flecha = "  \u25BC" if expandido else "  \u25B6"
        self._header = QPushButton(f"{icono_flecha}  {titulo}")
        self._header.setStyleSheet("""
            QPushButton {
                background-color: #343A40;
                color: #DEE2E6;
                border: 1px solid #495057;
                border-radius: 3px;
                padding: 6px 8px;
                text-align: left;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #3B4148;
                border-color: #00BC8C;
            }
        """)
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.clicked.connect(self._toggle)
        self._titulo = titulo
        self._layout.addWidget(self._header)

        # Contenedor de contenido
        self._contenido = QWidget()
        self._contenido_layout = QVBoxLayout(self._contenido)
        self._contenido_layout.setContentsMargins(8, 4, 0, 4)
        self._contenido_layout.setSpacing(4)
        self._contenido.setVisible(expandido)
        self._layout.addWidget(self._contenido)

    def _toggle(self):
        self._expandido = not self._expandido
        self._contenido.setVisible(self._expandido)
        flecha = "\u25BC" if self._expandido else "\u25B6"
        self._header.setText(f"  {flecha}  {self._titulo}")
        self.toggled.emit(self._expandido)

    def agregar_widget(self, widget: QWidget):
        """Agrega un widget al contenido del grupo."""
        self._contenido_layout.addWidget(widget)

    def agregar_layout(self, layout):
        """Agrega un layout al contenido del grupo."""
        self._contenido_layout.addLayout(layout)

    def limpiar(self):
        """Elimina todos los widgets del contenido."""
        while self._contenido_layout.count():
            item = self._contenido_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    @property
    def expandido(self) -> bool:
        return self._expandido
