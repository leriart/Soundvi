#!/usr/bin/env python3
"""
Modulo de visualizacion de waveform para Soundvi.

Ejemplo de modulo automaticamente cargado que implementa
visualizacion de audio estilo Wav2Bar.
"""

import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
import numpy as np
import cv2

from modules.base import Module


class WaveformModule(Module):
    """
    Modulo de visualizacion de waveform con fisica avanzada.
    
    Implementa un visualizador de audio con multiples modos y
    parametros configurables en tiempo real.
    """
    
    def __init__(self):
        super().__init__(nombre="Waveform Visualizer", 
                        descripcion="Visualizacion de audio con fisica avanzada estilo Wav2Bar")
        
        # Referencia a la app principal (se establecera luego)
        self.app = None
        
        # Motor de visualizacion
        self.engine = None
        
        # Configuracion por defecto
        self._config = {
            "mode": "bars",          # "bars", "waveform", "particles", "spectrum"
            "mirror": True,
            "invert": False,
            "physics_enabled": True,
            "gravity": 0.2,
            "inertia": 0.8,
            "response": 0.5,
            "smoothing": 0.3,
            "glow_intensity": 0.0,
            "corner_radius": 2,
            "num_bars": 64,
            "bar_color_r": 255,
            "bar_color_g": 255,
            "bar_color_b": 255,
            "opacity": 1.0,
            "height_ratio": 0.6,
            "width_ratio": 0.98,
            "spacing_ratio": 0.1,
            "shadow_enabled": True,
            "gradient_enabled": False,
        }
    
    def prepare_audio(self, audio_path, mel_data, sr, hop, duration, fps):
        """Prepara el modulo con datos de audio."""
        try:
            from core.wav2bar_engine import Wav2BarEngine
            
            # Crear motor si no existe
            if self.engine is None:
                width = 1280  # Valores por defecto, se ajustaran en render
                height = 720
                self.engine = Wav2BarEngine(num_bars=64, framerate=fps, 
                                          width=width, height=height)
            
            # Configurar motor
            # Primero convertir RGB a BGR y el resto de la configuracion
            bgr_color = (
                self._config.get("bar_color_b", 255),
                self._config.get("bar_color_g", 255),
                self._config.get("bar_color_r", 255)
            )
            
            # Parametros principales
            self.engine.set_config(
                mode=self._config.get("mode", "bars"),
                mirror=self._config.get("mirror", True),
                invert=self._config.get("invert", False),
                response=self._config.get("response", 0.5),
                gravity=self._config.get("gravity", 0.2),
                inertia=self._config.get("inertia", 0.8),
                smoothing=self._config.get("smoothing", 0.3),
                color=bgr_color,
                glow_intensity=self._config.get("glow_intensity", 0.0),
                corner_radius=self._config.get("corner_radius", 2),
                shadow_enabled=self._config.get("shadow_enabled", True),
                gradient_enabled=self._config.get("gradient_enabled", False),
                num_bars=self._config.get("num_bars", 64),
                pos_x=self._config.get("pos_x", 0.5),
                pos_y=self._config.get("pos_y", 0.9),
                scale_y=self._config.get("scale_y", 0.6),
                bar_width_ratio=self._config.get("bar_width_ratio", 0.98),
                spacing_ratio=self._config.get("spacing_ratio", 0.1)
            )
            
            # Cargar audio
            self.engine.load_audio(audio_path)
            
            print(f"[WaveformModule] Audio preparado: {duration:.2f}s")
            
        except Exception as e:
            print(f"[WaveformModule] Error preparando audio: {e}")
    
    def render(self, frame: np.ndarray, tiempo: float, **kwargs) -> np.ndarray:
        """
        Renderiza este modulo sobre el frame dado.
        
        Parametros:
            frame: Frame BGR de OpenCV (alto, ancho, 3)
            tiempo: Tiempo actual en segundos
            **kwargs: Datos adicionales
            
        Devuelve:
            Frame con el modulo renderizado
        """
        if not self.habilitado or self.engine is None or not self.engine.is_ready():
            return frame
        
        try:
            # Obtener dimensiones del frame
            height, width = frame.shape[:2]
            
            # Actualizar dimensiones del motor si cambiaron
            if self.engine.width != width or self.engine.height != height:
                self.engine.width = width
                self.engine.height = height
                self.engine._update_layout()
            
            # Calcular indice de frame
            fps = kwargs.get('fps', 30)
            frame_index = min(int(tiempo * fps), self.engine.total_frames - 1)
            
            # Renderizar con el motor
            rendered = self.engine.render_frame(frame_index, frame)
            
            # Aplicar opacidad si es necesario
            opacity = self._config["opacity"]
            if opacity < 1.0:
                blended = cv2.addWeighted(frame, 1.0 - opacity, 
                                        rendered, opacity, 0)
                return blended
            
            return rendered
            
        except Exception as e:
            print(f"[WaveformModule] Error en render: {e}")
            return frame
    
    def get_config_widgets(self, parent, app):
        """Crea widgets de configuracion para el sidebar."""
        self.app = app
        _as = app
        
        content_frame = tb.Frame(parent)
        
        # Selector de color (usando la nueva funcion base si esta disponible)
        if hasattr(self, 'create_color_picker'):
            # Generar HEX del color guardado (de las tres variables)
            r = self._config.get("bar_color_r", 255)
            g = self._config.get("bar_color_g", 255)
            b = self._config.get("bar_color_b", 255)
            
            current_hex = f"#{r:02x}{g:02x}{b:02x}"
            self._color_var = tk.StringVar(value=current_hex)
            
            color_frame = self.create_color_picker(content_frame, self._color_var, app, "Color:")
            color_frame.pack(fill=tk.X, pady=5)
            
            def update_color(*args):
                hex_color = self._color_var.get()
                if hex_color and hex_color.startswith('#') and len(hex_color) == 7:
                    try:
                        r_new = int(hex_color[1:3], 16)
                        g_new = int(hex_color[3:5], 16)
                        b_new = int(hex_color[5:7], 16)
                        self._update_config("bar_color_r", r_new, _as)
                        self._update_config("bar_color_g", g_new, _as)
                        self._update_config("bar_color_b", b_new, _as)
                    except ValueError:
                        pass
                        
            self._color_var.trace_add("write", update_color)
            
        # === MODOS DE VISUALIZACION ===
        mode_frame = tb.Frame(content_frame)
        mode_frame.pack(fill=tk.X, pady=2)
        
        tb.Label(mode_frame, text="Modo:").pack(side=tk.LEFT, padx=2)
        mode_var = tk.StringVar(value=self._config.get("mode", "bars"))
        mode_combo = tb.Combobox(mode_frame, textvariable=mode_var,
                               values=["bars", "waveform", "particles", "spectrum"],
                               width=10, state="readonly")
        mode_combo.pack(side=tk.LEFT, padx=2)
        
        def on_mode_change(*args):
            self._update_config("mode", mode_var.get(), _as)
        mode_var.trace_add("write", on_mode_change)
        
        # Opciones extra (espejo/invertir)
        opt_frame = tb.Frame(content_frame)
        opt_frame.pack(fill=tk.X, pady=2)
        mirror_var = tk.BooleanVar(value=self._config.get("mirror", True))
        tb.Checkbutton(opt_frame, text="Espejo",
                     variable=mirror_var,
                     bootstyle="info-round-toggle",
                     command=lambda: self._update_config("mirror", mirror_var.get(), _as)).pack(side=tk.LEFT, padx=5)

        invert_var = tk.BooleanVar(value=self._config.get("invert", False))
        tb.Checkbutton(opt_frame, text="Invertir",
                     variable=invert_var,
                     bootstyle="info-round-toggle",
                     command=lambda: self._update_config("invert", invert_var.get(), _as)).pack(side=tk.LEFT, padx=5)

        # === ESTILOS ===
        style_frame = tb.LabelFrame(content_frame, text="Estilo Visual")
        style_frame.pack(fill=tk.X, pady=5)

        # Transparencia
        opacity_frame = tb.Frame(style_frame)
        opacity_frame.pack(fill=tk.X, pady=2)
        tb.Label(opacity_frame, text="Transparencia:").pack(side=tk.LEFT, padx=2)
        opacity_scale = tb.Scale(
            opacity_frame,
            from_=0.0,
            to=1.0,
            value=self._config.get("opacity", 1.0),
            orient=tk.HORIZONTAL,
            length=120,
            command=lambda v: self._update_config("opacity", float(v), _as)
        )
        opacity_scale.pack(side=tk.LEFT, padx=2)
        opacity_label = tb.Label(opacity_frame, text=f"{self._config.get('opacity', 1.0):.2f}")
        opacity_label.pack(side=tk.LEFT, padx=2)
        opacity_scale.configure(command=lambda v: (
            self._update_config("opacity", float(v), _as),
            opacity_label.config(text=f"{float(v):.2f}")
        ))
        
        # Opciones visuales
        vis_opt_frame = tb.Frame(style_frame)
        vis_opt_frame.pack(fill=tk.X, pady=2)
        shadow_var = tk.BooleanVar(value=self._config.get("shadow_enabled", True))
        tb.Checkbutton(vis_opt_frame, text="Sombra", variable=shadow_var, bootstyle="info-round-toggle",
                     command=lambda: self._update_config("shadow_enabled", shadow_var.get(), _as)).pack(side=tk.LEFT, padx=5)

        grad_var = tk.BooleanVar(value=self._config.get("gradient_enabled", False))
        tb.Checkbutton(vis_opt_frame, text="Gradiente", variable=grad_var, bootstyle="info-round-toggle",
                     command=lambda: self._update_config("gradient_enabled", grad_var.get(), _as)).pack(side=tk.LEFT, padx=5)
                     
        # Cantidad de barras
        num_frame = tb.Frame(style_frame)
        num_frame.pack(fill=tk.X, pady=2)
        tb.Label(num_frame, text="Nº Barras:").pack(side=tk.LEFT, padx=2)
        num_spin = tb.Spinbox(num_frame, from_=8, to=256, width=5)
        num_spin.set(self._config.get("num_bars", 64))
        num_spin.pack(side=tk.LEFT, padx=2)
        
        def save_num_bars(*args):
            try:
                self._update_config("num_bars", int(num_spin.get()), _as)
            except: pass
        num_spin.config(command=save_num_bars)

        # Tamaño y espaciado (Grosor y Separacion)
        size_frame = tb.Frame(style_frame)
        size_frame.pack(fill=tk.X, pady=2)
        tb.Label(size_frame, text="Grosor:").pack(side=tk.LEFT, padx=2)
        width_spin = tb.Spinbox(size_frame, from_=0.1, to=1.0, increment=0.1, width=4)
        width_spin.set(self._config.get("bar_width_ratio", 0.98))
        width_spin.pack(side=tk.LEFT, padx=2)
        
        def save_width(*args):
            try:
                self._update_config("bar_width_ratio", float(width_spin.get()), _as)
            except: pass
        width_spin.config(command=save_width)
        
        tb.Label(size_frame, text="Separacion:").pack(side=tk.LEFT, padx=(5,2))
        space_spin = tb.Spinbox(size_frame, from_=0.0, to=1.0, increment=0.05, width=4)
        space_spin.set(self._config.get("spacing_ratio", 0.1))
        space_spin.pack(side=tk.LEFT, padx=2)
        
        def save_spacing(*args):
            try:
                self._update_config("spacing_ratio", float(space_spin.get()), _as)
            except: pass
        space_spin.config(command=save_spacing)

        # Posicion X e Y, Escala Y
        pos_frame = tb.Frame(style_frame)
        pos_frame.pack(fill=tk.X, pady=2)
        tb.Label(pos_frame, text="Pos X:").pack(side=tk.LEFT, padx=2)
        x_spin = tb.Spinbox(pos_frame, from_=0.0, to=1.0, increment=0.05, width=4)
        x_spin.set(self._config.get("pos_x", 0.5))
        x_spin.pack(side=tk.LEFT, padx=2)
        
        def save_x(*args):
            try:
                self._update_config("pos_x", float(x_spin.get()), _as)
            except: pass
        x_spin.config(command=save_x)
        
        tb.Label(pos_frame, text="Pos Y:").pack(side=tk.LEFT, padx=(5,2))
        y_spin = tb.Spinbox(pos_frame, from_=0.0, to=1.0, increment=0.05, width=4)
        y_spin.set(self._config.get("pos_y", 0.9))
        y_spin.pack(side=tk.LEFT, padx=2)
        
        def save_y(*args):
            try:
                self._update_config("pos_y", float(y_spin.get()), _as)
            except: pass
        y_spin.config(command=save_y)

        tb.Label(pos_frame, text="Tamaño (Escala Y):").pack(side=tk.LEFT, padx=(5,2))
        sc_spin = tb.Spinbox(pos_frame, from_=0.1, to=2.0, increment=0.1, width=4)
        sc_spin.set(self._config.get("scale_y", 0.6))
        sc_spin.pack(side=tk.LEFT, padx=2)
        
        def save_sc(*args):
            try:
                self._update_config("scale_y", float(sc_spin.get()), _as)
            except: pass
        sc_spin.config(command=save_sc)

        # Corner radius y glow
        slider_frame1 = tb.Frame(style_frame)
        slider_frame1.pack(fill=tk.X, pady=2)
        tb.Label(slider_frame1, text="Esquinas (px):").pack(side=tk.LEFT, padx=2)
        corner_spin = tb.Spinbox(slider_frame1, from_=0, to=20, width=4)
        corner_spin.set(self._config.get("corner_radius", 2))
        corner_spin.pack(side=tk.LEFT, padx=2)
        
        def save_corner(*args):
            try:
                self._update_config("corner_radius", int(corner_spin.get()), _as)
            except: pass
        corner_spin.config(command=save_corner)
        
        tb.Label(slider_frame1, text="Brillo (0-1):").pack(side=tk.LEFT, padx=10)
        glow_spin = tb.Spinbox(slider_frame1, from_=0.0, to=1.0, increment=0.1, width=4)
        glow_spin.set(self._config.get("glow_intensity", 0.0))
        glow_spin.pack(side=tk.LEFT, padx=2)
        
        def save_glow(*args):
            try:
                self._update_config("glow_intensity", float(glow_spin.get()), app)
            except: pass
        glow_spin.config(command=save_glow)

        # === PARAMETROS FISICOS ===
        physics_frame = tb.LabelFrame(content_frame, text="Parametros Fisicos")
        physics_frame.pack(fill=tk.X, pady=5)
        
        # Sensibilidad
        sens_frame = tb.Frame(physics_frame)
        sens_frame.pack(fill=tk.X, pady=2)
        tb.Label(sens_frame, text="Sensibilidad:").pack(side=tk.LEFT, padx=2)
        sens_scale = tb.Scale(sens_frame, from_=0.1, to=10.0, 
                            value=self._config.get("response", 0.5),
                            orient=tk.HORIZONTAL, length=120,
                            command=lambda v: self._update_config("response", float(v), _as))
        sens_scale.pack(side=tk.LEFT, padx=2)
        sens_label = tb.Label(sens_frame, text=f"{self._config.get('response', 0.5):.1f}")
        sens_label.pack(side=tk.LEFT)
        sens_scale.configure(command=lambda v: (
            self._update_config("response", float(v), _as),
            sens_label.config(text=f"{float(v):.1f}")
        ))
        
        # Gravedad
        grav_frame = tb.Frame(physics_frame)
        grav_frame.pack(fill=tk.X, pady=2)
        tb.Label(grav_frame, text="Gravedad:").pack(side=tk.LEFT, padx=2)
        grav_scale = tb.Scale(grav_frame, from_=0.01, to=5.0, 
                            value=self._config.get("gravity", 0.2),
                            orient=tk.HORIZONTAL, length=120,
                            command=lambda v: self._update_config("gravity", float(v), app))
        grav_scale.pack(side=tk.LEFT, padx=2)
        grav_label = tb.Label(grav_frame, text=f"{self._config.get('gravity', 0.2):.2f}")
        grav_label.pack(side=tk.LEFT)
        grav_scale.configure(command=lambda v: (
            self._update_config("gravity", float(v), app),
            grav_label.config(text=f"{float(v):.2f}")
        ))
        
        return content_frame

    def _update_config(self, key: str, value, app):
        # Primero, llamar al método base para actualizar config, guardar y refrescar preview
        super()._update_config(key, value, app)

        # Sincronizar con el engine interno de visualización si existe
        if self.engine is not None:
            config_map = {
                "mode": "mode", "mirror": "mirror", "invert": "invert",
                "response": "response", "gravity": "gravity", "inertia": "inertia",
                "smoothing": "smoothing", "glow_intensity": "glow_intensity",
                "corner_radius": "corner_radius", "shadow_enabled": "shadow_enabled",
                "gradient_enabled": "gradient_enabled",
                "num_bars": "num_bars", "pos_x": "pos_x", "pos_y": "pos_y",
                "scale_y": "scale_y", "bar_width_ratio": "bar_width_ratio",
                "spacing_ratio": "spacing_ratio"
            }
            if key in config_map:
                self.engine.set_config(**{config_map[key]: value})
            elif key in ("bar_color_r", "bar_color_g", "bar_color_b"):
                r = self._config.get("bar_color_r", 255)
                g = self._config.get("bar_color_g", 255)
                b = self._config.get("bar_color_b", 255)
                self.engine.set_config(color=(b, g, r))
