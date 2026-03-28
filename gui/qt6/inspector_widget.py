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
from core.timeline import Track, ModuleTimelineItem
from core.transitions import TransitionType
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

        # -- Sección: Transiciones (Intermedio/Profesional) --
        if self._adapter.opciones_avanzadas_visibles():
            grupo_trans = PropertyGroup("Transiciones", expandido=False)

            # Transición de entrada
            trans_in_layout = QHBoxLayout()
            trans_in_layout.addWidget(QLabel("Entrada:"))
            self._combo_trans_in = QComboBox()
            self._combo_trans_in.addItem("Ninguna", "")
            for ttype in ['fade_in', 'fade_from_color', 'crossfade', 'dissolve',
                          'wipe_left', 'zoom_in', 'iris_open', 'blur_transition']:
                name = TransitionType.DISPLAY_NAMES.get(ttype, ttype)
                self._combo_trans_in.addItem(name, ttype)
            # Set current
            current_in = clip.transition_in.get('type', '') if clip.transition_in else ''
            idx_in = self._combo_trans_in.findData(current_in)
            if idx_in >= 0:
                self._combo_trans_in.setCurrentIndex(idx_in)
            self._combo_trans_in.setStyleSheet(
                "QComboBox { background-color: #3B4148; color: #DEE2E6; "
                "border: 1px solid #495057; border-radius: 3px; padding: 2px 4px; }"
            )
            self._combo_trans_in.currentIndexChanged.connect(
                lambda idx: self._set_clip_transition(clip, 'in',
                    self._combo_trans_in.currentData())
            )
            trans_in_layout.addWidget(self._combo_trans_in)
            grupo_trans.agregar_layout(trans_in_layout)

            # Duración entrada
            if clip.transition_in:
                dur_in = SliderWithLabel("Duración entrada", 0.1, 5.0,
                                         clip.transition_in.get('duration', 1.0),
                                         decimales=1, paso=49)
                dur_in.value_changed.connect(
                    lambda v: self._set_transition_duration(clip, 'in', v))
                grupo_trans.agregar_widget(dur_in)

            # Transición de salida
            trans_out_layout = QHBoxLayout()
            trans_out_layout.addWidget(QLabel("Salida:"))
            self._combo_trans_out = QComboBox()
            self._combo_trans_out.addItem("Ninguna", "")
            for ttype in ['fade_out', 'fade_to_color', 'crossfade', 'dissolve',
                          'wipe_right', 'zoom_out', 'iris_close', 'blur_transition']:
                name = TransitionType.DISPLAY_NAMES.get(ttype, ttype)
                self._combo_trans_out.addItem(name, ttype)
            current_out = clip.transition_out.get('type', '') if clip.transition_out else ''
            idx_out = self._combo_trans_out.findData(current_out)
            if idx_out >= 0:
                self._combo_trans_out.setCurrentIndex(idx_out)
            self._combo_trans_out.setStyleSheet(
                "QComboBox { background-color: #3B4148; color: #DEE2E6; "
                "border: 1px solid #495057; border-radius: 3px; padding: 2px 4px; }"
            )
            self._combo_trans_out.currentIndexChanged.connect(
                lambda idx: self._set_clip_transition(clip, 'out',
                    self._combo_trans_out.currentData())
            )
            trans_out_layout.addWidget(self._combo_trans_out)
            grupo_trans.agregar_layout(trans_out_layout)

            # Duración salida
            if clip.transition_out:
                dur_out = SliderWithLabel("Duración salida", 0.1, 5.0,
                                          clip.transition_out.get('duration', 1.0),
                                          decimales=1, paso=49)
                dur_out.value_changed.connect(
                    lambda v: self._set_transition_duration(clip, 'out', v))
                grupo_trans.agregar_widget(dur_out)

            self._contenido_layout.addWidget(grupo_trans)

        self._contenido_layout.addStretch()

    def _set_clip_transition(self, clip: VideoClip, position: str, trans_type: str):
        """Establece o quita una transición en un clip desde el inspector."""
        if not trans_type:
            if position == 'in':
                clip.transition_in = None
            else:
                clip.transition_out = None
        else:
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
        self.preview_requested.emit()
        self.property_changed.emit(f"transition_{position}", trans_type)

    def _set_transition_duration(self, clip: VideoClip, position: str, duration: float):
        """Cambia la duración de una transición."""
        trans = clip.transition_in if position == 'in' else clip.transition_out
        if trans:
            trans['duration'] = duration
            self.preview_requested.emit()
            self.property_changed.emit(f"transition_{position}_duration", str(duration))

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

    # -- Mostrar propiedades de ModuleTimelineItem --------------------------------
    def mostrar_modulo_timeline(self, mod_item: 'ModuleTimelineItem',
                                 mod_instance=None, module_manager=None):
        """
        Muestra las propiedades editables de un módulo posicionado en el timeline.
        
        Args:
            mod_item: ModuleTimelineItem del timeline
            mod_instance: Instancia real del módulo (Module) si existe
            module_manager: ModuleManager para acceder a tipos de módulos
        """
        log = logging.getLogger("soundvi.qt6.inspector")
        log.debug("Showing module timeline item: %s (type: %s)", mod_item.name, mod_item.module_type)
        log.debug("Module instance provided: %s", mod_instance is not None)
        if mod_instance:
            log.debug("Instance type: %s", type(mod_instance).__name__)
            log.debug("Has get_config: %s", hasattr(mod_instance, 'get_config'))
        
        self._objeto_actual = mod_item
        self._limpiar_contenido()
        self._lbl_titulo.setText(f"Módulo: {mod_item.name}")
        self._btn_reset.setVisible(True)

        # -- Sección: Información general del módulo --
        grupo_info = PropertyGroup("Información", expandido=True)

        # Nombre editable
        nombre_layout = QHBoxLayout()
        nombre_layout.addWidget(QLabel("Nombre:"))
        edit_nombre = QLineEdit(mod_item.name)
        edit_nombre.setStyleSheet(
            "QLineEdit { background-color: #3B4148; color: #DEE2E6; "
            "border: 1px solid #495057; border-radius: 3px; padding: 2px 4px; }"
        )
        edit_nombre.editingFinished.connect(
            lambda: self._cambiar_propiedad_modulo_tl(mod_item, "name",
                                                       edit_nombre.text()))
        nombre_layout.addWidget(edit_nombre)
        grupo_info.agregar_layout(nombre_layout)

        # Tipo de módulo
        tipo_lbl = QLabel(f"Tipo: {mod_item.module_type}")
        tipo_lbl.setStyleSheet("color: #ADB5BD; font-size: 10px;")
        grupo_info.agregar_widget(tipo_lbl)

        # ID
        id_lbl = QLabel(f"ID: {mod_item.item_id}")
        id_lbl.setStyleSheet("color: #6C757D; font-size: 9px;")
        grupo_info.agregar_widget(id_lbl)

        self._contenido_layout.addWidget(grupo_info)

        # -- Sección: Posición temporal --
        grupo_tiempo = PropertyGroup("Posición temporal", expandido=True)

        tc_start = TimeCodeEdit("Inicio", mod_item.start_time)
        tc_start.time_changed.connect(
            lambda v: self._cambiar_propiedad_modulo_tl(mod_item, "start_time", v))
        grupo_tiempo.agregar_widget(tc_start)

        dur_slider = SliderWithLabel("Duración", 0.1, 300.0, mod_item.duration,
                                      decimales=2, paso=3000)
        dur_slider.slider_released.connect(lambda v: self._cambiar_propiedad_modulo_tl(mod_item, "duration", v))
        dur_slider.value_changed.connect(lambda v: self.preview_requested.emit())
        grupo_tiempo.agregar_widget(dur_slider)

        self._contenido_layout.addWidget(grupo_tiempo)

        # -- Sección: Estado --
        grupo_estado = PropertyGroup("Estado", expandido=True)

        chk_enabled = QCheckBox("Habilitado")
        chk_enabled.setChecked(mod_item.enabled)
        chk_enabled.stateChanged.connect(
            lambda s: self._cambiar_propiedad_modulo_tl(
                mod_item, "enabled", s == Qt.CheckState.Checked.value))
        grupo_estado.agregar_widget(chk_enabled)

        self._contenido_layout.addWidget(grupo_estado)

        # -- Sección: Parámetros del módulo (desde la instancia real) --
        config = {}
        if mod_instance is not None:
            log.debug("Getting config from module instance")
            if hasattr(mod_instance, 'get_config'):
                config = mod_instance.get_config()
                log.debug("Got config via get_config(): %d keys", len(config))
            elif hasattr(mod_instance, '_config'):
                config = dict(mod_instance._config)
                log.debug("Got config via _config: %d keys", len(config))
        # Fallback: usar params del ModuleTimelineItem
        if not config and mod_item.params:
            config = dict(mod_item.params)
            log.debug("Using params from ModuleTimelineItem: %d keys", len(config))
        
        log.debug("Final config to display: %d keys", len(config))
        if config:
            log.debug("Config keys: %s", list(config.keys()))

        if config:
            grupo_params = PropertyGroup("Parámetros del módulo", expandido=True)
            for clave, valor in config.items():
                if isinstance(valor, bool):
                    chk = QCheckBox(clave.replace("_", " ").title())
                    chk.setChecked(valor)
                    chk.stateChanged.connect(
                        lambda s, k=clave: self._cambiar_param_modulo_tl(
                            mod_item, mod_instance, k,
                            s == Qt.CheckState.Checked.value))
                    grupo_params.agregar_widget(chk)
                elif isinstance(valor, float):
                    # Rango inteligente
                    if 0.0 <= valor <= 1.0:
                        min_v, max_v = 0.0, 1.0
                    elif valor < 0:
                        min_v, max_v = valor * 3, abs(valor) * 3
                    else:
                        min_v, max_v = 0.0, max(valor * 3, 1.0)
                    slider = SliderWithLabel(clave.replace("_", " ").title(),
                                              min_v, max_v, valor, decimales=2)
                    slider.value_changed.connect(
                        lambda v, k=clave: self._cambiar_param_modulo_tl(
                            mod_item, mod_instance, k, v))
                    grupo_params.agregar_widget(slider)
                elif isinstance(valor, int):
                    spin_layout = QHBoxLayout()
                    spin_layout.addWidget(QLabel(clave.replace("_", " ").title()))
                    spin = QSpinBox()
                    spin.setRange(0, max(valor * 3, 100))
                    spin.setValue(valor)
                    spin.setStyleSheet(
                        "QSpinBox { background-color: #3B4148; color: #DEE2E6; "
                        "border: 1px solid #495057; border-radius: 3px; }"
                    )
                    spin.valueChanged.connect(
                        lambda v, k=clave: self._cambiar_param_modulo_tl(
                            mod_item, mod_instance, k, v))
                    spin_layout.addWidget(spin)
                    grupo_params.agregar_layout(spin_layout)
                elif isinstance(valor, str):
                    if valor.startswith("#") and len(valor) in (7, 9):
                        picker = ColorPickerWidget(clave.replace("_", " ").title(), valor)
                        picker.color_changed.connect(
                            lambda c, k=clave: self._cambiar_param_modulo_tl(
                                mod_item, mod_instance, k, c))
                        grupo_params.agregar_widget(picker)
                    else:
                        str_layout = QHBoxLayout()
                        str_layout.addWidget(QLabel(clave.replace("_", " ").title()))
                        edit = QLineEdit(valor)
                        edit.setStyleSheet(
                            "QLineEdit { background-color: #3B4148; color: #DEE2E6; "
                            "border: 1px solid #495057; border-radius: 3px; padding: 2px 4px; }"
                        )
                        edit.editingFinished.connect(
                            lambda k=clave, e=edit: self._cambiar_param_modulo_tl(
                                mod_item, mod_instance, k, e.text()))
                        str_layout.addWidget(edit)
                        grupo_params.agregar_layout(str_layout)

            self._contenido_layout.addWidget(grupo_params)

        # -- Sección: Widget de configuración nativo del módulo --
        if mod_instance is not None and hasattr(mod_instance, 'get_config_widgets'):
            try:
                grupo_nativo = PropertyGroup("Configuración avanzada", expandido=False)
                # Crear un objeto proxy para callbacks del módulo
                class _AppProxy:
                    def __init__(self, inspector):
                        self._inspector = inspector
                    def trigger_auto_save(self):
                        pass
                    def update_preview(self):
                        self._inspector.preview_requested.emit()

                proxy = _AppProxy(self)
                config_widget = mod_instance.get_config_widgets(
                    self._contenido, proxy
                )
                if config_widget:
                    grupo_nativo.agregar_widget(config_widget)
                    self._contenido_layout.addWidget(grupo_nativo)
            except Exception as e:
                log.debug("Error creando widgets nativos del módulo: %s", e)

        self._contenido_layout.addStretch()

    def _cambiar_propiedad_modulo_tl(self, mod_item, prop: str, valor):
        """Cambia una propiedad directa del ModuleTimelineItem."""
        setattr(mod_item, prop, valor)
        self.property_changed.emit(prop, valor)
        self.preview_requested.emit()

    def _cambiar_param_modulo_tl(self, mod_item, mod_instance, param: str, valor):
        """Cambia un parámetro del módulo y lo sincroniza con el ModuleTimelineItem."""
        # Guardar en params del item del timeline
        mod_item.params[param] = valor
        # Aplicar a la instancia real si existe
        if mod_instance is not None:
            if hasattr(mod_instance, '_config'):
                mod_instance._config[param] = valor
            if hasattr(mod_instance, 'set_config'):
                mod_instance.set_config({param: valor})
        self.property_changed.emit(param, valor)
        self.preview_requested.emit()

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
        elif isinstance(obj, ModuleTimelineItem):
            obj.enabled = True
            obj.params = {}
            self.mostrar_modulo_timeline(obj)

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
        elif isinstance(obj, ModuleTimelineItem):
            self.mostrar_modulo_timeline(obj)
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
