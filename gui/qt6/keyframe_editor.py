# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- Editor Visual de Keyframes.

Grafico de curvas de animacion interactivo usando QGraphicsView:
  - Anadir/eliminar/mover keyframes con click y arrastre
  - Cambiar modo de interpolacion (linear, ease-in, ease-out, bezier, constant)
  - Handles de Bezier para control fino
  - Zoom horizontal (tiempo) y vertical (valor)
  - Multiples propiedades en el mismo grafico con colores diferentes
  - Integracion con core/keyframes.py (KeyframeAnimator, KeyframeTrack)
  - Sincronizacion con timeline (playhead)
  - Solo visible en perfil Profesional
"""

from __future__ import annotations

import os
import sys
import math
import logging
from typing import Optional, Dict, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsPathItem,
    QGraphicsLineItem, QGraphicsTextItem, QGraphicsItem,
    QFrame, QComboBox, QMenu, QSizePolicy
)
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QColor, QBrush, QPen, QFont, QPainter, QPainterPath,
    QCursor, QWheelEvent
)

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _RAIZ) if _RAIZ not in sys.path else None

from core.keyframes import (
    KeyframeAnimator, KeyframeTrack, Keyframe,
    InterpolationMode, interpolate, lerp
)
from gui.qt6.base import ICONOS_UNICODE

log = logging.getLogger("soundvi.qt6.keyframe_editor")

# Constantes visuales
MARGIN_LEFT = 50     # Margen izquierdo para etiquetas de valor
MARGIN_BOTTOM = 30   # Margen inferior para etiquetas de tiempo
MARGIN_TOP = 20      # Margen superior
MARGIN_RIGHT = 20    # Margen derecho
KF_RADIUS = 6        # Radio de los puntos de keyframe
HANDLE_RADIUS = 4    # Radio de los handles de Bezier

# Colores para diferentes propiedades
PROPERTY_COLORS = [
    "#E74C3C",  # rojo
    "#2ECC71",  # verde
    "#3498DB",  # azul
    "#F39C12",  # naranja
    "#9B59B6",  # purpura
    "#1ABC9C",  # turquesa
    "#E67E22",  # naranja oscuro
    "#00BC8C",  # verde claro
]


# ---------------------------------------------------------------------------
#  KeyframePoint -- Punto de keyframe interactivo
# ---------------------------------------------------------------------------
class KeyframePoint(QGraphicsEllipseItem):
    """Punto interactivo que representa un keyframe en el grafico."""

    def __init__(self, keyframe: Keyframe, track_name: str,
                 color: QColor, editor: 'KeyframeEditorScene'):
        super().__init__(-KF_RADIUS, -KF_RADIUS, KF_RADIUS * 2, KF_RADIUS * 2)
        self.keyframe = keyframe
        self.track_name = track_name
        self._color = color
        self._editor = editor
        self._dragging = False

        self.setBrush(QBrush(color))
        self.setPen(QPen(color.darker(120), 1.5))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setZValue(100)

        # Tooltip con info
        self._actualizar_tooltip()

    def _actualizar_tooltip(self):
        self.setToolTip(
            f"Propiedad: {self.track_name}\n"
            f"Tiempo: {self.keyframe.time:.3f}s\n"
            f"Valor: {self.keyframe.value:.3f}\n"
            f"Interpolacion: {self.keyframe.interpolation}"
        )

    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(self._color.lighter(150)))
        self.setPen(QPen(QColor("#FFFFFF"), 2))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        if not self.isSelected():
            self.setBrush(QBrush(self._color))
            self.setPen(QPen(self._color.darker(120), 1.5))
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging:
            self._dragging = False
            # Actualizar keyframe con nueva posicion
            pos = self.pos()
            new_time, new_value = self._editor.pos_to_time_value(pos)
            self.keyframe.time = max(0.0, new_time)
            self.keyframe.value = new_value
            self._actualizar_tooltip()
            self._editor.redibujar_curvas()
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        """Menu contextual para cambiar interpolacion o eliminar."""
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #2B3035; color: #DEE2E6;
                border: 1px solid #495057; padding: 4px;
            }
            QMenu::item:selected { background-color: #375A7F; }
        """)

        # Modos de interpolacion
        sub_interp = menu.addMenu("Interpolacion")
        for modo in InterpolationMode.ALL_MODES:
            accion = sub_interp.addAction(modo.replace("_", " ").title())
            accion.setCheckable(True)
            accion.setChecked(self.keyframe.interpolation == modo)
            accion.triggered.connect(lambda checked, m=modo: self._set_interpolacion(m))

        menu.addSeparator()
        menu.addAction("Eliminar keyframe", self._eliminar)

        menu.exec(event.screenPos())

    def _set_interpolacion(self, modo: str):
        self.keyframe.interpolation = modo
        self._actualizar_tooltip()
        self._editor.redibujar_curvas()

    def _eliminar(self):
        self._editor.eliminar_keyframe(self.track_name, self.keyframe.time)


# ---------------------------------------------------------------------------
#  KeyframeEditorScene -- Escena del editor de keyframes
# ---------------------------------------------------------------------------
class KeyframeEditorScene(QGraphicsScene):
    """Escena que renderiza el grafico de curvas de keyframes."""

    keyframe_changed = pyqtSignal()
    keyframe_added = pyqtSignal(str, float, float)  # track, time, value

    def __init__(self, parent=None):
        super().__init__(parent)
        self._animator: Optional[KeyframeAnimator] = None
        self._time_range = (0.0, 10.0)    # Rango temporal visible
        self._value_range = (0.0, 1.0)    # Rango de valores visible
        self._view_width = 600
        self._view_height = 200
        self._playhead_time = 0.0
        self._kf_points: List[KeyframePoint] = []
        self._curve_paths: List[QGraphicsPathItem] = []
        self._playhead_line: Optional[QGraphicsLineItem] = None

    def set_animator(self, animator: KeyframeAnimator):
        """Establece el animador de keyframes a visualizar."""
        self._animator = animator
        self.redibujar_completo()

    def set_view_size(self, w: int, h: int):
        self._view_width = w
        self._view_height = h

    def set_time_range(self, start: float, end: float):
        self._time_range = (start, max(start + 0.1, end))

    def set_value_range(self, vmin: float, vmax: float):
        self._value_range = (vmin, max(vmin + 0.001, vmax))

    # -- Conversiones coordenadas <-> tiempo/valor --
    def time_value_to_pos(self, time: float, value: float) -> QPointF:
        """Convierte tiempo y valor a coordenadas de escena."""
        t_min, t_max = self._time_range
        v_min, v_max = self._value_range
        w = self._view_width - MARGIN_LEFT - MARGIN_RIGHT
        h = self._view_height - MARGIN_TOP - MARGIN_BOTTOM

        x = MARGIN_LEFT + ((time - t_min) / (t_max - t_min)) * w
        y = MARGIN_TOP + (1.0 - (value - v_min) / (v_max - v_min)) * h
        return QPointF(x, y)

    def pos_to_time_value(self, pos: QPointF):
        """Convierte coordenadas de escena a tiempo y valor."""
        t_min, t_max = self._time_range
        v_min, v_max = self._value_range
        w = self._view_width - MARGIN_LEFT - MARGIN_RIGHT
        h = self._view_height - MARGIN_TOP - MARGIN_BOTTOM

        time = t_min + ((pos.x() - MARGIN_LEFT) / w) * (t_max - t_min)
        value = v_min + (1.0 - (pos.y() - MARGIN_TOP) / h) * (v_max - v_min)
        return time, value

    # -- Dibujar completo ------------------------------------------------------
    def redibujar_completo(self):
        """Reconstruye toda la visualizacion."""
        self.clear()
        self._kf_points.clear()
        self._curve_paths.clear()

        w = self._view_width
        h = self._view_height
        self.setSceneRect(0, 0, w, h)

        # Fondo
        bg = self.addRect(0, 0, w, h, QPen(Qt.PenStyle.NoPen), QBrush(QColor("#1a1d21")))
        bg.setZValue(-100)

        # Area del grafico
        gw = w - MARGIN_LEFT - MARGIN_RIGHT
        gh = h - MARGIN_TOP - MARGIN_BOTTOM
        graph_bg = self.addRect(MARGIN_LEFT, MARGIN_TOP, gw, gh,
                                QPen(QColor("#343A40"), 0.5),
                                QBrush(QColor("#212529")))
        graph_bg.setZValue(-50)

        self._dibujar_grid()
        self._dibujar_ejes()

        if self._animator:
            color_idx = 0
            for name, track in self._animator.tracks.items():
                if not track.enabled:
                    continue
                color = QColor(PROPERTY_COLORS[color_idx % len(PROPERTY_COLORS)])
                self._dibujar_curva(track, color)
                self._dibujar_keyframes(track, name, color)
                color_idx += 1

        # Playhead
        self._dibujar_playhead()

    def redibujar_curvas(self):
        """Redibuja solo las curvas y keyframes (mas rapido)."""
        self.redibujar_completo()

    def _dibujar_grid(self):
        """Dibuja la cuadricula de fondo."""
        t_min, t_max = self._time_range
        v_min, v_max = self._value_range
        gw = self._view_width - MARGIN_LEFT - MARGIN_RIGHT
        gh = self._view_height - MARGIN_TOP - MARGIN_BOTTOM

        pen_grid = QPen(QColor("#2B3035"), 0.5, Qt.PenStyle.DotLine)

        # Lineas verticales (tiempo)
        num_v = 10
        for i in range(num_v + 1):
            x = MARGIN_LEFT + (i / num_v) * gw
            line = self.addLine(x, MARGIN_TOP, x, MARGIN_TOP + gh, pen_grid)
            line.setZValue(-20)

            # Etiqueta de tiempo
            t = t_min + (i / num_v) * (t_max - t_min)
            texto = self.addText(f"{t:.1f}s", QFont("Consolas", 7))
            texto.setDefaultTextColor(QColor("#6C757D"))
            texto.setPos(x - 15, MARGIN_TOP + gh + 2)

        # Lineas horizontales (valor)
        num_h = 5
        for i in range(num_h + 1):
            y = MARGIN_TOP + (i / num_h) * gh
            line = self.addLine(MARGIN_LEFT, y, MARGIN_LEFT + gw, y, pen_grid)
            line.setZValue(-20)

            # Etiqueta de valor
            v = v_max - (i / num_h) * (v_max - v_min)
            texto = self.addText(f"{v:.2f}", QFont("Consolas", 7))
            texto.setDefaultTextColor(QColor("#6C757D"))
            texto.setPos(2, y - 8)

    def _dibujar_ejes(self):
        """Dibuja los ejes X (tiempo) e Y (valor)."""
        pen_eje = QPen(QColor("#495057"), 1)
        gw = self._view_width - MARGIN_LEFT - MARGIN_RIGHT
        gh = self._view_height - MARGIN_TOP - MARGIN_BOTTOM

        # Eje X
        self.addLine(MARGIN_LEFT, MARGIN_TOP + gh, MARGIN_LEFT + gw, MARGIN_TOP + gh, pen_eje)
        # Eje Y
        self.addLine(MARGIN_LEFT, MARGIN_TOP, MARGIN_LEFT, MARGIN_TOP + gh, pen_eje)

    def _dibujar_curva(self, track: KeyframeTrack, color: QColor):
        """Dibuja la curva de interpolacion para un track de keyframes."""
        if len(track.keyframes) < 2:
            return

        path = QPainterPath()
        num_puntos = max(100, int((self._time_range[1] - self._time_range[0]) * 20))

        for i in range(num_puntos + 1):
            t = self._time_range[0] + (i / num_puntos) * (self._time_range[1] - self._time_range[0])
            val = track.get_value_at(t)
            pos = self.time_value_to_pos(t, val)

            if i == 0:
                path.moveTo(pos)
            else:
                path.lineTo(pos)

        path_item = QGraphicsPathItem(path)
        pen_curva = QPen(color, 2)
        pen_curva.setCapStyle(Qt.PenCapStyle.RoundCap)
        path_item.setPen(pen_curva)
        path_item.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        path_item.setZValue(50)
        self.addItem(path_item)
        self._curve_paths.append(path_item)

    def _dibujar_keyframes(self, track: KeyframeTrack, name: str, color: QColor):
        """Dibuja los puntos de keyframe interactivos."""
        for kf in track.keyframes:
            pos = self.time_value_to_pos(kf.time, kf.value)
            point = KeyframePoint(kf, name, color, self)
            point.setPos(pos)
            self.addItem(point)
            self._kf_points.append(point)

    def _dibujar_playhead(self):
        """Dibuja la linea vertical del playhead."""
        pos = self.time_value_to_pos(self._playhead_time, 0)
        gh = self._view_height - MARGIN_TOP - MARGIN_BOTTOM
        pen = QPen(QColor("#E74C3C"), 1.5, Qt.PenStyle.DashLine)
        self._playhead_line = self.addLine(pos.x(), MARGIN_TOP, pos.x(), MARGIN_TOP + gh, pen)
        self._playhead_line.setZValue(200)

    def actualizar_playhead(self, tiempo: float):
        """Mueve el playhead a un nuevo tiempo."""
        self._playhead_time = tiempo
        if self._playhead_line:
            pos = self.time_value_to_pos(tiempo, 0)
            gh = self._view_height - MARGIN_TOP - MARGIN_BOTTOM
            self._playhead_line.setLine(pos.x(), MARGIN_TOP, pos.x(), MARGIN_TOP + gh)

    # -- Operaciones de keyframe -----------------------------------------------
    def eliminar_keyframe(self, track_name: str, time: float):
        """Elimina un keyframe de un track."""
        if self._animator:
            track = self._animator.get_track(track_name)
            if track:
                track.remove_keyframe(time)
                self.redibujar_completo()
                self.keyframe_changed.emit()

    def mousePressEvent(self, event):
        """Doble click para anadir keyframe."""
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Doble click para anadir keyframe en la posicion del cursor."""
        pos = event.scenePos()
        # Verificar que estamos dentro del area del grafico
        gw = self._view_width - MARGIN_LEFT - MARGIN_RIGHT
        gh = self._view_height - MARGIN_TOP - MARGIN_BOTTOM
        if (MARGIN_LEFT <= pos.x() <= MARGIN_LEFT + gw and
                MARGIN_TOP <= pos.y() <= MARGIN_TOP + gh):
            time, value = self.pos_to_time_value(pos)
            self.keyframe_added.emit("", time, value)
        super().mouseDoubleClickEvent(event)


# ---------------------------------------------------------------------------
#  KeyframeEditorView -- Vista del editor
# ---------------------------------------------------------------------------
class KeyframeEditorView(QGraphicsView):
    """Vista con zoom via rueda del raton."""

    def __init__(self, scene: KeyframeEditorScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setStyleSheet("QGraphicsView { background-color: #1a1d21; border: none; }")

    def wheelEvent(self, event: QWheelEvent):
        """Zoom con Ctrl+Rueda."""
        # No propagar el zoom, lo maneja el widget padre
        event.accept()

    def resizeEvent(self, event):
        scene = self.scene()
        if isinstance(scene, KeyframeEditorScene):
            scene.set_view_size(event.size().width(), event.size().height())
            scene.redibujar_completo()
        super().resizeEvent(event)


# ---------------------------------------------------------------------------
#  KeyframeEditorWidget -- Widget principal del editor de keyframes
# ---------------------------------------------------------------------------
class KeyframeEditorWidget(QWidget):
    """
    Widget principal del editor de keyframes.
    Integra la vista grafica con controles de parametros.
    Solo visible en perfil Profesional.
    """

    # Senales
    keyframe_changed = pyqtSignal()
    playhead_sync = pyqtSignal(float)

    def __init__(self, profile_manager: Optional['ProfileManager'] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._pm = profile_manager
        self._animator: Optional[KeyframeAnimator] = None
        self._active_track_name: str = ""

        self._construir_ui()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # -- Barra de herramientas --
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(4, 2, 4, 2)
        toolbar.setSpacing(4)

        lbl = QLabel("\u2248  Editor de Keyframes")
        lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        toolbar.addWidget(lbl)

        toolbar.addStretch()

        # Selector de propiedad
        toolbar.addWidget(QLabel("Propiedad:"))
        self._combo_prop = QComboBox()
        self._combo_prop.setMinimumWidth(120)
        self._combo_prop.setStyleSheet("""
            QComboBox {
                background-color: #3B4148; color: #DEE2E6;
                border: 1px solid #495057; border-radius: 3px;
                padding: 2px 4px; font-size: 11px;
            }
        """)
        self._combo_prop.currentTextChanged.connect(self._on_property_changed)
        toolbar.addWidget(self._combo_prop)

        # Selector de interpolacion
        toolbar.addWidget(QLabel("Interp:"))
        self._combo_interp = QComboBox()
        self._combo_interp.addItems([m.replace("_", " ").title() for m in InterpolationMode.ALL_MODES])
        self._combo_interp.setMinimumWidth(100)
        self._combo_interp.setStyleSheet("""
            QComboBox {
                background-color: #3B4148; color: #DEE2E6;
                border: 1px solid #495057; border-radius: 3px;
                padding: 2px 4px; font-size: 11px;
            }
        """)
        toolbar.addWidget(self._combo_interp)

        # Boton agregar keyframe
        btn_add = QPushButton("+ KF")
        btn_add.setToolTip("Agregar keyframe en la posicion del playhead")
        btn_add.setFixedHeight(24)
        btn_add.setStyleSheet("""
            QPushButton {
                background-color: #00BC8C; color: #FFFFFF;
                border: none; border-radius: 3px;
                padding: 2px 8px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background-color: #00A37A; }
        """)
        btn_add.clicked.connect(self._agregar_keyframe)
        toolbar.addWidget(btn_add)

        # Boton eliminar keyframe
        btn_del = QPushButton("\u2717 KF")
        btn_del.setToolTip("Eliminar keyframe seleccionado")
        btn_del.setFixedHeight(24)
        btn_del.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C; color: #FFFFFF;
                border: none; border-radius: 3px;
                padding: 2px 8px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background-color: #C0392B; }
        """)
        btn_del.clicked.connect(self._eliminar_keyframe_seleccionado)
        toolbar.addWidget(btn_del)

        layout.addLayout(toolbar)

        # -- Grafico de curvas --
        self._scene = KeyframeEditorScene()
        self._view = KeyframeEditorView(self._scene)
        self._view.setMinimumHeight(120)
        self._scene.keyframe_changed.connect(self.keyframe_changed.emit)
        self._scene.keyframe_added.connect(self._on_keyframe_added)
        layout.addWidget(self._view)

    def _on_property_changed(self, name: str):
        """Cambia la propiedad activa en el editor."""
        self._active_track_name = name

    def _on_keyframe_added(self, track_name: str, time: float, value: float):
        """Callback cuando se agrega un keyframe por doble-click."""
        if not self._animator:
            return
        nombre = self._active_track_name or track_name
        if not nombre and self._animator.tracks:
            nombre = next(iter(self._animator.tracks.keys()))
        if nombre:
            track = self._animator.get_track(nombre)
            if track:
                interp_idx = self._combo_interp.currentIndex()
                modo = InterpolationMode.ALL_MODES[interp_idx] if interp_idx < len(InterpolationMode.ALL_MODES) else InterpolationMode.LINEAR
                track.add_keyframe(time, value, modo)
                self._scene.redibujar_completo()
                self.keyframe_changed.emit()

    def _agregar_keyframe(self):
        """Agrega un keyframe en la posicion actual del playhead."""
        if not self._animator:
            return
        nombre = self._active_track_name
        if not nombre and self._animator.tracks:
            nombre = next(iter(self._animator.tracks.keys()))
        if nombre:
            track = self._animator.get_track(nombre)
            if track:
                tiempo = self._scene._playhead_time
                valor_actual = track.get_value_at(tiempo)
                interp_idx = self._combo_interp.currentIndex()
                modo = InterpolationMode.ALL_MODES[interp_idx] if interp_idx < len(InterpolationMode.ALL_MODES) else InterpolationMode.LINEAR
                track.add_keyframe(tiempo, valor_actual, modo)
                self._scene.redibujar_completo()
                self.keyframe_changed.emit()

    def _eliminar_keyframe_seleccionado(self):
        """Elimina los keyframes seleccionados en la escena."""
        for item in self._scene.selectedItems():
            if isinstance(item, KeyframePoint):
                self._scene.eliminar_keyframe(item.track_name, item.keyframe.time)

    # -- API publica -----------------------------------------------------------
    def set_animator(self, animator: KeyframeAnimator, time_range: float = 10.0):
        """Establece el animador a editar."""
        self._animator = animator
        self._scene.set_time_range(0.0, time_range)

        # Auto-detectar rango de valores
        v_min, v_max = 0.0, 1.0
        for track in animator.tracks.values():
            for kf in track.keyframes:
                v_min = min(v_min, kf.value)
                v_max = max(v_max, kf.value)
        margin = (v_max - v_min) * 0.1 if v_max > v_min else 0.5
        self._scene.set_value_range(v_min - margin, v_max + margin)

        # Poblar combo de propiedades
        self._combo_prop.clear()
        for name in animator.tracks:
            self._combo_prop.addItem(name)
        if animator.tracks:
            self._active_track_name = next(iter(animator.tracks.keys()))

        self._scene.set_animator(animator)

    def set_playhead(self, tiempo: float):
        """Sincroniza el playhead con el timeline."""
        self._scene.actualizar_playhead(tiempo)

    def refrescar(self):
        """Refresca la visualizacion."""
        if self._animator:
            self._scene.redibujar_completo()

    def es_visible_segun_perfil(self) -> bool:
        """Verifica si el editor debe ser visible segun el perfil activo."""
        if self._pm is None:
            return True
        return self._pm.funcion_habilitada("keyframes")
