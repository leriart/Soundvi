#!/usr/bin/env python3
from __future__ import annotations
from utils.fonts import get_default_font
"""
Modulo de Subtitulos -- renderiza subtitulos SRT sobre el video.

MEJORADO CON:
- Selector de color mejorado
- Soporte para multiples instancias
- Interfaz unificada con el sistema de modulos
- Fuente JetBrainsMonoNerdFont por defecto
"""


import tkinter as tk
from tkinter import HORIZONTAL, LEFT, X, colorchooser
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    import ttkbootstrap as tb
except ImportError:
    import tkinter.ttk as tb

from modules.base import Module
from utils.subtitles import split_text_lines
from utils.fonts import get_font_path, get_default_font


class SubtitlesModule(Module):
    """
    Modulo de subtitulos SRT mejorado.

    Renderiza texto de subtitulos sobre el frame de video con
    multiples opciones de personalizacion.
    """

    def __init__(self, nombre: str = "Subtítulos", capa: int = 1):
        super().__init__(
            nombre=nombre,
            descripcion="Superposición de subtítulos desde archivos SRT",
            capa=capa
        )
        self._subtitles: list[dict] = []
        self._font_path: str = ""
        self.current_srt_path = None
        
        # Configuraciones por defecto
        self._config.update({
            "color": "#FFFFFF",  # Blanco por defecto
            "font_size": 36,
            "opacity": 1.0,
            "pos_x": 50,  # Porcentaje horizontal
            "pos_y": 90,  # Porcentaje vertical
            "line_break": 40,
            "background_enabled": False,
            "background_opacity": 0.7,
            "background_padding": 10,
            "shadow_enabled": False,
            "shadow_offset": 2,
            "shadow_blur": 3,
            "outline_enabled": False,
            "outline_width": 2,
            "outline_color": "#000000",
            "animation_enabled": False,
            "animation_type": "fade",  # fade, slide, typewriter
            "animation_duration": 0.5,
        })

    def set_subtitles(self, subtitles: list[dict]):
        """Establece la lista de subtitulos parseados."""
        self._subtitles = subtitles

    @property
    def subtitles(self) -> list[dict]:
        return self._subtitles

    def render(self, frame: np.ndarray, tiempo: float, **kwargs) -> np.ndarray:
        """Renderiza los subtitulos sobre el frame."""
        if not self._habilitado or not self._subtitles:
            return frame

        # Encontrar subtitulo activo
        texto = None
        for sub in self._subtitles:
            if sub["start"] <= tiempo <= sub["end"]:
                texto = sub["text"]
                break

        if not texto:
            return frame

        # Obtener configuraciones
        font_size = self._config.get("font_size", 36)
        opacity = self._config.get("opacity", 1.0)
        pos_x_pct = self._config.get("pos_x", 50)
        pos_y_pct = self._config.get("pos_y", 90)
        line_break = self._config.get("line_break", 40)
        bg_enabled = self._config.get("background_enabled", False)
        bg_opacity = self._config.get("background_opacity", 0.7)
        bg_padding = self._config.get("background_padding", 10)
        shadow_enabled = self._config.get("shadow_enabled", False)
        shadow_offset = self._config.get("shadow_offset", 2)
        outline_enabled = self._config.get("outline_enabled", False)
        outline_width = self._config.get("outline_width", 2)

        height_px, width_px = frame.shape[:2]

        # Convertir color hex a RGB desde el diccionario
        color_rgb = self._hex_to_rgb(self._config.get("color", "#FFFFFF"))
        
        # Usar PIL para renderizar texto con todas las caracteristicas
        try:
            # Convertir frame BGR a RGB y agregar alpha
            img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert('RGBA')
            
            # Crear capa transparente para los textos
            txt_layer = Image.new('RGBA', img_pil.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)

            # Cargar fuente
            font = self._load_font(font_size)
            
            # Dividir texto en lineas
            lineas = split_text_lines(texto, line_break) if line_break > 0 else [texto]
            
            # Calcular dimensiones del texto
            text_bboxes = []
            max_width = 0
            total_height = 0
            
            for ln in lineas:
                bbox = draw.textbbox((0, 0), ln, font=font)
                text_bboxes.append(bbox)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                max_width = max(max_width, w)
                total_height += h

            # Posicionamiento
            cx = (width_px - max_width) / 2 + (pos_x_pct - 50) * (width_px / 100)
            cy = int(height_px * pos_y_pct / 100) - total_height // 2

            # Dibujar fondo si esta habilitado
            if bg_enabled:
                bg_rect = [
                    cx - bg_padding,
                    cy - bg_padding,
                    cx + max_width + bg_padding,
                    cy + total_height + bg_padding
                ]
                bg_color = (0, 0, 0, int(255 * bg_opacity * opacity))
                draw.rectangle(bg_rect, fill=bg_color)

            # Dibujar texto con efectos
            y_offset = cy
            text_alpha = int(255 * opacity)
            
            for i, ln in enumerate(lineas):
                bbox = text_bboxes[i]
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                
                # Centrar horizontalmente respecto al bloque de texto
                x = cx + (max_width - w) / 2
                
                # Sombra si esta habilitada
                if shadow_enabled:
                    shadow_color = (0, 0, 0, text_alpha)
                    draw.text((x + shadow_offset, y_offset + shadow_offset), 
                             ln, fill=shadow_color, font=font)
                
                # Contorno si esta habilitado
                if outline_enabled:
                    outline_color = self._hex_to_rgb(self._config.get("outline_color", "#000000"))
                    outline_color_rgba = outline_color + (text_alpha,)
                    
                    # Dibujar contorno en todas las direcciones
                    for dx in [-outline_width, 0, outline_width]:
                        for dy in [-outline_width, 0, outline_width]:
                            if dx != 0 or dy != 0:
                                draw.text((x + dx, y_offset + dy), 
                                         ln, fill=outline_color_rgba, font=font)
                
                # Texto principal
                text_color = color_rgb + (text_alpha,)
                draw.text((x, y_offset), ln, fill=text_color, font=font)
                
                y_offset += h

            # Combinar capas
            combined = Image.alpha_composite(img_pil, txt_layer)
            
            # Convertir de vuelta a BGR
            frame = cv2.cvtColor(np.array(combined.convert("RGB")), cv2.COLOR_RGB2BGR)

        except Exception as e:
            print(f"[subtitles] Error renderizando: {e}")
            # Fallback: usar cv2.putText
            cy = int(height_px * pos_y_pct / 100)
            cv2.putText(
                frame, texto,
                (int(width_px * 0.1), cy),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                (color_rgb[2], color_rgb[1], color_rgb[0]), 2,
            )

        return frame

    def get_config_widgets(self, parent, app) -> tk.Frame:
        """Crea widgets de configuracion mejorados para el sidebar."""
        content_frame = tb.Frame(parent)
        
        _as = app.trigger_auto_save
        
        # Cargar archivo SRT
        row_file = tb.Frame(content_frame)
        row_file.pack(fill=X, pady=2)
        tb.Button(
            row_file, text="Cargar SRT",
            command=lambda: self._browse_subtitle(app),
            bootstyle="outline",
            width=12
        ).pack(side=LEFT, padx=2)
        
        # Mostrar nombre de archivo si ya hay uno cargado
        file_text = "Sin archivo"
        if hasattr(self, 'current_srt_path') and self.current_srt_path:
            import os
            file_text = os.path.basename(self.current_srt_path)
            
        self._file_label = tb.Label(row_file, text=file_text, font=(get_default_font(), 8))
        self._file_label.pack(side=LEFT, padx=5, fill=X, expand=True)

        # Selector de color
        self._color_var = tk.StringVar(value=self._config.get("color", "#FFFFFF"))
        color_frame = self.create_color_picker(content_frame, self._color_var, app, "Color texto:")
        color_frame.pack(fill=X, pady=5)
        
        def update_color(*args):
            self._update_config("color", self._color_var.get(), _as)
        
        self._color_var.trace_add("write", update_color)

        # Fuente y tamaño
        row_font = tb.Frame(content_frame)
        row_font.pack(fill=X, pady=2)
        tb.Label(row_font, text="Fuente:", font=(get_default_font(), 9)).pack(side=LEFT, padx=2)
        
        # Obtener fuentes del sistema
        from utils.fonts import get_system_fonts
        fonts = get_system_fonts()
        
        font_combo = tb.Combobox(
            row_font,
            values=fonts,
            width=20,
            state="readonly"
        )
        font_combo.pack(side=LEFT, padx=2)
        font_combo.set(get_default_font())
        
        tb.Label(row_font, text="Tamaño:", font=(get_default_font(), 9)).pack(side=LEFT, padx=(10, 2))
        
        # Guardar la variable para que no sea recolectada por el GC y rastrearla
        self._font_size_var = tk.IntVar(value=self._config.get("font_size", 36))
        
        def safe_update_size(*args):
            try:
                val = self._font_size_var.get()
                self._update_config("font_size", val, app)
            except (tk.TclError, ValueError):
                pass
                
        size_spin = _spin_pack(row_font, self._font_size_var, 12, 120, 4, safe_update_size)
        
        self._font_size_var.trace_add("write", safe_update_size)

        # Opacidad
        row_opacity = tb.Frame(content_frame)
        row_opacity.pack(fill=X, pady=2)
        tb.Label(row_opacity, text="Opacidad:", font=(get_default_font(), 9)).pack(side=LEFT, padx=2)
        opacity_scale = tb.Scale(
            row_opacity,
            from_=0.0,
            to=1.0,
            value=self._config["opacity"],
            orient=HORIZONTAL,
            length=120,
            command=lambda v: self._update_config("opacity", float(v), _as)
        )
        opacity_scale.pack(side=LEFT, padx=2)
        opacity_label = tb.Label(row_opacity, text=f"{self._config['opacity']:.2f}")
        opacity_label.pack(side=LEFT, padx=2)
        opacity_scale.configure(command=lambda v: (
            self._update_config("opacity", float(v), _as),
            opacity_label.config(text=f"{float(v):.2f}")
        ))

        # Posicion
        row_pos = tb.Frame(content_frame)
        row_pos.pack(fill=X, pady=2)
        tb.Label(row_pos, text="X (%):", font=(get_default_font(), 9)).pack(side=LEFT, padx=2)
        x_scale = tb.Scale(
            row_pos,
            from_=0,
            to=100,
            value=self._config["pos_x"],
            orient=HORIZONTAL,
            length=80,
            command=lambda v: self._update_config("pos_x", int(float(v)), _as)
        )
        x_scale.pack(side=LEFT, padx=2)
        
        tb.Label(row_pos, text="Y (%):", font=(get_default_font(), 9)).pack(side=LEFT, padx=2)
        y_scale = tb.Scale(
            row_pos,
            from_=0,
            to=100,
            value=self._config["pos_y"],
            orient=HORIZONTAL,
            length=80,
            command=lambda v: self._update_config("pos_y", int(float(v)), _as)
        )
        y_scale.pack(side=LEFT, padx=2)

        # Efectos avanzados (en un frame expandible)
        effects_frame = tb.LabelFrame(content_frame, text="Efectos Avanzados")
        effects_frame.pack(fill=X, pady=5)
        
        # Fondo
        bg_var = tk.BooleanVar(value=self._config["background_enabled"])
        bg_check = tb.Checkbutton(
            effects_frame,
            text="Fondo",
            variable=bg_var,
            bootstyle="info-round-toggle",
            command=lambda: self._update_config("background_enabled", bg_var.get(), _as)
        )
        bg_check.pack(anchor="w", pady=2)
        
        # Sombra
        shadow_var = tk.BooleanVar(value=self._config["shadow_enabled"])
        shadow_check = tb.Checkbutton(
            effects_frame,
            text="Sombra",
            variable=shadow_var,
            bootstyle="info-round-toggle",
            command=lambda: self._update_config("shadow_enabled", shadow_var.get(), _as)
        )
        shadow_check.pack(anchor="w", pady=2)
        
        # Contorno
        outline_var = tk.BooleanVar(value=self._config["outline_enabled"])
        outline_check = tb.Checkbutton(
            effects_frame,
            text="Contorno",
            variable=outline_var,
            bootstyle="info-round-toggle",
            command=lambda: self._update_config("outline_enabled", outline_var.get(), _as)
        )
        outline_check.pack(anchor="w", pady=2)

        return content_frame

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Carga la fuente con fallbacks."""
        try:
            # Intentar cargar JetBrainsMonoNerdFont primero
            font_path = get_font_path("JetBrainsMono Nerd Font")
            if font_path and os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
            
            # Fallback a fuentes del sistema
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            # Ultimo fallback
            return ImageFont.load_default()

    def _hex_to_rgb(self, hex_color: str) -> tuple:
        """Convierte color hex a RGB tuple."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        elif len(hex_color) == 8:  # Incluye alpha
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4, 6))
        return (255, 255, 255)  # Blanco por defecto

    def _browse_subtitle(self, app):
        """Abre dialogo para cargar archivo SRT."""
        from tkinter import filedialog
        filetypes = [("Archivos SRT", "*.srt"), ("Todos los archivos", "*.*")]
        path = filedialog.askopenfilename(title="Seleccionar archivo SRT", filetypes=filetypes)
        if path:
            try:
                from utils.subtitles import parse_srt
                subtitles = parse_srt(path)
                self.set_subtitles(subtitles)
                self.current_srt_path = path
                self._file_label.config(text=os.path.basename(path))
                app.trigger_auto_save()
                app.update_preview()
            except Exception as e:
                print(f"Error cargando SRT: {e}")
                self._file_label.config(text="Error cargando")

    def _update_config(self, key: str, value, app):
        """Delega la actualización al comportamiento base del sistema de módulos."""
        super()._update_config(key, value, app)


# -- Helpers ------------------------------------------------------------------

def _spin(parent, var, lo, hi, w, autosave, inc=None, fmt=None):
    kw = {"from_": lo, "to": hi, "textvariable": var, "width": w}
    if inc is not None:
        kw["increment"] = inc
    if fmt is not None:
        kw["format"] = fmt
    sb = tb.Spinbox(parent, **kw)
    for ev in ("<<Increment>>", "<<Decrement>>", "<KeyRelease>"):
        sb.bind(ev, lambda _e: autosave())
    return sb


def _spin_pack(parent, var, lo, hi, w, callback, inc=None, fmt=None):
    sb = _spin(parent, var, lo, hi, w, callback, inc, fmt)
    sb.pack(side=LEFT, padx=2)
    return sb