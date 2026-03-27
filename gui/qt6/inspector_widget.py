# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- Inspector de Propiedades.

Panel dinamico contextual que muestra y permite editar las propiedades
del elemento actualmente seleccionado en el timeline:
  - Propiedades de VideoClip (start_time, end_time, speed, volume, opacity)
  - Propiedades de modulos (parametros especificos)
  - Propiedades de Track (nombre, mute, solo, lock)
  - Secciones colapsables con PropertyGroup
  - Integracion con CommandManager para Undo/Redo
  - Preview en tiempo real de cambios
  - Boton "Reset to Default"
"""

from __future__ import annotations

import os
import sys
import logging
from typing import Optional, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy, QLineEdit, QCheckBox,
    QComboBox, QSpinBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _RAIZ) if _RAIZ not in sys.path else None

from core.video_clip import VideoClip
from core.timeline import Track
from core.commands import CommandManager, ChangePropertyCommand
from core.profiles import ProfileManager
from gui.qt6.widgets.custom_widgets import (
    PropertyGroup, SliderWithLabel, TimeCodeEdit, ColorPickerWidget
)
from gui.qt6.base import ICONOS_UNICODE, UserLevelAdapter, NIVEL_NOVATO, NIVEL_PROFESIONAL

log = logging.getLogger("soundvi.qt6.inspector")


# ---------------------------------------------------------------------------
#  InspectorWidget -- Panel principal del inspector
# ---------------------------------------------------------------------------
class InspectorWidget(QWidget):
    """
    Panel de propiedades contextual.
    Cambia su contenido segun el tipo de objeto seleccionado.
    """

    # Senales
    property_changed = pyqtSignal(str, object)  # nombre_propiedad, nuevo_valor
    preview_requested = pyqtSignal()

    def __init__(self, command_manager: Optional[CommandManager] = None,
                 profile_manager: Optional[ProfileManager] = None,
                 user_level_adapter: Optional[UserLevelAdapter] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._cmd = command_manager or CommandManager()
        self._pm = profile_manager
        self._adapter = user_level_adapter or UserLevelAdapter(profile_manager)
        self._objeto_actual: Any = None

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
                border-bottom: 2px solid #00BC8C;
                padding: 4px;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)

        self._lbl_titulo = QLabel("Inspector")
        self._lbl_titulo.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        header_layout.addWidget(self._lbl_titulo)

        header_layout.addStretch()

        # Boton reset
        self._btn_reset = QPushButton("\u21BA Reset")
        self._btn_reset.setToolTip("Restaurar valores por defecto")
        self._btn_reset.setFixedHeight(22)
        self._btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #495057; color: #DEE2E6;
                border: none; border-radius: 3px;
                padding: 2px 8px; font-size: 10px;
            }
            QPushButton:hover { background-color: #6C757D; }
        """)
        self._btn_reset.clicked.connect(self._reset_defaults)
        self._btn_reset.setVisible(False)
        header_layout.addWidget(self._btn_reset)

        layout.addWidget(header)

        # Area scrolleable de contenido
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("QScrollArea { background-color: #212529; border: none; }")

        self._contenido = QWidget()
        self._contenido_layout = QVBoxLayout(self._contenido)
        self._contenido_layout.setContentsMargins(4, 4, 4, 4)
        self._contenido_layout.setSpacing(4)
        self._scroll.setWidget(self._contenido)

        layout.addWidget(self._scroll)

        # Mostrar estado vacio
        self._mostrar_vacio()

    # -- Limpiar contenido -----------------------------------------------------
    def _limpiar_contenido(self):
        """Elimina todos los widgets del area de contenido."""
        while self._contenido_layout.count():
            item = self._contenido_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _mostrar_vacio(self):
        """Muestra mensaje cuando no hay seleccion."""
        self._limpiar_contenido()
        self._lbl_titulo.setText("Inspector")
        self._btn_reset.setVisible(False)

        lbl = QLabel("Selecciona un elemento en el\ntimeline para ver sus propiedades.")
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #6C757D; padding: 24px; font-size: 11px;")
        self._contenido_layout.addWidget(lbl)

        # Ayuda contextual para novatos
        ayuda = self._adapter.crear_label_ayuda("inspector")
        if ayuda:
            self._contenido_layout.addWidget(ayuda)

        self._contenido_layout.addStretch()

    # -- Mostrar propiedades de VideoClip --------------------------------------
    def mostrar_clip(self, clip: VideoClip):
        """Muestra las propiedades editables de un VideoClip."""
        self._objeto_actual = clip
        self._limpiar_contenido()
        self._lbl_titulo.setText(f"Clip: {clip.name}")
        self._btn_reset.setVisible(True)

        # -- Seccion: Informacion general --
        grupo_info = PropertyGroup("Informacion", expandido=True)
        # Nombre
        nombre_layout = QHBoxLayout()
        nombre_layout.addWidget(QLabel("Nombre:"))
        self._edit_nombre = QLineEdit(clip.name)
        self._edit_nombre.setStyleSheet("QLineEdit { background-color: #3B4148; color: #DEE2E6; border: 1px solid #495057; border-radius: 3px; padding: 2px 4px; }")
        self._edit_nombre.editingFinished.connect(
            lambda: self._cambiar_propiedad(clip, "name", self._edit_nombre.text(), "Renombrar clip"))
        nombre_layout.addWidget(self._edit_nombre)
        grupo_info.agregar_layout(nombre_layout)

        # Tipo de fuente
        tipo_lbl = QLabel(f"Tipo: {clip.source_type}")
        tipo_lbl.setStyleSheet("color: #ADB5BD; font-size: 10px;")
        grupo_info.agregar_widget(tipo_lbl)

        # Ruta
        if clip.source_path:
            ruta_lbl = QLabel(f"Archivo: {os.path.basename(clip.source_path)}")
            ruta_lbl.setStyleSheet("color: #ADB5BD; font-size: 10px;")
            ruta_lbl.setToolTip(clip.source_path)
            grupo_info.agregar_widget(ruta_lbl)

        self._contenido_layout.addWidget(grupo_info)

        # -- Seccion: Tiempo --
        grupo_tiempo = PropertyGroup("Posicion temporal", expandido=True)

        self._tc_start = TimeCodeEdit("Inicio", clip.start_time)
        self._tc_start.time_changed.connect(
            lambda v: self._cambiar_propiedad(clip, "start_time", v, "Cambiar inicio de clip"))
        grupo_tiempo.agregar_widget(self._tc_start)

        dur_slider = SliderWithLabel("Duracion", 0.1, 300.0, clip.duration, decimales=2, paso=3000)
        dur_slider.value_changed.connect(
            lambda v: self._cambiar_propiedad(clip, "duration", v, "Cambiar duracion de clip"))
        grupo_tiempo.agregar_widget(dur_slider)

        self._contenido_layout.addWidget(grupo_tiempo)

        # -- Seccion: Propiedades visuales --
        grupo_visual = PropertyGroup("Propiedades visuales", expandido=True)

        # Novato: solo volumen. Intermedio: volumen + opacidad. Profesional: todo
        if self._adapter.opciones_avanzadas_visibles():
            opacity_slider = SliderWithLabel("Opacidad", 0.0, 1.0, clip.opacity, decimales=2)
            opacity_slider.value_changed.connect(
                lambda v: self._cambiar_propiedad(clip, "opacity", v, "Cambiar opacidad"))
            grupo_visual.agregar_widget(opacity_slider)

        volume_slider = SliderWithLabel("Volumen", 0.0, 2.0, clip.volume, decimales=2, paso=200)
        volume_slider.value_changed.connect(
            lambda v: self._cambiar_propiedad(clip, "volume", v, "Cambiar volumen"))
        grupo_visual.agregar_widget(volume_slider)

        if self._adapter.opciones_avanzadas_visibles():
            speed_slider = SliderWithLabel("Velocidad", 0.1, 4.0, clip.speed, decimales=2, paso=390)
            speed_slider.value_changed.connect(
                lambda v: self._cambiar_propiedad(clip, "speed", v, "Cambiar velocidad"))
            grupo_visual.agregar_widget(speed_slider)

        self._contenido_layout.addWidget(grupo_visual)

        # Tip para novatos
        if self._adapter.es_novato:
            tip_lbl = QLabel("• Las opciones avanzadas (opacidad, velocidad)\nse habilitan al cambiar a nivel Intermedio.")
            tip_lbl.setWordWrap(True)
            tip_lbl.setStyleSheet("""
                QLabel {
                    background-color: #1a3a2a;
                    color: #00BC8C;
                    border: 1px solid #00BC8C;
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-size: 10px;
                }
            """)
            self._contenido_layout.addWidget(tip_lbl)

        # -- Seccion: Trim (oculto para novatos) --
        mostrar_trim = self._adapter.opciones_avanzadas_visibles()
        if self._pm:
            mostrar_trim = mostrar_trim and self._pm.funcion_habilitada("trim")

        if mostrar_trim:
            grupo_trim = PropertyGroup("Recorte (Trim)", expandido=False)

            trim_start = SliderWithLabel("Trim inicio", 0.0, max(clip.duration, 1.0),
                                         clip.trim_start, decimales=2, paso=1000)
            trim_start.value_changed.connect(
                lambda v: self._cambiar_propiedad(clip, "trim_start", v, "Cambiar trim inicio"))
            grupo_trim.agregar_widget(trim_start)

            trim_end_val = clip.trim_end if clip.trim_end > 0 else clip.duration
            trim_end = SliderWithLabel("Trim fin", 0.0, max(300.0, trim_end_val * 2),
                                       trim_end_val, decimales=2, paso=1000)
            trim_end.value_changed.connect(
                lambda v: self._cambiar_propiedad(clip, "trim_end", v, "Cambiar trim fin"))
            grupo_trim.agregar_widget(trim_end)

            self._contenido_layout.addWidget(grupo_trim)

        # -- Seccion: Estado (solo intermedio y profesional) --
        if self._adapter.opciones_avanzadas_visibles():
            grupo_estado = PropertyGroup("Estado", expandido=False)

            chk_enabled = QCheckBox("Habilitado")
            chk_enabled.setChecked(clip.enabled)
            chk_enabled.stateChanged.connect(
                lambda s: self._cambiar_propiedad(clip, "enabled", s == Qt.CheckState.Checked.value,
                                                   "Cambiar estado habilitado"))
            grupo_estado.agregar_widget(chk_enabled)

            self._contenido_layout.addWidget(grupo_estado)

        self._contenido_layout.addStretch()

    # -- Mostrar propiedades de Track ------------------------------------------
    def mostrar_track(self, track: Track):
        """Muestra las propiedades editables de un Track."""
        self._objeto_actual = track
        self._limpiar_contenido()
        self._lbl_titulo.setText(f"Track: {track.name}")
        self._btn_reset.setVisible(True)

        # -- Seccion: Informacion --
        grupo_info = PropertyGroup("Informacion", expandido=True)

        # Nombre
        nombre_layout = QHBoxLayout()
        nombre_layout.addWidget(QLabel("Nombre:"))
        edit_nombre = QLineEdit(track.name)
        edit_nombre.setStyleSheet("QLineEdit { background-color: #3B4148; color: #DEE2E6; border: 1px solid #495057; border-radius: 3px; padding: 2px 4px; }")
        edit_nombre.editingFinished.connect(
            lambda: self._cambiar_propiedad(track, "name", edit_nombre.text(), "Renombrar track"))
        nombre_layout.addWidget(edit_nombre)
        grupo_info.agregar_layout(nombre_layout)

        tipo_lbl = QLabel(f"Tipo: {track.track_type}")
        tipo_lbl.setStyleSheet("color: #ADB5BD; font-size: 10px;")
        grupo_info.agregar_widget(tipo_lbl)

        clips_lbl = QLabel(f"Clips: {len(track.clips)}")
        clips_lbl.setStyleSheet("color: #ADB5BD; font-size: 10px;")
        grupo_info.agregar_widget(clips_lbl)

        self._contenido_layout.addWidget(grupo_info)

        # -- Seccion: Controles --
        grupo_ctrl = PropertyGroup("Controles", expandido=True)

        chk_muted = QCheckBox("Silenciado (Mute)")
        chk_muted.setChecked(track.muted)
        chk_muted.stateChanged.connect(
            lambda s: self._cambiar_propiedad(track, "muted", s == Qt.CheckState.Checked.value,
                                               "Cambiar mute de track"))
        grupo_ctrl.agregar_widget(chk_muted)

        chk_solo = QCheckBox("Solo")
        chk_solo.setChecked(track.solo)
        chk_solo.stateChanged.connect(
            lambda s: self._cambiar_propiedad(track, "solo", s == Qt.CheckState.Checked.value,
                                               "Cambiar solo de track"))
        grupo_ctrl.agregar_widget(chk_solo)

        chk_locked = QCheckBox("Bloqueado (Lock)")
        chk_locked.setChecked(track.locked)
        chk_locked.stateChanged.connect(
            lambda s: self._cambiar_propiedad(track, "locked", s == Qt.CheckState.Checked.value,
                                               "Cambiar lock de track"))
        grupo_ctrl.agregar_widget(chk_locked)

        chk_visible = QCheckBox("Visible")
        chk_visible.setChecked(track.visible)
        chk_visible.stateChanged.connect(
            lambda s: self._cambiar_propiedad(track, "visible", s == Qt.CheckState.Checked.value,
                                               "Cambiar visibilidad de track"))
        grupo_ctrl.agregar_widget(chk_visible)

        self._contenido_layout.addWidget(grupo_ctrl)

        # -- Seccion: Audio (solo para tracks de audio) --
        if track.track_type == "audio":
            grupo_audio = PropertyGroup("Audio", expandido=True)

            vol_slider = SliderWithLabel("Volumen", 0.0, 2.0, track.volume, decimales=2, paso=200)
            vol_slider.value_changed.connect(
                lambda v: self._cambiar_propiedad(track, "volume", v, "Cambiar volumen de track"))
            grupo_audio.agregar_widget(vol_slider)

            pan_slider = SliderWithLabel("Panorama", -1.0, 1.0, track.pan, decimales=2, paso=200)
            pan_slider.value_changed.connect(
                lambda v: self._cambiar_propiedad(track, "pan", v, "Cambiar panorama de track"))
            grupo_audio.agregar_widget(pan_slider)

            self._contenido_layout.addWidget(grupo_audio)

        self._contenido_layout.addStretch()

    # -- Mostrar propiedades de modulo -----------------------------------------
    def mostrar_modulo(self, modulo: Any):
        """Muestra las propiedades editables de un modulo generico."""
        self._objeto_actual = modulo
        self._limpiar_contenido()

        nombre = getattr(modulo, "nombre", type(modulo).__name__)
        self._lbl_titulo.setText(f"Modulo: {nombre}")
        self._btn_reset.setVisible(True)

        grupo_mod = PropertyGroup("Parametros del modulo", expandido=True)

        # Obtener configuracion del modulo
        config = {}
        if hasattr(modulo, "get_config"):
            config = modulo.get_config()
        elif hasattr(modulo, "__dict__"):
            config = {k: v for k, v in modulo.__dict__.items()
                      if not k.startswith("_") and isinstance(v, (int, float, str, bool))}

        for clave, valor in config.items():
            if isinstance(valor, bool):
                chk = QCheckBox(clave.replace("_", " ").title())
                chk.setChecked(valor)
                chk.stateChanged.connect(
                    lambda s, k=clave: self._cambiar_propiedad(
                        modulo, k, s == Qt.CheckState.Checked.value,
                        f"Cambiar {k}"))
                grupo_mod.agregar_widget(chk)
            elif isinstance(valor, float):
                slider = SliderWithLabel(clave.replace("_", " ").title(),
                                         0.0, max(valor * 3, 1.0), valor, decimales=2)
                slider.value_changed.connect(
                    lambda v, k=clave: self._cambiar_propiedad(modulo, k, v, f"Cambiar {k}"))
                grupo_mod.agregar_widget(slider)
            elif isinstance(valor, int):
                spin_layout = QHBoxLayout()
                spin_layout.addWidget(QLabel(clave.replace("_", " ").title()))
                spin = QSpinBox()
                spin.setRange(0, max(valor * 3, 100))
                spin.setValue(valor)
                spin.setStyleSheet("QSpinBox { background-color: #3B4148; color: #DEE2E6; border: 1px solid #495057; border-radius: 3px; }")
                spin.valueChanged.connect(
                    lambda v, k=clave: self._cambiar_propiedad(modulo, k, v, f"Cambiar {k}"))
                spin_layout.addWidget(spin)
                grupo_mod.agregar_layout(spin_layout)
            elif isinstance(valor, str):
                if valor.startswith("#") and len(valor) in (7, 9):
                    # Parece ser un color
                    picker = ColorPickerWidget(clave.replace("_", " ").title(), valor)
                    picker.color_changed.connect(
                        lambda c, k=clave: self._cambiar_propiedad(modulo, k, c, f"Cambiar {k}"))
                    grupo_mod.agregar_widget(picker)
                else:
                    str_layout = QHBoxLayout()
                    str_layout.addWidget(QLabel(clave.replace("_", " ").title()))
                    edit = QLineEdit(valor)
                    edit.setStyleSheet("QLineEdit { background-color: #3B4148; color: #DEE2E6; border: 1px solid #495057; border-radius: 3px; padding: 2px 4px; }")
                    edit.editingFinished.connect(
                        lambda k=clave, e=edit: self._cambiar_propiedad(
                            modulo, k, e.text(), f"Cambiar {k}"))
                    str_layout.addWidget(edit)
                    grupo_mod.agregar_layout(str_layout)

        self._contenido_layout.addWidget(grupo_mod)
        self._contenido_layout.addStretch()

    # -- Cambiar propiedades con Undo/Redo -------------------------------------
    def _cambiar_propiedad(self, obj: Any, prop: str, valor: Any, desc: str = ""):
        """Cambia una propiedad usando CommandManager para soporte Undo/Redo."""
        cmd = ChangePropertyCommand(obj, prop, valor, desc)
        self._cmd.execute(cmd)
        self.property_changed.emit(prop, valor)
        self.preview_requested.emit()

    # -- Reset -----------------------------------------------------------------
    def _reset_defaults(self):
        """Restaura valores por defecto del objeto actual."""
        obj = self._objeto_actual
        if obj is None:
            return

        if isinstance(obj, VideoClip):
            obj.opacity = 1.0
            obj.volume = 1.0
            obj.speed = 1.0
            obj.enabled = True
            self.mostrar_clip(obj)
        elif isinstance(obj, Track):
            obj.muted = False
            obj.solo = False
            obj.locked = False
            obj.visible = True
            obj.volume = 1.0
            obj.pan = 0.0
            self.mostrar_track(obj)

        self.preview_requested.emit()

    # -- API publica -----------------------------------------------------------
    def limpiar(self):
        """Limpia el inspector (sin seleccion)."""
        self._objeto_actual = None
        self._mostrar_vacio()

    def set_objeto(self, obj: Any):
        """Establece el objeto a inspeccionar, detectando su tipo."""
        if obj is None:
            self.limpiar()
        elif isinstance(obj, VideoClip):
            self.mostrar_clip(obj)
        elif isinstance(obj, Track):
            self.mostrar_track(obj)
        else:
            self.mostrar_modulo(obj)

    def set_adapter(self, adapter: UserLevelAdapter):
        """Actualiza el adaptador de nivel y refresca la vista."""
        self._adapter = adapter
        # Refrescar vista actual si hay un objeto
        if self._objeto_actual is not None:
            self.set_objeto(self._objeto_actual)
        else:
            self._mostrar_vacio()

    @property
    def objeto_actual(self) -> Any:
        return self._objeto_actual
