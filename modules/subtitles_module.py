#!/usr/bin/env python3
from __future__ import annotations
from utils.fonts import get_default_font
"""
Modulo de Subtitulos -- renderiza subtitulos SRT sobre el video.

Con selector de color mejorado, soporte para multiples instancias,
interfaz unificada con el sistema de modulos.
"""

import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QComboBox, QSpinBox, QCheckBox, QGroupBox,
    QFileDialog
)
from PyQt6.QtCore import Qt

from modules.base import Module
from utils.subtitles import split_text_lines
from utils.fonts import get_font_path, get_default_font, get_system_fonts


class SubtitlesModule(Module):
    """
    Modulo de subtitulos SRT mejorado.
    Renderiza texto de subtitulos sobre el frame de video.
    """

    def __init__(self, nombre: str = "Subt\u00edtulos", capa: int = 1):
        super().__init__(
            nombre=nombre,
            descripcion="Superposici\u00f3n de subt\u00edtulos desde archivos SRT",
            capa=capa
        )
        self._subtitles: list[dict] = []
        self._font_path: str = ""
        self.current_srt_path = None

        self._config.update({
            "color": "#FFFFFF",
            "font_size": 36,
            "opacity": 1.0,
            "pos_x": 50,
            "pos_y": 90,
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
            "animation_type": "fade",
            "animation_duration": 0.5,
        })

    def set_subtitles(self, subtitles: list[dict]):
        self._subtitles = subtitles

    @property
    def subtitles(self) -> list[dict]:
        return self._subtitles

    def render(self, frame: np.ndarray, tiempo: float, **kwargs) -> np.ndarray:
        if not self._habilitado or not self._subtitles:
            return frame
        texto = None
        for sub in self._subtitles:
            if sub["start"] <= tiempo <= sub["end"]:
                texto = sub["text"]
                break
        if not texto:
            return frame

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
        color_rgb = self._hex_to_rgb(self._config.get("color", "#FFFFFF"))

        try:
            img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert('RGBA')
            txt_layer = Image.new('RGBA', img_pil.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)
            font = self._load_font(font_size)
            lineas = split_text_lines(texto, line_break) if line_break > 0 else [texto]
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
            cx = (width_px - max_width) / 2 + (pos_x_pct - 50) * (width_px / 100)
            cy = int(height_px * pos_y_pct / 100) - total_height // 2
            if bg_enabled:
                bg_rect = [cx - bg_padding, cy - bg_padding, cx + max_width + bg_padding, cy + total_height + bg_padding]
                bg_color = (0, 0, 0, int(255 * bg_opacity * opacity))
                draw.rectangle(bg_rect, fill=bg_color)
            y_offset = cy
            text_alpha = int(255 * opacity)
            for i, ln in enumerate(lineas):
                bbox = text_bboxes[i]
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                x = cx + (max_width - w) / 2
                if shadow_enabled:
                    shadow_color = (0, 0, 0, text_alpha)
                    draw.text((x + shadow_offset, y_offset + shadow_offset), ln, fill=shadow_color, font=font)
                if outline_enabled:
                    outline_color = self._hex_to_rgb(self._config.get("outline_color", "#000000"))
                    outline_color_rgba = outline_color + (text_alpha,)
                    for dx in [-outline_width, 0, outline_width]:
                        for dy in [-outline_width, 0, outline_width]:
                            if dx != 0 or dy != 0:
                                draw.text((x + dx, y_offset + dy), ln, fill=outline_color_rgba, font=font)
                text_color = color_rgb + (text_alpha,)
                draw.text((x, y_offset), ln, fill=text_color, font=font)
                y_offset += h
            combined = Image.alpha_composite(img_pil, txt_layer)
            frame = cv2.cvtColor(np.array(combined.convert("RGB")), cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"[subtitles] Error renderizando: {e}")
            cy = int(height_px * pos_y_pct / 100)
            cv2.putText(frame, texto, (int(width_px * 0.1), cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                        (color_rgb[2], color_rgb[1], color_rgb[0]), 2)
        return frame

    def get_config_widgets(self, parent, app) -> QWidget:
        """Crea widgets de configuracion mejorados para el sidebar."""
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        _as = app

        # Cargar archivo SRT
        file_row = QWidget()
        frl = QHBoxLayout(file_row)
        frl.setContentsMargins(0, 0, 0, 0)
        load_btn = QPushButton("Cargar SRT")
        load_btn.clicked.connect(lambda: self._browse_subtitle(app))
        frl.addWidget(load_btn)
        file_text = "Sin archivo"
        if hasattr(self, 'current_srt_path') and self.current_srt_path:
            file_text = os.path.basename(self.current_srt_path)
        self._file_label = QLabel(file_text)
        self._file_label.setStyleSheet("font-size: 8pt;")
        frl.addWidget(self._file_label)
        layout.addWidget(file_row)

        # Selector de color
        color_picker = self.create_color_picker(content, self._config.get("color", "#FFFFFF"), app, "Color texto:")
        color_picker.on_color_change(lambda hex_val: self._update_config("color", hex_val, _as))
        layout.addWidget(color_picker)

        # Fuente y tama\u00f1o
        font_row = QWidget()
        fntrl = QHBoxLayout(font_row)
        fntrl.setContentsMargins(0, 0, 0, 0)
        fntrl.addWidget(QLabel("Fuente:"))
        fonts = get_system_fonts()
        font_combo = QComboBox()
        font_combo.addItems(fonts)
        font_combo.setCurrentText(get_default_font())
        fntrl.addWidget(font_combo)
        fntrl.addWidget(QLabel("Tama\u00f1o:"))
        size_spin = QSpinBox()
        size_spin.setRange(12, 120)
        size_spin.setValue(self._config.get("font_size", 36))
        size_spin.valueChanged.connect(lambda v: self._update_config("font_size", v, app))
        fntrl.addWidget(size_spin)
        layout.addWidget(font_row)

        # Opacidad
        op_row = QWidget()
        oprl = QHBoxLayout(op_row)
        oprl.setContentsMargins(0, 0, 0, 0)
        oprl.addWidget(QLabel("Opacidad:"))
        op_label = QLabel(f"{self._config['opacity']:.2f}")
        op_slider = QSlider(Qt.Orientation.Horizontal)
        op_slider.setRange(0, 100)
        op_slider.setValue(int(self._config["opacity"] * 100))
        def on_opacity(v):
            val = v / 100.0
            self._update_config("opacity", val, _as)
            op_label.setText(f"{val:.2f}")
        op_slider.valueChanged.connect(on_opacity)
        oprl.addWidget(op_slider)
        oprl.addWidget(op_label)
        layout.addWidget(op_row)

        # Posicion
        pos_row = QWidget()
        posrl = QHBoxLayout(pos_row)
        posrl.setContentsMargins(0, 0, 0, 0)
        posrl.addWidget(QLabel("X (%):"))
        x_slider = QSlider(Qt.Orientation.Horizontal)
        x_slider.setRange(0, 100)
        x_slider.setValue(self._config["pos_x"])
        x_slider.valueChanged.connect(lambda v: self._update_config("pos_x", v, _as))
        posrl.addWidget(x_slider)
        posrl.addWidget(QLabel("Y (%):"))
        y_slider = QSlider(Qt.Orientation.Horizontal)
        y_slider.setRange(0, 100)
        y_slider.setValue(self._config["pos_y"])
        y_slider.valueChanged.connect(lambda v: self._update_config("pos_y", v, _as))
        posrl.addWidget(y_slider)
        layout.addWidget(pos_row)

        # Efectos avanzados
        effects_group = QGroupBox("Efectos Avanzados")
        egl = QVBoxLayout(effects_group)
        for label_text, key in [("Fondo", "background_enabled"), ("Sombra", "shadow_enabled"), ("Contorno", "outline_enabled")]:
            check = QCheckBox(label_text)
            check.setChecked(self._config[key])
            check.toggled.connect(lambda v, k=key: self._update_config(k, v, _as))
            egl.addWidget(check)
        layout.addWidget(effects_group)

        return content

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont:
        try:
            font_path = get_font_path("JetBrainsMono Nerd Font")
            if font_path and os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            return ImageFont.load_default()

    def _hex_to_rgb(self, hex_color: str) -> tuple:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        elif len(hex_color) == 8:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4, 6))
        return (255, 255, 255)

    def _browse_subtitle(self, app):
        path, _ = QFileDialog.getOpenFileName(
            None, "Seleccionar archivo SRT",
            "", "Archivos SRT (*.srt);;Todos los archivos (*.*)"
        )
        if path:
            try:
                from utils.subtitles import parse_srt
                subtitles = parse_srt(path)
                self.set_subtitles(subtitles)
                self.current_srt_path = path
                self._file_label.setText(os.path.basename(path))
                app.trigger_auto_save()
                app.update_preview()
            except Exception as e:
                print(f"Error cargando SRT: {e}")
                self._file_label.setText("Error cargando")

    def _update_config(self, key: str, value, app):
        super()._update_config(key, value, app)
