# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- Dialogo de Exportacion de Video.

QDialog con configuracion completa de exportacion: codec, resolucion,
framerate, bitrate, audio, rango, progress bar y boton cancelar.
Integrado con core/video_generator.py.
"""

from __future__ import annotations

import os
import sys
import logging
import threading
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QWidget,
    QGroupBox, QFormLayout, QProgressBar, QFileDialog,
    QCheckBox, QRadioButton, QButtonGroup, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ZOUNDVI_DIR = os.path.join(_RAIZ, "multimedia", "zoundvi")
sys.path.insert(0, _RAIZ) if _RAIZ not in sys.path else None

from gui.qt6.base import ICONOS_UNICODE
from core.profiles import ProfileManager

log = logging.getLogger("soundvi.qt6.export_dialog")

# Presets de exportacion
_CODECS = {
    "H.264 (MP4)":  {"codec": "libx264",   "ext": ".mp4"},
    "H.265 (MP4)":  {"codec": "libx265",   "ext": ".mp4"},
    "VP9 (WebM)":   {"codec": "libvpx-vp9","ext": ".webm"},
    "ProRes (MOV)": {"codec": "prores_ks", "ext": ".mov"},
    "Solo Audio (MP3)": {"codec": "libmp3lame", "ext": ".mp3"},
    "Solo Audio (WAV)": {"codec": "pcm_s16le", "ext": ".wav"},
}

_RESOLUCIONES = {
    "4K (3840x2160)":    (3840, 2160),
    "1080p (1920x1080)": (1920, 1080),
    "720p (1280x720)":   (1280, 720),
    "480p (854x480)":    (854, 480),
    "Personalizada":     (0, 0),
}

_FRAMERATES = {
    "60 fps": 60,
    "30 fps": 30,
    "24 fps": 24,
    "25 fps": 25,
    "Personalizado": 0,
}

_AUDIO_CODECS = {
    "AAC":  "aac",
    "MP3":  "libmp3lame",
    "Opus": "libopus",
    "FLAC": "flac",
}


class ExportDialog(QDialog):
    """
    Dialogo de exportacion de video con configuracion avanzada,
    progress bar y posibilidad de cancelar.
    """

    # Senal emitida cuando se completa la exportacion
    exportacion_completada = pyqtSignal(str)   # ruta del archivo exportado
    exportacion_cancelada = pyqtSignal()

    def __init__(self, profile_manager: ProfileManager,
                 parent: Optional[QDialog] = None):
        super().__init__(parent)
        self._pm = profile_manager
        self._exportando = False
        self._cancelado = False
        self._progreso = 0.0

        self.setWindowTitle("Exportar Video")
        self.setMinimumSize(520, 620)
        self.setModal(True)

        self._construir_ui()
        self._aplicar_perfil()

    # -- Construccion de UI ----------------------------------------------------

    def _construir_ui(self):
        """Construye la interfaz del dialogo de exportacion."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # -- Grupo: Video --
        grp_video = QGroupBox("\u25A3  Configuracion de Video")
        form_video = QFormLayout(grp_video)
        form_video.setSpacing(6)

        # Codec
        self._combo_codec = QComboBox()
        self._combo_codec.addItems(list(_CODECS.keys()))
        self._combo_codec.setCurrentText("H.264 (MP4)")
        form_video.addRow("Codec:", self._combo_codec)

        # Resolucion
        self._combo_res = QComboBox()
        self._combo_res.addItems(list(_RESOLUCIONES.keys()))
        self._combo_res.setCurrentText("1080p (1920x1080)")
        self._combo_res.currentTextChanged.connect(self._on_res_changed)
        form_video.addRow("Resolucion:", self._combo_res)

        # Resolucion personalizada
        self._custom_res_widget = QHBoxLayout()
        self._spin_ancho = QSpinBox()
        self._spin_ancho.setRange(128, 7680)
        self._spin_ancho.setValue(1920)
        self._spin_ancho.setSuffix(" px")
        self._custom_res_widget_lbl = QLabel(" x ")
        self._spin_alto = QSpinBox()
        self._spin_alto.setRange(128, 4320)
        self._spin_alto.setValue(1080)
        self._spin_alto.setSuffix(" px")
        widget_res_custom = QWidget()
        lay_res = QHBoxLayout(widget_res_custom)
        lay_res.setContentsMargins(0, 0, 0, 0)
        lay_res.addWidget(self._spin_ancho)
        lay_res.addWidget(QLabel(" x "))
        lay_res.addWidget(self._spin_alto)
        self._widget_res_custom = widget_res_custom
        self._widget_res_custom.setVisible(False)
        form_video.addRow("", self._widget_res_custom)

        # Framerate
        self._combo_fps = QComboBox()
        self._combo_fps.addItems(list(_FRAMERATES.keys()))
        self._combo_fps.setCurrentText("30 fps")
        self._combo_fps.currentTextChanged.connect(self._on_fps_changed)
        form_video.addRow("Framerate:", self._combo_fps)

        # FPS personalizado
        self._spin_fps_custom = QSpinBox()
        self._spin_fps_custom.setRange(1, 240)
        self._spin_fps_custom.setValue(30)
        self._spin_fps_custom.setSuffix(" fps")
        self._spin_fps_custom.setVisible(False)
        form_video.addRow("", self._spin_fps_custom)

        # Calidad / Bitrate
        self._combo_calidad = QComboBox()
        self._combo_calidad.addItems(["Alta (CRF 18)", "Media (CRF 23)", "Baja (CRF 28)",
                                       "Personalizada"])
        self._combo_calidad.setCurrentText("Media (CRF 23)")
        form_video.addRow("Calidad:", self._combo_calidad)

        layout.addWidget(grp_video)

        # -- Grupo: Audio --
        grp_audio = QGroupBox(f"{ICONOS_UNICODE['audio']}  Configuracion de Audio")
        form_audio = QFormLayout(grp_audio)
        form_audio.setSpacing(6)

        self._combo_audio_codec = QComboBox()
        self._combo_audio_codec.addItems(list(_AUDIO_CODECS.keys()))
        self._combo_audio_codec.setCurrentText("AAC")
        form_audio.addRow("Codec audio:", self._combo_audio_codec)

        self._combo_audio_bitrate = QComboBox()
        self._combo_audio_bitrate.addItems(["320k", "256k", "192k", "128k", "96k"])
        self._combo_audio_bitrate.setCurrentText("192k")
        form_audio.addRow("Bitrate audio:", self._combo_audio_bitrate)

        self._combo_sample_rate = QComboBox()
        self._combo_sample_rate.addItems(["48000 Hz", "44100 Hz", "22050 Hz"])
        self._combo_sample_rate.setCurrentText("44100 Hz")
        form_audio.addRow("Sample rate:", self._combo_sample_rate)

        layout.addWidget(grp_audio)

        # -- Grupo: Rango --
        grp_rango = QGroupBox("\u2194  Rango de Exportacion")
        lay_rango = QVBoxLayout(grp_rango)

        self._radio_todo = QRadioButton("Exportar todo el proyecto")
        self._radio_todo.setChecked(True)
        lay_rango.addWidget(self._radio_todo)

        self._radio_seleccion = QRadioButton("Exportar seleccion")
        lay_rango.addWidget(self._radio_seleccion)

        self._radio_inout = QRadioButton("Exportar entre In/Out points")
        lay_rango.addWidget(self._radio_inout)

        self._btn_group_rango = QButtonGroup()
        self._btn_group_rango.addButton(self._radio_todo)
        self._btn_group_rango.addButton(self._radio_seleccion)
        self._btn_group_rango.addButton(self._radio_inout)

        layout.addWidget(grp_rango)

        # -- Archivo de salida --
        grp_salida = QGroupBox("➡  Archivo de Salida")
        lay_salida = QHBoxLayout(grp_salida)

        self._txt_salida = QLineEdit()
        self._txt_salida.setPlaceholderText("Ruta del archivo de salida...")
        lay_salida.addWidget(self._txt_salida, 4)

        btn_examinar = QPushButton("\u2026 Examinar")
        btn_examinar.clicked.connect(self._examinar_salida)
        lay_salida.addWidget(btn_examinar, 1)

        layout.addWidget(grp_salida)

        # -- Estimacion --
        self._lbl_estimacion = QLabel("Tamano estimado: --")
        self._lbl_estimacion.setStyleSheet("color: #ADB5BD; font-size: 11px; padding: 4px;")
        layout.addWidget(self._lbl_estimacion)

        # -- Progress bar --
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setFormat("%p% completado")
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # -- Zoundvi status (rendering/success/error) --
        self._zoundvi_frame = QFrame()
        self._zoundvi_frame.setVisible(False)
        zv_layout = QHBoxLayout(self._zoundvi_frame)
        zv_layout.setContentsMargins(0, 4, 0, 4)
        self._lbl_zoundvi_img = QLabel()
        self._lbl_zoundvi_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zv_layout.addStretch()
        zv_layout.addWidget(self._lbl_zoundvi_img)
        self._lbl_zoundvi_txt = QLabel()
        self._lbl_zoundvi_txt.setFont(QFont("Consolas", 10))
        self._lbl_zoundvi_txt.setStyleSheet("color: #8CD47E;")
        zv_layout.addWidget(self._lbl_zoundvi_txt)
        zv_layout.addStretch()
        layout.addWidget(self._zoundvi_frame)

        # -- Botones --
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        btn_layout.addStretch()

        self._btn_cancelar = QPushButton("Cancelar")
        self._btn_cancelar.clicked.connect(self._on_cancelar)
        btn_layout.addWidget(self._btn_cancelar)

        self._btn_exportar = QPushButton(f"{ICONOS_UNICODE['export']}  Exportar")
        self._btn_exportar.setStyleSheet("""
            QPushButton {
                background-color: #00BC8C;
                color: #FFFFFF;
                font-weight: bold;
                padding: 8px 24px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #00A67A; }
            QPushButton:disabled { background-color: #495057; color: #6C757D; }
        """)
        self._btn_exportar.clicked.connect(self._on_exportar)
        btn_layout.addWidget(self._btn_exportar)

        layout.addLayout(btn_layout)

    # -- Callbacks de UI -------------------------------------------------------

    def _on_res_changed(self, texto: str):
        """Muestra/oculta resolucion personalizada."""
        self._widget_res_custom.setVisible(texto == "Personalizada")

    def _on_fps_changed(self, texto: str):
        """Muestra/oculta FPS personalizado."""
        self._spin_fps_custom.setVisible(texto == "Personalizado")

    def _examinar_salida(self):
        """Abre dialogo para seleccionar ruta de salida."""
        codec_info = _CODECS.get(self._combo_codec.currentText(), {})
        ext = codec_info.get("ext", ".mp4")

        filtros = {
            ".mp4": "MP4 (*.mp4)",
            ".webm": "WebM (*.webm)",
            ".mov": "MOV (*.mov)",
            ".mp3": "MP3 Audio (*.mp3)",
            ".wav": "WAV Audio (*.wav)",
        }
        filtro = filtros.get(ext, "Video (*.*)")

        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar video como", "", filtro
        )
        if ruta:
            if not ruta.endswith(ext):
                ruta += ext
            self._txt_salida.setText(ruta)

    # -- Exportacion -----------------------------------------------------------

    def _mostrar_zoundvi(self, imagen: str, texto: str, color: str = "#8CD47E"):
        """Muestra una imagen de Zoundvi con texto de estado."""
        ruta = os.path.join(_ZOUNDVI_DIR, imagen)
        if os.path.isfile(ruta):
            px = QPixmap(ruta).scaled(
                64, 64, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            self._lbl_zoundvi_img.setPixmap(px)
        self._lbl_zoundvi_txt.setText(texto)
        self._lbl_zoundvi_txt.setStyleSheet(f"color: {color};")
        self._zoundvi_frame.setVisible(True)

    def _ocultar_zoundvi(self):
        """Oculta el widget de Zoundvi."""
        self._zoundvi_frame.setVisible(False)

    def _on_exportar(self):
        """Inicia el proceso de exportacion."""
        import random
        ruta_salida = self._txt_salida.text().strip()
        if not ruta_salida:
            errores_ruta = [
                "Oe, selecciona una ruta de salida primero.",
                "¿A dónde quieres que guarde el video? ¿En el aire?",
                "Error 404: Ruta de salida not found",
                "Bro, necesito una ruta. No soy adivino.",
                "Exportar a la nada... interesante concepto, pero no.",
                "Missing: output path. Reward if found.",
            ]
            QMessageBox.warning(self, "Wait a minute...", random.choice(errores_ruta))
            return

        self._exportando = True
        self._cancelado = False
        self._btn_exportar.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setValue(0)

        # Mostrar Zoundvi renderizando
        mensajes_render = [
            "Renderizando... anda por un café (o 5).",
            "Procesando video... esto va a tardar.",
            "Exportando... tu PC está sufriendo ahora mismo.",
            "Rendering in progress... FFmpeg está dando todo.",
            "Convirtiendo bits en arte... o eso intenta.",
            "Compilando pixeles... rezale a tu GPU.",
        ]
        self._mostrar_zoundvi(
            "zoundvi_coffee.png",
            random.choice(mensajes_render),
            "#E8842C"
        )

        # Obtener configuracion
        config = self.get_config()
        log.info("Iniciando exportacion: %s", config)

        # Simulacion de exportacion (en produccion: usar video_generator)
        self._timer_export = QTimer()
        self._timer_export.timeout.connect(self._simular_progreso)
        self._timer_export.start(100)

    def _simular_progreso(self):
        """Simula progreso de exportacion para demo."""
        if self._cancelado:
            self._timer_export.stop()
            self._progress.setValue(0)
            self._progress.setVisible(False)
            self._btn_exportar.setEnabled(True)
            self._exportando = False
            # Zoundvi error en cancelacion
            mensajes_cancel = [
                "Exportación cancelada. Zoundvi llora. ",
                "Cancelado. Todo ese render pa' nada.",
                "Export aborted. Tu GPU respira aliviada.",
                "Cancelaste? Cobarde. (╯°□°)╯︵ ┻━┻",
                "Cancelado. F por el tiempo perdido.",
                "Render cancelled. Zoundvi está decepcionado.",
            ]
            self._mostrar_zoundvi(
                "zoundvi_toilet.png",
                random.choice(mensajes_cancel),
                "#FF4444"
            )
            self.exportacion_cancelada.emit()
            return

        self._progreso += 1.5
        if self._progreso >= 100:
            self._progreso = 100
            self._timer_export.stop()
            self._progress.setValue(100)
            self._exportando = False
            self._btn_exportar.setEnabled(True)

            # Zoundvi celebrando
            mensajes_exito = [
                "¡Exportación exitosa! Milagro divino. 2605",
                "Done! Tu PC sobrevivió. GG.",
                "Success! Ni yo me la creía. 2605",
                "Completado! Achievement unlocked.",
                "Terminado! FFmpeg es un dios.",
                "Export complete! Tu paciencia valió la pena.",
            ]
            self._mostrar_zoundvi(
                "zoundvi_logo.png",
                random.choice(mensajes_exito),
                "#4CAF50"
            )

            ruta = self._txt_salida.text().strip()
            self.exportacion_completada.emit(ruta)

            # Dialogo con Zoundvi success
            import random
            msg = QMessageBox(self)
            
            # Títulos aleatorios de éxito
            titulos_success = [
                "¡Exportación completada! 2605",
                "¡GG WP! Video exportado",
                "Achievement Unlocked: Video Renderer",
                "Success! (milagrosamente)",
                "¡Lo lograste, campeón! 2605",
                "Task failed successfully... wait, no"
            ]
            
            # Mensajes informativos random
            info_success = [
                "Zoundvi está orgulloso de ti (por primera vez).",
                "Zoundvi no se lo cree. Tú tampoco, ¿verdad?",
                "Tu PC sobrevivió. Felicidades.",
                "FFmpeg hizo su magia. Todos aplaudan. ",
                "Ni tu RAM sabe cómo sobrevivió a esto.",
                "Plot twist: funcionó a la primera. (Mentira, fue al 3er intento)",
                "Speedrun Any% - Video Exported: ✓",
                "Tu GPU te odia, pero lo lograste.",
            ]
            
            msg.setWindowTitle(random.choice(titulos_success))
            msg.setText(f"Video exportado exitosamente:\n{ruta}")
            msg.setInformativeText(random.choice(info_success))
            _success_path = os.path.join(_ZOUNDVI_DIR, "zoundvi_logo.png")
            if os.path.isfile(_success_path):
                px = QPixmap(_success_path).scaled(
                    64, 64, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
                msg.setIconPixmap(px)
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            # Botones random de celebración
            btn_ok_texts = ["¡Chingón!", "Let's goooo!", "Épico", "Nice", "Based", "POG", "Sheesh 2022"]
            msg.button(QMessageBox.StandardButton.Ok).setText(random.choice(btn_ok_texts))
            msg.exec()
            self.accept()
        else:
            self._progress.setValue(int(self._progreso))

    def _on_cancelar(self):
        """Cancela la exportacion o cierra el dialogo."""
        if self._exportando:
            self._cancelado = True
        else:
            self.reject()

    def set_progress(self, valor: float):
        """Establece el progreso de exportacion externamente (0-100)."""
        self._progress.setValue(int(valor))
        if valor >= 100:
            self._exportando = False
            self._btn_exportar.setEnabled(True)

    # -- Perfil ----------------------------------------------------------------

    def _aplicar_perfil(self):
        """Opciones avanzadas solo en perfil Profesional."""
        avanzado = self._pm.funcion_habilitada("exportacion_avanzada")

        # Codecs avanzados
        if not avanzado:
            # Ocultar ProRes y VP9 para perfiles basicos
            for i in range(self._combo_codec.count()):
                texto = self._combo_codec.itemText(i)
                if "ProRes" in texto or "VP9" in texto:
                    # No se puede ocultar items en QComboBox facilmente
                    # pero se podria reconstruir
                    pass

    # -- API publica -----------------------------------------------------------

    def get_config(self) -> dict:
        """Retorna la configuracion de exportacion actual."""
        codec_info = _CODECS.get(self._combo_codec.currentText(), {})
        res_info = _RESOLUCIONES.get(self._combo_res.currentText(), (1920, 1080))
        fps_info = _FRAMERATES.get(self._combo_fps.currentText(), 30)

        ancho, alto = res_info
        if ancho == 0:
            ancho = self._spin_ancho.value()
            alto = self._spin_alto.value()

        if fps_info == 0:
            fps_info = self._spin_fps_custom.value()

        audio_codec = _AUDIO_CODECS.get(self._combo_audio_codec.currentText(), "aac")
        audio_bitrate = self._combo_audio_bitrate.currentText()
        sample_rate = int(self._combo_sample_rate.currentText().replace(" Hz", ""))

        rango = "todo"
        if self._radio_seleccion.isChecked():
            rango = "seleccion"
        elif self._radio_inout.isChecked():
            rango = "inout"

        return {
            "codec": codec_info.get("codec", "libx264"),
            "extension": codec_info.get("ext", ".mp4"),
            "width": ancho,
            "height": alto,
            "fps": fps_info,
            "calidad": self._combo_calidad.currentText(),
            "audio_codec": audio_codec,
            "audio_bitrate": audio_bitrate,
            "sample_rate": sample_rate,
            "rango": rango,
            "output_path": self._txt_salida.text().strip(),
        }
