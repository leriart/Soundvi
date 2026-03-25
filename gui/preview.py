import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
import cv2

# Cambiar importaciones relativas por absolutas (root del proyecto)
from utils.config import get_default_font, load_config
from utils.ffmpeg import FFmpegWrapper
from core.video_generator import VideoGenerator
from core.audio_processor import AudioProcessor
from modules import list_modules, load_module

# Importar resource_path desde main.py (o definirlo localmente)
def resource_path(relative_path):
    """Obtener ruta absoluta a un recurso en ejecutable empaquetado."""
    if getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS'):
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


class PreviewPanel:
    """Panel de vista previa y control principal."""
    
    def __init__(self, app):
        self.app = app
        self.config = load_config()
        self._empty_photo = None
        self._current_video = None
        self._current_audio = None
        self._generator = None
        self._processor = None
        self._modules = []
        self._preview_thread = None
        self._stop_preview = threading.Event()
        
        self._setup_ui()
        self._load_logo_async()
        self._load_modules()
    
    def _setup_ui(self):
        """Configurar elementos de la interfaz."""
        self.frame = ttk.Frame(self.app.root, padding="10")
        self.frame.grid(row=0, column=0, sticky="nsew")
        
        # Panel de vista previa
        preview_container = ttk.Frame(self.frame)
        preview_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        self.preview_label = ttk.Label(
            preview_container,
            text="Cargando...",
            font=(get_default_font(), 16),
            anchor="center",
            relief="solid",
            borderwidth=2
        )
        self.preview_label.pack(expand=True, fill="both")
        
        # Controles
        controls_frame = ttk.Frame(self.frame)
        controls_frame.grid(row=0, column=1, sticky="ns")
        
        # Botones de carga
        ttk.Button(
            controls_frame,
            text="Cargar Audio",
            command=self._load_audio,
            width=20
        ).pack(pady=5)
        
        ttk.Button(
            controls_frame,
            text="Cargar Video",
            command=self._load_video,
            width=20
        ).pack(pady=5)
        
        # Selector de módulos
        ttk.Label(controls_frame, text="Módulos:").pack(pady=(10, 0))
        self.module_var = tk.StringVar()
        self.module_combo = ttk.Combobox(
            controls_frame,
            textvariable=self.module_var,
            state="readonly",
            width=18
        )
        self.module_combo.pack(pady=5)
        self.module_combo.bind("<<ComboboxSelected>>", self._on_module_selected)
        
        # Lista de módulos activos
        ttk.Label(controls_frame, text="Módulos activos:").pack(pady=(10, 0))
        self.module_listbox = tk.Listbox(
            controls_frame,
            height=4,
            width=20,
            selectmode="single"
        )
        self.module_listbox.pack(pady=5)
        
        # Botones de módulos
        module_btn_frame = ttk.Frame(controls_frame)
        module_btn_frame.pack(pady=5)
        
        ttk.Button(
            module_btn_frame,
            text="+",
            command=self._add_module,
            width=3
        ).pack(side="left", padx=2)
        
        ttk.Button(
            module_btn_frame,
            text="-",
            command=self._remove_module,
            width=3
        ).pack(side="left", padx=2)
        
        # Configuración
        ttk.Separator(controls_frame, orient="horizontal").pack(fill="x", pady=10)
        
        ttk.Label(controls_frame, text="Configuración:").pack()
        
        self.quality_var = tk.StringVar(value="alta")
        ttk.Combobox(
            controls_frame,
            textvariable=self.quality_var,
            values=["baja", "media", "alta", "ultra"],
            state="readonly",
            width=18
        ).pack(pady=5)
        
        # Botón de generación
        ttk.Button(
            controls_frame,
            text="Generar Video",
            command=self._generate_video,
            style="Accent.TButton"
        ).pack(pady=20)
        
        # Barra de progreso
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            controls_frame,
            variable=self.progress_var,
            maximum=100,
            mode="determinate"
        )
        self.progress_bar.pack(fill="x", pady=5)
        
        # Configurar expansión
        self.app.root.grid_rowconfigure(0, weight=1)
        self.app.root.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(0, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)
    
    def _load_logo_async(self):
        """Cargar logo de fondo de forma asíncrona."""
        def load_logo():
            try:
                # Usar resource_path para localizar el logo en cualquier entorno
                logo_path = resource_path("logos/Cagando.png")
                if os.path.exists(logo_path):
                    # Esperar a que la ventana tenga tamaño
                    w = self.preview_label.winfo_width()
                    h = self.preview_label.winfo_height()
                    if w < 10: 
                        self.app.root.after(100, load_logo)
                        return
                    
                    img = Image.open(logo_path)
                    max_size = min(w - 40, h - 100, 500)
                    
                    if max_size > 10:
                        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                        self._empty_photo = ImageTk.PhotoImage(img)
                        self.preview_label.config(
                            image=self._empty_photo, 
                            text="\n\nCarga un archivo de audio y video para empezar", 
                            compound="top",
                            font=(get_default_font(), 14, "bold"),
                            foreground="#4ec9b0"
                        )
                    else:
                        self.preview_label.config(
                            text="Soundvi\n\nCarga un archivo de audio\ny video para empezar",
                            font=(get_default_font(), 12, "bold")
                        )
                else:
                    self.preview_label.config(text="Soundvi", font=(get_default_font(), 16, "bold"))
                
                # Repetir cada segundo para ajustar si la ventana cambia de tamaño
                self.app.root.after(1000, load_logo)
            except Exception as e:
                print(f"Error cargando logo en preview: {e}")
                self.preview_label.config(text="Soundvi", font=(get_default_font(), 16, "bold"))
        
        # Iniciar la carga del logo
        load_logo()
    
    def _load_modules(self):
        """Cargar lista de módulos disponibles."""
        modules = list_modules()
        self.module_combo["values"] = [m["name"] for m in modules]
        if modules:
            self.module_combo.current(0)
    
    def _on_module_selected(self, event):
        pass
    
    def _add_module(self):
        module_name = self.module_var.get()
        if module_name and module_name not in self.module_listbox.get(0, tk.END):
            self.module_listbox.insert(tk.END, module_name)
            self._modules.append(module_name)
    
    def _remove_module(self):
        selection = self.module_listbox.curselection()
        if selection:
            index = selection[0]
            module_name = self.module_listbox.get(index)
            self.module_listbox.delete(index)
            if module_name in self._modules:
                self._modules.remove(module_name)
    
    def _load_audio(self):
        filetypes = [
            ("Audio files", "*.mp3 *.wav *.flac *.ogg *.m4a"),
            ("All files", "*.*")
        ]
        filename = filedialog.askopenfilename(title="Seleccionar audio", filetypes=filetypes)
        if filename:
            self._current_audio = filename
            self._show_preview()
    
    def _load_video(self):
        filetypes = [
            ("Video files", "*.mp4 *.avi *.mov *.mkv *.webm"),
            ("All files", "*.*")
        ]
        filename = filedialog.askopenfilename(title="Seleccionar video", filetypes=filetypes)
        if filename:
            self._current_video = filename
            self._show_preview()
    
    def _show_preview(self):
        if self._current_video and self.preview_label.winfo_exists():
            self._stop_preview.set()
            if self._preview_thread and self._preview_thread.is_alive():
                self._preview_thread.join(timeout=1)
            
            self._stop_preview.clear()
            self._preview_thread = threading.Thread(target=self._update_preview, daemon=True)
            self._preview_thread.start()
    
    def _update_preview(self):
        cap = cv2.VideoCapture(self._current_video)
        if not cap.isOpened():
            return
        
        try:
            while not self._stop_preview.is_set() and self.preview_label.winfo_exists():
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                
                height, width = frame.shape[:2]
                max_size = 400
                if width > height:
                    new_width = max_size
                    new_height = int(height * (max_size / width))
                else:
                    new_height = max_size
                    new_width = int(width * (max_size / height))
                
                frame = cv2.resize(frame, (new_width, new_height))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                img = Image.fromarray(frame)
                photo = ImageTk.PhotoImage(img)
                
                self.app.root.after(0, lambda p=photo: self._update_preview_image(p))
                self._stop_preview.wait(0.066)
        finally:
            cap.release()
    
    def _update_preview_image(self, photo):
        if self.preview_label.winfo_exists():
            self.preview_label.config(image=photo, text="")
            self.preview_label.image = photo
    
    def _generate_video(self):
        if not self._current_audio or not self._current_video:
            messagebox.showerror("Error", "Debes cargar un audio y un video primero.")
            return
        
        filetypes = [("MP4 files", "*.mp4"), ("All files", "*.*")]
        output_file = filedialog.asksaveasfilename(
            title="Guardar video como",
            defaultextension=".mp4",
            filetypes=filetypes
        )
        if not output_file:
            return
        
        self._generator = VideoGenerator(
            audio_path=self._current_audio,
            video_path=self._current_video,
            output_path=output_file,
            quality=self.quality_var.get()
        )
        
        modules = []
        for module_name in self._modules:
            module = load_module(module_name)
            if module:
                modules.append(module)
        
        thread = threading.Thread(target=self._run_generation, args=(modules,), daemon=True)
        thread.start()
    
    def _run_generation(self, modules):
        try:
            self._generator.generate(modules, progress_callback=self._update_progress)
            self.app.root.after(0, lambda: messagebox.showinfo("Éxito", "Video generado correctamente."))
        except Exception as e:
            self.app.root.after(0, lambda: messagebox.showerror("Error", f"Error generando video: {str(e)}"))
        finally:
            self.app.root.after(0, lambda: self.progress_var.set(0))
    
    def _update_progress(self, progress):
        self.app.root.after(0, lambda: self.progress_var.set(progress * 100))