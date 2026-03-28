from __future__ import annotations
from PyQt6.QtGui import QFont, QColor
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
from core.logger import get_logger
logger = get_logger(__name__)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF, QUrl, QTimer
from PyQt6.QtGui import (
    QColor, QBrush, QPen, QFont, QPainter, QPainterPath, QDrag, QCursor,
    QAction, QWheelEvent, QMouseEvent, QKeyEvent
)

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _RAIZ) if _RAIZ not in sys.path else None

from core.timeline import Timeline, Track, ModuleTimelineItem
from core.video_clip import VideoClip
from core.transitions import TransitionType
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
            painter.setBrush(QBrush(QColor(0, 188, 140, 80)))
            
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
                
                # Aplicar snap a guías de alineación si está activo
                new_start = self._apply_alignment_snap(new_start, event.scenePos().x(), check_end=False)
                # Recalcular duración basada en el nuevo inicio
                new_duration = self._drag_start_duration - (new_start - self._drag_start_time)
                
                if new_duration >= 0.1 and new_start >= 0.0:
                    self.clip.start_time = new_start
                    self.clip.duration = new_duration
                    # Ajustar trim del clip (comportamiento opcional, permite loop en GIF/audio)
                    if self.clip.source_type not in ["gif", "audio"]:
                        self.clip.trim_start = max(0.0, self.clip.trim_start + (new_start - self._drag_start_time))
                    self._actualizar_geometria()
                    
            elif self._resize_edge == "right":
                new_duration = self._drag_start_duration + delta_time
                
                # Para el borde derecho, podemos snap el final del clip
                # Calcular posición X del final del clip
                clip_end_x = HEADER_WIDTH + (self.clip.start_time + new_duration) * self._pps
                # Aplicar snap basado en la posición del mouse (que está en el borde derecho)
                snapped_end_x = self._apply_alignment_snap_edge(clip_end_x, event.scenePos().x())
                # Convertir de vuelta a duración
                if snapped_end_x != clip_end_x:
                    new_duration = (snapped_end_x - HEADER_WIDTH) / self._pps - self.clip.start_time
                
                if new_duration >= 0.1:
                    self.clip.duration = new_duration
                    self._actualizar_geometria()
                    
        elif self._drag_start_pos is not None:
            # Mover clip horizontalmente
            delta_x = event.scenePos().x() - self._drag_start_pos.x()
            delta_time = delta_x / self._pps
            new_start = max(0.0, self._drag_start_time + delta_time)
            
            # Aplicar snap a guías de alineación si está activo
            new_start = self._apply_alignment_snap(new_start, event.scenePos().x(), check_end=True)
            
            self.clip.start_time = new_start
            self._actualizar_geometria()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._resizing = False
        self._drag_start_pos = None
        if hasattr(self.scene(), 'update_snap_line'):
            self.scene().update_snap_line(None)
        super().mouseReleaseEvent(event)
    
    def _get_snap_times(self, timeline_widget) -> list:
        """Obtiene todos los puntos de tiempo a los que se puede hacer snap."""
        snap_times = [0.0]
        
        if hasattr(timeline_widget, '_timeline') and timeline_widget._timeline:
            snap_times.append(timeline_widget._timeline.playhead)
            for track in timeline_widget._timeline.tracks:
                for c in track.clips:
                    if c.clip_id != self.clip.clip_id:
                        snap_times.append(c.start_time)
                        snap_times.append(c.end_time)
        return snap_times

    def _apply_alignment_snap(self, proposed_start: float, mouse_x: float, check_end: bool = True) -> float:
        """
        Aplica magnetismo (snap) a otros clips, playhead y guías.
        """
        scene = self.scene()
        if not scene: return proposed_start
        view = scene.views()[0] if scene.views() else None
        timeline_widget = view.parent() if view else None
        if not timeline_widget: return proposed_start
        
        snap_active = False
        if hasattr(timeline_widget, '_timeline') and timeline_widget._timeline.snap_enabled:
            snap_active = True
        elif hasattr(timeline_widget, '_btn_alignment') and timeline_widget._btn_alignment.isChecked():
            snap_active = True
            
        if not snap_active:
            if hasattr(scene, 'update_snap_line'): scene.update_snap_line(None)
            return proposed_start
            
        SNAP_THRESHOLD_PX = 8
        threshold_time = SNAP_THRESHOLD_PX / self._pps
        
        best_start = proposed_start
        min_dist = threshold_time
        snapped_time_point = None
        
        snap_times = self._get_snap_times(timeline_widget)
        proposed_end = proposed_start + self.clip.duration
        
        for t in snap_times:
            dist_start = abs(proposed_start - t)
            if dist_start < min_dist:
                min_dist = dist_start
                best_start = t
                snapped_time_point = t
                
            if check_end:
                dist_end = abs(proposed_end - t)
                if dist_end < min_dist:
                    min_dist = dist_end
                    best_start = t - self.clip.duration
                    snapped_time_point = t
                    
        if hasattr(timeline_widget, '_alignment_guides') and hasattr(timeline_widget, '_btn_alignment') and timeline_widget._btn_alignment.isChecked():
            prop_x_start = HEADER_WIDTH + proposed_start * self._pps
            prop_x_end = HEADER_WIDTH + proposed_end * self._pps
            for guide in timeline_widget._alignment_guides[:9]:
                if guide.isVisible():
                    guide_x = guide.line().x1()
                    dist_start_px = abs(prop_x_start - guide_x)
                    if dist_start_px < SNAP_THRESHOLD_PX and (dist_start_px / self._pps) < min_dist:
                        min_dist = dist_start_px / self._pps
                        best_start = (guide_x - HEADER_WIDTH) / self._pps
                        snapped_time_point = best_start
                        
                    if check_end:
                        dist_end_px = abs(prop_x_end - guide_x)
                        if dist_end_px < SNAP_THRESHOLD_PX and (dist_end_px / self._pps) < min_dist:
                            min_dist = dist_end_px / self._pps
                            best_start = ((guide_x - HEADER_WIDTH) / self._pps) - self.clip.duration
                            snapped_time_point = (guide_x - HEADER_WIDTH) / self._pps
                            
        if snapped_time_point is not None and hasattr(scene, 'update_snap_line'):
            scene.update_snap_line(HEADER_WIDTH + snapped_time_point * self._pps)
        elif hasattr(scene, 'update_snap_line'):
            scene.update_snap_line(None)
            
        return max(0.0, best_start)
    
    def _apply_alignment_snap_edge(self, proposed_x: float, mouse_x: float) -> float:
        """
        Aplica snap para el borde derecho del clip durante el redimensionado.
        """
        scene = self.scene()
        if not scene: return proposed_x
        view = scene.views()[0] if scene.views() else None
        timeline_widget = view.parent() if view else None
        if not timeline_widget: return proposed_x
        
        snap_active = False
        if hasattr(timeline_widget, '_timeline') and timeline_widget._timeline.snap_enabled:
            snap_active = True
        elif hasattr(timeline_widget, '_btn_alignment') and timeline_widget._btn_alignment.isChecked():
            snap_active = True
            
        if not snap_active:
            if hasattr(scene, 'update_snap_line'): scene.update_snap_line(None)
            return proposed_x
            
        SNAP_THRESHOLD_PX = 8
        threshold_time = SNAP_THRESHOLD_PX / self._pps
        
        proposed_end_time = (proposed_x - HEADER_WIDTH) / self._pps
        best_end_time = proposed_end_time
        min_dist = threshold_time
        snapped_time_point = None
        
        snap_times = self._get_snap_times(timeline_widget)
        
        for t in snap_times:
            dist = abs(proposed_end_time - t)
            if dist < min_dist:
                min_dist = dist
                best_end_time = t
                snapped_time_point = t
                
        if hasattr(timeline_widget, '_alignment_guides') and hasattr(timeline_widget, '_btn_alignment') and timeline_widget._btn_alignment.isChecked():
            for guide in timeline_widget._alignment_guides[:9]:
                if guide.isVisible():
                    guide_x = guide.line().x1()
                    dist_px = abs(proposed_x - guide_x)
                    if dist_px < SNAP_THRESHOLD_PX and (dist_px / self._pps) < min_dist:
                        min_dist = dist_px / self._pps
                        best_end_time = (guide_x - HEADER_WIDTH) / self._pps
                        snapped_time_point = best_end_time
                        
        if snapped_time_point is not None and hasattr(scene, 'update_snap_line'):
            scene.update_snap_line(HEADER_WIDTH + snapped_time_point * self._pps)
        elif hasattr(scene, 'update_snap_line'):
            scene.update_snap_line(None)
            
        return HEADER_WIDTH + best_end_time * self._pps

# ---------------------------------------------------------------------------
#  TransitionIndicatorItem -- Indicador visual de transición en un clip
# ---------------------------------------------------------------------------
class TransitionIndicatorItem(QGraphicsRectItem):
    """
    Indicador visual de una transición aplicada a un clip.
    Muestra un triángulo/gradiente en el inicio o fin del clip.
    """

    # Colores por tipo de transición
    TRANSITION_COLORS = {
        'fade_in': "#3498DB",
        'fade_out': "#E74C3C",
        'crossfade': "#2ECC71",
        'dissolve': "#9B59B6",
        'fade': "#F39C12",
    }

    def __init__(self, clip_item: 'ClipItem', position: str, transition_data: dict,
                 pps: float, track_height: float):
        """
        Args:
            clip_item: ClipItem padre
            position: 'in' para inicio, 'out' para final
            transition_data: Dict con {type, duration, ...}
            pps: Pixels por segundo
            track_height: Altura del track
        """
        super().__init__()
        self._clip_item = clip_item
        self._position = position
        self._data = transition_data
        self._pps = pps
        self._track_height = track_height

        trans_type = transition_data.get('type', 'fade_in')
        trans_dur = transition_data.get('duration', 1.0)

        # Calcular dimensiones
        w = max(4, trans_dur * pps)
        h = track_height - 8

        color_hex = self.TRANSITION_COLORS.get(trans_type, "#F39C12")
        color = QColor(color_hex)
        color.setAlpha(120)

        self.setRect(0, 0, w, h)
        self.setBrush(QBrush(color))
        self.setPen(QPen(QColor(color_hex), 1.5))
        self.setZValue(50)
        self.setToolTip(
            f"{'Entrada' if position == 'in' else 'Salida'}: "
            f"{TransitionType.DISPLAY_NAMES.get(trans_type, trans_type)} "
            f"({trans_dur:.1f}s)"
        )

    def paint(self, painter: QPainter, option, widget=None):
        """Renderiza el indicador con un gradiente triangular."""
        rect = self.rect()
        w, h = rect.width(), rect.height()

        trans_type = self._data.get('type', 'fade_in')
        color_hex = self.TRANSITION_COLORS.get(trans_type, "#F39C12")
        color = QColor(color_hex)

        # Dibujar gradiente diagonal para indicar la dirección del fade
        path = QPainterPath()
        if self._position == 'in':
            # Triángulo que crece de izq a derecha (fade in)
            path.moveTo(0, h)
            path.lineTo(w, 0)
            path.lineTo(w, h)
            path.closeSubpath()
        else:
            # Triángulo que decrece de izq a derecha (fade out)
            path.moveTo(0, 0)
            path.lineTo(0, h)
            path.lineTo(w, h)
            path.closeSubpath()

        color.setAlpha(100)
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(QColor(color_hex), 1))
        painter.drawPath(path)

        # Icono tipo texto
        if w > 20:
            painter.setPen(QPen(QColor("#FFFFFF")))
            painter.setFont(QFont("Consolas", 7))
            label = "▶" if self._position == 'in' else "◀"
            painter.drawText(rect.adjusted(2, 2, -2, -2),
                             Qt.AlignmentFlag.AlignCenter, label)


# ---------------------------------------------------------------------------
#  ModuleTimelineGraphicsItem -- Módulo posicionado en el timeline
# ---------------------------------------------------------------------------
class ModuleTimelineGraphicsItem(QGraphicsRectItem):
    """
    Representación gráfica de un ModuleTimelineItem en el timeline.
    Muestra módulos/efectos con duración y posición en el tiempo.
    """

    # Colores por categoría de módulo
    MODULE_COLORS = {
        'video': "#9B59B6",
        'audio': "#1ABC9C",
        'text': "#E67E22",
        'utility': "#3498DB",
        'export': "#95A5A6",
        'effect': "#E74C3C",
    }

    def __init__(self, module_item: ModuleTimelineItem, pps: float,
                 track_y: float, track_height: float):
        super().__init__()
        self.module_item = module_item
        self._pps = pps
        self._track_y = track_y
        self._track_height = track_height
        self._drag_start_pos = None
        self._drag_start_time = 0.0
        self._resizing = False
        self._resize_edge = ""

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Determinar color basado en tipo de módulo
        mod_type = module_item.module_type.split("/")[0] if "/" in module_item.module_type else "effect"
        self._color_base = QColor(module_item.color or self.MODULE_COLORS.get(mod_type, "#9B59B6"))

        self._actualizar_geometria()

    def _actualizar_geometria(self):
        x = HEADER_WIDTH + self.module_item.start_time * self._pps
        w = max(8, self.module_item.duration * self._pps)
        h = self._track_height - 8
        self.setRect(0, 0, w, h)
        self.setPos(x, self._track_y + 4)
        self._pintar()

    def _pintar(self):
        if self.isSelected():
            color = self._color_base.lighter(140)
            pen = QPen(QColor("#00BC8C"), 2)
        else:
            color = self._color_base
            pen = QPen(QColor(self._color_base.darker(130)), 1)

        if not self.module_item.enabled:
            color.setAlpha(80)
        else:
            color.setAlpha(180)

        self.setBrush(QBrush(color))
        self.setPen(pen)

    def paint(self, painter: QPainter, option, widget=None):
        super().paint(painter, option, widget)
        rect = self.rect()

        # Patrón de rayas diagonales para diferenciar de clips
        painter.save()
        painter.setClipRect(rect)
        pen_stripe = QPen(QColor(255, 255, 255, 30), 1)
        painter.setPen(pen_stripe)
        step = 8
        for i in range(0, int(rect.width() + rect.height()), step):
            painter.drawLine(
                int(rect.x() + i), int(rect.y()),
                int(rect.x() + i - rect.height()), int(rect.y() + rect.height())
            )
        painter.restore()

        # Nombre del módulo
        if rect.width() > 30:
            painter.setPen(QPen(QColor("#FFFFFF")))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            text = self.module_item.name
            if len(text) > 18 and rect.width() < 140:
                text = text[:16] + ".."
            painter.drawText(rect.adjusted(4, 2, -4, -2),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                             f"⚡ {text}")

        # Duración
        if rect.width() > 60:
            painter.setPen(QPen(QColor("#ADB5BD")))
            painter.setFont(QFont("Consolas", 7))
            painter.drawText(rect.adjusted(4, 0, -4, -2),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
                             f"{self.module_item.duration:.1f}s")

        # Indicador deshabilitado
        if not self.module_item.enabled:
            painter.setPen(QPen(QColor("#E74C3C"), 2))
            painter.drawLine(rect.topLeft().toPoint(), rect.bottomRight().toPoint())

    def hoverMoveEvent(self, event):
        x = event.pos().x()
        if x < 6 or x > self.rect().width() - 6:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        # Verificación de seguridad: asegurar que module_item existe
        if not hasattr(self, 'module_item') or self.module_item is None:
            super().mousePressEvent(event)
            return
            
        if event.button() == Qt.MouseButton.LeftButton:
            x = event.pos().x()
            if x < 6:
                self._resizing = True
                self._resize_edge = "left"
                self._drag_start_pos = event.scenePos()
                self._drag_start_time = self.module_item.start_time
                self._drag_start_duration = self.module_item.duration
            elif x > self.rect().width() - 6:
                self._resizing = True
                self._resize_edge = "right"
                self._drag_start_pos = event.scenePos()
                self._drag_start_duration = self.module_item.duration
            else:
                self._drag_start_pos = event.scenePos()
                self._drag_start_time = self.module_item.start_time
        super().mousePressEvent(event)

    def _get_snap_times(self, timeline_widget) -> list:
        """Obtiene todos los puntos de tiempo a los que se puede hacer snap."""
        snap_times = [0.0]
        
        # Verificación de seguridad
        if not hasattr(self, 'module_item') or self.module_item is None:
            return snap_times
            
        if hasattr(timeline_widget, '_timeline') and timeline_widget._timeline:
            snap_times.append(timeline_widget._timeline.playhead)
            for track in timeline_widget._timeline.tracks:
                for c in track.clips:
                    snap_times.append(c.start_time)
                    snap_times.append(c.end_time)
            # Snap a otros módulos
            for m in timeline_widget._timeline.module_items:
                if m.item_id != self.module_item.item_id:
                    snap_times.append(m.start_time)
                    snap_times.append(m.start_time + m.duration)
        return snap_times

    def _apply_alignment_snap(self, proposed_start: float, mouse_x: float, check_end: bool = True) -> float:
        """Aplica magnetismo (snap) a otros clips, módulos, playhead y guías."""
        scene = self.scene()
        if not scene:
            return proposed_start
        view = scene.views()[0] if scene.views() else None
        timeline_widget = view.parent() if view else None
        if not timeline_widget:
            return proposed_start

        snap_active = False
        if hasattr(timeline_widget, '_timeline') and timeline_widget._timeline.snap_enabled:
            snap_active = True
        elif hasattr(timeline_widget, '_btn_alignment') and timeline_widget._btn_alignment.isChecked():
            snap_active = True

        if not snap_active:
            if hasattr(scene, 'update_snap_line'):
                scene.update_snap_line(None)
            return proposed_start

        SNAP_THRESHOLD_PX = 8
        threshold_time = SNAP_THRESHOLD_PX / self._pps

        best_start = proposed_start
        min_dist = threshold_time
        snapped_time_point = None

        snap_times = self._get_snap_times(timeline_widget)
        proposed_end = proposed_start + self.module_item.duration

        for t in snap_times:
            dist_start = abs(proposed_start - t)
            if dist_start < min_dist:
                min_dist = dist_start
                best_start = t
                snapped_time_point = t

            if check_end:
                dist_end = abs(proposed_end - t)
                if dist_end < min_dist:
                    min_dist = dist_end
                    best_start = t - self.module_item.duration
                    snapped_time_point = t

        # Snap a guías de alineación
        if hasattr(timeline_widget, '_alignment_guides') and hasattr(timeline_widget, '_btn_alignment') and timeline_widget._btn_alignment.isChecked():
            prop_x_start = HEADER_WIDTH + proposed_start * self._pps
            prop_x_end = HEADER_WIDTH + proposed_end * self._pps
            for guide in timeline_widget._alignment_guides[:9]:
                if guide.isVisible():
                    guide_x = guide.line().x1()
                    dist_start_px = abs(prop_x_start - guide_x)
                    if dist_start_px < SNAP_THRESHOLD_PX and (dist_start_px / self._pps) < min_dist:
                        min_dist = dist_start_px / self._pps
                        best_start = (guide_x - HEADER_WIDTH) / self._pps
                        snapped_time_point = best_start
                    if check_end:
                        dist_end_px = abs(prop_x_end - guide_x)
                        if dist_end_px < SNAP_THRESHOLD_PX and (dist_end_px / self._pps) < min_dist:
                            min_dist = dist_end_px / self._pps
                            best_start = ((guide_x - HEADER_WIDTH) / self._pps) - self.module_item.duration
                            snapped_time_point = (guide_x - HEADER_WIDTH) / self._pps

        if snapped_time_point is not None and hasattr(scene, 'update_snap_line'):
            scene.update_snap_line(HEADER_WIDTH + snapped_time_point * self._pps)
        elif hasattr(scene, 'update_snap_line'):
            scene.update_snap_line(None)

        return max(0.0, best_start)

    def _apply_alignment_snap_edge(self, proposed_x: float, mouse_x: float) -> float:
        """Aplica snap para el borde derecho del módulo durante el redimensionado."""
        scene = self.scene()
        if not scene:
            return proposed_x
        view = scene.views()[0] if scene.views() else None
        timeline_widget = view.parent() if view else None
        if not timeline_widget:
            return proposed_x

        snap_active = False
        if hasattr(timeline_widget, '_timeline') and timeline_widget._timeline.snap_enabled:
            snap_active = True
        elif hasattr(timeline_widget, '_btn_alignment') and timeline_widget._btn_alignment.isChecked():
            snap_active = True

        if not snap_active:
            if hasattr(scene, 'update_snap_line'):
                scene.update_snap_line(None)
            return proposed_x

        SNAP_THRESHOLD_PX = 8
        proposed_end_time = (proposed_x - HEADER_WIDTH) / self._pps
        best_end_time = proposed_end_time
        min_dist = SNAP_THRESHOLD_PX / self._pps
        snapped_time_point = None

        snap_times = self._get_snap_times(timeline_widget)
        for t in snap_times:
            dist = abs(proposed_end_time - t)
            if dist < min_dist:
                min_dist = dist
                best_end_time = t
                snapped_time_point = t

        # Snap a guías de alineación
        if hasattr(timeline_widget, '_alignment_guides') and hasattr(timeline_widget, '_btn_alignment') and timeline_widget._btn_alignment.isChecked():
            for guide in timeline_widget._alignment_guides[:9]:
                if guide.isVisible():
                    guide_x = guide.line().x1()
                    dist_px = abs(proposed_x - guide_x)
                    if dist_px < SNAP_THRESHOLD_PX and (dist_px / self._pps) < min_dist:
                        min_dist = dist_px / self._pps
                        best_end_time = (guide_x - HEADER_WIDTH) / self._pps
                        snapped_time_point = best_end_time

        if snapped_time_point is not None and hasattr(scene, 'update_snap_line'):
            scene.update_snap_line(HEADER_WIDTH + snapped_time_point * self._pps)
        elif hasattr(scene, 'update_snap_line'):
            scene.update_snap_line(None)

        return HEADER_WIDTH + best_end_time * self._pps

    def mouseMoveEvent(self, event):
        # Verificación de seguridad
        if not hasattr(self, 'module_item') or self.module_item is None:
            super().mouseMoveEvent(event)
            return
            
        if self._resizing and self._drag_start_pos:
            delta_x = event.scenePos().x() - self._drag_start_pos.x()
            delta_time = delta_x / self._pps
            if self._resize_edge == "left":
                new_start = self._drag_start_time + delta_time
                new_dur = self._drag_start_duration - delta_time

                # Aplicar snap al borde izquierdo
                new_start = self._apply_alignment_snap(new_start, event.scenePos().x(), check_end=False)
                new_dur = self._drag_start_duration - (new_start - self._drag_start_time)

                if new_dur >= 0.1 and new_start >= 0.0:
                    self.module_item.start_time = new_start
                    self.module_item.duration = new_dur
                    self._actualizar_geometria()
            elif self._resize_edge == "right":
                new_dur = self._drag_start_duration + delta_time

                # Aplicar snap al borde derecho
                mod_end_x = HEADER_WIDTH + (self.module_item.start_time + new_dur) * self._pps
                snapped_end_x = self._apply_alignment_snap_edge(mod_end_x, event.scenePos().x())
                if snapped_end_x != mod_end_x:
                    new_dur = (snapped_end_x - HEADER_WIDTH) / self._pps - self.module_item.start_time

                if new_dur >= 0.1:
                    self.module_item.duration = new_dur
                    self._actualizar_geometria()
        elif self._drag_start_pos is not None:
            delta_x = event.scenePos().x() - self._drag_start_pos.x()
            delta_time = delta_x / self._pps
            new_start = max(0, self._drag_start_time + delta_time)

            # Aplicar snap a clips, módulos, playhead y guías
            new_start = self._apply_alignment_snap(new_start, event.scenePos().x(), check_end=True)

            self.module_item.start_time = new_start
            self._actualizar_geometria()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        # Verificación de seguridad
        if not hasattr(self, 'module_item') or self.module_item is None:
            super().mouseReleaseEvent(event)
            return
            
        self._resizing = False
        self._drag_start_pos = None
        if hasattr(self.scene(), 'update_snap_line'):
            self.scene().update_snap_line(None)
        super().mouseReleaseEvent(event)

    def set_pixels_per_second(self, pps: float):
        self._pps = pps
        self._actualizar_geometria()


class PlayheadItem(QGraphicsItem):
    """Línea roja con un cabezal arriba que indica la posición y es fácil de arrastrar."""

    def __init__(self, height: float):
        super().__init__()
        self._height = height
        self.setZValue(1000)  # Siempre encima
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self._dragging = False

    def set_position(self, x: float):
        self.setPos(x, 0)

    def set_height(self, h: float):
        self._height = h
        self.prepareGeometryChange()

    def boundingRect(self):
        # 20px de ancho total (-10 a 10) para fácil arrastre
        return QRectF(-10, 0, 20, self._height)

    def paint(self, painter, option, widget=None):
        # Dibujar línea fina vertical
        painter.setPen(QPen(QColor(PLAYHEAD_COLOR), 2))
        painter.drawLine(0, 0, 0, int(self._height))

        # Dibujar cabezal (triángulo/bandera superior)
        path = QPainterPath()
        path.moveTo(-8, 0)
        path.lineTo(8, 0)
        path.lineTo(8, 12)
        path.lineTo(0, 20)
        path.lineTo(-8, 12)
        path.closeSubpath()

        painter.setBrush(QBrush(QColor(PLAYHEAD_COLOR)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if hasattr(self, '_dragging') and self._dragging:
            scene = self.scene()
            if scene and hasattr(scene, '_pps'):
                new_x = event.scenePos().x()
                tiempo = max(0.0, (new_x - HEADER_WIDTH) / scene._pps)
                if hasattr(scene, 'playhead_moved'):
                    scene.playhead_moved.emit(tiempo)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and hasattr(self, '_dragging') and self._dragging:
            self._dragging = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def hoverEnterEvent(self, event):
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverLeaveEvent(event)


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
        # Altura será ajustada dinámicamente por el padre
        self.setMinimumHeight(40)
        self.setMaximumHeight(80)
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

        # Icono según tipo de track (caracteres Unicode)
        tipo_iconos = {
            'video': '🎥',  # Cámara de video (U+1F3A5)
            'audio': '♪',   # Nota musical (U+266A)
            'subtitle': '📄', # Documento (U+1F4C4)
            'effect': '★'   # Estrella negra (U+2605)
        }
        icono = tipo_iconos.get(self.track.track_type, '📁')
        
        # Nombre del track con icono
        nombre_texto = f"{icono} {self.track.name}"
        nombre = QLabel(nombre_texto)
        nombre.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        nombre.setStyleSheet(f"color: {TRACK_COLORS.get(self.track.track_type, '#DEE2E6')};")
        
        # Tooltip con información del tipo de track
        if hasattr(self.track, 'get_track_type_description'):
            descripcion = self.track.get_track_type_description()
            nombre.setToolTip(f"{descripcion}\n\nTipos permitidos: {', '.join(self.track.get_allowed_clip_types() or ['módulos'])}")
        else:
            nombre.setToolTip(f"Track de {self.track.track_type}")
        
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
    module_selected = pyqtSignal(object)   # ModuleTimelineItem o None
    clip_moved = pyqtSignal(str, float)    # clip_id, new_start_time
    playhead_moved = pyqtSignal(float)     # tiempo en segundos

    def __init__(self, parent=None):
        super().__init__(parent)
        self._clip_items: Dict[str, ClipItem] = {}  # clip_id -> ClipItem
        self._playhead: Optional[PlayheadItem] = None
        self._snap_line: Optional[QGraphicsLineItem] = None
        self._pps: float = 100.0  # pixeles por segundo
        self._total_height: float = 0.0
        self._track_height: float = TRACK_HEIGHT  # Altura dinámica de tracks

        # Detectar cambios de selección para emitir señales de módulo/clip
        self.selectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self):
        """Detecta qué tipo de item fue seleccionado y emite la señal apropiada."""
        selected = self.selectedItems()
        if not selected:
            return
        item = selected[0]
        
        # Emitir señales de forma asíncrona para evitar crashes 
        # si la escena se refresca mientras procesa eventos del ratón
        from PyQt6.QtCore import QTimer
        if isinstance(item, ModuleTimelineGraphicsItem):
            QTimer.singleShot(0, lambda: self.module_selected.emit(item.module_item))
        elif isinstance(item, ClipItem):
            QTimer.singleShot(0, lambda: self.clip_selected.emit(item.clip))

    def update_snap_line(self, x: float = None, height: float = 0.0):
        """Muestra o oculta la linea indicadora de snap magnetico."""
        if not self._snap_line:
            from PyQt6.QtGui import QPen, QColor
            from PyQt6.QtCore import Qt
            self._snap_line = QGraphicsLineItem()
            self._snap_line.setPen(QPen(QColor("#3498DB"), 2, Qt.PenStyle.DashLine))
            self._snap_line.setZValue(999)
            self.addItem(self._snap_line)
        try:
            # Verificacion simple nativa en Python/Qt para evitar module sip no encontrado
            if x is not None:
                h = height if height > 0 else (self.sceneRect().height() if self.sceneRect().height() > 0 else 1000)
                self._snap_line.setLine(x, 0, x, h)
                self._snap_line.setVisible(True)
            else:
                self._snap_line.setVisible(False)
        except RuntimeError:
            self._snap_line = None
            if x is not None:
                self.update_snap_line(x, height)

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

    def get_selected_modules(self) -> List[ModuleTimelineItem]:
        """Retorna los módulos actualmente seleccionados."""
        modules = []
        for item in self.selectedItems():
            if isinstance(item, ModuleTimelineGraphicsItem):
                modules.append(item.module_item)
        return modules

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
    transition_dropped = pyqtSignal(str, QPointF) # transition_type, scene pos
    module_dropped = pyqtSignal(str, QPointF)  # module_type, scene pos

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
        mime = event.mimeData()
        if (mime.hasUrls() or 
            (mime.hasText() and mime.text().startswith("transition:")) or
            (mime.hasText() and mime.text().startswith("module:"))):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        mime = event.mimeData()
        if (mime.hasUrls() or 
            (mime.hasText() and mime.text().startswith("transition:")) or
            (mime.hasText() and mime.text().startswith("module:"))):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls():
            urls = [url.toLocalFile() for url in mime.urls() if url.isLocalFile()]
            if urls:
                pos = self.mapToScene(event.position().toPoint())
                self.files_dropped.emit(urls, pos)
            event.acceptProposedAction()
        elif mime.hasText() and mime.text().startswith("transition:"):
            trans_type = mime.text().split(":", 1)[1]
            pos = self.mapToScene(event.position().toPoint())
            self.transition_dropped.emit(trans_type, pos)
            event.acceptProposedAction()
        elif mime.hasText() and mime.text().startswith("module:"):
            mod_type = mime.text().split(":", 1)[1]
            pos = self.mapToScene(event.position().toPoint())
            self.module_dropped.emit(mod_type, pos)
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
                # Rango de zoom ampliado: 1px por segundo hasta 5000px por segundo
                new_pps = max(1.0, min(5000.0, scene._pps * factor))
                scene._pps = new_pps
                self.zoom_changed.emit(new_pps)
                
                # Ajustar viewport para mantener el punto bajo el cursor
                if delta != 0:
                    self._zoom_around_cursor(event.position(), factor)
        else:
            super().wheelEvent(event)
    
    def _zoom_around_cursor(self, cursor_pos: QPointF, factor: float):
        """
        Ajusta el viewport para hacer zoom centrado en el cursor.
        
        Args:
            cursor_pos: Posición del cursor en coordenadas de vista
            factor: Factor de zoom (ej: 1.15 para acercar, 0.87 para alejar)
        """
        # Obtener posición actual del viewport
        old_center = self.mapToScene(self.viewport().rect().center())
        
        # Calcular nueva transformación
        self.scale(factor, 1.0)
        
        # Ajustar para mantener el punto bajo el cursor en la misma posición
        new_center = self.mapToScene(self.viewport().rect().center())
        delta = new_center - old_center
        self.translate(delta.x(), 0)


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
    module_selected = pyqtSignal(object)       # ModuleTimelineItem o None
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
        self._clipboard: List[VideoClip] = []
        
        # Configuración de editor de video profesional
        # Timeline es el elemento principal, debe expandirse
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(150)  # Altura mínima reducida para dar espacio al inspector y preview
        self.setMinimumWidth(800)   # Ancho mínimo para timeline extenso

        self._construir_ui()
        self._refrescar_completo()
        
        # Scrollbars en esquina superior izquierda al inicio
        QTimer.singleShot(200, self._scrollbars_a_esquina_superior_izquierda)
        
        # Asegurar que el widget sea visible
        log = logging.getLogger("soundvi.qt6.timeline")
        log.info("TimelineWidget inicializado - Altura: %d, Tracks: %d", 
                self.height(), len(self._timeline.tracks))

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
        self._btn_add_track = QPushButton("+ Pista")
        self._btn_add_track.setToolTip("Agregar nueva pista")
        self._btn_add_track.setFixedHeight(24)
        self._btn_add_track.setStyleSheet("""
            QPushButton {
                background-color: #343A40; color: #DEE2E6;
                border: 1px solid #495057; border-radius: 3px;
                padding: 2px 8px; font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { border-color: #00BC8C; }
        """)
        self._btn_add_track.clicked.connect(self._menu_agregar_track)
        toolbar.addWidget(self._btn_add_track)

        # Snap toggle
        self._btn_snap = QPushButton("⇅ Snap")
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

        # Asistente de alineacion
        self._btn_alignment = QPushButton("⧉ Alinear")
        self._btn_alignment.setToolTip("Asistente de alineación - Ayuda a alinear objetos con precisión")
        self._btn_alignment.setCheckable(True)
        self._btn_alignment.setChecked(False)
        self._btn_alignment.setFixedHeight(24)
        self._btn_alignment.setStyleSheet("""
            QPushButton {
                background-color: #343A40; color: #DEE2E6;
                border: 1px solid #495057; border-radius: 3px;
                padding: 2px 8px; font-size: 11px;
            }
            QPushButton:checked { background-color: #F39C12; color: #FFFFFF; }
            QPushButton:hover { border-color: #F39C12; }
        """)
        self._btn_alignment.clicked.connect(self._toggle_alignment_assistant)
        toolbar.addWidget(self._btn_alignment)

        # Zoom
        btn_zoom_out = QPushButton("−")
        btn_zoom_out.setFixedSize(24, 24)
        btn_zoom_out.setToolTip("Alejar")
        btn_zoom_out.setStyleSheet("""
            QPushButton {
                background-color: #343A40; color: #DEE2E6;
                border: 1px solid #495057; border-radius: 3px;
                font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { border-color: #00BC8C; }
        """)
        btn_zoom_out.clicked.connect(self._zoom_out)
        toolbar.addWidget(btn_zoom_out)

        self._lbl_zoom = QLabel("100%")
        self._lbl_zoom.setFont(QFont("Consolas", 9))
        self._lbl_zoom.setMinimumWidth(40)
        self._lbl_zoom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toolbar.addWidget(self._lbl_zoom)

        btn_zoom_in = QPushButton("+")
        btn_zoom_in.setFixedSize(24, 24)
        btn_zoom_in.setToolTip("Acercar")
        btn_zoom_in.setStyleSheet("""
            QPushButton {
                background-color: #343A40; color: #DEE2E6;
                border: 1px solid #495057; border-radius: 3px;
                font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { border-color: #00BC8C; }
        """)
        btn_zoom_in.clicked.connect(self._zoom_in)
        toolbar.addWidget(btn_zoom_in)

        btn_zoom_fit = QPushButton("\u2922")
        btn_zoom_fit.setFixedSize(24, 24)
        btn_zoom_fit.setToolTip("Ajustar timeline completo a ventana")
        btn_zoom_fit.setStyleSheet("""
            QPushButton {
                background-color: #343A40; color: #DEE2E6;
                border: 1px solid #495057; border-radius: 3px;
                font-size: 14px;
            }
            QPushButton:hover { border-color: #00BC8C; }
        """)
        btn_zoom_fit.clicked.connect(self._zoom_fit)
        toolbar.addWidget(btn_zoom_fit)

        btn_zoom_to_selection = QPushButton("🔎")  # Lupa (carácter Unicode)
        btn_zoom_to_selection.setFixedSize(24, 24)
        btn_zoom_to_selection.setToolTip("Zoom a selección (ajustar a clips seleccionados)")
        btn_zoom_to_selection.setStyleSheet("""
            QPushButton {
                background-color: #343A40; color: #DEE2E6;
                border: 1px solid #495057; border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover { border-color: #00BC8C; }
            QPushButton:disabled { color: #6C757D; }
        """)
        btn_zoom_to_selection.clicked.connect(self._zoom_to_selection)
        toolbar.addWidget(btn_zoom_to_selection)

        layout.addLayout(toolbar)

        # -- Area principal: headers + escena --
        area = QHBoxLayout()
        area.setContentsMargins(0, 0, 0, 0)
        area.setSpacing(0)

        # Columna de headers de tracks
        from PyQt6.QtWidgets import QScrollArea
        
        self._headers_container = QWidget()
        self._headers_layout = QVBoxLayout(self._headers_container)
        self._headers_layout.setContentsMargins(0, RULER_HEIGHT, 0, 0)
        self._headers_layout.setSpacing(0)
        
        # Envolver en QScrollArea para poder sincronizar el scroll vertical
        self._headers_scroll = QScrollArea()
        self._headers_scroll.setWidget(self._headers_container)
        self._headers_scroll.setWidgetResizable(True)
        self._headers_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._headers_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._headers_scroll.setFixedWidth(HEADER_WIDTH)
        self._headers_scroll.setStyleSheet("QScrollArea { border: none; background-color: #212529; } QWidget { background-color: #212529; }")
        
        area.addWidget(self._headers_scroll)

        # Vista grafica (escena) - Timeline "infinito"
        self._scene = TimelineScene()
        self._view = TimelineView(self._scene)
        self._view.setMinimumHeight(150)  # Más altura para ver mejor
        self._view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Configurar scroll horizontal infinito
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Área de escena muy grande para timeline "infinito"
        self._scene.setSceneRect(0, 0, 10000 + HEADER_WIDTH, 1000)
        
        area.addWidget(self._view)
        
        # Sincronizar scroll vertical entre headers y la vista de timeline
        self._view.verticalScrollBar().valueChanged.connect(self._headers_scroll.verticalScrollBar().setValue)
        self._headers_scroll.verticalScrollBar().valueChanged.connect(self._view.verticalScrollBar().setValue)
        
        # Scrollbars fijos en esquina superior izquierda - NO centrado automático

        # Conectar senales de la escena
        self._scene.clip_selected.connect(self.clip_selected.emit)
        self._scene.module_selected.connect(self.module_selected.emit)
        self._scene.playhead_moved.connect(self._on_playhead_scene_click)
        self._view.zoom_changed.connect(self._on_zoom_changed)
        self._view.files_dropped.connect(self._on_files_dropped)
        self._view.transition_dropped.connect(self._on_transition_dropped)
        self._view.module_dropped.connect(self._on_module_dropped)

        layout.addLayout(area)

    # -- Gestion de tracks -----------------------------------------------------
    def _refrescar_completo(self):
        """Reconstruye toda la representacion visual del timeline."""
        log = logging.getLogger("soundvi.qt6.timeline")
        log.info("Refrescando timeline - Tracks: %d, Módulos: %d", 
                len(self._timeline.tracks), len(self._timeline.module_items))
        
        # Calcular ancho total necesario para timeline "infinito"
        # Basado en la duración máxima del proyecto
        max_duration = max(30.0, self._timeline.duration + 10.0)  # Mínimo 30s, +10s extra
        total_width_px = HEADER_WIDTH + (max_duration * self._pps)
        
        # Ajustar área de escena para timeline extenso
        total_height_px = RULER_HEIGHT + (len(self._timeline.tracks) * TRACK_HEIGHT) + 100
        self._scene.setSceneRect(0, 0, total_width_px, total_height_px)
        
        log.info("Timeline extenso configurado: %.1fs -> %dpx, altura: %dpx", 
                max_duration, total_width_px, total_height_px)
        
        # Scrollbars fijos en esquina superior izquierda (no centrado automático)
        QTimer.singleShot(100, self._scrollbars_a_esquina_superior_izquierda)
        
        # Guardar estado del asistente de alineación antes de limpiar
        alignment_enabled = False
        if hasattr(self, '_btn_alignment') and self._btn_alignment:
            alignment_enabled = self._btn_alignment.isChecked()
        
        # Limpiar escena pero preservar guías de alineación si están activas
        if hasattr(self, '_alignment_guides') and alignment_enabled:
            # Remover guías temporalmente de la escena
            for guide in self._alignment_guides:
                if guide.scene() == self._scene:
                    self._scene.removeItem(guide)
        
        # Destruir snap_line explicitly para evitar C++ obj deleted errors
        if hasattr(self._scene, '_snap_line') and self._scene._snap_line:
            self._scene._snap_line = None
            
        if hasattr(self._scene, '_playhead') and self._scene._playhead:
            self._scene._playhead = None
            
        self._scene.clear()
        self._scene._clip_items.clear()

        # Restaurar guías si estaban activas
        if hasattr(self, '_alignment_guides') and alignment_enabled:
            for guide in self._alignment_guides:
                self._scene.addItem(guide)
                guide.setVisible(True)

        # Limpiar headers
        for h in getattr(self, '_track_headers', []):
            h.deleteLater()
        self._track_headers = []
        if hasattr(self, '_headers_layout'):
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
        track_height = self._scene._track_height if hasattr(self._scene, '_track_height') else TRACK_HEIGHT
        
        for track in self._timeline.tracks:
            # Fondo del track
            color_bg = TRACK_BG_COLORS.get(track.track_type, "#2B3035")
            track_bg = QGraphicsRectItem()
            width_total = max(3000, (self._timeline.duration + 30) * self._pps + HEADER_WIDTH)
            track_bg.setRect(HEADER_WIDTH, y, width_total, track_height)
            track_bg.setBrush(QBrush(QColor(color_bg)))
            track_bg.setPen(QPen(QColor("#343A40"), 0.5))
            track_bg.setZValue(-10)
            self._scene.addItem(track_bg)
            
            # Header del track (agregado al layout de headers, no en la escena)
            header = TrackHeaderWidget(track)
            header.setFixedHeight(int(track_height))
            header.mute_toggled.connect(lambda tid, m: self.track_changed.emit(
                next((t for t in self._timeline.tracks if t.track_id == tid), None)))
            header.solo_toggled.connect(lambda tid, s: self.track_changed.emit(
                next((t for t in self._timeline.tracks if t.track_id == tid), None)))
            header.lock_toggled.connect(lambda tid, l: self.track_changed.emit(
                next((t for t in self._timeline.tracks if t.track_id == tid), None)))
            header.delete_requested.connect(self._eliminar_track)
            if hasattr(self, '_headers_layout'):
                self._headers_layout.addWidget(header)
            self._track_headers.append(header)

            # Clips del track
            for clip in track.clips:
                clip_item = ClipItem(clip, track.track_type, self._pps, y, track_height)
                clip_item.setPos(HEADER_WIDTH + clip.start_time * self._pps, y)
                self._scene.addItem(clip_item)
                self._scene.registrar_clip_item(clip.clip_id, clip_item)

                # Dibujar indicadores de transición en el clip
                if hasattr(clip, 'transition_in') and clip.transition_in:
                    trans_in = TransitionIndicatorItem(
                        clip_item, 'in', clip.transition_in, self._pps, track_height
                    )
                    trans_in.setPos(clip_item.pos().x(), y + 4)
                    trans_in.setZValue(60)
                    self._scene.addItem(trans_in)

                if hasattr(clip, 'transition_out') and clip.transition_out:
                    trans_dur = clip.transition_out.get('duration', 1.0)
                    trans_out = TransitionIndicatorItem(
                        clip_item, 'out', clip.transition_out, self._pps, track_height
                    )
                    out_x = clip_item.pos().x() + clip_item.rect().width() - max(4, trans_dur * self._pps)
                    trans_out.setPos(out_x, y + 4)
                    trans_out.setZValue(60)
                    self._scene.addItem(trans_out)

            y += track_height
            total_h += track_height
            
        if hasattr(self, '_headers_layout'):
            self._headers_layout.addStretch()

        # Dibujar módulos del timeline en el track de efectos
        effect_track_y = None
        for i, track in enumerate(self._timeline.tracks):
            if track.track_type == 'effect':
                effect_track_y = RULER_HEIGHT + i * track_height
                break
        
        if effect_track_y is None:
            # Si no hay track de efectos, usar la parte inferior
            effect_track_y = y
        
        for mod_item in self._timeline.module_items:
            mod_gfx = ModuleTimelineGraphicsItem(
                mod_item, self._pps, effect_track_y, track_height
            )
            # Posicionar módulo considerando HEADER_WIDTH
            mod_gfx.setPos(HEADER_WIDTH + mod_item.start_time * self._pps, effect_track_y)
            self._scene.addItem(mod_gfx)

        # Headers ahora están en la escena, no en layout separado

        # Playhead
        self._scene.crear_playhead(total_h)
        self._scene.actualizar_playhead(self._timeline.playhead)

        # Ajustar escena - asegurar que sea lo suficientemente grande para todo el contenido
        # Ancho mínimo: 2000px o duración del timeline + margen
        timeline_width = max(2000.0, (self._timeline.duration + 60) * self._pps + HEADER_WIDTH)
        # Alto mínimo: altura total de tracks + margen
        scene_height = max(800.0, total_h + 100)
        
        self._scene.setSceneRect(0, 0, timeline_width, scene_height)
        
        # Igualar la altura del contenedor de headers para que el scroll cuadre exacto
        # Añadimos un margen extra (200px) para evitar que el scroll vertical de los headers se bloquee
        # si la vista principal tiene una barra de scroll horizontal que reduzca su viewport.
        if hasattr(self, '_headers_container'):
            self._headers_container.setFixedHeight(int(scene_height) + 200)

        self._scene._total_height = total_h
        
        # Asegurar que la vista pueda mostrar todo el contenido
        self._view.ensureVisible(0, 0, timeline_width, scene_height)

        self._actualizar_lbl_zoom()
        
        # Actualizar guías de alineación si están activas
        if hasattr(self, '_btn_alignment') and self._btn_alignment.isChecked():
            self._actualizar_guias_alineacion()

    def _dibujar_regla(self):
        """Dibuja la regla temporal en la parte superior."""
        # Fondo de regla - usar el mismo cálculo que en _refrescar_completo
        width_total = max(2000.0, (self._timeline.duration + 60) * self._pps + HEADER_WIDTH)
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
        """Acercar (aumentar píxeles por segundo)."""
        self._pps = min(5000.0, self._pps * 1.3)
        self._aplicar_zoom()

    def _zoom_out(self):
        """Alejar (disminuir píxeles por segundo)."""
        self._pps = max(1.0, self._pps / 1.3)
        self._aplicar_zoom()

    def _zoom_fit(self):
        """Ajustar zoom para que todo el timeline quepa en la vista."""
        if self._timeline.duration > 0:
            ancho_disponible = self._view.viewport().width() - HEADER_WIDTH - 100  # Margen
            if ancho_disponible > 0:
                self._pps = max(1.0, min(5000.0, ancho_disponible / self._timeline.duration))
        self._aplicar_zoom()
    
    def _zoom_to_selection(self):
        """Ajustar zoom para que la selección quepa en la vista."""
        selected_clips = self.get_selected_clips()
        if not selected_clips:
            return
        
        # Calcular rango de la selección
        min_time = min(c.start_time for c in selected_clips)
        max_time = max(c.end_time for c in selected_clips)
        selection_duration = max_time - min_time
        
        if selection_duration > 0:
            ancho_disponible = self._view.viewport().width() - HEADER_WIDTH - 100  # Margen
            if ancho_disponible > 0:
                self._pps = max(1.0, min(5000.0, ancho_disponible / selection_duration))
                self._aplicar_zoom()
                
                # Centrar en la selección
                center_time = (min_time + max_time) / 2
                self._view.centerOn(HEADER_WIDTH + center_time * self._pps, self._view.viewport().height() / 2)

    def _on_zoom_changed(self, pps: float):
        self._pps = pps
        self._aplicar_zoom()

    def _aplicar_zoom(self):
        self._timeline.zoom_level = self._pps / 100.0
        self._scene._pps = self._pps
        self._refrescar_completo()

    def _actualizar_lbl_zoom(self):
        """Actualiza la etiqueta de zoom con información útil."""
        # Calcular porcentaje basado en 100px/segundo como 100%
        base_pps = 100.0
        porcentaje = int((self._pps / base_pps) * 100)
        
        # Mostrar información adicional para zoom extremo
        if self._pps >= 1000:
            zoom_text = f"{porcentaje}% (⏩)"
        elif self._pps <= 5:
            zoom_text = f"{porcentaje}% (⏪)"
        else:
            zoom_text = f"{porcentaje}%"
        
        self._lbl_zoom.setText(zoom_text)
        self._lbl_zoom.setToolTip(f"Zoom: {self._pps:.1f} px/segundo\n"
                                  f"Rango: 1-5000 px/segundo\n"
                                  f"Ctrl+Rueda para ajustar")

    def resizeEvent(self, event):
        """Maneja el cambio de tamaño del widget."""
        super().resizeEvent(event)
        
        # Ajustar altura de tracks basado en el tamaño disponible
        self._ajustar_tamanos_dinamicos()
        
        # Actualizar guías de alineación si están activas
        if hasattr(self, '_btn_alignment') and self._btn_alignment.isChecked():
            self._actualizar_guias_alineacion()
    
    def _scrollbars_a_esquina_superior_izquierda(self):
        """Pone los scrollbars en la esquina superior izquierda (0,0)."""
        self._view.horizontalScrollBar().setValue(0)
        self._view.verticalScrollBar().setValue(0)
        
        log = logging.getLogger("soundvi.qt6.timeline")
        log.debug("Scrollbars posicionados en esquina superior izquierda")
    
    def _centrar_en_contenido(self):
        """(MÉTODO MANTENIDO PARA COMPATIBILIDAD - NO SE USA)
        Centra la vista del timeline en donde hay contenido."""
        # Este método ya no se usa - scrollbars fijos en esquina superior izquierda
        pass
    
    def _centrar_en_tiempo(self, tiempo_segundos: float):
        """Centra la vista del timeline en un tiempo específico."""
        # Calcular posición X (considerando HEADER_WIDTH)
        target_x = HEADER_WIDTH + (tiempo_segundos * self._pps)
        
        # Obtener el viewport
        viewport = self._view.viewport()
        viewport_width = viewport.width()
        
        # Ajustar scroll para centrar en el tiempo
        scroll_x = target_x - (viewport_width / 2)
        scroll_x = max(0, scroll_x)  # No scroll negativo
        
        # Aplicar scroll
        self._view.horizontalScrollBar().setValue(int(scroll_x))
        
        log = logging.getLogger("soundvi.qt6.timeline")
        log.debug("Timeline centrado en tiempo: %.1fs, scroll X: %dpx", 
                 tiempo_segundos, int(scroll_x))
    
    def _ajustar_tamanos_dinamicos(self):
        """Ajusta dinámicamente los tamaños basado en el espacio disponible."""
        height = self.height()
        
        # Calcular altura disponible para tracks (excluyendo toolbar y ruler)
        available_height = max(100, height - 80)  # 80px para toolbar + ruler
        
        # Ajustar altura de tracks si hay muchos
        num_tracks = len(self._timeline.tracks)
        if num_tracks > 0:
            # Altura mínima por track: 40px, máxima: 80px
            track_height = max(40, min(80, available_height // max(1, num_tracks)))
            
            # Actualizar altura en la escena
            if hasattr(self._scene, '_track_height'):
                self._scene._track_height = track_height
            
            # Recalcular layout (headers ahora están en la escena)
            self._refrescar_completo()

    # -- Snap ------------------------------------------------------------------
    def _toggle_snap(self):
        self._timeline.snap_enabled = self._btn_snap.isChecked()

    def _toggle_alignment_assistant(self):
        """Activa/desactiva el asistente de alineación."""
        alignment_enabled = self._btn_alignment.isChecked()
        
        if alignment_enabled:
            # Activar modo alineación
            logger.info("[Asistente] Modo alineación activado")
            self._mostrar_guia_alineacion()
        else:
            # Desactivar modo alineación
            logger.info("[Asistente] Modo alineación desactivado")
            self._ocultar_guia_alineacion()
        
        # Actualizar estado en el timeline si es necesario
        if hasattr(self._timeline, 'alignment_assistant_enabled'):
            self._timeline.alignment_assistant_enabled = alignment_enabled

    def _mostrar_guia_alineacion(self):
        """Muestra guías de alineación en el timeline."""
        # Crear o mostrar guías visuales
        if not hasattr(self, '_alignment_guides'):
            self._alignment_guides = []
            
            # Guías verticales (para alinear en tiempo)
            for i in range(1, 10):  # 9 guías verticales
                guide = QGraphicsLineItem()
                guide.setPen(QPen(QColor("#F39C12"), 1, Qt.PenStyle.DashLine))
                guide.setZValue(1000)  # Alto z-value para estar sobre todo
                guide.setVisible(False)
                self._scene.addItem(guide)
                self._alignment_guides.append(guide)
            
            # Guías horizontales (para alinear entre tracks)
            for i in range(1, 6):  # 5 guías horizontales
                guide = QGraphicsLineItem()
                guide.setPen(QPen(QColor("#F39C12"), 1, Qt.PenStyle.DashLine))
                guide.setZValue(1000)
                guide.setVisible(False)
                self._scene.addItem(guide)
                self._alignment_guides.append(guide)
        
        # Mostrar todas las guías
        for guide in self._alignment_guides:
            guide.setVisible(True)
        
        # Actualizar posición de las guías
        self._actualizar_guias_alineacion()

    def _ocultar_guia_alineacion(self):
        """Oculta las guías de alineación."""
        if hasattr(self, '_alignment_guides'):
            for guide in self._alignment_guides:
                guide.setVisible(False)

    def _actualizar_guias_alineacion(self):
        """Actualiza la posición de las guías de alineación."""
        if not hasattr(self, '_alignment_guides') or not self._btn_alignment.isChecked():
            return
        
        scene_rect = self._scene.sceneRect()
        scene_width = scene_rect.width()
        scene_height = scene_rect.height()
        
        # Actualizar guías verticales (divisiones temporales)
        vertical_guides = self._alignment_guides[:9]
        for i, guide in enumerate(vertical_guides):
            x_pos = HEADER_WIDTH + (scene_width - HEADER_WIDTH) * (i + 1) / 10
            guide.setLine(x_pos, RULER_HEIGHT, x_pos, scene_height)
        
        # Actualizar guías horizontales (entre tracks)
        horizontal_guides = self._alignment_guides[9:]
        track_count = len(self._timeline.tracks)
        if track_count > 1:
            track_height = (scene_height - RULER_HEIGHT) / track_count
            for i, guide in enumerate(horizontal_guides):
                if i < track_count - 1:
                    y_pos = RULER_HEIGHT + track_height * (i + 1)
                    guide.setLine(HEADER_WIDTH, y_pos, scene_width, y_pos)
                else:
                    guide.setVisible(False)
        else:
            for guide in horizontal_guides:
                guide.setVisible(False)

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

        # Iconos para cada tipo de track (caracteres Unicode)
        track_icons = {
            "video": "🎥",  # Cámara de video (U+1F3A5)
            "audio": "♪",   # Nota musical (U+266A)
            "subtitle": "📄", # Documento (U+1F4C4)
            "effect": "★"   # Estrella negra (U+2605)
        }
        
        # Descripciones de tipos de tracks
        track_descriptions = {
            "video": "Multimedia (videos, imágenes, GIFs)",
            "audio": "Audio (archivos de sonido)",
            "subtitle": "Subtítulos y texto (módulos)",
            "effect": "Efectos y módulos"
        }
        
        # Tipos permitidos para cada track
        allowed_types = {
            "video": "Videos, imágenes, GIFs",
            "audio": "Archivos de audio",
            "subtitle": "Módulos de texto/subtítulos",
            "effect": "Módulos de efectos"
        }

        for tipo in ["video", "audio", "subtitle", "effect"]:
            icon = track_icons.get(tipo, "📁")
            nombre = track_descriptions.get(tipo, tipo.capitalize())
            count = len(self._timeline.get_tracks_by_type(tipo))
            
            accion = menu.addAction(f"{icon} {nombre} ({count})")
            accion.triggered.connect(lambda checked, t=tipo: self._agregar_track(t))
            
            # Tooltip con información detallada
            accion.setToolTip(f"Tipos permitidos: {allowed_types.get(tipo, 'Todos')}")
            
            # Deshabilitar si se alcanzo el limite
            if self._pm:
                perfil = self._pm.perfil_activo
                if perfil:
                    if tipo == "audio" and perfil.max_pistas_audio >= 0 and count >= perfil.max_pistas_audio:
                        accion.setEnabled(False)
                        accion.setText(f"{icon} {nombre} ({count}) - Límite alcanzado")
                    elif tipo == "video" and perfil.max_capas_video >= 0 and count >= perfil.max_capas_video:
                        accion.setEnabled(False)
                        accion.setText(f"{icon} {nombre} ({count}) - Límite alcanzado")
        
        # Separador
        menu.addSeparator()
        
        # Acción para mostrar ayuda sobre tipos de tracks
        ayuda_action = menu.addAction("❓ Ayuda sobre tipos de tracks")
        ayuda_action.triggered.connect(self._mostrar_ayuda_tipos_tracks)

        menu.exec(QCursor.pos())
    
    def _mostrar_ayuda_tipos_tracks(self):
        """Muestra un diálogo de ayuda sobre los tipos de tracks."""
        from PyQt6.QtWidgets import QMessageBox
        
        ayuda_texto = """
        <h3>Tipos de Tracks en Soundvi</h3>
        
        <b>🎥 Multimedia (video):</b><br>
        • Videos (.mp4, .avi, .mov, etc.)<br>
        • Imágenes (.jpg, .png, .bmp, etc.)<br>
        • GIFs animados (.gif)<br>
        • Fondos de color<br>
        <br>
        
        <b>♪ Audio:</b><br>
        • Archivos de audio (.mp3, .wav, .ogg, etc.)<br>
        • Audio extraído de videos<br>
        <br>
        
        <b>📄 Subtítulos:</b><br>
        • Módulos de texto y subtítulos<br>
        • Títulos animados<br>
        • Créditos<br>
        <br>
        
        <b>★ Efectos:</b><br>
        • Módulos de efectos visuales<br>
        • Transiciones<br>
        • Filtros y ajustes<br>
        <br>
        
        <i>Nota: Los archivos se asignan automáticamente al track correcto.</i>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Ayuda - Tipos de Tracks")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(ayuda_texto)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def _agregar_track(self, tipo: str):
        """Agrega un nuevo track al timeline con nombre descriptivo."""
        # Contar tracks existentes de este tipo para numeración
        existing_tracks = self._timeline.get_tracks_by_type(tipo)
        count = len(existing_tracks) + 1
        
        # Nombres descriptivos según tipo
        track_names = {
            "video": f"Multimedia {count}",
            "audio": f"Audio {count}",
            "subtitle": f"Subtítulos {count}" if count > 1 else "Subtítulos",
            "effect": f"Efectos {count}" if count > 1 else "Efectos"
        }
        
        name = track_names.get(tipo, f"{tipo.capitalize()} {count}")
        self._timeline.add_track(track_type=tipo, name=name)
        self._refrescar_completo()
        self.clips_changed.emit()
        
        # NO centrar automáticamente - scrollbars fijos

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

        # Aplicar magnetismo (snap) si esta habilitado
        if self._timeline.snap_enabled or (hasattr(self, '_btn_alignment') and self._btn_alignment.isChecked()):
            threshold_time = 15.0 / self._pps # 15 pixeles de tolerancia
            best_time = tiempo
            min_dist = threshold_time
            
            snap_times = [0.0, self._timeline.playhead]
            for track in self._timeline.tracks:
                for c in track.clips:
                    snap_times.extend([c.start_time, c.end_time])
                    
            for t in snap_times:
                dist = abs(tiempo - t)
                if dist < min_dist:
                    min_dist = dist
                    best_time = t
            tiempo = max(0.0, best_time)

        from core.video_clip import detect_source_type
        
        from core.commands import AddClipCommand
        successful_drops = 0
        failed_drops = 0
        
        for url in urls:
            from core.video_clip import VideoClip
            clip = VideoClip(
                source_path=url,
                source_type=detect_source_type(url),
                track_index=track_index,
                start_time=tiempo
            )
            
            # Validar duracion y recargar frames base si es necesario
            if clip.duration <= 0.1:
                clip.duration = 5.0
            
            # Verificar si el track es compatible con este tipo de archivo
            target_track = self._timeline.get_track(track_index)
            if target_track and not target_track._is_clip_type_allowed(clip):
                # Track incompatible - intentar agregar automáticamente a un track compatible
                result = self._timeline._add_clip_to_compatible_track(clip)
                if result:
                    successful_drops += 1
                    logger.info(f"Archivo '{os.path.basename(url)}' agregado automáticamente a track compatible")
                else:
                    failed_drops += 1
                    logger.warning(f"No se pudo agregar '{os.path.basename(url)}' - tipo incompatible")
            else:
                # Track compatible o no hay validación
                cmd = AddClipCommand(self._timeline, clip, track_index)
                self._cmd.execute(cmd)
                successful_drops += 1
            
            # Avanzar tiempo para el siguiente clip droppeado a la vez
            tiempo += clip.duration
        
        # Mostrar notificación si hubo errores
        if failed_drops > 0:
            from PyQt6.QtWidgets import QMessageBox
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Archivos no compatibles")
            msg.setText(f"{failed_drops} de {len(urls)} archivos no pudieron ser agregados.")
            msg.setInformativeText("Los archivos de audio deben ir en tracks de audio, "
                                  "y los archivos de video/imágenes en tracks de multimedia.")
            msg.exec()
        
        if successful_drops > 0:
            self._refrescar_completo()
            self.clips_changed.emit()

    def _on_transition_dropped(self, trans_type: str, pos: QPointF):
        """Maneja drop de una transición en el timeline."""
        # Encontrar el clip más cercano a la posición del drop
        x = pos.x()
        y = pos.y() - RULER_HEIGHT
        if y < 0 or x < HEADER_WIDTH:
            return

        tiempo = (x - HEADER_WIDTH) / self._pps
        track_index = int(y / TRACK_HEIGHT)
        if track_index < 0 or track_index >= len(self._timeline.tracks):
            return

        track = self._timeline.tracks[track_index]
        best_clip = None
        best_dist = float('inf')
        apply_position = 'in'  # 'in' para inicio, 'out' para final

        for clip in track.clips:
            # Distancia al inicio del clip
            dist_start = abs(tiempo - clip.start_time)
            if dist_start < best_dist:
                best_dist = dist_start
                best_clip = clip
                apply_position = 'in'
            # Distancia al final del clip
            dist_end = abs(tiempo - clip.end_time)
            if dist_end < best_dist:
                best_dist = dist_end
                best_clip = clip
                apply_position = 'out'

        if best_clip is None:
            return

        # Determinar si es transición de entrada o salida
        # según el tipo de transición y la posición
        trans_data = {
            'type': trans_type,
            'duration': 1.0,
            'easing': 'ease_in_out',
            'color': [0, 0, 0],
            'softness': 0.1,
        }

        # Transiciones que son inherentemente de entrada o salida
        in_types = {'fade_in', 'fade_from_color'}
        out_types = {'fade_out', 'fade_to_color'}

        if trans_type in in_types:
            apply_position = 'in'
        elif trans_type in out_types:
            apply_position = 'out'

        if apply_position == 'in':
            best_clip.transition_in = trans_data
            logger.info("Transición IN '%s' aplicada a clip '%s'", trans_type, best_clip.name)
        else:
            best_clip.transition_out = trans_data
            logger.info("Transición OUT '%s' aplicada a clip '%s'", trans_type, best_clip.name)

        self._refrescar_completo()
        self.clips_changed.emit()

    def _on_module_dropped(self, mod_type: str, pos: QPointF):
        """Maneja drop de un módulo desde el sidebar al timeline."""
        x = pos.x()
        if x < HEADER_WIDTH:
            x = HEADER_WIDTH
        
        tiempo = (x - HEADER_WIDTH) / self._pps
        
        # Crear ModuleTimelineItem
        item = ModuleTimelineItem(
            module_type=mod_type,
            start_time=max(0.0, tiempo),
            duration=5.0,
        )
        
        # Buscar track de efectos
        for i, track in enumerate(self._timeline.tracks):
            if track.track_type == 'effect':
                item.track_index = i
                break
        
        self._timeline.add_module_item(item)
        logger.info("Módulo '%s' añadido al timeline en t=%.1fs", mod_type, tiempo)
        
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

    def eliminar_modulo_seleccionado(self) -> bool:
        """Elimina el o los módulos seleccionados del timeline.
        
        Returns:
            True si se eliminó al menos un módulo, False si no había módulos seleccionados.
        """
        mods_sel = self._scene.get_selected_modules()
        
        # Debug: mostrar qué módulos están seleccionados
        log = logging.getLogger("soundvi.qt6.timeline")
        log.debug("Módulos seleccionados para eliminar: %d", len(mods_sel))
        for i, mod in enumerate(mods_sel):
            log.debug("  [%d] %s (id: %s)", i, mod.name, mod.item_id)
        
        if not mods_sel:
            log.debug("No hay módulos seleccionados para eliminar")
            return False
            
        for mod in mods_sel:
            self._timeline.remove_module_item(mod.item_id)
            logger.info("Módulo '%s' eliminado del timeline", mod.name)
            
        self._refrescar_completo()
        self.module_selected.emit(None)
        self.clips_changed.emit()
        return True

    def eliminar_clip_seleccionado(self):
        """Elimina el o los clips seleccionados del timeline."""
        clips_sel = self.get_selected_clips()
        if not clips_sel:
            return
            
        from core.commands import RemoveClipCommand
        for clip in clips_sel:
            cmd = RemoveClipCommand(self._timeline, clip.clip_id)
            self._cmd.execute(cmd)
            
        self._refrescar_completo()
        self.clip_selected.emit(None)
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
        mods_sel = self._scene.get_selected_modules()

        if clips_sel:
            menu.addAction(f"{ICONOS_UNICODE['cut']} Dividir en playhead",
                           self.dividir_clip_en_playhead)
            menu.addAction(f"{ICONOS_UNICODE['copy']} Copiar", self.copiar_seleccion)
            menu.addAction(f"{ICONOS_UNICODE['trash']} Eliminar",
                           self.eliminar_clip_seleccionado)
            menu.addSeparator()
        
        if mods_sel:
            menu.addAction(f"{ICONOS_UNICODE['trash']} Eliminar módulo(s)",
                           self.eliminar_modulo_seleccionado)
            menu.addSeparator()

            # Submenu de transiciones
            trans_menu = menu.addMenu("⇄ Transiciones")
            
            # Transición de entrada
            in_menu = trans_menu.addMenu("▶ Entrada (Fade In)")
            for ttype, tname in [
                ("fade_in", "Fade In (negro)"),
                ("fade_from_color", "Fade desde color"),
                ("crossfade", "Crossfade"),
                ("dissolve", "Disolver"),
                ("wipe_left", "Barrido izquierda"),
                ("zoom_in", "Zoom acercar"),
                ("iris_open", "Iris abrir"),
                ("blur_transition", "Desenfoque"),
            ]:
                act = in_menu.addAction(tname)
                act.triggered.connect(
                    lambda checked, c=clips_sel[0], t=ttype: self._aplicar_transicion_clip(c, 'in', t)
                )
            
            # Transición de salida
            out_menu = trans_menu.addMenu("◀ Salida (Fade Out)")
            for ttype, tname in [
                ("fade_out", "Fade Out (negro)"),
                ("fade_to_color", "Fade a color"),
                ("crossfade", "Crossfade"),
                ("dissolve", "Disolver"),
                ("wipe_right", "Barrido derecha"),
                ("zoom_out", "Zoom alejar"),
                ("iris_close", "Iris cerrar"),
                ("blur_transition", "Desenfoque"),
            ]:
                act = out_menu.addAction(tname)
                act.triggered.connect(
                    lambda checked, c=clips_sel[0], t=ttype: self._aplicar_transicion_clip(c, 'out', t)
                )
            
            trans_menu.addSeparator()
            
            # Quitar transiciones
            if clips_sel[0].transition_in:
                act_rm_in = trans_menu.addAction("✕ Quitar transición de entrada")
                act_rm_in.triggered.connect(
                    lambda: self._quitar_transicion_clip(clips_sel[0], 'in')
                )
            if clips_sel[0].transition_out:
                act_rm_out = trans_menu.addAction("✕ Quitar transición de salida")
                act_rm_out.triggered.connect(
                    lambda: self._quitar_transicion_clip(clips_sel[0], 'out')
                )
            
            menu.addSeparator()
            menu.addAction("Propiedades...", lambda: self.clip_selected.emit(clips_sel[0]))
        
        # Opciones para módulos seleccionados
        elif mods_sel:
            menu.addAction(f"{ICONOS_UNICODE['trash']} Eliminar módulo(s)",
                          self.eliminar_modulo_seleccionado)
            menu.addSeparator()
            menu.addAction("Propiedades del módulo...", 
                          lambda: self.module_selected.emit(mods_sel[0]))
        
        # Si no hay clips ni módulos seleccionados
        else:
            menu.addAction(f"{ICONOS_UNICODE['paste']} Pegar", self.pegar_clips)
            menu.addSeparator()
            
            # Submenú para agregar tracks específicos
            add_track_menu = menu.addMenu("➕ Agregar pista")
            
            # Iconos para cada tipo de track (caracteres Unicode)
            track_icons = {
                "video": "🎥",  # Cámara de video (U+1F3A5)
                "audio": "♪",   # Nota musical (U+266A)
                "subtitle": "📄", # Documento (U+1F4C4)
                "effect": "★"   # Estrella negra (U+2605)
            }
            
            for tipo, nombre in [("video", "Multimedia (video/imágenes)"), 
                                 ("audio", "Audio"), 
                                 ("subtitle", "Subtítulos/texto"),
                                 ("effect", "Efectos/módulos")]:
                icon = track_icons.get(tipo, "📁")
                action = add_track_menu.addAction(f"{icon} {nombre}")
                action.triggered.connect(lambda checked, t=tipo: self._agregar_track(t))
                
                # Mostrar conteo actual de tracks de este tipo
                count = len(self._timeline.get_tracks_by_type(tipo))
                action.setText(f"{icon} {nombre} ({count})")
                
                # Deshabilitar si hay límites de perfil
                if self._pm:
                    perfil = self._pm.perfil_activo
                    if perfil:
                        if tipo == "audio" and perfil.max_pistas_audio >= 0 and count >= perfil.max_pistas_audio:
                            action.setEnabled(False)
                            action.setText(f"{icon} {nombre} ({count}) - Límite alcanzado")
                        elif tipo == "video" and perfil.max_capas_video >= 0 and count >= perfil.max_capas_video:
                            action.setEnabled(False)
                            action.setText(f"{icon} {nombre} ({count}) - Límite alcanzado")

        menu.exec(event.globalPos())

    # -- Atajos de teclado -----------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent):
        """Manejo de atajos de teclado del timeline."""
        log = logging.getLogger("soundvi.qt6.timeline")
        
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            log.debug("Tecla DEL presionada - intentando eliminar")
            # Primero intentar eliminar módulos seleccionados
            mods_deleted = self.eliminar_modulo_seleccionado()
            if mods_deleted:
                log.debug("Módulo(s) eliminado(s) exitosamente")
            else:
                log.debug("No hay módulos seleccionados, intentando eliminar clips")
                # Si no hay módulos seleccionados, eliminar clips
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

    def _aplicar_transicion_clip(self, clip: VideoClip, position: str, trans_type: str):
        """Aplica una transición de entrada o salida a un clip."""
        trans_data = {
            'type': trans_type,
            'duration': 1.0,
            'easing': 'ease_in_out',
            'color': [0, 0, 0],
            'softness': 0.1,
        }
        if position == 'in':
            clip.transition_in = trans_data
        else:
            clip.transition_out = trans_data
        
        logger.info("Transición '%s' (%s) aplicada a '%s'", trans_type, position, clip.name)
        self._refrescar_completo()
        self.clips_changed.emit()

    def _quitar_transicion_clip(self, clip: VideoClip, position: str):
        """Quita una transición de un clip."""
        if position == 'in':
            clip.transition_in = None
        else:
            clip.transition_out = None
        
        logger.info("Transición (%s) quitada de '%s'", position, clip.name)
        self._refrescar_completo()
        self.clips_changed.emit()

    def agregar_clip(self, clip: VideoClip, track_index: int = 0):
        """Agrega un clip al timeline (API pública)."""
        cmd = AddClipCommand(self._timeline, clip, track_index)
        self._cmd.execute(cmd)
        self._refrescar_completo()
        self.clips_changed.emit()