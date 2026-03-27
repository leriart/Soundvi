# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- Mezclador de Audio.

Panel con channel strips para cada track de audio, faders verticales,
pan control, mute/solo, VU meters y master fader.
Solo visible en perfiles Creador y Profesional.
Integrado con core/timeline.py (Track).
"""

from __future__ import annotations

import os
import sys
import logging
from typing import Optional, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QDial, QProgressBar, QFrame, QSizePolicy,
    QScrollArea, QGroupBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QColor, QPainter, QPen

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _RAIZ) if _RAIZ not in sys.path else None

from gui.qt6.base import ICONOS_UNICODE
from core.profiles import ProfileManager

log = logging.getLogger("soundvi.qt6.audio_mixer")


class VUMeterWidget(QProgressBar):
    """
    Widget personalizado de VU meter para indicador de nivel de audio.
    Muestra barras con colores verde/amarillo/rojo segun nivel.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setOrientation(Qt.Orientation.Vertical)
        self.setRange(0, 100)
        self.setValue(0)
        self.setTextVisible(False)
        self.setFixedWidth(12)
        self.setMinimumHeight(80)
        self.setStyleSheet("""
            QProgressBar {
                background-color: #212529;
                border: 1px solid #495057;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                border-radius: 2px;
            }
        """)
        self._nivel = 0

    def set_nivel(self, nivel: float):
        """Establece el nivel del VU meter (0.0 a 1.0)."""
        self._nivel = max(0.0, min(1.0, nivel))
        valor_int = int(self._nivel * 100)
        self.setValue(valor_int)

        # Cambiar color segun nivel
        if valor_int < 60:
            color = "#00BC8C"  # Verde
        elif valor_int < 85:
            color = "#F39C12"  # Amarillo
        else:
            color = "#E74C3C"  # Rojo

        self.setStyleSheet(f"""
            QProgressBar {{
                background-color: #212529;
                border: 1px solid #495057;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 2px;
            }}
        """)


class ChannelStripWidget(QFrame):
    """
    Channel strip individual para un track de audio.
    Incluye: nombre, VU meter, fader, pan, mute/solo.
    """

    # Senales
    volumen_changed = pyqtSignal(str, float)   # track_id, volumen (0.0 - 2.0)
    pan_changed = pyqtSignal(str, float)       # track_id, pan (-1.0 a 1.0)
    mute_changed = pyqtSignal(str, bool)       # track_id, muted
    solo_changed = pyqtSignal(str, bool)       # track_id, solo

    def __init__(self, track_id: str, track_name: str, track_color: str = "#2ecc71",
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._track_id = track_id
        self._track_name = track_name
        self._muted = False
        self._solo = False

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedWidth(80)
        self.setMinimumHeight(280)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #2B3035;
                border: 1px solid #495057;
                border-radius: 4px;
            }}
        """)

        self._construir_ui(track_color)

    def _construir_ui(self, color: str):
        """Construye la interfaz del channel strip."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # Nombre del track
        lbl_nombre = QLabel(self._track_name)
        lbl_nombre.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_nombre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_nombre.setStyleSheet(f"color: {color}; border: none;")
        lbl_nombre.setWordWrap(True)
        layout.addWidget(lbl_nombre)

        # VU Meters (L + R)
        vu_layout = QHBoxLayout()
        vu_layout.setSpacing(2)
        vu_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._vu_l = VUMeterWidget()
        self._vu_r = VUMeterWidget()
        vu_layout.addWidget(self._vu_l)
        vu_layout.addWidget(self._vu_r)
        layout.addLayout(vu_layout)

        # Fader de volumen (vertical)
        self._fader = QSlider(Qt.Orientation.Vertical)
        self._fader.setRange(0, 200)  # 0% a 200%
        self._fader.setValue(100)     # 100% = volumen normal
        self._fader.setTickPosition(QSlider.TickPosition.TicksBothSides)
        self._fader.setTickInterval(25)
        self._fader.setFixedHeight(100)
        self._fader.setToolTip("Volumen: 100%")
        self._fader.setStyleSheet("""
            QSlider::groove:vertical {
                width: 6px;
                background: #495057;
                border-radius: 3px;
            }
            QSlider::handle:vertical {
                background: #00BC8C;
                height: 14px;
                width: 20px;
                margin: 0 -7px;
                border-radius: 3px;
            }
            QSlider::handle:vertical:hover {
                background: #375A7F;
            }
            QSlider::sub-page:vertical {
                background: #495057;
            }
            QSlider::add-page:vertical {
                background: #00BC8C;
                border-radius: 3px;
            }
        """)
        self._fader.valueChanged.connect(self._on_fader_changed)
        layout.addWidget(self._fader, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Label de volumen
        self._lbl_vol = QLabel("100%")
        self._lbl_vol.setFont(QFont("Segoe UI", 8))
        self._lbl_vol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_vol.setStyleSheet("color: #ADB5BD; border: none;")
        layout.addWidget(self._lbl_vol)

        # Pan control (dial)
        lbl_pan = QLabel("Pan")
        lbl_pan.setFont(QFont("Segoe UI", 8))
        lbl_pan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_pan.setStyleSheet("color: #6C757D; border: none;")
        layout.addWidget(lbl_pan)

        self._pan = QDial()
        self._pan.setRange(-100, 100)
        self._pan.setValue(0)
        self._pan.setFixedSize(40, 40)
        self._pan.setNotchesVisible(True)
        self._pan.setToolTip("Pan: C (centro)")
        self._pan.valueChanged.connect(self._on_pan_changed)
        layout.addWidget(self._pan, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Botones Mute / Solo
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(2)

        self._btn_mute = QPushButton("M")
        self._btn_mute.setFixedSize(28, 24)
        self._btn_mute.setCheckable(True)
        self._btn_mute.setToolTip("Silenciar track")
        self._btn_mute.setStyleSheet("""
            QPushButton {
                background-color: #343A40;
                color: #ADB5BD;
                border: 1px solid #495057;
                border-radius: 3px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:checked {
                background-color: #E74C3C;
                color: #FFFFFF;
                border-color: #E74C3C;
            }
        """)
        self._btn_mute.clicked.connect(self._on_mute_clicked)
        btn_layout.addWidget(self._btn_mute)

        self._btn_solo = QPushButton("S")
        self._btn_solo.setFixedSize(28, 24)
        self._btn_solo.setCheckable(True)
        self._btn_solo.setToolTip("Solo (escuchar solo este track)")
        self._btn_solo.setStyleSheet("""
            QPushButton {
                background-color: #343A40;
                color: #ADB5BD;
                border: 1px solid #495057;
                border-radius: 3px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:checked {
                background-color: #F39C12;
                color: #212529;
                border-color: #F39C12;
            }
        """)
        self._btn_solo.clicked.connect(self._on_solo_clicked)
        btn_layout.addWidget(self._btn_solo)

        layout.addLayout(btn_layout)

    # -- Callbacks -------------------------------------------------------------

    def _on_fader_changed(self, valor: int):
        """Callback al mover el fader de volumen."""
        vol = valor / 100.0
        self._lbl_vol.setText(f"{valor}%")
        self._fader.setToolTip(f"Volumen: {valor}%")
        self.volumen_changed.emit(self._track_id, vol)

    def _on_pan_changed(self, valor: int):
        """Callback al mover el dial de pan."""
        pan = valor / 100.0
        if valor == 0:
            txt = "C"
        elif valor < 0:
            txt = f"L{abs(valor)}%"
        else:
            txt = f"R{valor}%"
        self._pan.setToolTip(f"Pan: {txt}")
        self.pan_changed.emit(self._track_id, pan)

    def _on_mute_clicked(self):
        """Callback al pulsar Mute."""
        self._muted = self._btn_mute.isChecked()
        self.mute_changed.emit(self._track_id, self._muted)

    def _on_solo_clicked(self):
        """Callback al pulsar Solo."""
        self._solo = self._btn_solo.isChecked()
        self.solo_changed.emit(self._track_id, self._solo)

    # -- API publica -----------------------------------------------------------

    def set_volumen(self, vol: float):
        """Establece el volumen (0.0 a 2.0)."""
        self._fader.blockSignals(True)
        self._fader.setValue(int(vol * 100))
        self._lbl_vol.setText(f"{int(vol * 100)}%")
        self._fader.blockSignals(False)

    def set_pan(self, pan: float):
        """Establece el pan (-1.0 a 1.0)."""
        self._pan.blockSignals(True)
        self._pan.setValue(int(pan * 100))
        self._pan.blockSignals(False)

    def set_muted(self, muted: bool):
        """Establece el estado de mute."""
        self._btn_mute.setChecked(muted)
        self._muted = muted

    def set_solo(self, solo: bool):
        """Establece el estado de solo."""
        self._btn_solo.setChecked(solo)
        self._solo = solo

    def actualizar_vu(self, nivel_l: float, nivel_r: float):
        """Actualiza los VU meters con niveles de audio (0.0 a 1.0)."""
        self._vu_l.set_nivel(nivel_l)
        self._vu_r.set_nivel(nivel_r)


class AudioMixerWidget(QFrame):
    """
    Mezclador de audio con channel strips para cada track.
    Incluye master fader y actualizacion en tiempo real de VU meters.
    Solo visible en perfiles Creador y Profesional.
    """

    # Senales
    track_volumen_changed = pyqtSignal(str, float)
    track_pan_changed = pyqtSignal(str, float)
    track_mute_changed = pyqtSignal(str, bool)
    track_solo_changed = pyqtSignal(str, bool)
    master_volumen_changed = pyqtSignal(float)

    def __init__(self, profile_manager: ProfileManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._pm = profile_manager
        self._strips: dict = {}  # track_id -> ChannelStripWidget
        self._master_strip = None

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._construir_ui()

        # Timer para simular actualizacion de VU meters
        self._vu_timer = QTimer()
        self._vu_timer.timeout.connect(self._actualizar_vu_meters)
        self._vu_timer.setInterval(50)  # ~20fps para VU meters

    # -- Construccion de UI ----------------------------------------------------

    def _construir_ui(self):
        """Construye la interfaz del mixer."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Titulo
        titulo = QLabel(f"{ICONOS_UNICODE['audio']}  Audio Mixer")
        titulo.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(titulo)

        # Area scrolleable para channel strips
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._strips_container = QWidget()
        self._strips_layout = QHBoxLayout(self._strips_container)
        self._strips_layout.setContentsMargins(0, 0, 0, 0)
        self._strips_layout.setSpacing(4)
        self._strips_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        scroll_area.setWidget(self._strips_container)
        layout.addWidget(scroll_area)

    # -- Gestion de tracks -----------------------------------------------------

    def cargar_desde_timeline(self, timeline):
        """
        Carga los channel strips desde un objeto Timeline.
        Crea un strip por cada track de audio.
        """
        # Limpiar strips existentes
        for strip in self._strips.values():
            strip.deleteLater()
        self._strips.clear()

        if self._master_strip:
            self._master_strip.deleteLater()
            self._master_strip = None

        # Limpiar layout
        while self._strips_layout.count():
            item = self._strips_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # Crear strips para tracks de audio
        audio_tracks = [t for t in timeline.tracks if t.track_type == "audio"]

        if not audio_tracks:
            lbl = QLabel("Sin tracks de audio")
            lbl.setStyleSheet("color: #6C757D; padding: 16px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._strips_layout.addWidget(lbl)
            return

        for track in audio_tracks:
            strip = ChannelStripWidget(
                track_id=track.track_id,
                track_name=track.name,
                track_color=track.color,
            )
            # Sincronizar estado inicial
            strip.set_volumen(track.volume)
            strip.set_pan(track.pan)
            strip.set_muted(track.muted)
            strip.set_solo(track.solo)

            # Conectar senales
            strip.volumen_changed.connect(self._on_track_volumen)
            strip.pan_changed.connect(self._on_track_pan)
            strip.mute_changed.connect(self._on_track_mute)
            strip.solo_changed.connect(self._on_track_solo)

            self._strips[track.track_id] = strip
            self._strips_layout.addWidget(strip)

        # Separador antes de master
        separador = QFrame()
        separador.setFrameShape(QFrame.Shape.VLine)
        separador.setStyleSheet("color: #495057;")
        self._strips_layout.addWidget(separador)

        # Master fader
        self._master_strip = ChannelStripWidget(
            track_id="__master__",
            track_name="MASTER",
            track_color="#E74C3C",
        )
        self._master_strip.volumen_changed.connect(
            lambda tid, v: self.master_volumen_changed.emit(v)
        )
        self._strips_layout.addWidget(self._master_strip)

        # Spacer al final
        self._strips_layout.addStretch()

    # -- Callbacks de strips ---------------------------------------------------

    def _on_track_volumen(self, track_id: str, vol: float):
        """Propaga cambio de volumen."""
        self.track_volumen_changed.emit(track_id, vol)

    def _on_track_pan(self, track_id: str, pan: float):
        """Propaga cambio de pan."""
        self.track_pan_changed.emit(track_id, pan)

    def _on_track_mute(self, track_id: str, muted: bool):
        """Propaga cambio de mute."""
        self.track_mute_changed.emit(track_id, muted)

    def _on_track_solo(self, track_id: str, solo: bool):
        """Propaga cambio de solo."""
        self.track_solo_changed.emit(track_id, solo)

    # -- VU Meters en tiempo real ----------------------------------------------

    def iniciar_monitoreo(self):
        """Inicia la actualizacion de VU meters."""
        self._vu_timer.start()

    def detener_monitoreo(self):
        """Detiene la actualizacion de VU meters."""
        self._vu_timer.stop()

    def _actualizar_vu_meters(self):
        """
        Actualiza los VU meters con datos simulados.
        En produccion, esto leeria los niveles de audio reales.
        """
        import random
        for strip in self._strips.values():
            # Simulacion de niveles de audio (en produccion: datos reales)
            nivel_l = random.uniform(0.1, 0.7) if not strip._muted else 0.0
            nivel_r = random.uniform(0.1, 0.7) if not strip._muted else 0.0
            strip.actualizar_vu(nivel_l, nivel_r)

        if self._master_strip:
            nivel_master = max(
                (s._vu_l._nivel + s._vu_r._nivel) / 2
                for s in self._strips.values()
            ) if self._strips else 0.0
            self._master_strip.actualizar_vu(nivel_master * 0.9, nivel_master * 0.95)

    def actualizar_niveles(self, niveles: dict):
        """
        Actualiza los VU meters con niveles reales.
        niveles: {track_id: (nivel_l, nivel_r)}
        """
        for track_id, (nivel_l, nivel_r) in niveles.items():
            if track_id in self._strips:
                self._strips[track_id].actualizar_vu(nivel_l, nivel_r)

    # -- Verificacion de perfil ------------------------------------------------

    def es_visible_para_perfil(self) -> bool:
        """Verifica si el mixer es visible para el perfil activo."""
        return self._pm.funcion_habilitada("audio_reactivo")
