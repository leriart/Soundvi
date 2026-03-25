#!/usr/bin/env python3
from __future__ import annotations
"""
Panel de preview en tiempo real de Soundvi.
REOPTIMIZADO: Con sistema de overlay para carga sin bloqueo visual.
"""


import os
import time
import threading
import tkinter as tk
from tkinter import BOTH, YES, LEFT, RIGHT, X, Y, TOP, BOTTOM, HORIZONTAL

import numpy as np
import cv2
import pygame
from PIL import Image, ImageTk

try:
    import ttkbootstrap as tb
except ImportError:
    import tkinter.ttk as tb

from utils.fonts import get_default_font


class PreviewPanel:
    """Panel de vista previa con controles de reproduccion y overlay de carga."""

    def __init__(self, parent: tk.Frame, app):
        self.app = app
        self.parent = parent
        self._playing = False
        self._reverse = False
        self._current_time = 0.0
        self._duration = 0.0
        self._fps = 30
        self._audio_path: str | None = None
        self._background_frame: np.ndarray | None = None
        self._gif_frames: list[np.ndarray] = []
        self._gif_fps = 10
        self._is_gif = False
        self._play_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_render_time = 0.0

        try:
            pygame.mixer.init()
        except:
            pass

        self._build_ui()

    def _build_ui(self):
        """Construye la interfaz con soporte para overlays."""
        main = tb.Frame(self.parent)
        main.pack(fill=BOTH, expand=YES)

        header = tb.Frame(main)
        header.pack(fill=X, pady=(0, 5))
        tb.Label(header, text="Vista Previa en Tiempo Real", font=("", 12, "bold")).pack(side=LEFT)

        # -- AREA DE PREVIEW CON CAPAS --
        self.preview_container = tb.Frame(main, bootstyle="dark")
        self.preview_container.pack(fill=BOTH, expand=YES, pady=5)

        # Capa de Video (Fondo)
        self.preview_label = tk.Label(
            self.preview_container, bg="#1a1a2e", bd=0
        )
        self.preview_label.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Capa de Carga (Overlay superior)
        self.loading_overlay = tk.Label(
            self.preview_container, bg="#1a1a2e", bd=0
        )
        # Se activa via place() cuando sea necesario

        self._show_empty_state()
        self._build_controls(main)

        info = tb.Frame(main)
        info.pack(fill=X, pady=2)
        self.info_label = tb.Label(info, text="Modulos activos: ninguno", font=("", 8), bootstyle="secondary")
        self.info_label.pack(side=LEFT)

    def _show_loading_state(self, show=True):
        """Muestra el logo 'Cagando.png' con fondo negro total cubriendo el preview."""
        if not show:
            self.loading_overlay.place_forget()
            self.preview_container.update()
            return

        loading_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logos", "Cagando.png")
        if os.path.exists(loading_path):
            try:
                # Cubrir todo el contenedor con fondo negro
                self.loading_overlay.config(bg="black")
                self.loading_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
                
                img = Image.open(loading_path)
                # Forzar dimensiones si el widget aún no está listo
                w = self.preview_label.winfo_width()
                h = self.preview_label.winfo_height()
                if w < 50: w, h = 800, 450
                
                # Imagen un poco más pequeña que el frame para que se vea centrada
                max_size = min(w - 100, h - 100, 450)
                if max_size < 100: max_size = 300
                
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                self._loading_photo = ImageTk.PhotoImage(img)
                
                self.loading_overlay.config(image=self._loading_photo)
                
                # Forzar actualización visual antes del proceso pesado
                self.loading_overlay.update()
                self.preview_container.update()
            except Exception as e:
                print(f"Error en pantalla de carga: {e}")

    def _show_empty_state(self):
        """Estado inicial con logo de Soundvi."""
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logos", "logo.png")
        if os.path.exists(logo_path):
            try:
                def load_logo():
                    w, h = self.preview_label.winfo_width(), self.preview_label.winfo_height()
                    if w < 10: 
                        self.app.root.after(100, load_logo)
                        return
                    img = Image.open(logo_path)
                    max_size = min(w - 40, h - 100, 500)
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                    self._empty_photo = ImageTk.PhotoImage(img)
                    self.preview_label.config(
                        image=self._empty_photo, 
                        text="\n\nCarga un archivo de audio y video para empezar", 
                        compound="top",
                        font=(get_default_font(), 14, "bold"),
                        foreground="#4ec9b0"
                    )
                self.app.root.after(100, load_logo)
            except Exception as e:
                print(f"Error cargando logo en preview: {e}")
                self.preview_label.config(text="Soundvi", font=(get_default_font(), 16, "bold"))
        else:
            self.preview_label.config(text="Soundvi", font=(get_default_font(), 16, "bold"))

    def _build_controls(self, main):
        seek_frame = tb.Frame(main)
        seek_frame.pack(fill=X, pady=2)
        self.time_label = tb.Label(seek_frame, text="00:00", font=(get_default_font(), 9))
        self.time_label.pack(side=LEFT, padx=5)
        self.seek_var = tk.DoubleVar(value=0.0)
        self.seek_slider = tb.Scale(seek_frame, from_=0.0, to=100.0, variable=self.seek_var, orient=HORIZONTAL, command=self._on_seek)
        self.seek_slider.pack(side=LEFT, fill=X, expand=YES, padx=5)
        self.duration_label = tb.Label(seek_frame, text="00:00", font=(get_default_font(), 9))
        self.duration_label.pack(side=LEFT, padx=5)

        controls = tb.Frame(main)
        controls.pack(fill=X, pady=5)
        self.reverse_btn = tb.Button(controls, text="Reverse", command=self._toggle_reverse, bootstyle="outline", width=10)
        self.reverse_btn.pack(side=LEFT, padx=3)
        tb.Button(controls, text="-5s", command=lambda: self._seek_relative(-5), bootstyle="outline", width=7).pack(side=LEFT, padx=3)
        self.play_btn = tb.Button(controls, text="Play", command=self._toggle_play, bootstyle="success", width=10)
        self.play_btn.pack(side=LEFT, padx=3)
        tb.Button(controls, text="+5s", command=lambda: self._seek_relative(5), bootstyle="outline", width=7).pack(side=LEFT, padx=3)

        vol_frame = tb.Frame(controls)
        vol_frame.pack(side=RIGHT, padx=5)
        tb.Label(vol_frame, text="Vol").pack(side=LEFT)
        self.volume_slider = tb.Scale(vol_frame, from_=0, to=200, variable=self.app.final_volume, orient=HORIZONTAL, length=80, command=lambda v: self._on_volume_change(v))
        self.volume_slider.pack(side=LEFT, padx=3)

    def load_background(self, media_path: str):
        if not media_path: return
        self._is_gif = media_path.lower().endswith(".gif")
        if self._is_gif:
            cap = cv2.VideoCapture(media_path)
            self._gif_fps = cap.get(cv2.CAP_PROP_FPS) or 10
            self._gif_frames = []
            while True:
                ok, f = cap.read()
                if not ok: break
                self._gif_frames.append(f)
            cap.release()
        else:
            img = cv2.imread(media_path)
            if img is not None: self._background_frame = img
        
        # Ocultar estado vacío si tenemos contenido
        if self._has_content():
            self.preview_label.config(image="", text="")
            self._render_current_frame()

    def load_audio(self, audio_path: str):
        if not audio_path: return
        self._audio_path = audio_path
        try:
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.set_volume(self.app.final_volume.get() / 100.0)
        except: pass
        
        # Ocultar estado vacío si tenemos contenido
        if self._has_content():
            self.preview_label.config(image="", text="")
            self._render_current_frame()

    def set_duration(self, duration: float):
        self._duration = duration
        self.seek_slider.config(to=duration)
        self.duration_label.config(text=self._format_time(duration))

    def set_fps(self, fps: int): self._fps = fps

    def _toggle_play(self):
        if self._playing: self._pause()
        else: self._play()

    def _play(self):
        if not self._has_content(): return
        self._playing = True
        self._stop_event.clear()
        self.play_btn.config(text="Pausa", bootstyle="warning")
        if self._audio_path:
            try:
                pygame.mixer.music.play(start=self._current_time)
                pygame.mixer.music.set_volume(self.app.final_volume.get() / 100.0)
            except: pass
        self._play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self._play_thread.start()

    def _pause(self):
        self._playing = False
        self._stop_event.set()
        self.play_btn.config(text="Play", bootstyle="success")
        try: pygame.mixer.music.stop()
        except: pass

    def _play_loop(self):
        start_time = time.perf_counter()
        initial_offset = self._current_time
        
        while not self._stop_event.is_set():
            # Obtener FPS actuales
            try:
                target_fps = float(self.app.fps.get())
                if target_fps <= 0: target_fps = 30.0
            except:
                target_fps = 30.0
                
            frame_duration = 1.0 / target_fps
            
            # Calcular tiempo
            self._current_time = initial_offset + (time.perf_counter() - start_time)
            if self._current_time >= self._duration:
                self._current_time = self._duration
                self.app.root.after(0, self._pause)
                break
                
            # Renderizar
            self.app.root.after(0, self._render_current_frame)
            
            # Esperar para mantener FPS constantes
            elapsed = (time.perf_counter() - start_time) + initial_offset - self._current_time
            sleep_time = max(0.001, frame_duration - elapsed)
            time.sleep(sleep_time)

    def _toggle_reverse(self): self._reverse = not self._reverse

    def _seek_relative(self, delta: float):
        self._current_time = max(0, min(self._duration, self._current_time + delta))
        self._render_current_frame()

    def _on_seek(self, value):
        try:
            t = float(value)
            self._current_time = t
            if self._playing and self._audio_path:
                try: pygame.mixer.music.play(start=t)
                except: pass
            if not self._playing: self._render_current_frame()
        except: pass

    def _on_volume_change(self, value):
        try: pygame.mixer.music.set_volume(float(value) / 100.0)
        except: pass

    def _has_content(self) -> bool: return self._background_frame is not None or len(self._gif_frames) > 0

    def _get_background_frame(self) -> np.ndarray:
        w, h = self.app.width.get(), self.app.height.get()
        if self._is_gif and self._gif_frames:
            idx = int((self._current_time * self._gif_fps)) % len(self._gif_frames)
            frame = self._gif_frames[idx].copy()
        elif self._background_frame is not None:
            frame = self._background_frame.copy()
        else:
            frame = np.zeros((h, w, 3), dtype=np.uint8)
        return cv2.resize(frame, (w, h))

    def _render_current_frame(self):
        if not self._has_content(): return
        try:
            width, height = self.app.width.get(), self.app.height.get()
            frame = self._get_background_frame()
            kwargs = {
                "fps": self.app.fps.get(),
                "font": self.app.subtitle_font.get(),
                "font_size": self.app.subtitle_size.get(),
                "color": (self.app.subtitle_color_r.get(), self.app.subtitle_color_g.get(), self.app.subtitle_color_b.get()),
                "opacity": self.app.subtitle_opacity.get(),
                "pos_x": self.app.subtitle_x.get(),
                "pos_y": self.app.subtitle_y.get(),
                "line_break": self.app.subtitle_line_break.get(),
                "audio_path": self.app.audio_path.get(),
            }
            frame = self.app.module_manager.render_all(frame, self._current_time, **kwargs)
            fade = self.app.fade.get()
            if fade > 0 and self._duration > 0:
                alfa = 1.0
                if self._current_time < fade: alfa = self._current_time / fade
                elif self._current_time > self._duration - fade: alfa = (self._duration - self._current_time) / fade
                alfa = max(0.0, min(1.0, alfa))
                if alfa < 1.0: frame = (frame.astype(np.float32) * alfa).astype(np.uint8)

            qual = self.app.config_vars["preview_quality"].get()
            scale = 0.4 if qual == "low" else 0.7 if qual == "medium" else 1.0
            
            canvas_w = self.preview_label.winfo_width()
            canvas_h = self.preview_label.winfo_height()
            if canvas_w < 10: canvas_w, canvas_h = 640, 360

            self.preview_label.config(image="") # Anti-ghosting
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Calcular dimensiones manteniendo proporcion
            target_width = int(width * scale)
            target_height = int(height * scale)
            
            # Mantener proporcion original
            aspect_ratio = width / height
            canvas_aspect = canvas_w / canvas_h
            
            if canvas_aspect > aspect_ratio:
                # Canvas mas ancho que la imagen, ajustar por altura
                display_height = canvas_h
                display_width = int(display_height * aspect_ratio)
            else:
                # Canvas mas alto que la imagen, ajustar por ancho
                display_width = canvas_w
                display_height = int(display_width / aspect_ratio)
            
            # Redimensionar manteniendo proporcion
            frame_resized = cv2.resize(frame_rgb, (display_width, display_height), interpolation=cv2.INTER_AREA)

            img = Image.fromarray(frame_resized)
            photo = ImageTk.PhotoImage(img)
            self.preview_label.config(image=photo)
            self.preview_label.image = photo
            self.seek_var.set(self._current_time)
            self.time_label.config(text=self._format_time(self._current_time))
        except: pass

    def render_single_frame(self, tiempo: float | None = None):
        if tiempo is not None: self._current_time = tiempo
        self._render_current_frame()

    @staticmethod
    def _format_time(seconds: float) -> str:
        m, s = int(seconds // 60), int(seconds % 60)
        return f"{m:02d}:{s:02d}"

    def stop(self): self._stop_event.set(); self._playing = False
