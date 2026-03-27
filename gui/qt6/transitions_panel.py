# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- Panel de Transiciones.

Biblioteca visual de las 19 transiciones disponibles con:
  - Lista/grid de transiciones con thumbnails/iconos
  - Preview animado al hover (simulado con colores)
  - Drag & drop a timeline (entre clips)
  - Configuracion de duracion de transicion
  - Filtrado por categoria (fade, wipe, slide, etc.)
  - Solo visible en perfiles Creador y Profesional
"""

from __future__ import annotations

import os
import sys
import logging
from typing import Optional, Dict, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy, QGridLayout, QComboBox,
    QDoubleSpinBox, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QTimer, QSize, QPropertyAnimation
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QPixmap, QDrag, QCursor,
    QLinearGradient, QPen, QBrush
)

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _RAIZ) if _RAIZ not in sys.path else None

from core.transitions import TransitionType, Transition
from core.profiles import ProfileManager
from gui.qt6.base import ICONOS_UNICODE

log = logging.getLogger("soundvi.qt6.transitions")

# Categorias de transiciones para filtrado
CATEGORIAS: Dict[str, List[str]] = {
    "Todas": TransitionType.ALL_TYPES,
    "Fundido": [TransitionType.FADE, TransitionType.CROSSFADE, TransitionType.DISSOLVE],
    "Barrido": [TransitionType.WIPE_LEFT, TransitionType.WIPE_RIGHT,
                TransitionType.WIPE_UP, TransitionType.WIPE_DOWN,
                TransitionType.WIPE_DIAGONAL],
    "Deslizar": [TransitionType.SLIDE_LEFT, TransitionType.SLIDE_RIGHT,
                 TransitionType.SLIDE_UP, TransitionType.SLIDE_DOWN],
    "Zoom": [TransitionType.ZOOM_IN, TransitionType.ZOOM_OUT],
    "Empujar": [TransitionType.PUSH_LEFT, TransitionType.PUSH_RIGHT],
    "Iris": [TransitionType.IRIS_OPEN, TransitionType.IRIS_CLOSE],
    "Desenfoque": [TransitionType.BLUR_TRANSITION],
}

# Iconos Unicode por categoria
ICONOS_TRANSICION: Dict[str, str] = {
    TransitionType.FADE:           "\u25A0",
    TransitionType.CROSSFADE:      "\u25A3",
    TransitionType.DISSOLVE:       "\u2591",
    TransitionType.WIPE_LEFT:      "\u25C0",
    TransitionType.WIPE_RIGHT:     "▶",
    TransitionType.WIPE_UP:        "\u25B2",
    TransitionType.WIPE_DOWN:      "\u25BC",
    TransitionType.WIPE_DIAGONAL:  "\u25E2",
    TransitionType.SLIDE_LEFT:     "\u21E6",
    TransitionType.SLIDE_RIGHT:    "\u21E8",
    TransitionType.SLIDE_UP:       "\u21E7",
    TransitionType.SLIDE_DOWN:     "\u21E9",
    TransitionType.ZOOM_IN:        "\u2295",
    TransitionType.ZOOM_OUT:       "\u2296",
    TransitionType.PUSH_LEFT:      "\u21D0",
    TransitionType.PUSH_RIGHT:     "\u21D2",
    TransitionType.IRIS_OPEN:      "\u25CE",
    TransitionType.IRIS_CLOSE:     "\u25C9",
    TransitionType.BLUR_TRANSITION: "\u224B",
}

# Colores de preview por tipo de transicion
COLORES_PREVIEW: Dict[str, tuple] = {
    "fade":    ("#3498DB", "#000000"),
    "cross":   ("#3498DB", "#E74C3C"),
    "dissolve": ("#3498DB", "#2ECC71"),
    "wipe":    ("#F39C12", "#9B59B6"),
    "slide":   ("#1ABC9C", "#E67E22"),
    "zoom":    ("#3498DB", "#F39C12"),
    "push":    ("#E74C3C", "#2ECC71"),
    "iris":    ("#9B59B6", "#F39C12"),
    "blur":    ("#3498DB", "#ADB5BD"),
}


# ---------------------------------------------------------------------------
#  TransitionCard -- Tarjeta visual de una transicion
# ---------------------------------------------------------------------------
class TransitionCard(QFrame):
    """Tarjeta que representa una transicion con icono, nombre y preview."""

    selected = pyqtSignal(str)        # transition_type
    drag_started = pyqtSignal(str)    # transition_type

    def __init__(self, transition_type: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.transition_type = transition_type
        self._hover = False
        self._timer_anim = QTimer()
        self._timer_anim.setInterval(50)
        self._anim_progress = 0.0
        self._timer_anim.timeout.connect(self._tick_anim)

        self.setFixedSize(100, 80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._actualizar_estilo(False)
        self.setToolTip(TransitionType.DISPLAY_NAMES.get(transition_type, transition_type))

        self._construir_ui()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Icono grande
        icono = ICONOS_TRANSICION.get(self.transition_type, "\u25A0")
        self._lbl_icono = QLabel(icono)
        self._lbl_icono.setFont(QFont("Segoe UI", 22))
        self._lbl_icono.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_icono.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self._lbl_icono)

        # Nombre corto
        nombre = TransitionType.DISPLAY_NAMES.get(self.transition_type, self.transition_type)
        # Acortar si es muy largo
        if len(nombre) > 14:
            nombre = nombre[:12] + ".."
        self._lbl_nombre = QLabel(nombre)
        self._lbl_nombre.setFont(QFont("Segoe UI", 8))
        self._lbl_nombre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_nombre.setStyleSheet("background: transparent; border: none; color: #ADB5BD;")
        layout.addWidget(self._lbl_nombre)

    def _actualizar_estilo(self, hover: bool):
        if hover:
            self.setStyleSheet("""
                TransitionCard {
                    background-color: #3B4148;
                    border: 2px solid #00BC8C;
                    border-radius: 6px;
                }
            """)
        else:
            self.setStyleSheet("""
                TransitionCard {
                    background-color: #2B3035;
                    border: 1px solid #495057;
                    border-radius: 6px;
                }
            """)

    def enterEvent(self, event):
        self._hover = True
        self._actualizar_estilo(True)
        self._anim_progress = 0.0
        self._timer_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self._actualizar_estilo(False)
        self._timer_anim.stop()
        self._anim_progress = 0.0
        self._lbl_icono.setStyleSheet("background: transparent; border: none;")
        super().leaveEvent(event)

    def _tick_anim(self):
        """Animacion de preview al hacer hover."""
        self._anim_progress += 0.05
        if self._anim_progress > 1.0:
            self._anim_progress = 0.0

        # Simular efecto visual con cambio de color del icono
        r = int(200 + 55 * self._anim_progress)
        g = int(200 - 100 * self._anim_progress)
        b = int(200 + 55 * (1.0 - self._anim_progress))
        self._lbl_icono.setStyleSheet(
            f"background: transparent; border: none; color: rgb({min(r,255)},{min(g,255)},{min(b,255)});"
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.transition_type)
            # Iniciar drag
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(f"transition:{self.transition_type}")
            drag.setMimeData(mime)
            # Crear pixmap de arrastre
            pixmap = QPixmap(80, 40)
            pixmap.fill(QColor("#2B3035"))
            painter = QPainter(pixmap)
            painter.setPen(QPen(QColor("#00BC8C"), 1))
            painter.drawRect(0, 0, 79, 39)
            painter.setPen(QPen(QColor("#DEE2E6")))
            painter.setFont(QFont("Segoe UI", 9))
            nombre = TransitionType.DISPLAY_NAMES.get(self.transition_type, "")
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter,
                             nombre[:15] if len(nombre) > 15 else nombre)
            painter.end()
            drag.setPixmap(pixmap)
            drag.exec(Qt.DropAction.CopyAction)

        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
#  TransitionsPanel -- Panel principal de transiciones
# ---------------------------------------------------------------------------
class TransitionsPanel(QWidget):
    """
    Panel de biblioteca de transiciones.
    Muestra una grid de tarjetas de transiciones con filtrado por categoria.
    """

    # Senales
    transition_selected = pyqtSignal(str)       # transition_type
    transition_applied = pyqtSignal(str, float)  # transition_type, duration

    def __init__(self, profile_manager: Optional[ProfileManager] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._pm = profile_manager
        self._duracion = 1.0
        self._categoria_actual = "Todas"
        self._tarjetas: List[TransitionCard] = []

        self._construir_ui()
        self._poblar_grid()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # -- Header --
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #2B3035;
                border-bottom: 2px solid #9B59B6;
                padding: 4px;
            }
        """)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(4)

        titulo = QLabel("\u25A6  Transiciones")
        titulo.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        header_layout.addWidget(titulo)

        # Filtro y duracion
        filtro_layout = QHBoxLayout()
        filtro_layout.setSpacing(4)

        filtro_layout.addWidget(QLabel("Categoria:"))
        self._combo_cat = QComboBox()
        self._combo_cat.addItems(list(CATEGORIAS.keys()))
        self._combo_cat.setStyleSheet("""
            QComboBox {
                background-color: #3B4148; color: #DEE2E6;
                border: 1px solid #495057; border-radius: 3px;
                padding: 2px 4px; font-size: 11px;
            }
        """)
        self._combo_cat.currentTextChanged.connect(self._on_cat_changed)
        filtro_layout.addWidget(self._combo_cat)

        filtro_layout.addStretch()

        filtro_layout.addWidget(QLabel("Duracion:"))
        self._spin_dur = QDoubleSpinBox()
        self._spin_dur.setRange(0.1, 10.0)
        self._spin_dur.setValue(1.0)
        self._spin_dur.setSingleStep(0.1)
        self._spin_dur.setSuffix("s")
        self._spin_dur.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #3B4148; color: #DEE2E6;
                border: 1px solid #495057; border-radius: 3px;
                padding: 2px 4px; font-size: 11px;
                max-width: 70px;
            }
        """)
        self._spin_dur.valueChanged.connect(lambda v: setattr(self, '_duracion', v))
        filtro_layout.addWidget(self._spin_dur)

        header_layout.addLayout(filtro_layout)
        layout.addWidget(header)

        # -- Grid de transiciones (scrolleable) --
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("QScrollArea { background-color: #212529; border: none; }")

        self._grid_widget = QWidget()
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setContentsMargins(8, 8, 8, 8)
        self._grid_layout.setSpacing(6)
        self._scroll.setWidget(self._grid_widget)

        layout.addWidget(self._scroll)

    def _poblar_grid(self):
        """Puebla la grid con las transiciones de la categoria actual."""
        # Limpiar grid
        for card in self._tarjetas:
            card.deleteLater()
        self._tarjetas.clear()
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Obtener tipos segun categoria
        tipos = CATEGORIAS.get(self._categoria_actual, TransitionType.ALL_TYPES)

        col = 0
        fila = 0
        cols_max = 3

        for tipo in tipos:
            card = TransitionCard(tipo)
            card.selected.connect(self._on_transition_selected)
            self._grid_layout.addWidget(card, fila, col)
            self._tarjetas.append(card)

            col += 1
            if col >= cols_max:
                col = 0
                fila += 1

        # Espaciador al final
        self._grid_layout.setRowStretch(fila + 1, 1)

    def _on_cat_changed(self, categoria: str):
        """Cambia la categoria de filtrado."""
        self._categoria_actual = categoria
        self._poblar_grid()

    def _on_transition_selected(self, tipo: str):
        """Cuando se selecciona una transicion."""
        self.transition_selected.emit(tipo)
        self.transition_applied.emit(tipo, self._duracion)
        log.info("Transicion seleccionada: %s (dur=%.1fs)",
                 TransitionType.DISPLAY_NAMES.get(tipo, tipo), self._duracion)

    # -- API publica -----------------------------------------------------------
    def get_duracion(self) -> float:
        return self._duracion

    def set_duracion(self, dur: float):
        self._duracion = dur
        self._spin_dur.setValue(dur)

    def es_visible_segun_perfil(self) -> bool:
        """Verifica si el panel debe ser visible segun el perfil activo."""
        if self._pm is None:
            return True
        return self._pm.funcion_habilitada("transiciones")

    def crear_transicion(self, tipo: str) -> Transition:
        """Crea un objeto Transition con el tipo y duracion configurados."""
        return Transition(transition_type=tipo, duration=self._duracion)
