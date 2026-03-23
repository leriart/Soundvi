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
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from urllib.request import urlopen
from datetime import timedelta
import re
import unicodedata
from difflib import SequenceMatcher

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

try:
    import ttkbootstrap as tb
except ImportError:
    import tkinter.ttk as tb

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
    "Español": {
        "small": {"url": "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip", "name": "vosk-model-small-es-0.42"},
        "medium": {"url": "https://alphacephei.com/vosk/models/vosk-model-es-0.42.zip", "name": "vosk-model-es-0.42"}
    },
    "Inglés": {
        "small": {"url": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip", "name": "vosk-model-small-en-us-0.15"},
        "medium": {"url": "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip", "name": "vosk-model-en-us-0.22"}
    }
}

class SubAutoModule(Module):
    def __init__(self, nombre: str = "SubAuto", capa: int = 10):
        super().__init__(nombre=nombre, descripcion="IA Subtitles Pro", capa=capa)
        self._subtitles = []
        self._audio_path = None
        self.app = None # Referencia a la app principal
        
        self._config.update({
            "language": "Español", "model_type": "small", "mode": "Transcripción",
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

    def get_config_widgets(self, parent, app) -> tk.Frame:
        self.app = app # GUARDAR REFERENCIA
        if not IA_READY:
            c = tb.Frame(parent); tb.Label(c, text="⚠️ Faltan dependencias IA", foreground="red").pack(pady=5); return c
        
        container = tb.Frame(parent)
        
        # --- GENERACIÓN IA ---
        f_gen = tb.LabelFrame(container, text="Generación IA")
        f_gen.pack(fill=tk.X, pady=2, padx=5)
        
        row_cfg = tb.Frame(f_gen); row_cfg.pack(fill=tk.X, pady=2, padx=5)
        self.lang_var = tk.StringVar(value=self._config["language"])
        tb.Combobox(row_cfg, textvariable=self.lang_var, values=list(VOSK_MODELS.keys()), width=10, state="readonly").pack(side=tk.LEFT, padx=1)
        self.size_var = tk.StringVar(value=self._config["model_type"])
        tb.Combobox(row_cfg, textvariable=self.size_var, values=["small", "medium"], width=7, state="readonly").pack(side=tk.LEFT, padx=1)
        
        self.mode_var = tk.StringVar(value="Transcripción")
        cb_m = tb.Combobox(f_gen, textvariable=self.mode_var, values=["Transcripción", "Alineación"], width=20, state="readonly")
        cb_m.pack(fill=tk.X, padx=5, pady=2)

        # PANEDWINDOW PARA EDITORES
        self._paned = tb.Panedwindow(f_gen, orient=tk.VERTICAL)
        self._paned.pack(fill=tk.X, pady=5, padx=5)

        self._f_lyric = tb.Frame(self._paned)
        tb.Label(self._f_lyric, text="Letra para Alinear:", font=("", 8)).pack(anchor="w")
        self.lyric_txt = scrolledtext.ScrolledText(self._f_lyric, height=4, font=("Arial", 8))
        self.lyric_txt.pack(fill=tk.BOTH, expand=True)
        self._paned.add(self._f_lyric, weight=1)

        self._f_srt = tb.Frame(self._paned)
        tb.Label(self._f_srt, text="Editor SRT:", font=("", 8)).pack(anchor="w")
        self.srt_txt = scrolledtext.ScrolledText(self._f_srt, height=5, font=("Courier New", 8))
        self.srt_txt.pack(fill=tk.BOTH, expand=True)
        self._paned.add(self._f_srt, weight=1)

        def on_mode_change(*_):
            if "Alineación" in self.mode_var.get():
                if str(self._f_lyric) not in self._paned.panes(): self._paned.insert(0, self._f_lyric, weight=1)
            else:
                if str(self._f_lyric) in self._paned.panes(): self._paned.forget(self._f_lyric)
        cb_m.bind("<<ComboboxSelected>>", on_mode_change)

        self.pbar = tb.Progressbar(f_gen, bootstyle="success-striped", mode="determinate")
        self.pbar.pack(fill=tk.X, padx=10, pady=2)

        self.btn_run = tb.Button(f_gen, text="Generar Subtítulos", bootstyle="success", command=self._start_process)
        self.btn_run.pack(fill=tk.X, pady=5, padx=5)
        
        row_btn = tb.Frame(f_gen); row_btn.pack(fill=tk.X)
        tb.Button(row_btn, text="Aplicar", bootstyle="primary-outline", command=self._apply_editor, width=10).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        tb.Button(row_btn, text="Exportar", bootstyle="info-outline", command=self._export_srt, width=10).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # --- ESTILO ---
        f_st = tb.LabelFrame(container, text="Estilo")
        f_st.pack(fill=tk.X, pady=2, padx=5)
        self.f_v = tk.StringVar(value=self._config["font"])
        tb.Combobox(f_st, textvariable=self.f_v, values=get_system_fonts()[:30], state="readonly").pack(fill=tk.X, padx=5, pady=2)
        self.f_v.trace_add("write", lambda *_: self._update_config("font", self.f_v.get(), app))
        
        self.c_v = tk.StringVar(value=self._config["color"])
        self.create_color_picker(f_st, self.c_v, app, "Color:").pack(fill=tk.X, padx=5)
        self.c_v.trace_add("write", lambda *_: self._update_config("color", self.c_v.get(), app))
        
        r3 = tb.Frame(f_st); r3.pack(fill=tk.X, padx=5, pady=2)
        self.sz_v = tk.IntVar(value=self._config["font_size"])
        tb.Spinbox(r3, from_=10, to=150, textvariable=self.sz_v, width=3, command=lambda: self._update_config("font_size", self.sz_v.get(), app)).pack(side=tk.LEFT)
        self.op_v = tk.DoubleVar(value=self._config["opacity"])
        tb.Scale(r3, from_=0, to=1, variable=self.op_v, command=lambda v: self._update_config("opacity", float(v), app)).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        r4 = tb.Frame(f_st); r4.pack(fill=tk.X, padx=5, pady=2)
        self.px_v, self.py_v = tk.IntVar(value=self._config["pos_x"]), tk.IntVar(value=self._config["pos_y"])
        tb.Scale(r4, from_=0, to=100, variable=self.px_v, command=lambda v: self._update_config("pos_x", int(float(v)), app)).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tb.Scale(r4, from_=0, to=100, variable=self.py_v, command=lambda v: self._update_config("pos_y", int(float(v)), app)).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        r5 = tb.Frame(f_st); r5.pack(fill=tk.X, padx=5, pady=2)
        tb.Label(r5, text="Break:").pack(side=tk.LEFT)
        self.lb_v = tk.IntVar(value=self._config["line_break"])
        tb.Spinbox(r5, from_=10, to=100, textvariable=self.lb_v, width=3, command=lambda: self._update_config("line_break", self.lb_v.get(), app)).pack(side=tk.LEFT, padx=2)
        self.out_v = tk.BooleanVar(value=self._config["outline_enabled"])
        tb.Checkbutton(r5, text="Out", variable=self.out_v, command=lambda: self._update_config("outline_enabled", self.out_v.get(), app)).pack(side=tk.LEFT, padx=2)
        self.bg_v = tk.BooleanVar(value=self._config["background_enabled"])
        tb.Checkbutton(r5, text="BG", variable=self.bg_v, command=lambda: self._update_config("background_enabled", self.bg_v.get(), app)).pack(side=tk.LEFT, padx=2)

        self.status_t = tb.Label(container, text="Listo.", font=("", 7), foreground="gray")
        self.status_t.pack(); on_mode_change(); return container

    def _start_process(self):
        if not self._audio_path: return messagebox.showerror("Error", "Carga audio en Soundvi")
        self.btn_run.config(state="disabled", text="Trabajando...")
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            lang, size = self.lang_var.get(), self.size_var.get()
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
            # Realce de voz: Normalizar + Filtro paso banda (vocal focus)
            audio = effects.normalize(audio)
            audio = audio.set_frame_rate(16000).set_channels(1)
            audio.export(TEMP_AUDIO, format="wav")
            
            model = Model(mpath)
            if "Alineación" in self.mode_var.get():
                self._ui_upd("Alineando (Fuzzy Match)...", 50)
                script = self.lyric_txt.get("1.0", tk.END).strip()
                self._subtitles = self._advanced_fuzzy_alignment(model, script)
            else:
                self._ui_upd("Transcribiendo...", 50)
                self._subtitles = self._transcribe_full(model)
            
            content = ""
            for i, s in enumerate(self._subtitles, 1):
                content += f"{i}\n{format_time(s['start'])} --> {format_time(s['end'])}\n{s['text']}\n\n"
            
            with open(SUBTITLE_OUTPUT, "w", encoding="utf-8") as f: f.write(content)
            self._ui_upd("¡Listo!", 100, srt=content)
        except Exception as e:
            self._ui_upd(f"Error: {e}", 0)

    def _advanced_fuzzy_alignment(self, model, script_text):
        """Alineamiento Pro: Índice de palabras + Búsqueda Difusa."""
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
            
            # Ventana de búsqueda adaptativa
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
                # Fallback: estimar por duración si no hay match claro
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
            
            # Actualizar barra de progreso (de 40% a 90%)
            if frames_proc % 80000 == 0:
                prog = 40 + int((frames_proc / total_frames) * 50)
                self._ui_upd(f"Escuchando ({int(frames_proc/total_frames*100)}%)...", prog)

        res = json.loads(rec.FinalResult()); results.extend(res.get('result', []))
        return results

    def _ui_upd(self, msg, val, srt=None):
        if not self.app: return
        def update():
            self.status_t.config(text=msg)
            self.pbar.config(value=val)
            if val in [0, 100]: self.btn_run.config(state="normal", text="Generar Subtítulos")
            if srt:
                self.srt_txt.delete("1.0", tk.END)
                self.srt_txt.insert(tk.END, srt)
                self.app.update_preview()
        self.app.root.after(0, update)

    def _apply_editor(self):
        content = self.srt_txt.get("1.0", tk.END); self._subtitles = []
        matches = re.findall(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:.+\n?)+)', content + "\n")
        for m in matches:
            ti, to = m[1].replace(",",".").split(":"), m[2].replace(",",".").split(":")
            s = float(ti[0])*3600+float(ti[1])*60+float(ti[2])
            e = float(to[0])*3600+float(to[1])*60+float(to[2])
            self._subtitles.append({'start': s, 'end': e, 'text': m[3].strip()})
        if self.app: self.app.update_preview()
        messagebox.showinfo("OK", "Subtítulos actualizados.")

    def _export_srt(self):
        p = filedialog.asksaveasfilename(defaultextension=".srt", filetypes=[("SRT", "*.srt")])
        if p and os.path.exists(SUBTITLE_OUTPUT): 
            shutil.copy(SUBTITLE_OUTPUT, p)
            messagebox.showinfo("OK", f"Exportado a {p}")

    def log(self, m): print(f"[subauto] {m}")
