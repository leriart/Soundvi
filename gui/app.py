#!/usr/bin/env python3
from __future__ import annotations
"""
SoundviApp -- aplicacion principal de Soundvi.

Layout: Sidebar izquierdo (30%) + Preview derecho (70%)
Con sistema de modulos extensible y preview en tiempo real.
"""


import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, BOTH, YES, DISABLED, NORMAL

import ttkbootstrap as tb
from PIL import Image

from utils.config import (
    load_config, save_config, hex_to_rgb,
)
from utils.ffmpeg import get_ffmpeg_path, set_custom_ffmpeg_path
from utils.gpu import detect_gpu_codecs
from utils.fonts import get_system_fonts
from utils.subtitles import parse_srt

from gui.loading import LoadingOverlay
from modules.manager import ModuleManager
# Los modulos se cargan automaticamente desde la carpeta modules/

# from core.video_generator import generate_video  # Deshabilitado temporalmente
from core.audio_processing import get_audio_features, compute_bar_heights


class SoundviApp:
    """Controlador principal de Soundvi."""

    def __init__(self, root: tb.Window):
        self.root = root
        self.root.title("Soundvi - Generador de Video con Visualizador")
        self.root.geometry("1280x800")
        self.root.resizable(True, True)
        self.root.minsize(900, 600)

        # -- Cargar configuracion persistente ---------------------------------
        self._cfg = load_config()
        self._gpu_codecs = detect_gpu_codecs()
        if self._gpu_codecs:
            print(f"[app] Codificadores GPU detectados: {self._gpu_codecs}")
        
        # -- Información del sistema ------------------------------------------
        import sys
        self._python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        # Aplicar ruta personalizada de FFmpeg si existe
        ffmpeg_custom = self._cfg.get("ffmpeg_path", "")
        if ffmpeg_custom:
            set_custom_ffmpeg_path(ffmpeg_custom)

        # -- Inicializar sistema de modulos -----------------------------------
        self.module_manager = ModuleManager()  # Carga automatica de modulos

        # -- Declarar variables tk --------------------------------------------
        self._init_tk_vars()

        # -- Conectar auto-guardado -------------------------------------------
        self._setup_autosave()

        # -- Construir interfaz (Sidebar + Preview) ---------------------------
        self._build_layout()

        # -- Inicializar estado de modulos ------------------------------------
        self._init_module_states()

        # -- Overlay de Carga ("cagando....") ---------------------------------
        self.loading_overlay = LoadingOverlay(self.root, self)

        # -- Datos de audio pre-procesados ------------------------------------
        self._audio_heights: None | object = None
        self._audio_duration: float = 0.0

    # ────────────────────────────────────────────────────────────────────
    # Inicializacion de variables tk
    # ────────────────────────────────────────────────────────────────────

    def _init_tk_vars(self):
        C = self._cfg

        self.media_path = tk.StringVar(value=C.get("media_path", ""))
        self.audio_path = tk.StringVar(value=C.get("audio_path", ""))
        self.output_path = tk.StringVar(value=C.get("output_path", ""))
        self.ffmpeg_custom_path = tk.StringVar(value=C.get("ffmpeg_path", ""))
        self.width = tk.IntVar(value=C.get("width", 1920))
        self.height = tk.IntVar(value=C.get("height", 1080))
        self.fps = tk.IntVar(value=C.get("fps", 30))
        self.fade = tk.DoubleVar(value=C.get("fade", 3.0))

        self.final_volume = tk.IntVar(value=C.get("final_volume", 100))
        self.volume_protection = tk.BooleanVar(value=C.get("volume_protection", True))
        self.normalize_audio = tk.BooleanVar(value=C.get("normalize_audio", True))
        self.max_safe_volume = tk.IntVar(value=C.get("max_safe_volume", 150))

        # Variables para subtítulos (mantenidas por compatibilidad con módulo existente)
        self.subtitle_enabled = tk.BooleanVar(value=C.get("subtitles_enabled", False))
        self.subtitle_path = tk.StringVar(value=C.get("subtitle_path", ""))
        self.subtitle_font = tk.StringVar(value=C.get("subtitle_font", "Arial"))
        self.subtitle_size = tk.IntVar(value=C.get("subtitle_size", 36))
        self.subtitle_color_r = tk.IntVar(value=C.get("subtitle_color_r", 255))
        self.subtitle_color_g = tk.IntVar(value=C.get("subtitle_color_g", 255))
        self.subtitle_color_b = tk.IntVar(value=C.get("subtitle_color_b", 255))
        self.subtitle_opacity = tk.DoubleVar(value=C.get("subtitle_opacity", 1.0))
        self.subtitle_x = tk.IntVar(value=C.get("subtitle_x", 50))
        self.subtitle_y = tk.IntVar(value=C.get("subtitle_y", 90))
        self.subtitle_layer = tk.StringVar(value=C.get("subtitle_layer", "above"))
        self.subtitle_line_break = tk.IntVar(value=C.get("subtitle_line_break", 40))

        # Variables para activación de módulos (solo subtítulos por ahora, CAVA eliminado)
        self.subtitles_enabled_var = tk.BooleanVar(value=C.get("subtitles_enabled", False))

        self.config_vars: dict[str, tk.Variable] = {
            "video_library": tk.StringVar(value=C.get("video_library", "moviepy")),
            "theme": tk.StringVar(value=C.get("theme", "darkly")),
            "cpu_threads": tk.IntVar(value=C.get("cpu_threads", 4)),
            "ffmpeg_preset": tk.StringVar(value=C.get("ffmpeg_preset", "medium")),
            "ffmpeg_codec": tk.StringVar(value=C.get("ffmpeg_codec", "libx264")),
            "use_gpu": tk.BooleanVar(value=C.get("use_gpu", False)),
            "gpu_codec": tk.StringVar(value=C.get("gpu_codec", "h264_nvenc")),
            "auto_save": tk.BooleanVar(value=C.get("auto_save", True)),
            "preview_quality": tk.StringVar(value=C.get("preview_quality", "medium")),
            "log_level": tk.StringVar(value=C.get("log_level", "info")),
        }

    # ────────────────────────────────────────────────────────────────────
    # Layout principal: Sidebar (30%) + Preview (70%)
    # ────────────────────────────────────────────────────────────────────

    def _build_layout(self):
        ffmpeg = get_ffmpeg_path()
        os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg

        # PanedWindow para dividir sidebar y preview
        self.paned = tb.Panedwindow(self.root, orient="horizontal")
        self.paned.pack(fill=BOTH, expand=YES, padx=5, pady=5)

        # -- Sidebar izquierdo ------------------------------------------------
        sidebar_container = tb.Frame(self.paned, width=380)
        self.paned.add(sidebar_container, weight=30)

        from gui.sidebar import build_sidebar
        self.sidebar = build_sidebar(self, sidebar_container)
        self.sidebar.pack(fill=BOTH, expand=YES)

        # -- Preview derecho --------------------------------------------------
        preview_container = tb.Frame(self.paned)
        self.paned.add(preview_container, weight=70)

        from gui.preview import PreviewPanel
        self.preview_panel = PreviewPanel(preview_container, self)

        # Poblar fuentes
        fuentes = get_system_fonts()
        if hasattr(self, "font_combo"):
            self.font_combo["values"] = fuentes[:30]
            self._setup_font_autocomplete(fuentes)

    # ────────────────────────────────────────────────────────────────────
    # Inicializacion de modulos
    # ────────────────────────────────────────────────────────────────────

    def _init_module_states(self):
        """Inicializa modulos a partir de los archivos guardados en modules_config/."""
        
        # Limpiar modulos por defecto cargados al iniciar sin eliminarlos de config (porque podrian no tener id aun)
        self.module_manager._modules.clear()
            
        # Cargar desde los archivos JSON
        loaded_modules = self.module_manager.load_saved_modules()
        
        # Si no hay configuracion nueva, instanciar los por defecto
        if not loaded_modules:
            for mod_type in self.module_manager.get_module_types():
                if "waveform" in mod_type.lower() or "subtitles" in mod_type.lower():
                    mod = self.module_manager.create_module_instance(mod_type)
                    if mod:
                        self.module_manager.add_module_instance(mod)
                        
        # Refrescar la UI
        if hasattr(self, 'refresh_modules_ui'):
            self.refresh_modules_ui()
                        
        # Si hay audio cargado, reprocesarlo para los módulos recién recuperados
        if self.audio_path.get() and os.path.exists(self.audio_path.get()):
            self._process_audio_for_preview()

    # ────────────────────────────────────────────────────────────────────
    # Auto-guardado
    # ────────────────────────────────────────────────────────────────────

    def trigger_auto_save(self, *_args):
        self.root.after(50, self._do_save)

    def _do_save(self):
        auto = self.config_vars["auto_save"]
        if hasattr(auto, "get") and not auto.get():
            return
        config = self._collect_config()
        save_config(config)

    def _collect_config(self) -> dict:
        salida: dict = {}
        mapeo = {
            **{k: v for k, v in self.config_vars.items()},
            "ffmpeg_path": self.ffmpeg_custom_path,
            "final_volume": self.final_volume,
            "volume_protection": self.volume_protection,
            "normalize_audio": self.normalize_audio,
            "max_safe_volume": self.max_safe_volume,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "fade": self.fade,
            "media_path": self.media_path,
            "audio_path": self.audio_path,
            "output_path": self.output_path,
        }
        for key, var in mapeo.items():
            try:
                salida[key] = var.get()
            except Exception:
                pass
                
        # Guardar configuracion de modulos
        self.module_manager.save_all_modules()
                
        return salida

    def _setup_autosave(self):
        rastreadas = [
            self.final_volume, self.volume_protection, self.normalize_audio,
            self.max_safe_volume,
            self.subtitle_enabled, self.subtitle_font, self.subtitle_size,
            self.subtitle_color_r, self.subtitle_color_g, self.subtitle_color_b,
            self.subtitle_opacity, self.subtitle_x, self.subtitle_y,
            self.subtitle_layer, self.subtitle_line_break,
            self.width, self.height, self.fps, self.fade,
            self.media_path, self.audio_path, self.output_path,
            self.subtitle_path, self.ffmpeg_custom_path,
        ]
        for v in self.config_vars.values():
            rastreadas.append(v)

        for v in rastreadas:
            v.trace_add("write", self.trigger_auto_save)
            v.trace_add("write", self.update_preview)

    # ────────────────────────────────────────────────────────────────────
    # Navegacion de archivos
    # ────────────────────────────────────────────────────────────────────

    def browse_media(self):
        ft = [("Imagenes y GIFs", "*.gif *.jpg *.jpeg *.png *.bmp"), ("Todos", "*.*")]
        path = filedialog.askopenfilename(title="Seleccionar GIF o imagen", filetypes=ft)
        if path:
            self.media_path.set(path)
            try:
                img = Image.open(path)
                self.width.set(img.size[0])
                self.height.set(img.size[1])
            except Exception:
                pass
            self.preview_panel.load_background(path)
            self._process_audio_for_preview()
            self.update_preview()

    def browse_audio(self):
        ft = [("Audio", "*.mp3 *.wav *.ogg *.flac *.m4a"), ("Todos", "*.*")]
        path = filedialog.askopenfilename(title="Seleccionar archivo de audio", filetypes=ft)
        if path:
            self.audio_path.set(path)
            self._process_audio_for_preview()

    def browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Guardar video como", defaultextension=".mp4",
            filetypes=[("MP4", "*.mp4")],
        )
        if path:
            self.output_path.set(path)

    def clear_all_files(self):
        """Limpia todas las rutas de archivos cargados."""
        self.media_path.set("")
        self.audio_path.set("")
        self.output_path.set("")
        self.subtitle_path.set("")
        if hasattr(self, "preview_panel"):
            self.preview_panel._background_frame = None
            self.preview_panel._gif_frames = []
            self.preview_panel._audio_path = None
            try:
                import pygame
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except:
                pass
            self.preview_panel._show_empty_state()
        self.status.config(text="Archivos limpiados")

    def reload_current_files(self):
        """Recarga los archivos que ya están en las rutas hacia el preview."""
        media = self.media_path.get()
        audio = self.audio_path.get()
        
        if not media and not audio:
            self.status.config(text="No hay archivos configurados para cargar")
            return
            
        if media:
            self.preview_panel.load_background(media)
        
        if audio:
            self._process_audio_for_preview()
            
        self.status.config(text="Archivos cargados en preview")
        self.update_preview()

    def browse_subtitle(self):
        ft = [("Archivos SRT", "*.srt"), ("Todos", "*.*")]
        path = filedialog.askopenfilename(title="Seleccionar archivo SRT", filetypes=ft)
        if path:
            self.subtitle_path.set(path)
            self._load_subtitles(path)

    def _load_subtitles(self, path: str):
        subs = parse_srt(path)
        self._subtitles_module.set_subtitles(subs)
        cantidad = len(subs)
        print(f"[app] {cantidad} subtitulo(s) cargado(s)")
        if hasattr(self, "subtitle_file_label"):
            self.subtitle_file_label.config(text=f"{cantidad} subtítulos cargados")
        self.update_preview()

    # ────────────────────────────────────────────────────────────────────
    # Procesamiento de audio para preview
    # ────────────────────────────────────────────────────────────────────

    def _process_audio_for_preview(self):
        """Procesa el audio en un hilo para preparar datos de preview."""
        audio = self.audio_path.get()
        media = self.media_path.get()
        if not audio or not media:
            return

        # Mostrar overlay de carga del sistema
        if hasattr(self, "loading_overlay"):
            self.loading_overlay.show()

        def _worker():
            try:
                self.status.config(text="Procesando audio para preview...")
                # ... resto del procesamiento ...

                # Obtener duracion
                try:
                    from moviepy import AudioFileClip
                    clip = AudioFileClip(audio)
                    duration = clip.duration
                    clip.close()
                except Exception:
                    # Fallback
                    from pydub import AudioSegment
                    seg = AudioSegment.from_file(audio)
                    duration = seg.duration_seconds

                self._audio_duration = duration
                fps = self.fps.get()

                # Extraer caracteristicas de audio (sin parametros CAVA)
                mel, sr, hop = get_audio_features(audio)
                heights = compute_bar_heights(mel, duration, fps, hop, sr)

                # Preparar modulos activos con los datos de audio
                for module in self.module_manager.get_active_modules():
                    if hasattr(module, 'prepare_audio'):
                        module.prepare_audio(audio, mel, sr, hop, duration, fps)
                
                self._audio_heights = heights

                # Ocultar pantalla de carga
                if hasattr(self, "preview_panel"):
                    self.root.after(0, lambda: self.preview_panel._show_loading_state(False))

                # Actualizar preview panel
                self.root.after(0, lambda: self._setup_preview(duration, fps))
                self.root.after(0, lambda: self.status.config(text="Audio procesado "))

            except Exception as e:
                print(f"[app] Error al procesar audio: {e}")
                self.root.after(0, lambda: self.status.config(text=f"Error: {e}"))
            finally:
                # -- AGREGADO: Ocultar overlay en el bloque finally --
                # Esto asegura que se oculte incluso si hay un error.
                if hasattr(self, "loading_overlay"):
                    self.root.after(0, self.loading_overlay.hide)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def _setup_preview(self, duration: float, fps: int):
        """Configura el panel de preview con los datos procesados."""
        self.preview_panel.set_duration(duration)
        self.preview_panel.set_fps(fps)
        self.preview_panel.load_audio(self.audio_path.get())
        self.preview_panel.render_single_frame(0.0)

    # ────────────────────────────────────────────────────────────────────
    # Vista previa
    # ────────────────────────────────────────────────────────────────────

    def update_preview(self, *_args):
        """Actualiza el frame actual del preview."""
        if hasattr(self, "preview_panel"):
            # Notificar a los modulos activos que los parametros pueden haber cambiado
            # (Cada modulo es responsable de observar sus propias variables)
            # Forzar re-renderizado del frame actual
            self.preview_panel.render_single_frame()

    # Nota: CAVA eliminado, reemplazado por sistema de modulos automaticos

    # ────────────────────────────────────────────────────────────────────
    # Tema
    # ────────────────────────────────────────────────────────────────────

    def apply_theme(self):
        tema = self.config_vars["theme"].get()
        try:
            tb.Style(theme=tema)
            messagebox.showinfo(
                "Tema aplicado",
                f"Tema '{tema}' aplicado.\nReinicia la app si algunos elementos se ven mal.",
            )
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo aplicar el tema: {exc}")

    # ────────────────────────────────────────────────────────────────────
    # Generacion de video
    # ────────────────────────────────────────────────────────────────────

    def start_generation(self):
        if not self.media_path.get() or not self.audio_path.get() or not self.output_path.get():
            messagebox.showerror("Error", "Todos los campos de archivo deben estar llenos.")
            return

        self.generate_btn.config(state=DISABLED, text="Generando ...")
        self.progress["value"] = 0
        self.status.config(text="Procesando ...")

        # Color por defecto (blanco) - los modulos manejan sus propios colores
        bar_color = (255, 255, 255)
        t = threading.Thread(target=self._run_generation, args=(bar_color,), daemon=True)
        t.start()

    def _run_generation(self, bar_color):
        """Genera video usando el sistema de modulos."""
        from core.video_generator import generate_video
        def cb(val):
            fmt = f"{val:.1f}" if val % 1 else f"{int(val)}"
            self.progress["value"] = val
            self.status.config(text=f"Generando ... {fmt}%")
            self.root.update_idletasks()
        
        active_modules = self.module_manager.get_active_modules()
        ok = generate_video(
            media_path=self.media_path.get(),
            audio_path=self.audio_path.get(),
            output_path=self.output_path.get(),
            width=self.width.get(),
            height=self.height.get(),
            fps=self.fps.get(),
            fade_duration=self.fade.get(),
            active_modules=active_modules,
            progress_callback=cb,
            use_gpu=self.config_vars["use_gpu"].get(),
            gpu_codec=self.config_vars["gpu_codec"].get()
        )
        self.root.after(0, self._gen_done, ok)

    def _gen_done(self, success: bool):
        self.generate_btn.config(state=NORMAL, text="Generar Video")
        if success:
            self.status.config(text="Video generado exitosamente! ")
            messagebox.showinfo("Listo", f"Video guardado en:\n{self.output_path.get()}")
        else:
            self.status.config(text="La generación falló. ❌")
            messagebox.showerror(
                "Error",
                "Ocurrió un error durante la generación. Revisa la salida de consola.",
            )

    def _validated_subtitle_params(self) -> dict:
        def _clamp(val, lo, hi, default):
            try:
                v = float(val)
                return max(lo, min(hi, v))
            except (ValueError, TypeError):
                return default

        fuente = self.subtitle_font.get() or "Arial"
        tamano = _clamp(self.subtitle_size.get(), 12, 72, 24)
        r = int(_clamp(self.subtitle_color_r.get(), 0, 255, 255))
        g = int(_clamp(self.subtitle_color_g.get(), 0, 255, 255))
        b = int(_clamp(self.subtitle_color_b.get(), 0, 255, 255))
        return {
            "font": fuente,
            "size": int(tamano),
            "color": (r, g, b),
            "opacity": _clamp(self.subtitle_opacity.get(), 0, 1, 1.0),
            "x": _clamp(self.subtitle_x.get(), 0, 100, 50),
            "y": _clamp(self.subtitle_y.get(), 0, 100, 90),
            "layer": self.subtitle_layer.get() if self.subtitle_layer.get() in ("above", "below") else "above",
            "line_break": int(_clamp(self.subtitle_line_break.get(), 20, 100, 40)),
        }

    # ────────────────────────────────────────────────────────────────────
    # Autocompletado de fuentes
    # ────────────────────────────────────────────────────────────────────

    def _setup_font_autocomplete(self, todas_fuentes: list[str]):
        def actualizar(_event=None):
            cur = self.subtitle_font.get().lower()
            if not cur:
                self.font_combo["values"] = todas_fuentes[:30]
            else:
                coincidencias = [f for f in todas_fuentes if cur in f.lower()][:30]
                self.font_combo["values"] = coincidencias

        self.font_combo.bind("<KeyRelease>", actualizar)
        self.font_combo.config(postcommand=actualizar)

    # ────────────────────────────────────────────────────────────────────
    # mainloop
    # ────────────────────────────────────────────────────────────────────

    def mainloop(self):
        self.root.mainloop()
