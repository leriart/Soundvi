#!/usr/bin/env python3
"""
Módulo de Subtítulos SRT.
Categorizado: text/subtitles
"""
from __future__ import annotations
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QSpinBox, QCheckBox, QGroupBox, QFileDialog
)
from PyQt6.QtCore import Qt

from modules.core.base import Module
from utils.subtitles import split_text_lines
from utils.fonts import get_font_path, get_default_font, get_system_fonts

class SubtitlesModule(Module):
    module_type = "text"
    module_category = "subtitles"
    module_tags = ["subtitles", "srt", "text", "captions"]
    module_version = "2.0.0"

    def __init__(self, nombre: str = "Subt\u00edtulos", capa: int = 1):
        super().__init__(nombre=nombre, descripcion="Superposici\u00f3n de subt\u00edtulos desde archivos SRT", capa=capa)
        self._subtitles = []
        self.current_srt_path = None
        self._config.update({
            "color": "#FFFFFF", "font_size": 36, "opacity": 1.0,
            "pos_x": 50, "pos_y": 90, "line_break": 40,
            "background_enabled": False, "background_opacity": 0.7,
            "shadow_enabled": False, "shadow_offset": 2,
            "outline_enabled": False, "outline_width": 2, "outline_color": "#000000",
            "animation_enabled": False, "animation_type": "fade", "animation_duration": 0.5,
        })

    def set_subtitles(self, subtitles):
        self._subtitles = subtitles

    @property
    def subtitles(self):
        return self._subtitles

    def render(self, frame, tiempo, **kwargs):
        if not self._habilitado or not self._subtitles: return frame
        texto = None
        for sub in self._subtitles:
            if sub["start"] <= tiempo <= sub["end"]:
                texto = sub["text"]; break
        if not texto: return frame
        try:
            h, w = frame.shape[:2]
            color_rgb = self._hex_to_rgb(self._config.get("color", "#FFFFFF"))
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert('RGBA')
            txt = Image.new('RGBA', img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(txt)
            font = self._load_font(self._config.get("font_size", 36))
            lineas = split_text_lines(texto, self._config.get("line_break", 40))
            bboxes = [draw.textbbox((0, 0), ln, font=font) for ln in lineas]
            max_w = max(bb[2] - bb[0] for bb in bboxes)
            total_h = sum(bb[3] - bb[1] for bb in bboxes)
            cx = (w - max_w) / 2 + (self._config["pos_x"] - 50) * (w / 100)
            cy = int(h * self._config["pos_y"] / 100) - total_h // 2
            alpha = int(255 * self._config.get("opacity", 1.0))
            if self._config.get("background_enabled"):
                bg_a = int(255 * self._config.get("background_opacity", 0.7) * self._config.get("opacity", 1.0))
                draw.rectangle([cx - 10, cy - 5, cx + max_w + 10, cy + total_h + 5], fill=(0, 0, 0, bg_a))
            y_off = cy
            for i, ln in enumerate(lineas):
                bb = bboxes[i]
                lw, lh = bb[2] - bb[0], bb[3] - bb[1]
                x = cx + (max_w - lw) / 2
                if self._config.get("shadow_enabled"):
                    so = self._config.get("shadow_offset", 2)
                    draw.text((x + so, y_off + so), ln, fill=(0, 0, 0, alpha), font=font)
                if self._config.get("outline_enabled"):
                    oc = self._hex_to_rgb(self._config.get("outline_color", "#000000")) + (alpha,)
                    ow = self._config.get("outline_width", 2)
                    for dx in [-ow, 0, ow]:
                        for dy in [-ow, 0, ow]:
                            if dx or dy: draw.text((x + dx, y_off + dy), ln, fill=oc, font=font)
                draw.text((x, y_off), ln, fill=color_rgb + (alpha,), font=font)
                y_off += lh
            return cv2.cvtColor(np.array(Image.alpha_composite(img, txt).convert('RGB')), cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"[subtitles] Error: {e}")
            return frame

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        # Load SRT button
        file_row = QWidget()
        frl = QHBoxLayout(file_row)
        frl.setContentsMargins(0, 0, 0, 0)
        load_btn = QPushButton("Cargar SRT")
        load_btn.clicked.connect(lambda: self._browse_subtitle(app))
        frl.addWidget(load_btn)
        file_text = os.path.basename(self.current_srt_path) if self.current_srt_path else "Sin archivo"
        self._file_label = QLabel(file_text)
        self._file_label.setStyleSheet("font-size: 8pt;")
        frl.addWidget(self._file_label)
        layout.addWidget(file_row)

        # Color
        color_picker = self.create_color_picker(content, self._config.get("color", "#FFFFFF"), app, "Color:")
        color_picker.on_color_change(lambda hex_val: self._update_config("color", hex_val, app))
        layout.addWidget(color_picker)

        # Size
        sz_row = QWidget()
        szrl = QHBoxLayout(sz_row)
        szrl.setContentsMargins(0, 0, 0, 0)
        szrl.addWidget(QLabel("Tama\u00f1o:"))
        sz_spin = QSpinBox()
        sz_spin.setRange(12, 120)
        sz_spin.setValue(self._config.get("font_size", 36))
        sz_spin.valueChanged.connect(lambda v: self._update_config("font_size", v, app))
        szrl.addWidget(sz_spin)
        layout.addWidget(sz_row)

        # Position
        pos_row = QWidget()
        prl = QHBoxLayout(pos_row)
        prl.setContentsMargins(0, 0, 0, 0)
        prl.addWidget(QLabel("X%:"))
        x_slider = QSlider(Qt.Orientation.Horizontal)
        x_slider.setRange(0, 100)
        x_slider.setValue(self._config["pos_x"])
        x_slider.valueChanged.connect(lambda v: self._update_config("pos_x", v, app))
        prl.addWidget(x_slider)
        prl.addWidget(QLabel("Y%:"))
        y_slider = QSlider(Qt.Orientation.Horizontal)
        y_slider.setRange(0, 100)
        y_slider.setValue(self._config["pos_y"])
        y_slider.valueChanged.connect(lambda v: self._update_config("pos_y", v, app))
        prl.addWidget(y_slider)
        layout.addWidget(pos_row)

        # Effects
        ef_group = QGroupBox("Efectos")
        efl = QVBoxLayout(ef_group)
        for label_text, key in [("Fondo", "background_enabled"), ("Sombra", "shadow_enabled"), ("Contorno", "outline_enabled")]:
            check = QCheckBox(label_text)
            check.setChecked(self._config[key])
            check.toggled.connect(lambda v, k=key: self._update_config(k, v, app))
            efl.addWidget(check)
        layout.addWidget(ef_group)

        return content

    def _load_font(self, size):
        try:
            fp = get_font_path(get_default_font())
            if fp and os.path.exists(fp): return ImageFont.truetype(fp, size)
            return ImageFont.truetype("arial.ttf", size)
        except: return ImageFont.load_default()

    def _hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        if len(hex_color) >= 6: return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return (255, 255, 255)

    def _browse_subtitle(self, app):
        path, _ = QFileDialog.getOpenFileName(None, "Seleccionar SRT", "", "SRT (*.srt);;Todos (*.*)")
        if path:
            try:
                from utils.subtitles import parse_srt
                self.set_subtitles(parse_srt(path))
                self.current_srt_path = path
                self._file_label.setText(os.path.basename(path))
                app.trigger_auto_save(); app.update_preview()
            except Exception as e:
                print(f"Error SRT: {e}")
