# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- Widget de preview de video.

Proporciona un reproductor de video integrado con controles de reproduccion,
scrubber temporal y display de frames.  Usa QLabel + QImage para mostrar
frames renderizados por el motor de Soundvi (sin dependencia de QMediaPlayer
para maxima compatibilidad con el pipeline de render existente).
"""

from __future__ import annotations

import os
import sys
import time
import logging
from typing import Optional

import numpy as np
import cv2

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QFrame, QSizePolicy, QStyle, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QFont, QPainter, QColor

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _RAIZ) if _RAIZ not in sys.path else None

from gui.qt6.base import ICONOS_UNICODE

log = logging.getLogger("soundvi.qt6.preview")


def _formatear_tiempo(segundos: float) -> str:
    """Formatea segundos a MM:SS.mmm"""
    m = int(segundos // 60)
    s = int(segundos % 60)
    ms = int((segundos % 1) * 1000)
    return f"{m:02d}:{s:02d}.{ms:03d}"


class DisplayFrame(QLabel):
    """
    Widget que muestra un frame de video (numpy array BGR o QImage).
    Mantiene aspect ratio y centra el contenido.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(QSize(320, 180))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("""
            QLabel {
                background-color: #000000;
                border: 1px solid #343A40;
                border-radius: 4px;
            }
        """)
        self._frame_actual: Optional[QPixmap] = None
        self._mostrar_placeholder()

    def _mostrar_placeholder(self):
        """Muestra un mensaje cuando no hay video cargado."""
        self.setText("Sin video cargado\n\nImporta un archivo para comenzar")
        self.setStyleSheet("""
            QLabel {
                background-color: #111111;
                color: #495057;
                font-size: 14px;
                border: 2px dashed #343A40;
                border-radius: 8px;
            }
        """)

    def mostrar_frame_numpy(self, frame: np.ndarray):
        """
        Muestra un frame desde un numpy array BGR (OpenCV format).
        Convierte a QImage y escala manteniendo aspect ratio.
        """
        if frame is None or frame.size == 0:
            return

        h, w = frame.shape[:2]
        canales = frame.shape[2] if len(frame.shape) == 3 else 1

        if canales == 3:
            # BGR -> RGB
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            qimg = QImage(rgb.data, w, h, w * 3, QImage.Format.Format_RGB888)
        elif canales == 4:
            rgba = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGBA)
            qimg = QImage(rgba.data, w, h, w * 4, QImage.Format.Format_RGBA8888)
        else:
            qimg = QImage(frame.data, w, h, w, QImage.Format.Format_Grayscale8)

        pixmap = QPixmap.fromImage(qimg)
        self._mostrar_pixmap(pixmap)

    def mostrar_qimage(self, qimg: QImage):
        """Muestra un QImage directamente."""
        pixmap = QPixmap.fromImage(qimg)
        self._mostrar_pixmap(pixmap)

    def _mostrar_pixmap(self, pixmap: QPixmap):
        """Escala y muestra un QPixmap manteniendo aspect ratio."""
        self._frame_actual = pixmap
        escalado = pixmap.scaled(
            self.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(escalado)
        # Restaurar estilo normal
        self.setStyleSheet("""
            QLabel {
                background-color: #000000;
                border: 1px solid #343A40;
                border-radius: 4px;
            }
        """)

    def resizeEvent(self, event):
        """Reescala el frame al redimensionar el widget."""
        if self._frame_actual:
            escalado = self._frame_actual.scaled(
                event.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.setPixmap(escalado)
        super().resizeEvent(event)


class PreviewWidget(QWidget):
    """
    Widget completo de preview con:
      - Display de frames (DisplayFrame)
      - Controles de reproduccion (play/pause/stop)
      - Scrubber temporal (slider)
      - Display de tiempo actual / duracion total
    """

    # Senales
    tiempo_cambiado = pyqtSignal(float)   # tiempo actual en segundos
    play_toggled = pyqtSignal(bool)        # True=playing, False=paused
    stop_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._reproduciendo = False
        self._tiempo_actual = 0.0
        self._duracion_total = 0.0
        self._fps = 30
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._timeline = None
        self._audio_player = None

        # Inicializar reproductor de audio
        try:
            from core.audio_player import AudioPlayer
            self._audio_player = AudioPlayer()
        except Exception as e:
            log.warning("No se pudo inicializar AudioPlayer: %s", e)

        self._construir_ui()

    def set_timeline(self, timeline):
        """Establece el timeline para sincronizar audio."""
        self._timeline = timeline
    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Display de frames
        self._display = DisplayFrame()
        layout.addWidget(self._display, stretch=1)

        # Scrubber
        scrubber_layout = QHBoxLayout()
        scrubber_layout.setSpacing(8)

        self._lbl_tiempo = QLabel("00:00.000")
        self._lbl_tiempo.setFont(QFont("Consolas", 10))
        self._lbl_tiempo.setMinimumWidth(80)
        self._lbl_tiempo.setStyleSheet("color: #00BC8C;")
        scrubber_layout.addWidget(self._lbl_tiempo)

        self._scrubber = QSlider(Qt.Orientation.Horizontal)
        self._scrubber.setRange(0, 10000)  # 0 a 10000 para precision
        self._scrubber.setValue(0)
        self._scrubber.sliderMoved.connect(self._on_scrub)
        self._scrubber.setToolTip("Posicion temporal")
        scrubber_layout.addWidget(self._scrubber)

        self._lbl_duracion = QLabel("00:00.000")
        self._lbl_duracion.setFont(QFont("Consolas", 10))
        self._lbl_duracion.setMinimumWidth(80)
        self._lbl_duracion.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._lbl_duracion.setStyleSheet("color: #ADB5BD;")
        scrubber_layout.addWidget(self._lbl_duracion)

        layout.addLayout(scrubber_layout)

        # Controles de reproduccion
        controles = QHBoxLayout()
        controles.setSpacing(4)
        controles.addStretch()

        estilo_btn = """
            QPushButton {
                background-color: #343A40;
                color: #DEE2E6;
                border: 1px solid #495057;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 18px;
                min-width: 40px;
            }
            QPushButton:hover {
                background-color: #495057;
                border-color: #00BC8C;
            }
            QPushButton:pressed {
                background-color: #00BC8C;
                color: #FFFFFF;
            }
        """

        # Retroceder
        self._btn_backward = QPushButton(ICONOS_UNICODE["backward"])
        self._btn_backward.setToolTip("Retroceder 5s")
        self._btn_backward.setStyleSheet(estilo_btn)
        self._btn_backward.clicked.connect(self._retroceder)
        controles.addWidget(self._btn_backward)

        # Stop
        self._btn_stop = QPushButton(ICONOS_UNICODE["stop"])
        self._btn_stop.setToolTip("Detener")
        self._btn_stop.setStyleSheet(estilo_btn)
        self._btn_stop.clicked.connect(self._detener)
        controles.addWidget(self._btn_stop)

        # Play / Pause
        self._btn_play = QPushButton(ICONOS_UNICODE["play"])
        self._btn_play.setToolTip("Reproducir / Pausar")
        self._btn_play.setStyleSheet("""
            QPushButton {
                background-color: #00BC8C;
                color: #FFFFFF;
                border: none;
                border-radius: 20px;
                padding: 8px 16px;
                font-size: 22px;
                min-width: 50px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #00A37A;
            }
            QPushButton:pressed {
                background-color: #008F6B;
            }
        """)
        self._btn_play.clicked.connect(self._toggle_play)
        controles.addWidget(self._btn_play)

        # Avanzar
        self._btn_forward = QPushButton(ICONOS_UNICODE["forward"])
        self._btn_forward.setToolTip("Avanzar 5s")
        self._btn_forward.setStyleSheet(estilo_btn)
        self._btn_forward.clicked.connect(self._avanzar)
        controles.addWidget(self._btn_forward)

        controles.addStretch()

        # Info de frame
        self._lbl_frame_info = QLabel("Frame: 0 / 0")
        self._lbl_frame_info.setFont(QFont("Consolas", 9))
        self._lbl_frame_info.setStyleSheet("color: #6C757D;")
        controles.addWidget(self._lbl_frame_info)
        
        # Separador
        controles.addSpacing(10)
        
        # Control de FPS
        fps_label = QLabel("FPS:")
        fps_label.setFont(QFont("Consolas", 9))
        fps_label.setStyleSheet("color: #6C757D;")
        controles.addWidget(fps_label)
        
        self._fps_combo = QComboBox()
        self._fps_combo.addItems(["15", "24", "30", "60", "120"])
        self._fps_combo.setCurrentText("30")
        self._fps_combo.setFixedWidth(60)
        self._fps_combo.setStyleSheet("""
            QComboBox {
                background-color: #343A40;
                color: #DEE2E6;
                border: 1px solid #495057;
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 11px;
            }
            QComboBox:hover {
                border-color: #00BC8C;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #DEE2E6;
            }
        """)
        self._fps_combo.currentTextChanged.connect(self._on_fps_changed)
        controles.addWidget(self._fps_combo)

        layout.addLayout(controles)

    # -- Control de reproduccion -----------------------------------------------
    def _on_fps_changed(self, fps_text: str):
        """Cambia el FPS de reproduccion."""
        try:
            new_fps = int(fps_text)
            if new_fps != self._fps:
                self._fps = new_fps
                # Si esta reproduciendo, actualizar el timer
                if self._reproduciendo:
                    self._timer.stop()
                    intervalo = max(1, int(1000 / self._fps))
                    self._timer.start(intervalo)
                # Actualizar informacion de frames
                self._actualizar_info_frames()
        except ValueError:
            pass  # Ignorar valores no numericos

    def _toggle_play(self):
        if self._reproduciendo:
            self._pausar()
        else:
            self._reproducir()
            
            # Sincronizar audio con video
            self._sync_audio_playback()

    def _reproducir(self):
        self._reproduciendo = True
        self._btn_play.setText(ICONOS_UNICODE["pause"])
        self._btn_play.setToolTip("Pausar")
        intervalo = max(1, int(1000 / self._fps))
        self._timer.start(intervalo)
        self.play_toggled.emit(True)

    def _pausar(self):
        self._reproduciendo = False
        self._btn_play.setText(ICONOS_UNICODE["play"])
        self._btn_play.setToolTip("Reproducir")
        self._timer.stop()
        self._pause_audio()
        self.play_toggled.emit(False)

    def _detener(self):
        self._pausar()
        self._stop_audio()
        self._tiempo_actual = 0.0
        self._actualizar_ui_tiempo()
        self.stop_signal.emit()

    def _retroceder(self):
        self._tiempo_actual = max(0, self._tiempo_actual - 5.0)
        self._actualizar_ui_tiempo()
        self.tiempo_cambiado.emit(self._tiempo_actual)

    def _avanzar(self):
        self._tiempo_actual = min(self._duracion_total, self._tiempo_actual + 5.0)
        self._actualizar_ui_tiempo()
        self.tiempo_cambiado.emit(self._tiempo_actual)

    def _tick(self):
        """Llamado por el timer durante la reproduccion."""
        paso = 1.0 / self._fps
        self._tiempo_actual += paso
        if self._duracion_total > 0 and self._tiempo_actual >= self._duracion_total:
            self._tiempo_actual = self._duracion_total
            self._pausar()
        self._actualizar_ui_tiempo()
        self.tiempo_cambiado.emit(self._tiempo_actual)

    def _on_scrub(self, valor: int):
        """Llamado cuando el usuario mueve el scrubber."""
        if self._duracion_total > 0:
            self._tiempo_actual = (valor / 10000.0) * self._duracion_total
        else:
            self._tiempo_actual = 0.0
        self._actualizar_ui_tiempo(actualizar_slider=False)
        self.tiempo_cambiado.emit(self._tiempo_actual)

    def _actualizar_ui_tiempo(self, actualizar_slider: bool = True):
        """Actualiza labels y slider con el tiempo actual."""
        self._lbl_tiempo.setText(_formatear_tiempo(self._tiempo_actual))
        if actualizar_slider and self._duracion_total > 0:
            pos = int((self._tiempo_actual / self._duracion_total) * 10000)
            self._scrubber.blockSignals(True)
            self._scrubber.setValue(pos)
            self._scrubber.blockSignals(False)

        self._actualizar_info_frames()

    def _actualizar_info_frames(self):
        """Actualiza la informacion de frames en la UI."""
        frame_num = int(self._tiempo_actual * self._fps)
        total_frames = int(self._duracion_total * self._fps) if self._duracion_total > 0 else 0
        self._lbl_frame_info.setText(
            f"Frame: {frame_num} / {total_frames}"
        )

    # -- API publica -----------------------------------------------------------
    def set_duracion(self, duracion: float, fps: int = 30):
        """Establece la duracion total del video."""
        self._duracion_total = duracion
        # Solo actualizar FPS si no se ha seleccionado uno manualmente
        if not hasattr(self, '_fps_combo') or self._fps_combo.currentText() == "30":
            self._fps = fps
        self._lbl_duracion.setText(_formatear_tiempo(duracion))
        self._actualizar_ui_tiempo()

    def mostrar_frame(self, frame: np.ndarray):
        """Muestra un frame numpy BGR en el display."""
        self._display.mostrar_frame_numpy(frame)

    def get_tiempo_actual(self) -> float:
        return self._tiempo_actual

    def set_tiempo(self, tiempo: float):
        self._tiempo_actual = tiempo
        self._actualizar_ui_tiempo()

    @property
    def display(self) -> DisplayFrame:
        return self._display

    # Metodos publicos para control de reproduccion
    def play(self):
        """Inicia la reproduccion."""
        self._reproducir()

    def pause(self):
        """Pausa la reproduccion."""
        self._pausar()

    def stop(self):
        """Detiene la reproduccion."""
        self._detener()

    def toggle_play(self):
        """Alterna entre reproducir y pausar."""
        self._toggle_play()

    def is_playing(self) -> bool:
        """Retorna True si esta reproduciendo."""
        return self._reproduciendo
    def _sync_audio_playback(self):
        """Sincroniza la reproducción de audio con la posición del playhead."""
        if self._timeline is None or self._audio_player is None:
            return

        if self._reproduciendo:
            playhead_time = self._tiempo_actual
            
            # Obtener todos los clips de audio activos en este tiempo
            audio_clips = self._timeline.get_audio_clips_at_time(playhead_time)
            
            if audio_clips:
                self._audio_player.play_clips_at_time(audio_clips, playhead_time)
            else:
                self._audio_player.stop()
        else:
            self._audio_player.stop()

    def _stop_audio(self):
        """Detiene toda la reproducción de audio."""
        if self._audio_player is not None:
            self._audio_player.stop(fade_out_ms=50)

    def _pause_audio(self):
        """Pausa la reproducción de audio."""
        if self._audio_player is not None:
            self._audio_player.pause()

    def _resume_audio(self):
        """Reanuda la reproducción de audio."""
        if self._audio_player is not None:
            self._audio_player.resume()
