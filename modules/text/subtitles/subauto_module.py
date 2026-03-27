#!/usr/bin/env python3
"""
Módulo SubAuto IA.
Categorizado: text/subtitles
(Migrado del original con metadatos de categorización)
"""
import os, json, wave, threading, tempfile, shutil, zipfile
from urllib.request import urlopen
from datetime import timedelta
import re, unicodedata
from difflib import SequenceMatcher
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QComboBox, QSpinBox, QGroupBox, QPushButton,
    QTextEdit, QProgressBar, QSplitter, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt

from modules.core.base import Module
from utils.subtitles import parse_srt, format_time, split_text_lines
from utils.fonts import get_font_path, get_system_fonts

try:
    from vosk import Model, KaldiRecognizer
    from pydub import AudioSegment, effects
    IA_READY = True
except ImportError:
    IA_READY = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
    module_type = "text"
    module_category = "subtitles"
    module_tags = ["subauto", "ia", "transcription", "vosk", "alignment", "subtitles"]
    module_version = "2.0.0"
    module_author = "Soundvi Team"

    def __init__(self, nombre: str = "SubAuto IA", capa: int = 10):
        super().__init__(nombre=nombre, descripcion="Subt\u00edtulos autom\u00e1ticos con IA", capa=capa)
        self._subtitles = []; self._audio_path = None; self.app = None
        self._config.update({
            "language": "Espa\u00f1ol", "model_type": "small", "mode": "Transcripci\u00f3n",
            "font": "Arial", "font_size": 36, "color": "#FFFFFF", "opacity": 1.0,
            "pos_x": 50, "pos_y": 90, "line_break": 40,
            "outline_enabled": True, "outline_color": "#000000", "outline_width": 2,
            "background_enabled": False, "background_opacity": 0.5
        })
        if not os.path.exists(MODELS_DIR): os.makedirs(MODELS_DIR)

    def prepare_audio(self, audio_path, *_args): self._audio_path = audio_path

    def render(self, frame, tiempo, **kwargs):
        if not self._habilitado or not self._subtitles: return frame
        sub = next((s for s in self._subtitles if s["start"] <= tiempo <= s["end"]), None)
        if not sub: return frame
        try:
            h, w = frame.shape[:2]
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert('RGBA')
            txt = Image.new('RGBA', img.size, (0,0,0,0))
            draw = ImageDraw.Draw(txt)
            font = ImageFont.truetype(get_font_path(self._config["font"]) or "arial.ttf", self._config["font_size"])
            lineas = split_text_lines(sub["text"], self._config["line_break"])
            txt_join = "\n".join(lineas)
            bbox = draw.textbbox((0,0), txt_join, font=font)
            tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
            px = (w-tw)/2 + (self._config["pos_x"]-50)*(w/100)
            py = (h*self._config["pos_y"]/100) - th/2
            alpha = int(255 * self._config["opacity"])
            color = tuple(int(self._config["color"].lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (alpha,)
            if self._config["background_enabled"]:
                bg_a = int(255 * self._config["background_opacity"] * self._config["opacity"])
                draw.rectangle([px-10, py-5, px+tw+10, py+th+5], fill=(0,0,0,bg_a))
            if self._config["outline_enabled"]:
                oc = tuple(int(self._config["outline_color"].lstrip('#')[i:i+2], 16) for i in (0,2,4)) + (alpha,)
                bw = self._config["outline_width"]
                for dx, dy in [(-bw,-bw),(-bw,bw),(bw,-bw),(bw,bw),(0,-bw),(0,bw)]:
                    draw.text((px+dx, py+dy), txt_join, font=font, fill=oc)
            draw.text((px, py), txt_join, font=font, fill=color)
            return cv2.cvtColor(np.array(Image.alpha_composite(img, txt).convert("RGB")), cv2.COLOR_RGB2BGR)
        except: return frame

    def get_config_widgets(self, parent, app):
        self.app = app
        if not IA_READY:
            c = QWidget(parent)
            cl = QVBoxLayout(c)
            lbl = QLabel("\u26a0\ufe0f Faltan dependencias IA (vosk, pydub)")
            lbl.setStyleSheet("color: red;")
            cl.addWidget(lbl)
            return c

        container = QWidget(parent)
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)

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
        gen_layout.addWidget(self._mode_combo)

        splitter = QSplitter(Qt.Orientation.Vertical)
        lyric_w = QWidget()
        ll = QVBoxLayout(lyric_w)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(QLabel("Letra:"))
        self.lyric_txt = QTextEdit()
        self.lyric_txt.setMaximumHeight(60)
        self.lyric_txt.setStyleSheet("font-size: 8pt;")
        ll.addWidget(self.lyric_txt)
        splitter.addWidget(lyric_w)
        srt_w = QWidget()
        sl = QVBoxLayout(srt_w)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.addWidget(QLabel("Editor SRT:"))
        self.srt_txt = QTextEdit()
        self.srt_txt.setMaximumHeight(80)
        self.srt_txt.setStyleSheet("font-family: 'Courier New'; font-size: 8pt;")
        sl.addWidget(self.srt_txt)
        splitter.addWidget(srt_w)
        gen_layout.addWidget(splitter)

        self.pbar = QProgressBar()
        self.pbar.setRange(0, 100)
        gen_layout.addWidget(self.pbar)

        self.btn_run = QPushButton("Generar Subt\u00edtulos")
        self.btn_run.clicked.connect(self._start_process)
        gen_layout.addWidget(self.btn_run)

        btn_row = QWidget()
        brl = QHBoxLayout(btn_row)
        brl.setContentsMargins(0, 0, 0, 0)
        apply_btn = QPushButton("Aplicar")
        apply_btn.clicked.connect(self._apply_editor)
        brl.addWidget(apply_btn)
        export_btn = QPushButton("Exportar")
        export_btn.clicked.connect(self._export_srt)
        brl.addWidget(export_btn)
        gen_layout.addWidget(btn_row)
        main_layout.addWidget(f_gen)

        f_st = QGroupBox("Estilo")
        stl = QVBoxLayout(f_st)
        color_picker = self.create_color_picker(f_st, self._config["color"], app, "Color:")
        color_picker.on_color_change(lambda hex_val: self._update_config("color", hex_val, app))
        stl.addWidget(color_picker)
        sz_spin = QSpinBox()
        sz_spin.setRange(10, 150)
        sz_spin.setValue(self._config["font_size"])
        sz_spin.valueChanged.connect(lambda v: self._update_config("font_size", v, app))
        stl.addWidget(sz_spin)
        main_layout.addWidget(f_st)

        self.status_t = QLabel("Listo.")
        self.status_t.setStyleSheet("font-size: 7pt; color: gray;")
        main_layout.addWidget(self.status_t)

        return container

    def _start_process(self):
        if not self._audio_path:
            QMessageBox.critical(None, "Error", "Carga audio")
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
                with zipfile.ZipFile(temp_zip, 'r') as z: z.extractall(MODELS_DIR); os.remove(temp_zip)
            self._ui_upd("Filtrando voz...", 25)
            audio = AudioSegment.from_file(self._audio_path)
            audio = effects.normalize(audio).set_frame_rate(16000).set_channels(1)
            audio.export(TEMP_AUDIO, format="wav")
            model = Model(mpath)
            if "Alineaci\u00f3n" in self._mode_combo.currentText():
                self._ui_upd("Alineando...", 50)
                script = self.lyric_txt.toPlainText().strip()
                self._subtitles = self._align(model, script)
            else:
                self._ui_upd("Transcribiendo...", 50)
                self._subtitles = self._transcribe(model)
            content = ""
            for i, s in enumerate(self._subtitles, 1):
                content += f"{i}\n{format_time(s['start'])} --> {format_time(s['end'])}\n{s['text']}\n\n"
            with open(SUBTITLE_OUTPUT, "w", encoding="utf-8") as f: f.write(content)
            self._ui_upd("\u00a1Listo!", 100, srt=content)
        except Exception as e: self._ui_upd(f"Error: {e}", 0)

    def _align(self, model, script_text):
        lines = [l.strip() for l in script_text.split('\n') if l.strip()]
        words = self._get_words(model)
        if not words: return []
        wi = [w['word'].lower() for w in words]; subs = []; last = 0
        for line in lines:
            lw = re.findall(r"\w+", line.lower())
            if not lw: continue
            best_r, best_s = 0, None
            for i in range(last, min(last + 100, len(wi))):
                chunk = wi[i:i+len(lw)]
                r = SequenceMatcher(None, lw, chunk).ratio()
                if r > best_r and r > 0.45: best_r = r; best_s = (i, min(i+len(lw)-1, len(words)-1))
            if best_s:
                s, e = best_s
                subs.append({'start': words[s]['start'], 'end': words[e]['end'], 'text': line}); last = e+1
            elif subs:
                start = subs[-1]['end'] + 0.1; dur = max(1.5, len(lw) * 0.4)
                subs.append({'start': start, 'end': start + dur, 'text': line})
        return subs

    def _transcribe(self, model):
        words = self._get_words(model); subs = []
        if not words: return subs
        curr, start = [], words[0]["start"]
        for w in words:
            curr.append(w["word"])
            if len(" ".join(curr)) > 42 or w["end"] - start > 5.0:
                subs.append({"start": start, "end": w["end"], "text": " ".join(curr)}); curr, start = [], w["end"]
        if curr: subs.append({"start": start, "end": words[-1]["end"], "text": " ".join(curr)})
        return subs

    def _get_words(self, model):
        wf = wave.open(TEMP_AUDIO, "rb")
        rec = KaldiRecognizer(model, 16000); rec.SetWords(True); results = []
        while True:
            data = wf.readframes(8000)
            if not data: break
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                if 'result' in res: results.extend(res['result'])
        res = json.loads(rec.FinalResult()); results.extend(res.get('result', [])); return results

    def _ui_upd(self, msg, val, srt=None):
        if not self.app: return
        try:
            self.status_t.setText(msg)
            self.pbar.setValue(val)
            if val in [0, 100]:
                self.btn_run.setEnabled(True)
                self.btn_run.setText("Generar Subt\u00edtulos")
            if srt:
                self.srt_txt.setPlainText(srt)
                if hasattr(self.app, 'update_preview'): self.app.update_preview()
        except RuntimeError:
            pass

    def _apply_editor(self):
        content = self.srt_txt.toPlainText(); self._subtitles = []
        matches = re.findall(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:.+\n?)+)', content + "\n")
        for m in matches:
            ti, to = m[1].replace(",",".").split(":"), m[2].replace(",",".").split(":")
            s = float(ti[0])*3600+float(ti[1])*60+float(ti[2])
            e = float(to[0])*3600+float(to[1])*60+float(to[2])
            self._subtitles.append({'start': s, 'end': e, 'text': m[3].strip()})
        if self.app and hasattr(self.app, 'update_preview'): self.app.update_preview()
        QMessageBox.information(None, "OK", "Subt\u00edtulos actualizados.")

    def _export_srt(self):
        p, _ = QFileDialog.getSaveFileName(None, "Exportar SRT", "", "SRT (*.srt)")
        if p and os.path.exists(SUBTITLE_OUTPUT): shutil.copy(SUBTITLE_OUTPUT, p); QMessageBox.information(None, "OK", f"Exportado a {p}")
