# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- Timeline Visual interactivo.

Implementa un timeline multi-track completo usando QGraphicsView/QGraphicsScene:
  - Multiples tracks (video, audio, efectos, subtitulos) con colores diferenciados
  - Drag & drop de clips desde media library
  - Reordenamiento de clips con snap/magnetismo
  - Zoom temporal (horizontal) y vertical
  - Scrubber/playhead sincronizado con preview
  - Seleccion multiple de clips
  - Menu contextual (cortar, copiar, pegar, eliminar, propiedades)
  - Integracion con core/timeline.py (Timeline, Track)
  - Integracion con CommandManager para Undo/Redo
  - Respeta limites de pistas segun ProfileManager
  - Indicadores visuales de transiciones
"""

from __future__ import annotations

import os
import sys
import logging
import numpy as np
from typing import Optional, Dict, List, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsLineItem,
    QGraphicsTextItem, QGraphicsItem, QMenu, QFrame, QSizePolicy,
    QToolButton, QSplitter, QScrollBar, QGraphicsProxyWidget
)
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, QSizeF, pyqtSignal, QMimeData, QTimer
)
from PyQt6.QtGui import (
    QColor, QBrush, QPen, QFont, QPainter, QPainterPath, QDrag, QCursor,
    QAction, QWheelEvent, QMouseEvent, QKeyEvent
)

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _RAIZ) if _RAIZ not in sys.path else None

from core.timeline import Timeline, Track
from core.video_clip import VideoClip
from core.commands import (
    CommandManager, MoveClipCommand, RemoveClipCommand,
    SplitClipCommand, AddClipCommand, ChangePropertyCommand
)
from core.profiles import ProfileManager
from gui.qt6.base import ICONOS_UNICODE

log = logging.getLogger("soundvi.qt6.timeline")

# -- Constantes visuales ---------------------------------------------------
HEADER_WIDTH = 120        # Ancho del header de track (px)
TRACK_HEIGHT = 60         # Altura por defecto de cada track (px)
RULER_HEIGHT = 24         # Altura de la regla temporal (px)
PLAYHEAD_COLOR = "#E74C3C"
SNAP_LINE_COLOR = "#F39C12"
SELECTION_COLOR = "#375A7F"

# Colores de tracks por tipo
TRACK_COLORS: Dict[str, str] = {
    "video":    "#3498db",
    "audio":    "#2ecc71",
    "subtitle": "#e67e22",
    "effect":   "#9b59b6",
}

TRACK_BG_COLORS: Dict[str, str] = {
    "video":    "#1a2a3d",
    "audio":    "#1a3d2a",
    "subtitle": "#3d2a1a",
    "effect":   "#2a1a3d",
}


# ---------------------------------------------------------------------------
#  ClipItem -- Elemento grafico que representa un clip en el timeline
# ---------------------------------------------------------------------------
class ClipItem(QGraphicsRectItem):
    """
    Representacion grafica de un VideoClip en el timeline.
    Soporta seleccion, arrastre y redimensionado.
    """

    def __init__(self, clip: VideoClip, track_type: str, pixels_per_second: float,
                 track_y: float, track_height: float):
        super().__init__()
        self.clip = clip
        self.track_type = track_type
        self._pps = pixels_per_second
        self._track_y = track_y
        self._track_height = track_height
        self._drag_start_pos: Optional[QPointF] = None
        self._drag_start_time: float = 0.0
        self._drag_start_duration: float = 0.0
        self._resizing: bool = False
        self._resize_edge: str = ""  # "left" o "right"

        # Configurar interaccion
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Apariencia
        self._color_base = QColor(TRACK_COLORS.get(track_type, "#95a5a6"))
        self._actualizar_geometria()

    def _actualizar_geometria(self):
        """Recalcula posicion y tamano basado en el clip."""
        x = HEADER_WIDTH + self.clip.start_time * self._pps
        w = max(2, self.clip.duration * self._pps)
        h = self._track_height - 4
        self.setRect(0, 0, w, h)
        self.setPos(x, self._track_y + 2)
        self._pintar()

    def _pintar(self):
        """Aplica colores segun estado de seleccion."""
        if self.isSelected():
            color = self._color_base.lighter(140)
            pen = QPen(QColor("#00BC8C"), 2)
        else:
            color = self._color_base
            pen = QPen(QColor(self._color_base.darker(130)), 1)

        # Opacidad del clip
        color.setAlpha(int(self.clip.opacity * 200 + 55))
        self.setBrush(QBrush(color))
        self.setPen(pen)

    def set_pixels_per_second(self, pps: float):
        """Actualiza la escala temporal."""
        self._pps = pps
        self._actualizar_geometria()

    def set_track_y(self, y: float):
        """Actualiza la posicion vertical del track."""
        self._track_y = y
        self._actualizar_geometria()

    def paint(self, painter: QPainter, option, widget=None):
        """Renderizado personalizado del clip."""
        super().paint(painter, option, widget)
        rect = self.rect()

        # Nombre del clip
        if rect.width() > 40:
            painter.setPen(QPen(QColor("#FFFFFF")))
            painter.setFont(QFont("Segoe UI", 8))
            text_rect = rect.adjusted(4, 2, -4, -2)
            nombre = self.clip.name
            if len(nombre) > 20 and rect.width() < 150:
                nombre = nombre[:18] + ".."
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                             nombre)

        # Duracion
        if rect.width() > 80:
            painter.setPen(QPen(QColor("#ADB5BD")))
            painter.setFont(QFont("Consolas", 7))
            dur_text = f"{self.clip.duration:.1f}s"
            painter.drawText(rect.adjusted(4, 0, -4, -2),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
                             dur_text)

        # Indicador de velocidad si != 1.0
        if abs(self.clip.speed - 1.0) > 0.01 and rect.width() > 60:
            painter.setPen(QPen(QColor("#F39C12")))
            painter.setFont(QFont("Consolas", 7))
            painter.drawText(rect.adjusted(0, 0, -4, -2),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                             f"x{self.clip.speed:.1f}")

        # Indicador de deshabilitado
        if not self.clip.enabled:
            painter.setPen(QPen(QColor("#E74C3C"), 2))
            painter.drawLine(rect.topLeft().toPoint(), rect.bottomRight().toPoint())
            
        # Waveform para clips de audio (visualizacion simple)
        if self.clip.source_type == "audio" and rect.width() > 30 and rect.height() > 20:
            painter.save()
            painter.setPen(QPen(QColor("#00BC8C"), 1))
            painter.setBrush(QBrush(QColor("#00BC8C", 80)))
            
            # Dibujar waveform simple (ondas sinusoidales)
            h = rect.height() - 10
            w = rect.width() - 10
            center_y = rect.center().y()
            amplitude = h * 0.3
            
            path = QPainterPath()
            path.moveTo(5, center_y)
            
            # Generar onda simple
            for x in range(5, int(w) + 5, 3):
                rel_x = (x - 5) / w
                # Multiples frecuencias para efecto de waveform
                y1 = amplitude * 0.7 * (0.5 * (1 + np.sin(rel_x * 4 * np.pi)))
                y2 = amplitude * 0.3 * (0.5 * (1 + np.sin(rel_x * 8 * np.pi + 1)))
                y = center_y - (y1 + y2) + amplitude * 0.5
                path.lineTo(x, y)
                
            painter.drawPath(path)
            painter.restore()

    def hoverMoveEvent(self, event):
        """Cambia cursor en bordes para indicar redimensionado."""
        x = event.pos().x()
        if x < 6:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif x > self.rect().width() - 6:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        """Inicio de arrastre o redimensionado."""
        if event.button() == Qt.MouseButton.LeftButton:
            x = event.pos().x()
            if x < 6:
                self._resizing = True
                self._resize_edge = "left"
                self._drag_start_pos = event.scenePos()
                self._drag_start_time = self.clip.start_time
                self._drag_start_duration = self.clip.duration
            elif x > self.rect().width() - 6:
                self._resizing = True
                self._resize_edge = "right"
                self._drag_start_pos = event.scenePos()
                self._drag_start_duration = self.clip.duration
            else:
                self._drag_start_pos = event.scenePos()
                self._drag_start_time = self.clip.start_time
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Arrastre del clip o redimensionado."""
        if self._resizing:
            delta_x = event.scenePos().x() - self._drag_start_pos.x()
            delta_time = delta_x / self._pps
            
            if self._resize_edge == "left":
                new_start = self._drag_start_time + delta_time
                new_duration = self._drag_start_duration - delta_time
                if new_duration >= 0.1 and new_start >= 0.0:
                    self.clip.start_time = new_start
                    self.clip.duration = new_duration
                    # Ajustar trim del clip (comportamiento opcional, permite loop en GIF/audio)
                    if self.clip.source_type not in ["gif", "audio"]:
                        self.clip.trim_start = max(0.0, self.clip.trim_start + delta_time)
                    self._actualizar_geometria()
                    
            elif self._resize_edge == "right":
                new_duration = self._drag_start_duration + delta_time
                if new_duration >= 0.1:
                    self.clip.duration = new_duration
                    self._actualizar_geometria()
                    
        elif self._drag_start_pos is not None:
            # Mover clip horizontalmente
            delta_x = event.scenePos().x() - self._drag_start_pos.x()
            delta_time = delta_x / self._pps
            new_start = max(0.0, self._drag_start_time + delta_time)
            self.clip.start_time = new_start
            self._actualizar_geometria()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Fin de arrastre o redimensionado."""
        self._resizing = False
        self._resize_edge = ""
        self._drag_start_pos = None
        self._pintar()
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        """Actualiza apariencia al cambiar seleccion."""
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            QTimer.singleShot(0, self._pintar)
        return super().itemChange(change, value)


# ---------------------------------------------------------------------------
#  PlayheadItem -- Linea vertical del cabezal de reproduccion
# ---------------------------------------------------------------------------
class PlayheadItem(QGraphicsLineItem):
    """Linea vertical roja que indica la posicion de reproduccion."""

    def __init__(self, height: float):
        super().__init__()
        self._height = height
        self.setPen(QPen(QColor(PLAYHEAD_COLOR), 2))
        self.setZValue(1000)  # Siempre encima
        self.setLine(0, 0, 0, height)

    def set_position(self, x: float):
        self.setPos(x, 0)

    def set_height(self, h: float):
        self._height = h
        self.setLine(0, 0, 0, h)


# ---------------------------------------------------------------------------
#  TrackHeaderWidget -- Header lateral de cada track
# ---------------------------------------------------------------------------
class TrackHeaderWidget(QFrame):
    """Widget lateral que muestra nombre, tipo e iconos de control del track."""

    mute_toggled = pyqtSignal(str, bool)   # track_id, muted
    solo_toggled = pyqtSignal(str, bool)   # track_id, solo
    lock_toggled = pyqtSignal(str, bool)   # track_id, locked
    delete_requested = pyqtSignal(str)     # track_id

    def __init__(self, track: Track, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.track = track
        self.setFixedWidth(HEADER_WIDTH)
        self.setFixedHeight(TRACK_HEIGHT)
        color = TRACK_BG_COLORS.get(track.track_type, "#2B3035")
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-right: 2px solid {TRACK_COLORS.get(track.track_type, '#495057')};
                border-bottom: 1px solid #343A40;
            }}
        """)
        self._construir_ui()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(1)

        # Nombre del track
        nombre = QLabel(self.track.name)
        nombre.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        nombre.setStyleSheet(f"color: {TRACK_COLORS.get(self.track.track_type, '#DEE2E6')};")
        layout.addWidget(nombre)

        # Controles (M S L)
        controles = QHBoxLayout()
        controles.setSpacing(2)

        estilo_btn = """
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: 1px solid #495057;
                border-radius: 2px;
                font-size: 8px;
                font-weight: bold;
                padding: 1px;
                min-width: 18px;
                max-width: 18px;
                min-height: 16px;
                max-height: 16px;
            }}
            QPushButton:hover {{ border-color: #00BC8C; }}
        """

        # Mute
        self._btn_mute = QPushButton("M")
        self._btn_mute.setToolTip("Silenciar pista")
        self._btn_mute.setCheckable(True)
        self._btn_mute.setChecked(self.track.muted)
        self._actualizar_btn_mute()
        self._btn_mute.clicked.connect(self._on_mute)
        controles.addWidget(self._btn_mute)

        # Solo
        self._btn_solo = QPushButton("S")
        self._btn_solo.setToolTip("Solo esta pista")
        self._btn_solo.setCheckable(True)
        self._btn_solo.setChecked(self.track.solo)
        self._actualizar_btn_solo()
        self._btn_solo.clicked.connect(self._on_solo)
        controles.addWidget(self._btn_solo)

        # Lock
        self._btn_lock = QPushButton("L")
        self._btn_lock.setToolTip("Bloquear pista")
        self._btn_lock.setCheckable(True)
        self._btn_lock.setChecked(self.track.locked)
        self._actualizar_btn_lock()
        self._btn_lock.clicked.connect(self._on_lock)
        controles.addWidget(self._btn_lock)

        controles.addStretch()
        layout.addLayout(controles)

    def _actualizar_btn_mute(self):
        bg = "#E74C3C" if self.track.muted else "#3B4148"
        fg = "#FFFFFF" if self.track.muted else "#ADB5BD"
        self._btn_mute.setStyleSheet(
            f"QPushButton {{ background-color: {bg}; color: {fg}; "
            f"border: 1px solid #495057; border-radius: 2px; font-size: 8px; "
            f"font-weight: bold; min-width: 18px; max-width: 18px; "
            f"min-height: 16px; max-height: 16px; }}"
            f"QPushButton:hover {{ border-color: #00BC8C; }}"
        )

    def _actualizar_btn_solo(self):
        bg = "#F39C12" if self.track.solo else "#3B4148"
        fg = "#FFFFFF" if self.track.solo else "#ADB5BD"
        self._btn_solo.setStyleSheet(
            f"QPushButton {{ background-color: {bg}; color: {fg}; "
            f"border: 1px solid #495057; border-radius: 2px; font-size: 8px; "
            f"font-weight: bold; min-width: 18px; max-width: 18px; "
            f"min-height: 16px; max-height: 16px; }}"
            f"QPushButton:hover {{ border-color: #00BC8C; }}"
        )

    def _actualizar_btn_lock(self):
        bg = "#3498DB" if self.track.locked else "#3B4148"
        fg = "#FFFFFF" if self.track.locked else "#ADB5BD"
        self._btn_lock.setStyleSheet(
            f"QPushButton {{ background-color: {bg}; color: {fg}; "
            f"border: 1px solid #495057; border-radius: 2px; font-size: 8px; "
            f"font-weight: bold; min-width: 18px; max-width: 18px; "
            f"min-height: 16px; max-height: 16px; }}"
            f"QPushButton:hover {{ border-color: #00BC8C; }}"
        )

    def _on_mute(self):
        self.track.muted = self._btn_mute.isChecked()
        self._actualizar_btn_mute()
        self.mute_toggled.emit(self.track.track_id, self.track.muted)

    def _on_solo(self):
        self.track.solo = self._btn_solo.isChecked()
        self._actualizar_btn_solo()
        self.solo_toggled.emit(self.track.track_id, self.track.solo)

    def _on_lock(self):
        self.track.locked = self._btn_lock.isChecked()
        self._actualizar_btn_lock()
        self.lock_toggled.emit(self.track.track_id, self.track.locked)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #2B3035; color: #DEE2E6; border: 1px solid #495057; padding: 4px; }
            QMenu::item:selected { background-color: #E74C3C; }
        """)
        action = menu.addAction(f"{ICONOS_UNICODE.get('trash', 'X')} Eliminar pista")
        action.triggered.connect(lambda: self.delete_requested.emit(self.track.track_id))
        menu.exec(event.globalPos())


# ---------------------------------------------------------------------------
#  TimelineScene -- Escena del timeline con clips y tracks
# ---------------------------------------------------------------------------
class TimelineScene(QGraphicsScene):
    """Escena personalizada que gestiona la disposicion de tracks y clips."""

    clip_selected = pyqtSignal(object)     # VideoClip o None
    clip_moved = pyqtSignal(str, float)    # clip_id, new_start_time
    playhead_moved = pyqtSignal(float)     # tiempo en segundos

    def __init__(self, parent=None):
        super().__init__(parent)
        self._clip_items: Dict[str, ClipItem] = {}  # clip_id -> ClipItem
        self._playhead: Optional[PlayheadItem] = None
        self._snap_line: Optional[QGraphicsLineItem] = None
        self._pps: float = 100.0  # pixeles por segundo
        self._total_height: float = 0.0

    def crear_playhead(self, height: float):
        """Crea el indicador de playhead."""
        self._playhead = PlayheadItem(height)
        self.addItem(self._playhead)

    def actualizar_playhead(self, tiempo: float):
        """Mueve el playhead a la posicion temporal indicada."""
        if self._playhead:
            x = HEADER_WIDTH + tiempo * self._pps
            self._playhead.set_position(x)

    def get_clip_item(self, clip_id: str) -> Optional[ClipItem]:
        return self._clip_items.get(clip_id)

    def registrar_clip_item(self, clip_id: str, item: ClipItem):
        self._clip_items[clip_id] = item

    def eliminar_clip_item(self, clip_id: str):
        item = self._clip_items.pop(clip_id, None)
        if item:
            self.removeItem(item)

    def get_selected_clips(self) -> List[VideoClip]:
        """Retorna los clips actualmente seleccionados."""
        clips = []
        for item in self.selectedItems():
            if isinstance(item, ClipItem):
                clips.append(item.clip)
        return clips

    def mousePressEvent(self, event):
        """Click en area vacia mueve el playhead."""
        pos = event.scenePos()
        # Si no hay item bajo el cursor, mover playhead
        item = self.itemAt(pos, self.views()[0].transform() if self.views() else __import__('PyQt6.QtGui', fromlist=['QTransform']).QTransform())
        if item is None and pos.x() > HEADER_WIDTH:
            tiempo = (pos.x() - HEADER_WIDTH) / self._pps
            self.playhead_moved.emit(max(0.0, tiempo))
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
#  TimelineView -- Vista principal del timeline
# ---------------------------------------------------------------------------
class TimelineView(QGraphicsView):
    """Vista con soporte para zoom con rueda y scroll horizontal."""

    zoom_changed = pyqtSignal(float)  # nuevo nivel de zoom (pps)
    files_dropped = pyqtSignal(list, QPointF) # List of paths, scene pos

    def __init__(self, scene: TimelineScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setStyleSheet("""
            QGraphicsView {
                background-color: #1a1d21;
                border: none;
            }
        """)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
            if urls:
                pos = self.mapToScene(event.position().toPoint())
                self.files_dropped.emit(urls, pos)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        """Zoom horizontal con Ctrl+Rueda, scroll normal sin Ctrl."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            factor = 1.15 if delta > 0 else 1.0 / 1.15
            scene = self.scene()
            if isinstance(scene, TimelineScene):
                new_pps = max(10.0, min(1000.0, scene._pps * factor))
                scene._pps = new_pps
                self.zoom_changed.emit(new_pps)
        else:
            super().wheelEvent(event)


# ---------------------------------------------------------------------------
#  TimelineWidget -- Widget principal del timeline
# ---------------------------------------------------------------------------
class TimelineWidget(QWidget):
    """
    Widget principal del timeline que integra:
      - Regla temporal
      - Headers de tracks
      - Area de clips (QGraphicsView/Scene)
      - Controles de zoom y navegacion
      - Integracion con core/timeline.py y CommandManager
    """

    # Senales publicas
    clip_selected = pyqtSignal(object)         # VideoClip o None
    playhead_changed = pyqtSignal(float)       # tiempo en segundos
    clips_changed = pyqtSignal()               # cuando cambia algun clip
    track_changed = pyqtSignal(object)         # Track modificado

    def __init__(self, timeline: Optional[Timeline] = None,
                 command_manager: Optional[CommandManager] = None,
                 profile_manager: Optional[ProfileManager] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._timeline = timeline or Timeline()
        self._cmd = command_manager or CommandManager()
        self._pm = profile_manager
        self._pps: float = 100.0  # pixeles por segundo
        self._track_headers: List[TrackHeaderWidget] = []
        self._clipboard: List[VideoClip] = []

        self._construir_ui()
        self._refrescar_completo()

    def _construir_ui(self):
        """Construye la interfaz del timeline."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # -- Barra de herramientas del timeline --
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(4, 2, 4, 2)
        toolbar.setSpacing(4)

        lbl = QLabel(f"{ICONOS_UNICODE.get('layers', '')}  Timeline")
        lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        toolbar.addWidget(lbl)

        toolbar.addStretch()

        # Boton agregar track
        self._btn_add_track = QPushButton(f"+ Pista")
        self._btn_add_track.setToolTip("Agregar nueva pista")
        self._btn_add_track.setFixedHeight(24)
        self._btn_add_track.setStyleSheet("""
            QPushButton {
                background-color: #343A40; color: #DEE2E6;
                border: 1px solid #495057; border-radius: 3px;
                padding: 2px 8px; font-size: 11px;
            }
            QPushButton:hover { border-color: #00BC8C; }
        """)
        self._btn_add_track.clicked.connect(self._menu_agregar_track)
        toolbar.addWidget(self._btn_add_track)

        # Snap toggle
        self._btn_snap = QPushButton("Snap")
        self._btn_snap.setToolTip("Activar/desactivar snap")
        self._btn_snap.setCheckable(True)
        self._btn_snap.setChecked(self._timeline.snap_enabled)
        self._btn_snap.setFixedHeight(24)
        self._btn_snap.setStyleSheet("""
            QPushButton {
                background-color: #343A40; color: #DEE2E6;
                border: 1px solid #495057; border-radius: 3px;
                padding: 2px 8px; font-size: 11px;
            }
            QPushButton:checked { background-color: #00BC8C; color: #FFFFFF; }
            QPushButton:hover { border-color: #00BC8C; }
        """)
        self._btn_snap.clicked.connect(self._toggle_snap)
        toolbar.addWidget(self._btn_snap)

        # Zoom
        btn_zoom_out = QPushButton(ICONOS_UNICODE["zoom_out"])
        btn_zoom_out.setFixedSize(24, 24)
        btn_zoom_out.setToolTip("Alejar")
        btn_zoom_out.setStyleSheet("QPushButton { background-color: #343A40; border: 1px solid #495057; border-radius: 3px; } QPushButton:hover { border-color: #00BC8C; }")
        btn_zoom_out.clicked.connect(self._zoom_out)
        toolbar.addWidget(btn_zoom_out)

        self._lbl_zoom = QLabel("100%")
        self._lbl_zoom.setFont(QFont("Consolas", 9))
        self._lbl_zoom.setMinimumWidth(40)
        self._lbl_zoom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toolbar.addWidget(self._lbl_zoom)

        btn_zoom_in = QPushButton(ICONOS_UNICODE["zoom_in"])
        btn_zoom_in.setFixedSize(24, 24)
        btn_zoom_in.setToolTip("Acercar")
        btn_zoom_in.setStyleSheet("QPushButton { background-color: #343A40; border: 1px solid #495057; border-radius: 3px; } QPushButton:hover { border-color: #00BC8C; }")
        btn_zoom_in.clicked.connect(self._zoom_in)
        toolbar.addWidget(btn_zoom_in)

        btn_zoom_fit = QPushButton("\u2922")
        btn_zoom_fit.setFixedSize(24, 24)
        btn_zoom_fit.setToolTip("Ajustar al ancho")
        btn_zoom_fit.setStyleSheet("QPushButton { background-color: #343A40; border: 1px solid #495057; border-radius: 3px; } QPushButton:hover { border-color: #00BC8C; }")
        btn_zoom_fit.clicked.connect(self._zoom_fit)
        toolbar.addWidget(btn_zoom_fit)

        layout.addLayout(toolbar)

        # -- Area principal: headers + escena --
        area = QHBoxLayout()
        area.setContentsMargins(0, 0, 0, 0)
        area.setSpacing(0)

        # Columna de headers de tracks
        self._headers_container = QWidget()
        self._headers_layout = QVBoxLayout(self._headers_container)
        self._headers_layout.setContentsMargins(0, RULER_HEIGHT, 0, 0)
        self._headers_layout.setSpacing(0)
        self._headers_container.setFixedWidth(HEADER_WIDTH)
        self._headers_container.setStyleSheet("background-color: #212529;")
        area.addWidget(self._headers_container)

        # Vista grafica (escena)
        self._scene = TimelineScene()
        self._view = TimelineView(self._scene)
        self._view.setMinimumHeight(100)
        area.addWidget(self._view)

        # Conectar senales de la escena
        self._scene.clip_selected.connect(self.clip_selected.emit)
        self._scene.playhead_moved.connect(self._on_playhead_scene_click)
        self._view.zoom_changed.connect(self._on_zoom_changed)
        self._view.files_dropped.connect(self._on_files_dropped)

        layout.addLayout(area)

    # -- Gestion de tracks -----------------------------------------------------
    def _refrescar_completo(self):
        """Reconstruye toda la representacion visual del timeline."""
        # Limpiar escena
        self._scene.clear()
        self._scene._clip_items.clear()

        # Limpiar headers
        for h in self._track_headers:
            h.deleteLater()
        self._track_headers.clear()
        while self._headers_layout.count():
            item = self._headers_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._pps = self._timeline.zoom_level * 100.0
        if self._pps < 10:
            self._pps = 100.0
        self._scene._pps = self._pps

        y = RULER_HEIGHT
        total_h = RULER_HEIGHT

        # Dibujar regla temporal
        self._dibujar_regla()

        # Dibujar tracks y clips
        for track in self._timeline.tracks:
            # Fondo del track
            color_bg = TRACK_BG_COLORS.get(track.track_type, "#2B3035")
            track_bg = QGraphicsRectItem()
            width_total = max(3000, (self._timeline.duration + 30) * self._pps + HEADER_WIDTH)
            track_bg.setRect(HEADER_WIDTH, y, width_total, TRACK_HEIGHT)
            track_bg.setBrush(QBrush(QColor(color_bg)))
            track_bg.setPen(QPen(QColor("#343A40"), 0.5))
            track_bg.setZValue(-10)
            self._scene.addItem(track_bg)

            # Header del track
            header = TrackHeaderWidget(track)
            header.mute_toggled.connect(lambda tid, m: self.track_changed.emit(
                next((t for t in self._timeline.tracks if t.track_id == tid), None)))
            header.solo_toggled.connect(lambda tid, s: self.track_changed.emit(
                next((t for t in self._timeline.tracks if t.track_id == tid), None)))
            header.lock_toggled.connect(lambda tid, l: self.track_changed.emit(
                next((t for t in self._timeline.tracks if t.track_id == tid), None)))
            header.delete_requested.connect(self._eliminar_track)
            self._headers_layout.addWidget(header)
            self._track_headers.append(header)

            # Clips del track
            for clip in track.clips:
                clip_item = ClipItem(clip, track.track_type, self._pps, y, TRACK_HEIGHT)
                self._scene.addItem(clip_item)
                self._scene.registrar_clip_item(clip.clip_id, clip_item)

            y += TRACK_HEIGHT
            total_h += TRACK_HEIGHT

        self._headers_layout.addStretch()

        # Playhead
        self._scene.crear_playhead(total_h)
        self._scene.actualizar_playhead(self._timeline.playhead)

        # Ajustar escena
        self._scene.setSceneRect(0, 0, max(3000, (self._timeline.duration + 30) * self._pps + HEADER_WIDTH), total_h + 20)
        self._scene._total_height = total_h

        self._actualizar_lbl_zoom()

    def _dibujar_regla(self):
        """Dibuja la regla temporal en la parte superior."""
        # Fondo de regla
        width_total = max(3000, (self._timeline.duration + 30) * self._pps + HEADER_WIDTH)
        ruler_bg = QGraphicsRectItem(HEADER_WIDTH, 0, width_total, RULER_HEIGHT)
        ruler_bg.setBrush(QBrush(QColor("#2B3035")))
        ruler_bg.setPen(QPen(Qt.PenStyle.NoPen))
        ruler_bg.setZValue(-5)
        self._scene.addItem(ruler_bg)

        # Marcas de tiempo
        # Calcular intervalo segun zoom
        if self._pps > 200:
            intervalo = 1.0
        elif self._pps > 50:
            intervalo = 5.0
        elif self._pps > 20:
            intervalo = 10.0
        else:
            intervalo = 30.0

        duracion = max(30.0, self._timeline.duration + 10)
        t = 0.0
        while t <= duracion:
            x = HEADER_WIDTH + t * self._pps
            # Linea de marca
            line = QGraphicsLineItem(x, RULER_HEIGHT - 8, x, RULER_HEIGHT)
            line.setPen(QPen(QColor("#6C757D"), 1))
            self._scene.addItem(line)

            # Texto de tiempo
            minutos = int(t // 60)
            segundos = int(t % 60)
            texto = QGraphicsTextItem(f"{minutos}:{segundos:02d}")
            texto.setFont(QFont("Consolas", 7))
            texto.setDefaultTextColor(QColor("#ADB5BD"))
            texto.setPos(x - 12, 0)
            self._scene.addItem(texto)

            t += intervalo

    # -- Zoom ------------------------------------------------------------------
    def _zoom_in(self):
        self._pps = min(1000.0, self._pps * 1.3)
        self._aplicar_zoom()

    def _zoom_out(self):
        self._pps = max(10.0, self._pps / 1.3)
        self._aplicar_zoom()

    def _zoom_fit(self):
        if self._timeline.duration > 0:
            ancho_disponible = self._view.viewport().width() - HEADER_WIDTH
            self._pps = max(10.0, ancho_disponible / self._timeline.duration)
        self._aplicar_zoom()

    def _on_zoom_changed(self, pps: float):
        self._pps = pps
        self._aplicar_zoom()

    def _aplicar_zoom(self):
        self._timeline.zoom_level = self._pps / 100.0
        self._scene._pps = self._pps
        self._refrescar_completo()

    def _actualizar_lbl_zoom(self):
        porcentaje = int(self._pps)
        self._lbl_zoom.setText(f"{porcentaje}%")

    # -- Snap ------------------------------------------------------------------
    def _toggle_snap(self):
        self._timeline.snap_enabled = self._btn_snap.isChecked()

    # -- Agregar track ---------------------------------------------------------
    def _menu_agregar_track(self):
        """Muestra menu para seleccionar tipo de track a agregar."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2B3035; color: #DEE2E6;
                border: 1px solid #495057; padding: 4px;
            }
            QMenu::item:selected { background-color: #375A7F; }
        """)

        # Verificar limites de perfil
        for tipo, nombre in [("video", "Video"), ("audio", "Audio"),
                             ("subtitle", "Subtitulos"), ("effect", "Efectos")]:
            accion = menu.addAction(f"Pista de {nombre}")
            accion.triggered.connect(lambda checked, t=tipo: self._agregar_track(t))

            # Deshabilitar si se alcanzo el limite
            if self._pm:
                perfil = self._pm.perfil_activo
                if perfil:
                    count = len(self._timeline.get_tracks_by_type(tipo))
                    if tipo == "audio" and perfil.max_pistas_audio >= 0 and count >= perfil.max_pistas_audio:
                        accion.setEnabled(False)
                        accion.setText(f"Pista de {nombre} (limite alcanzado)")
                    elif tipo == "video" and perfil.max_capas_video >= 0 and count >= perfil.max_capas_video:
                        accion.setEnabled(False)
                        accion.setText(f"Pista de {nombre} (limite alcanzado)")

        menu.exec(QCursor.pos())

    def _agregar_track(self, tipo: str):
        """Agrega un nuevo track al timeline."""
        self._timeline.add_track(tipo)
        self._refrescar_completo()
        self.clips_changed.emit()

    def _eliminar_track(self, track_id: str):
        """Elimina un track por su ID."""
        if self._timeline.remove_track(track_id):
            self._refrescar_completo()
            self.clips_changed.emit()

    def _on_files_dropped(self, urls: List[str], pos: QPointF):
        """Maneja el evento de drop de archivos en la escena."""
        if not urls:
            return
            
        y = pos.y() - RULER_HEIGHT
        if y < 0: return
        track_index = int(y / TRACK_HEIGHT)
        if track_index < 0 or track_index >= len(self._timeline.tracks):
            return

        x = pos.x() - HEADER_WIDTH
        if x < 0: x = 0
        tiempo = x / self._pps

        from core.video_clip import detect_source_type
        
        for url in urls:
            clip = VideoClip(
                source_path=url,
                source_type=detect_source_type(url),
                track_index=track_index,
                start_time=tiempo,
                duration=0.0, # se autocalcula en VideoClip
                name=os.path.basename(url)
            )
            self.agregar_clip(clip, track_index)
            # asume duracion para el proximo offset si es 0 (imagenes por defecto es 5.0)
            tiempo += max(1.0, clip.duration)

    # -- Gestion de clips ------------------------------------------------------
    def agregar_clip(self, clip: VideoClip, track_index: int = 0):
        """Agrega un clip al timeline via CommandManager."""
        cmd = AddClipCommand(self._timeline, clip, track_index)
        self._cmd.execute(cmd)
        self._refrescar_completo()
        
        # Auto-adaptar zoom si la duracion excede lo visible (acercarse/alejarse)
        if self._timeline.duration > 0:
            ancho_disponible = self._view.viewport().width() - HEADER_WIDTH
            duracion_visible = ancho_disponible / self._pps if self._pps > 0 else 0
            # Si el clip nuevo hace que la duracion sea mayor al area visible o muy pequena
            if self._timeline.duration > duracion_visible or duracion_visible > self._timeline.duration * 2:
                self._zoom_fit()
                
        self.clips_changed.emit()

    def eliminar_clip_seleccionado(self):
        """Elimina los clips seleccionados."""
        clips = self._scene.get_selected_clips()
        for clip in clips:
            cmd = RemoveClipCommand(self._timeline, clip.clip_id)
            self._cmd.execute(cmd)
        self._refrescar_completo()
        self.clips_changed.emit()

    def dividir_clip_en_playhead(self):
        """Divide el clip seleccionado en la posicion del playhead."""
        clips = self._scene.get_selected_clips()
        if clips:
            clip = clips[0]
            cmd = SplitClipCommand(self._timeline, clip.clip_id, self._timeline.playhead)
            self._cmd.execute(cmd)
            self._refrescar_completo()
            self.clips_changed.emit()

    def copiar_seleccion(self):
        """Copia los clips seleccionados al clipboard interno."""
        self._clipboard = list(self._scene.get_selected_clips())

    def pegar_clips(self):
        """Pega clips del clipboard en la posicion del playhead."""
        for clip_orig in self._clipboard:
            nuevo = VideoClip(
                source_path=clip_orig.source_path,
                source_type=clip_orig.source_type,
                track_index=clip_orig.track_index,
                start_time=self._timeline.playhead,
                duration=clip_orig.duration,
                name=f"{clip_orig.name} (copia)"
            )
            nuevo.opacity = clip_orig.opacity
            nuevo.volume = clip_orig.volume
            nuevo.speed = clip_orig.speed
            cmd = AddClipCommand(self._timeline, nuevo, clip_orig.track_index)
            self._cmd.execute(cmd)
        if self._clipboard:
            self._refrescar_completo()
            self.clips_changed.emit()

    # -- Playhead --------------------------------------------------------------
    def set_playhead(self, tiempo: float):
        """Establece la posicion del playhead."""
        self._timeline.set_playhead(tiempo)
        self._scene.actualizar_playhead(tiempo)

    def _on_playhead_scene_click(self, tiempo: float):
        """Callback cuando se hace click en la escena para mover playhead."""
        self._timeline.set_playhead(tiempo)
        self._scene.actualizar_playhead(tiempo)
        self.playhead_changed.emit(tiempo)

    # -- Menu contextual -------------------------------------------------------
    def contextMenuEvent(self, event):
        """Menu contextual del timeline."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2B3035; color: #DEE2E6;
                border: 1px solid #495057; padding: 4px;
            }
            QMenu::item:selected { background-color: #375A7F; }
        """)

        clips_sel = self._scene.get_selected_clips()

        if clips_sel:
            menu.addAction(f"{ICONOS_UNICODE['cut']} Dividir en playhead",
                           self.dividir_clip_en_playhead)
            menu.addAction(f"{ICONOS_UNICODE['copy']} Copiar", self.copiar_seleccion)
            menu.addAction(f"{ICONOS_UNICODE['trash']} Eliminar",
                           self.eliminar_clip_seleccionado)
            menu.addSeparator()
            menu.addAction("Propiedades...", lambda: self.clip_selected.emit(clips_sel[0]))
        else:
            menu.addAction(f"{ICONOS_UNICODE['paste']} Pegar", self.pegar_clips)
            menu.addSeparator()
            for tipo, nombre in [("video", "Video"), ("audio", "Audio"),
                                 ("subtitle", "Subtitulos"), ("effect", "Efectos")]:
                menu.addAction(f"Agregar pista de {nombre}",
                               lambda t=tipo: self._agregar_track(t))

        menu.exec(event.globalPos())

    # -- Atajos de teclado -----------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent):
        """Manejo de atajos de teclado del timeline."""
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            self.eliminar_clip_seleccionado()
        elif event.key() == Qt.Key.Key_S and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.dividir_clip_en_playhead()
        elif event.key() == Qt.Key.Key_C and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.copiar_seleccion()
        elif event.key() == Qt.Key.Key_V and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.pegar_clips()
        elif event.key() == Qt.Key.Key_Right:
            self._timeline.goto_next_clip_edge()
            self._scene.actualizar_playhead(self._timeline.playhead)
            self.playhead_changed.emit(self._timeline.playhead)
        elif event.key() == Qt.Key.Key_Left:
            self._timeline.goto_prev_clip_edge()
            self._scene.actualizar_playhead(self._timeline.playhead)
            self.playhead_changed.emit(self._timeline.playhead)
        else:
            super().keyPressEvent(event)

    # -- API publica -----------------------------------------------------------
    @property
    def timeline(self) -> Timeline:
        return self._timeline

    def set_timeline(self, timeline: Timeline):
        """Reemplaza el timeline actual."""
        self._timeline = timeline
        self._refrescar_completo()

    def refrescar(self):
        """Refresca la visualizacion completa."""
        self._refrescar_completo()

    def get_selected_clips(self) -> List[VideoClip]:
        """Retorna los clips seleccionados."""
        return self._scene.get_selected_clips()
