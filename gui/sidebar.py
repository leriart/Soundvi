#!/usr/bin/env python3
from __future__ import annotations
"""
Sidebar izquierdo de Soundvi -- contiene configuraciones generales y modulos.
CON PESTAÑAS: Principal, Ajustes, Logs.
Modificado para soportar el nuevo sistema de modulos con:
- Areas separadas para modulos activos e inactivos
- Interfaz unificada con checks estilo sidebar
- Soporte para multiples instancias de modulos
- Selectores de color integrados
"""


import os
import tkinter as tk
from tkinter import BOTH, YES, LEFT, RIGHT, X, Y, TOP, BOTTOM, HORIZONTAL, filedialog, scrolledtext
import logging

import ttkbootstrap as tb

from utils.ffmpeg import validate_ffmpeg_path
from utils.fonts import get_default_font


def build_sidebar(app, parent: tk.Frame) -> tk.Frame:
    """
    Construye el sidebar izquierdo con secciones fijas y pestañas.
    """
    sidebar = tb.Frame(parent)

    # -- SECCION FIJA SUPERIOR: Generación y Estado --
    top_fixed = tb.Frame(sidebar, padding=5)
    top_fixed.pack(fill=X, side=TOP)

    # Aviso / Status superior
    status_frame = tb.Frame(top_fixed)
    status_frame.pack(fill=X, pady=(0, 5))

    # Logo al lado del estado si existe
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logos", "logo.png")
    if os.path.exists(logo_path):
        try:
            from PIL import Image, ImageTk
            pill_img = Image.open(logo_path).resize((24, 24), Image.Resampling.LANCZOS)
            app._logo_img = ImageTk.PhotoImage(pill_img)
            tb.Label(status_frame, image=app._logo_img).pack(side=LEFT, padx=(0, 5))
        except Exception as e:
            print(f"Error cargando mini-logo: {e}")

    app.status_msg = tb.Label(
        status_frame, 
        text="Soundvi - Listo", 
        font=(get_default_font(), 10, "bold")
    )
    app.status_msg.pack(side=LEFT, fill=X)

    # Botón Generar Video (Fijo arriba)
    app.generate_btn = tb.Button(
        top_fixed, text="Generar Video",
        command=app.start_generation,
        bootstyle="success",
    )
    app.generate_btn.pack(fill=X, pady=2)

    # Barra de progreso (Fija arriba)
    app.progress = tb.Progressbar(
        top_fixed, length=200, mode="determinate",
        bootstyle="success-striped",
    )
    app.progress.pack(fill=X, pady=2)

    # Separador
    tb.Separator(sidebar, orient="horizontal").pack(fill=X, pady=5)

    # -- Notebook (Pestañas) --
    notebook = tb.Notebook(sidebar)
    notebook.pack(fill=BOTH, expand=YES, padx=2, pady=2)

    # Crear las pestañas
    tab_principal = create_tab_principal(app, notebook)
    tab_modulos = create_tab_modulos(app, notebook)
    tab_ajustes = create_tab_ajustes(app, notebook)
    tab_logs = create_tab_logs(app, notebook)

    notebook.add(tab_principal, text="Principal")
    notebook.add(tab_modulos, text="Módulos")
    notebook.add(tab_ajustes, text="Ajustes")
    notebook.add(tab_logs, text="Logs")

    # Referencia para el estado de aviso
    app.status = app.status_msg  # Mantener compatibilidad con llamadas a app.status.config

    return sidebar


def create_tab_principal(app, notebook) -> tb.Frame:
    """Crea la pestaña Principal con Archivos y Config General."""
    tab = tb.Frame(notebook)
    
    # Canvas con scroll
    canvas = tk.Canvas(tab, highlightthickness=0, width=360)
    scrollbar = tb.Scrollbar(tab, orient="vertical", command=canvas.yview)
    inner = tb.Frame(canvas)
    
    cid = canvas.create_window((0, 0), window=inner, anchor="nw")
    inner.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(cid, width=e.width))
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Scroll con rueda
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux(event):
        if event.num == 4: canvas.yview_scroll(-1, "units")
        elif event.num == 5: canvas.yview_scroll(1, "units")
    
    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    canvas.bind_all("<Button-4>", _on_mousewheel_linux)
    canvas.bind_all("<Button-5>", _on_mousewheel_linux)
    
    scrollbar.pack(side=RIGHT, fill=Y)
    canvas.pack(side=LEFT, fill=BOTH, expand=YES)
    
    _as = app.trigger_auto_save

    # ========== SECCION: BOTONES DE ACCION (Cargar / Limpiar) ==========
    btn_row = tb.Frame(inner)
    btn_row.pack(fill=X, pady=(5, 10), padx=2)
    
    tb.Button(
        btn_row, text="Cargar",
        command=app.reload_current_files,
        bootstyle="info",
        width=10
    ).pack(side=LEFT, padx=2, expand=YES, fill=X)
    
    tb.Button(
        btn_row, text="Limpiar",
        command=app.clear_all_files,
        bootstyle="secondary-outline",
        width=10
    ).pack(side=LEFT, padx=2, expand=YES, fill=X)
    
    # ========== SECCION: Archivos ==========
    ff = tb.LabelFrame(inner, text="Archivos")
    ff.pack(fill=X, pady=4, padx=2)
    
    # GIF/Imagen
    row_media = tb.Frame(ff)
    row_media.pack(fill=X, pady=2)
    tb.Label(row_media, text="GIF / Imagen:").pack(anchor="w")
    media_row = tb.Frame(ff)
    media_row.pack(fill=X, pady=1)
    tb.Entry(media_row, textvariable=app.media_path, width=25, state="readonly").pack(side=LEFT, fill=X, expand=YES, padx=(0, 2))
    tb.Button(media_row, text="...", command=app.browse_media, width=3).pack(side=LEFT)
    
    # Audio
    tb.Label(ff, text="Audio:").pack(anchor="w", pady=(4, 0))
    audio_row = tb.Frame(ff)
    audio_row.pack(fill=X, pady=1)
    tb.Entry(audio_row, textvariable=app.audio_path, width=25, state="readonly").pack(side=LEFT, fill=X, expand=YES, padx=(0, 2))
    tb.Button(audio_row, text="...", command=app.browse_audio, width=3).pack(side=LEFT)
    
    # Salida
    tb.Label(ff, text="Video de salida:").pack(anchor="w", pady=(4, 0))
    out_row = tb.Frame(ff)
    out_row.pack(fill=X, pady=1)
    tb.Entry(out_row, textvariable=app.output_path, width=25, state="readonly").pack(side=LEFT, fill=X, expand=YES, padx=(0, 2))
    tb.Button(out_row, text="...", command=app.browse_output, width=3).pack(side=LEFT)
    
    # ========== SECCION: Configuración General ==========
    gf = tb.LabelFrame(inner, text="Configuración General")
    gf.pack(fill=X, pady=4, padx=2)
    
    # Resolución
    row_res = tb.Frame(gf)
    row_res.pack(fill=X, pady=2)
    tb.Label(row_res, text="Resolución:").pack(side=LEFT, padx=2)
    _spin_pack(row_res, app.width, 320, 3840, 6, _as)
    tb.Label(row_res, text="x").pack(side=LEFT)
    _spin_pack(row_res, app.height, 240, 2160, 6, _as)
    
    # FPS y Fundido
    row_fps = tb.Frame(gf)
    row_fps.pack(fill=X, pady=2)
    tb.Label(row_fps, text="FPS:").pack(side=LEFT, padx=2)
    _spin_pack(row_fps, app.fps, 1, 120, 5, _as)
    tb.Label(row_fps, text="Fundido (s):").pack(side=LEFT, padx=(8, 2))
    _spin_pack(row_fps, app.fade, 0.0, 10.0, 5, _as, inc=0.1)
    
    # Volumen
    row_vol = tb.Frame(gf)
    row_vol.pack(fill=X, pady=2)
    tb.Label(row_vol, text="Volumen (%):").pack(side=LEFT, padx=2)
    tb.Scale(row_vol, from_=0, to=200, variable=app.final_volume,
             orient=HORIZONTAL, length=120, command=lambda _: _as()).pack(side=LEFT, padx=2)
    app._vol_lbl = tb.Label(row_vol, text=str(int(app.final_volume.get())))
    app._vol_lbl.pack(side=LEFT, padx=2)
    app.final_volume.trace_add("write", lambda *_: app._vol_lbl.config(text=str(int(app.final_volume.get()))))
    
    row_vol_opts = tb.Frame(gf)
    row_vol_opts.pack(fill=X, pady=2)
    tb.Checkbutton(row_vol_opts, text="Protección recorte", variable=app.volume_protection,
                   bootstyle="info-round-toggle").pack(side=LEFT, padx=2)
    tb.Checkbutton(row_vol_opts, text="Normalizar", variable=app.normalize_audio,
                   bootstyle="info-round-toggle").pack(side=LEFT, padx=2)
    
    return tab


def create_tab_modulos(app, notebook) -> tb.Frame:
    """Crea la pestaña Módulos con áreas separadas para activos e inactivos."""
    tab = tb.Frame(notebook)
    
    # Canvas con scroll
    canvas = tk.Canvas(tab, highlightthickness=0, width=360)
    scrollbar = tb.Scrollbar(tab, orient="vertical", command=canvas.yview)
    inner = tb.Frame(canvas)
    
    cid = canvas.create_window((0, 0), window=inner, anchor="nw")
    inner.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(cid, width=e.width))
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Scroll con rueda
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux(event):
        if event.num == 4: canvas.yview_scroll(-1, "units")
        elif event.num == 5: canvas.yview_scroll(1, "units")
    
    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    canvas.bind_all("<Button-4>", _on_mousewheel_linux)
    canvas.bind_all("<Button-5>", _on_mousewheel_linux)
    
    scrollbar.pack(side=RIGHT, fill=Y)
    canvas.pack(side=LEFT, fill=BOTH, expand=YES)
    
    _as = app.trigger_auto_save
    
    # ========== SECCION: Añadir Nuevos Módulos ==========
    add_frame = tb.LabelFrame(inner, text="Añadir Módulos")
    add_frame.pack(fill=X, pady=4, padx=2)
    
    # Selector de tipo de módulo
    row_type = tb.Frame(add_frame)
    row_type.pack(fill=X, pady=2)
    tb.Label(row_type, text="Tipo:", font=(get_default_font(), 9)).pack(side=LEFT, padx=2)
    
    # Obtener tipos de módulos disponibles
    module_types = app.module_manager.get_module_types()
    type_combo = tb.Combobox(
        row_type,
        values=module_types,
        width=25,
        state="readonly"
    )
    type_combo.pack(side=LEFT, padx=2)
    
    if module_types:
        type_combo.set(module_types[0])
    
    # ========== SECCION: Módulos Activos ==========
    active_frame = tb.LabelFrame(inner, text="Módulos Activos")
    active_frame.pack(fill=X, pady=4, padx=2)
    
    app.active_modules_container = tb.Frame(active_frame)
    app.active_modules_container.pack(fill=X, padx=5, pady=5)
    
    # ========== SECCION: Módulos Inactivos ==========
    inactive_frame = tb.LabelFrame(inner, text="Módulos Inactivos")
    inactive_frame.pack(fill=X, pady=4, padx=2)
    
    app.inactive_modules_container = tb.Frame(inactive_frame)
    app.inactive_modules_container.pack(fill=X, padx=5, pady=5)

    # Función para refrescar la UI de módulos
    def refresh_modules_ui():
        # Limpiar contenedores
        for widget in app.active_modules_container.winfo_children():
            widget.destroy()
        for widget in app.inactive_modules_container.winfo_children():
            widget.destroy()
        
        # Obtener módulos activos e inactivos
        active_modules = app.module_manager.get_active_modules()
        inactive_modules = app.module_manager.get_inactive_modules()
        
        # Mostrar módulos activos
        if active_modules:
            for module in active_modules:
                module_frame = module.create_module_frame(app.active_modules_container, app, on_refresh=refresh_modules_ui)
                module_frame.pack(fill=X, pady=2)
        else:
            tb.Label(
                app.active_modules_container,
                text="No hay módulos activos",
                font=(get_default_font(), 9),
                foreground="gray"
            ).pack(pady=10)
        
        # Mostrar módulos inactivos
        if inactive_modules:
            for module in inactive_modules:
                module_frame = module.create_module_frame(app.inactive_modules_container, app, on_refresh=refresh_modules_ui)
                module_frame.pack(fill=X, pady=2)
        else:
            tb.Label(
                app.inactive_modules_container,
                text="No hay módulos inactivos",
                font=(get_default_font(), 9),
                foreground="gray"
            ).pack(pady=10)

    # Botón para añadir módulo (actualizado para usar LoadingOverlay y auto-refresh)
    def add_module():
        module_type = type_combo.get()
        if not module_type:
            return
        
        # Crear nueva instancia
        new_module = app.module_manager.create_module_instance(module_type)
        if new_module:
            app.loading_overlay.show()
            def background_add():
                # Asignar nombre único
                existing_names = [m.nombre for m in app.module_manager.get_modules()]
                base_name = new_module.nombre
                counter = 1
                while new_module.nombre in existing_names:
                    new_module.nombre = f"{base_name} {counter}"
                    counter += 1
                
                # Si el modulo necesita audio, inyectarlo (por ejemplo para waveform)
                if hasattr(new_module, 'prepare_audio') and app.audio_path.get():
                    import os
                    if os.path.exists(app.audio_path.get()) and hasattr(app, '_audio_heights') and app._audio_heights is not None:
                        try:
                            # Re-usar datos procesados previamente
                            new_module.prepare_audio(app.audio_path.get(), app._audio_heights, 44100, 512, app._audio_duration, app.fps.get())
                        except Exception as e:
                            print(f"Error inyectando audio a {new_module.nombre}: {e}")

                # Añadir al gestor
                app.module_manager.add_module_instance(new_module)
                
                # Actualizar la UI en el hilo principal
                app.root.after(0, refresh_modules_ui)
                app.root.after(0, _as)
                app.root.after(500, lambda: app.loading_overlay.hide()) # mostrar cagando un rato
                
            import threading
            threading.Thread(target=background_add, daemon=True).start()
    
    tb.Button(
        add_frame,
        text="Añadir Módulo",
        command=add_module,
        bootstyle="success-outline",
        width=15
    ).pack(fill=X, pady=5, padx=5)
    
    # Inicializar la vista
    app.refresh_modules_ui = refresh_modules_ui
    refresh_modules_ui()
    
    return tab


def create_tab_ajustes(app, notebook) -> tb.Frame:
    """Crea la pestaña Ajustes con FFmpeg, GPU e Interfaz."""
    tab = tb.Frame(notebook)
    canvas = tk.Canvas(tab, highlightthickness=0, width=360)
    scrollbar = tb.Scrollbar(tab, orient="vertical", command=canvas.yview)
    inner = tb.Frame(canvas)
    cid = canvas.create_window((0, 0), window=inner, anchor="nw")
    inner.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(cid, width=e.width))
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=RIGHT, fill=Y)
    canvas.pack(side=LEFT, fill=BOTH, expand=YES)
    _as = app.trigger_auto_save
    
    # ========== SECCION: FFmpeg ==========
    fmpg = tb.LabelFrame(inner, text="FFmpeg")
    fmpg.pack(fill=X, pady=4, padx=2)
    tb.Label(fmpg, text="Ruta personalizada (opcional):").pack(anchor="w")
    ffmpeg_row = tb.Frame(fmpg)
    ffmpeg_row.pack(fill=X, pady=2)
    app.ffmpeg_path_entry = tb.Entry(ffmpeg_row, textvariable=app.ffmpeg_custom_path, width=25)
    app.ffmpeg_path_entry.pack(side=LEFT, fill=X, expand=YES, padx=(0, 2))
    tb.Button(ffmpeg_row, text="...", command=lambda: _browse_ffmpeg(app), width=3).pack(side=LEFT)
    app.ffmpeg_status_label = tb.Label(fmpg, text="", font=("", 8))
    app.ffmpeg_status_label.pack(anchor="w", pady=2)
    tb.Button(fmpg, text="Validar FFmpeg", command=lambda: _validate_ffmpeg(app),
              bootstyle="outline").pack(fill=X, pady=2)
    
    # GPU
    tb.Separator(fmpg, orient="horizontal").pack(fill=X, pady=5)
    row_gpu = tb.Frame(fmpg)
    row_gpu.pack(fill=X, pady=2)
    tb.Checkbutton(row_gpu, text="Habilitar GPU", variable=app.config_vars["use_gpu"],
                   bootstyle="info-round-toggle").pack(side=LEFT, padx=2)
    if app._gpu_codecs:
        tb.Combobox(row_gpu, textvariable=app.config_vars["gpu_codec"], values=app._gpu_codecs,
                    width=15, state="readonly").pack(side=LEFT, padx=5)
    else:
        tb.Label(row_gpu, text="No se detecto GPU", font=("", 8), bootstyle="warning").pack(side=LEFT, padx=5)
    
    # Preset y hilos
    row_enc = tb.Frame(fmpg)
    row_enc.pack(fill=X, pady=2)
    tb.Label(row_enc, text="Preset:").pack(side=LEFT, padx=2)
    tb.Combobox(row_enc, textvariable=app.config_vars["ffmpeg_preset"],
                values=["ultrafast", "superfast", "veryfast", "faster", "fast",
                        "medium", "slow", "slower", "veryslow"],
                width=10, state="readonly").pack(side=LEFT, padx=2)
    tb.Label(row_enc, text="Hilos:").pack(side=LEFT, padx=(8, 2))
    _spin_pack(row_enc, app.config_vars["cpu_threads"], 1, os.cpu_count() or 1, 4, _as)
    
    # ========== SECCION: Interfaz ==========
    uif = tb.LabelFrame(inner, text="Interfaz")
    uif.pack(fill=X, pady=4, padx=2)
    row_theme = tb.Frame(uif)
    row_theme.pack(fill=X, pady=2)
    tb.Label(row_theme, text="Tema:").pack(side=LEFT, padx=2)
    temas = ["darkly", "superhero", "cyborg", "flatly", "journal", "litera",
             "cosmo", "minty", "pulse", "sandstone", "yeti", "morph"]
    tb.Combobox(row_theme, textvariable=app.config_vars["theme"], values=temas,
                width=12, state="readonly").pack(side=LEFT, padx=2)
    tb.Button(row_theme, text="Aplicar", command=app.apply_theme,
              bootstyle="outline", width=7).pack(side=LEFT, padx=5)
    tb.Checkbutton(uif, text="Guardar automaticamente", variable=app.config_vars["auto_save"],
                   bootstyle="info-round-toggle").pack(anchor="w", pady=2)
    
    # Configuración de fuentes
    tb.Separator(uif, orient="horizontal").pack(fill=X, pady=5)
    font_label = tb.Label(uif, text="Fuente principal: JetBrainsMono Nerd Font", 
                         font=(get_default_font(), 9))
    font_label.pack(anchor="w", pady=2)
    
    return tab

def create_tab_logs(app, notebook) -> tb.Frame:
    """Crea la pestaña Logs."""
    tab = tb.Frame(notebook)
    log_frame = tb.Frame(tab)
    log_frame.pack(fill=BOTH, expand=YES, padx=5, pady=5)
    app.log_area = scrolledtext.ScrolledText(
        log_frame, wrap=tk.WORD, width=40, height=20,
        font=(get_default_font(), 9),
        bg="#1e1e1e", fg="#d4d4d4",
        insertbackground="white"
    )
    app.log_area.pack(fill=BOTH, expand=YES)
    app.log_area.config(state=tk.DISABLED)
    app.log_area.tag_config("INFO", foreground="#4ec9b0")
    app.log_area.tag_config("WARNING", foreground="#ce9178")
    app.log_area.tag_config("ERROR", foreground="#f44747")
    app.log_area.tag_config("DEBUG", foreground="#808080")
    ctrl_frame = tb.Frame(tab)
    ctrl_frame.pack(fill=X, padx=5, pady=2)
    tb.Button(ctrl_frame, text="Limpiar Logs", command=lambda: _clear_logs(app),
              bootstyle="danger-outline").pack(side=LEFT, padx=2)
    app.auto_scroll = tk.BooleanVar(value=True)
    tb.Checkbutton(ctrl_frame, text="Auto-scroll", variable=app.auto_scroll,
                   bootstyle="round-toggle").pack(side=RIGHT, padx=5)
    setup_app_logging(app)
    return tab


def setup_app_logging(app):
    class InterfaceLogHandler(logging.Handler):
        def __init__(self, log_widget, auto_scroll_var):
            super().__init__()
            self.log_widget = log_widget
            self.auto_scroll = auto_scroll_var
        def emit(self, record):
            msg = self.format(record)
            level = record.levelname
            def append():
                try:
                    self.log_widget.config(state=tk.NORMAL)
                    self.log_widget.insert(tk.END, f"{msg}\n", level)
                    self.log_widget.config(state=tk.DISABLED)
                    if self.auto_scroll.get(): self.log_widget.see(tk.END)
                except:
                    pass
            app.root.after(0, append)
    handler = InterfaceLogHandler(app.log_area, app.auto_scroll)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S'))
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def _clear_logs(app):
    app.log_area.config(state=tk.NORMAL)
    app.log_area.delete(1.0, tk.END)
    app.log_area.config(state=tk.DISABLED)


def _browse_ffmpeg(app):
    ft = [("Ejecutables", "*"), ("Todos", "*.*")]
    path = filedialog.askopenfilename(title="Seleccionar ejecutable FFmpeg", filetypes=ft)
    if path:
        app.ffmpeg_custom_path.set(path)
        _validate_ffmpeg(app)


def _validate_ffmpeg(app):
    ruta = app.ffmpeg_custom_path.get().strip()
    if not ruta:
        app.ffmpeg_status_label.config(text="Usando auto-deteccion", bootstyle="info")
        from utils.ffmpeg import set_custom_ffmpeg_path
        set_custom_ffmpeg_path(None)
        return
    if validate_ffmpeg_path(ruta):
        app.ffmpeg_status_label.config(text="FFmpeg valido", bootstyle="success")
        from utils.ffmpeg import set_custom_ffmpeg_path
        set_custom_ffmpeg_path(ruta)
    else:
        app.ffmpeg_status_label.config(text="FFmpeg no valido", bootstyle="danger")


def _spin(parent, var, lo, hi, w, autosave, inc=None, fmt=None):
    kw = {"from_": lo, "to": hi, "textvariable": var, "width": w}
    if inc is not None: kw["increment"] = inc
    if fmt is not None: kw["format"] = fmt
    sb = tb.Spinbox(parent, **kw)
    for ev in ("<<Increment>>", "<<Decrement>>", "<KeyRelease>"):
        sb.bind(ev, lambda _e: autosave())
    return sb


def _spin_pack(parent, var, lo, hi, w, autosave, inc=None, fmt=None):
    sb = _spin(parent, var, lo, hi, w, autosave, inc, fmt)
    sb.pack(side=LEFT, padx=2)
    return sb