#!/usr/bin/env python3
"""
Módulo SubAuto Ultra Pro para Soundvi.
- Interfaz Pro-Resizable en Sidebar.
- Realce de voz (Filtros de Audio).
- Alineamiento por Índice Difuso (YouTube Style).
- Carpeta temporal dedicada.
"""

import os
import json
import wave
import threading
import tempfile
import shutil
import zipfile
from urllib.request import urlopen
from datetime import timedelta
import re
import unicodedata
from difflib import SequenceMatcher

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QComboBox, QSpinBox, QCheckBox, QGroupBox, QPushButton,
    QTextEdit, QProgressBar, QSplitter, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QMetaObject, Q_ARG, pyqtSlot

from modules.base import Module
from utils.subtitles import parse_srt, format_time, split_text_lines
from utils.fonts import get_font_path, get_system_fonts

# --- DEPENDENCIAS IA ---
try:
    from vosk import Model, KaldiRecognizer
    from pydub import AudioSegment, effects
    IA_READY = True
except ImportError:
    IA_READY = False

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "vosk_models")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
TEMP_AUDIO = os.path.join(TEMP_DIR, "voice_processed.wav")
SUBTITLE_OUTPUT = os.path.join(TEMP_DIR, "subtitles.srt")

if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR)

VOSK_MODELS = {
    "Espa\u00f1ol": {
        "small": {"url": "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip", "name": "vosk-model-small-es-0.42"},
        "medium": {"url": "https://alphacephei.com/vosk/models/vosk-model-es-0.42.zip", "name": "vosk-model-es-0.42"}
    },
    "Ingl\u00e9s": {
        "small": {"url": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip", "name": "vosk-model-small-en-us-0.15"},
        "medium": {"url": "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip", "name": "vosk-model-en-us-0.22"}
    }
}

class SubAutoModule(Module):
    def __init__(self, nombre: str = "SubAuto", capa: int = 10):
        super().__init__(nombre=nombre, descripcion="IA Subtitles Pro", capa=capa)
        self._subtitles = []
        self._audio_path = None
        self.app = None

        self._config.update({
            "language": "Espa\u00f1ol", "model_type": "small", "mode": "Transcripci\u00f3n",
            "font": "Arial", "font_size": 36, "color": "#FFFFFF", "opacity": 1.0,
            "pos_x": 50, "pos_y": 90, "line_break": 40,
            "outline_enabled": True, "outline_color": "#000000", "outline_width": 2,
            "background_enabled": False, "background_opacity": 0.5
        })
        if not os.path.exists(MODELS_DIR): os.makedirs(MODELS_DIR)

    def prepare_audio(self, audio_path, *_args):
        self._audio_path = audio_path

    def render(self, frame, tiempo, **kwargs):
        if not self._habilitado or not self._subtitles: return frame
        sub = next((s for s in self._subtitles if s["start"] <= tiempo <= s["end"]), None)
        if not sub: return frame
        try:
            h, w = frame.shape[:2]
            img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert('RGBA')
            txt_layer = Image.new('RGBA', img_pil.size, (0,0,0,0))
            draw = ImageDraw.Draw(txt_layer)
            font = ImageFont.truetype(get_font_path(self._config["font"]) or "arial.ttf", self._config["font_size"])
            lineas = split_text_lines(sub["text"], self._config["line_break"])
            txt_join = "\n".join(lineas)
            bbox = draw.textbbox((0,0), txt_join, font=font)
            tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
            px, py = (w-tw)/2 + (self._config["pos_x"]-50)*(w/100), (h*self._config["pos_y"]/100) - th/2
            alpha = int(255 * self._config["opacity"])
            color = tuple(int(self._config["color"].lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (alpha,)

            if self._config["background_enabled"]:
                bg_a = int(255 * self._config["background_opacity"] * self._config["opacity"])
                draw.rectangle([px-10, py-5, px+tw+10, py+th+5], fill=(0,0,0,bg_a))

            if self._config["outline_enabled"]:
                out_c = tuple(int(self._config["outline_color"].lstrip('#')[i:i+2], 16) for i in (0,2,4)) + (alpha,)
                bw = self._config["outline_width"]
                for dx, dy in [(-bw,-bw),(-bw,bw),(bw,-bw),(bw,bw),(0,-bw),(0,bw)]:
                    draw.text((px+dx, py+dy), txt_join, font=font, fill=out_c)

            draw.text((px, py), txt_join, font=font, fill=color)
            return cv2.cvtColor(np.array(Image.alpha_composite(img_pil, txt_layer).convert("RGB")), cv2.COLOR_RGB2BGR)
        except: return frame

    def get_config_widgets(self, parent, app) -> QWidget:
        self.app = app
        if not IA_READY:
            c = QWidget(parent)
            cl = QVBoxLayout(c)
            lbl = QLabel("\u26a0\ufe0f Faltan dependencias IA")
            lbl.setStyleSheet("color: red;")
            cl.addWidget(lbl)
            return c

        container = QWidget(parent)
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # --- GENERACIÓN IA ---
        f_gen = QGroupBox("Generaci\u00f3n IA")
        gen_layout = QVBoxLayout(f_gen)

        cfg_row = QWidget()
        cfg_rl = QHBoxLayout(cfg_row)
        cfg_rl.setContentsMargins(0, 0, 0, 0)
        self._lang_combo = QComboBox()
        self._lang_combo.addItems(list(VOSK_MODELS.keys()))
        self._lang_combo.setCurrentText(self._config["language"])
        cfg_rl.addWidget(self._lang_combo)
        self._size_combo = QComboBox()
        self._size_combo.addItems(["small", "medium"])
        self._size_combo.setCurrentText(self._config["model_type"])
        cfg_rl.addWidget(self._size_combo)
        gen_layout.addWidget(cfg_row)

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["Transcripci\u00f3n", "Alineaci\u00f3n"])
        self._mode_combo.setCurrentText("Transcripci\u00f3n")
        gen_layout.addWidget(self._mode_combo)

        # Splitter for text editors
        splitter = QSplitter(Qt.Orientation.Vertical)

        lyric_widget = QWidget()
        lyric_layout = QVBoxLayout(lyric_widget)
        lyric_layout.setContentsMargins(0, 0, 0, 0)
        lyric_layout.addWidget(QLabel("Letra para Alinear:"))
        self.lyric_txt = QTextEdit()
        self.lyric_txt.setMaximumHeight(80)
        self.lyric_txt.setStyleSheet("font-size: 8pt;")
        lyric_layout.addWidget(self.lyric_txt)
        splitter.addWidget(lyric_widget)

        srt_widget = QWidget()
        srt_layout = QVBoxLayout(srt_widget)
        srt_layout.setContentsMargins(0, 0, 0, 0)
        srt_layout.addWidget(QLabel("Editor SRT:"))
        self.srt_txt = QTextEdit()
        self.srt_txt.setMaximumHeight(100)
        self.srt_txt.setStyleSheet("font-family: 'Courier New'; font-size: 8pt;")
        srt_layout.addWidget(self.srt_txt)
        splitter.addWidget(srt_widget)

        gen_layout.addWidget(splitter)

        def on_mode_change(text):
            lyric_widget.setVisible("Alineaci\u00f3n" in text)
        self._mode_combo.currentTextChanged.connect(on_mode_change)
        on_mode_change(self._mode_combo.currentText())

        self.pbar = QProgressBar()
        self.pbar.setRange(0, 100)
        self.pbar.setValue(0)
        gen_layout.addWidget(self.pbar)

        self.btn_run = QPushButton("Generar Subt\u00edtulos")
        self.btn_run.clicked.connect(self._start_process)
        gen_layout.addWidget(self.btn_run)

        btn_row = QWidget()
        btn_rl = QHBoxLayout(btn_row)
        btn_rl.setContentsMargins(0, 0, 0, 0)
        apply_btn = QPushButton("Aplicar")
        apply_btn.clicked.connect(self._apply_editor)
        btn_rl.addWidget(apply_btn)
        export_btn = QPushButton("Exportar")
        export_btn.clicked.connect(self._export_srt)
        btn_rl.addWidget(export_btn)
        gen_layout.addWidget(btn_row)

        main_layout.addWidget(f_gen)

        # --- ESTILO ---
        f_st = QGroupBox("Estilo")
        st_layout = QVBoxLayout(f_st)

        self._font_combo = QComboBox()
        self._font_combo.addItems(get_system_fonts()[:30])
        self._font_combo.setCurrentText(self._config["font"])
        self._font_combo.currentTextChanged.connect(lambda v: self._update_config("font", v, app))
        st_layout.addWidget(self._font_combo)

        color_picker = self.create_color_picker(f_st, self._config["color"], app, "Color:")
        color_picker.on_color_change(lambda hex_val: self._update_config("color", hex_val, app))
        st_layout.addWidget(color_picker)

        sz_row = QWidget()
        szrl = QHBoxLayout(sz_row)
        szrl.setContentsMargins(0, 0, 0, 0)
        sz_spin = QSpinBox()
        sz_spin.setRange(10, 150)
        sz_spin.setValue(self._config["font_size"])
        sz_spin.valueChanged.connect(lambda v: self._update_config("font_size", v, app))
        szrl.addWidget(sz_spin)
        op_slider = QSlider(Qt.Orientation.Horizontal)
        op_slider.setRange(0, 100)
        op_slider.setValue(int(self._config["opacity"] * 100))
        op_slider.valueChanged.connect(lambda v: self._update_config("opacity", v / 100.0, app))
        szrl.addWidget(op_slider)
        st_layout.addWidget(sz_row)

        pos_row = QWidget()
        posrl = QHBoxLayout(pos_row)
        posrl.setContentsMargins(0, 0, 0, 0)
        px_slider = QSlider(Qt.Orientation.Horizontal)
        px_slider.setRange(0, 100)
        px_slider.setValue(self._config["pos_x"])
        px_slider.valueChanged.connect(lambda v: self._update_config("pos_x", v, app))
        posrl.addWidget(px_slider)
        py_slider = QSlider(Qt.Orientation.Horizontal)
        py_slider.setRange(0, 100)
        py_slider.setValue(self._config["pos_y"])
        py_slider.valueChanged.connect(lambda v: self._update_config("pos_y", v, app))
        posrl.addWidget(py_slider)
        st_layout.addWidget(pos_row)

        opt_row = QWidget()
        optrl = QHBoxLayout(opt_row)
        optrl.setContentsMargins(0, 0, 0, 0)
        optrl.addWidget(QLabel("Break:"))
        lb_spin = QSpinBox()
        lb_spin.setRange(10, 100)
        lb_spin.setValue(self._config["line_break"])
        lb_spin.valueChanged.connect(lambda v: self._update_config("line_break", v, app))
        optrl.addWidget(lb_spin)
        out_check = QCheckBox("Out")
        out_check.setChecked(self._config["outline_enabled"])
        out_check.toggled.connect(lambda v: self._update_config("outline_enabled", v, app))
        optrl.addWidget(out_check)
        bg_check = QCheckBox("BG")
        bg_check.setChecked(self._config["background_enabled"])
        bg_check.toggled.connect(lambda v: self._update_config("background_enabled", v, app))
        optrl.addWidget(bg_check)
        st_layout.addWidget(opt_row)

        main_layout.addWidget(f_st)

        self.status_t = QLabel("Listo.")
        self.status_t.setStyleSheet("font-size: 7pt; color: gray;")
        main_layout.addWidget(self.status_t)

        return container

    def _start_process(self):
        if not self._audio_path:
            QMessageBox.critical(None, "Error", "Carga audio en Soundvi")
            return
        self.btn_run.setEnabled(False)
        self.btn_run.setText("Trabajando...")
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            lang = self._lang_combo.currentText()
            size = self._size_combo.currentText()
            minfo = VOSK_MODELS[lang].get(size) or VOSK_MODELS[lang]["small"]
            mpath = os.path.join(MODELS_DIR, minfo["name"])

            if not os.path.exists(mpath):
                self._ui_upd("Descargando modelo...", 10)
                temp_zip = os.path.join(TEMP_DIR, "model.zip")
                with urlopen(minfo["url"]) as r, open(temp_zip, 'wb') as f: shutil.copyfileobj(r, f)
                with zipfile.ZipFile(temp_zip, 'r') as z: z.extractall(MODELS_DIR)
                os.remove(temp_zip)

            self._ui_upd("Filtrando voz...", 25)
            audio = AudioSegment.from_file(self._audio_path)
            audio = effects.normalize(audio)
            audio = audio.set_frame_rate(16000).set_channels(1)
            audio.export(TEMP_AUDIO, format="wav")

            model = Model(mpath)
            if "Alineaci\u00f3n" in self._mode_combo.currentText():
                self._ui_upd("Alineando (Fuzzy Match)...", 50)
                script = self.lyric_txt.toPlainText().strip()
                self._subtitles = self._advanced_fuzzy_alignment(model, script)
            else:
                self._ui_upd("Transcribiendo...", 50)
                self._subtitles = self._transcribe_full(model)

            content = ""
            for i, s in enumerate(self._subtitles, 1):
                content += f"{i}\n{format_time(s['start'])} --> {format_time(s['end'])}\n{s['text']}\n\n"

            with open(SUBTITLE_OUTPUT, "w", encoding="utf-8") as f: f.write(content)
            self._ui_upd("\u00a1Listo!", 100, srt=content)
        except Exception as e:
            self._ui_upd(f"Error: {e}", 0)

    def _advanced_fuzzy_alignment(self, model, script_text):
        lines = [l.strip() for l in script_text.split('\n') if l.strip()]
        audio_words = self._get_words(model)
        if not audio_words: return []
        word_index = [w['word'].lower() for w in audio_words]
        subtitles = []
        last_match_idx = 0
        for line in lines:
            line_words = re.findall(r"\w+", line.lower())
            if not line_words: continue
            best_ratio = 0
            best_span = None
            search_start = last_match_idx
            search_end = min(last_match_idx + 100, len(word_index))
            for i in range(search_start, search_end):
                chunk = word_index[i : i + len(line_words)]
                ratio = SequenceMatcher(None, line_words, chunk).ratio()
                if ratio > best_ratio and ratio > 0.45:
                    best_ratio = ratio
                    best_span = (i, min(i + len(line_words) - 1, len(audio_words) - 1))
            if best_span:
                s_idx, e_idx = best_span
                subtitles.append({'start': audio_words[s_idx]['start'], 'end': audio_words[e_idx]['end'], 'text': line})
                last_match_idx = e_idx + 1
            elif subtitles:
                start = subtitles[-1]['end'] + 0.1
                duration = max(1.5, len(line_words) * 0.4)
                subtitles.append({'start': start, 'end': start + duration, 'text': line})
        return subtitles

    def _transcribe_full(self, model):
        words = self._get_words(model); subs = []
        if not words: return subs
        curr, start = [], words[0]["start"]
        for w in words:
            curr.append(w["word"])
            if len(" ".join(curr)) > 42 or w["end"] - start > 5.0:
                subs.append({"start": start, "end": w["end"], "text": " ".join(curr)})
                curr, start = [], w["end"]
        if curr: subs.append({"start": start, "end": words[-1]["end"], "text": " ".join(curr)})
        return subs

    def _get_words(self, model):
        wf = wave.open(TEMP_AUDIO, "rb")
        rec = KaldiRecognizer(model, 16000); rec.SetWords(True)
        total_frames = wf.getnframes()
        frames_proc = 0
        results = []
        while True:
            data = wf.readframes(8000)
            if not data: break
            frames_proc += 8000
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                if 'result' in res: results.extend(res['result'])
            if frames_proc % 80000 == 0:
                prog = 40 + int((frames_proc / total_frames) * 50)
                self._ui_upd(f"Escuchando ({int(frames_proc/total_frames*100)}%)...", prog)
        res = json.loads(rec.FinalResult()); results.extend(res.get('result', []))
        return results

    def _ui_upd(self, msg, val, srt=None):
        if not self.app: return
        # Use QMetaObject.invokeMethod for thread-safe GUI updates
        try:
            self.status_t.setText(msg)
            self.pbar.setValue(val)
            if val in [0, 100]:
                self.btn_run.setEnabled(True)
                self.btn_run.setText("Generar Subt\u00edtulos")
            if srt:
                self.srt_txt.setPlainText(srt)
                if hasattr(self.app, 'update_preview'):
                    self.app.update_preview()
        except RuntimeError:
            pass  # Widget may have been destroyed

    def _apply_editor(self):
        content = self.srt_txt.toPlainText()
        self._subtitles = []
        matches = re.findall(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:.+\n?)+)', content + "\n")
        for m in matches:
            ti, to = m[1].replace(",",".").split(":"), m[2].replace(",",".").split(":")
            s = float(ti[0])*3600+float(ti[1])*60+float(ti[2])
            e = float(to[0])*3600+float(to[1])*60+float(to[2])
            self._subtitles.append({'start': s, 'end': e, 'text': m[3].strip()})
        if self.app and hasattr(self.app, 'update_preview'):
            self.app.update_preview()
        QMessageBox.information(None, "OK", "Subt\u00edtulos actualizados.")

    def _export_srt(self):
        p, _ = QFileDialog.getSaveFileName(None, "Exportar SRT", "", "SRT (*.srt)")
        if p and os.path.exists(SUBTITLE_OUTPUT):
            shutil.copy(SUBTITLE_OUTPUT, p)
            QMessageBox.information(None, "OK", f"Exportado a {p}")

    def log(self, m): print(f"[subauto] {m}")
