#!/usr/bin/env python3
"""
Módulo de Títulos y Lower Thirds.
Categorizado: text/titles
"""
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QDoubleSpinBox
)
from PyQt6.QtCore import Qt

from modules.core.base import Module
from utils.fonts import get_font_path, get_default_font

class TitlesModule(Module):
    module_type = "text"
    module_category = "titles"
    module_tags = ["titles", "lower-thirds", "credits", "text"]
    module_version = "1.0.0"

    def __init__(self):
        super().__init__(nombre="Títulos", descripcion="Títulos, créditos y lower thirds")
        self._config = {
            "title": "Título", "subtitle": "Subtítulo", "style": "center",
            "color": "#FFFFFF", "bg_color": "#000000", "bg_opacity": 0.6,
            "font_size": 48, "sub_font_size": 24, "show_time": 0.0, "hide_time": 5.0,
            "animation": "fade", "pos_y": 50,
        }

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado: return frame
        if tiempo < self._config["show_time"] or tiempo > self._config["hide_time"]: return frame
        try:
            h, w = frame.shape[:2]
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert('RGBA')
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            fp = get_font_path(get_default_font())
            try:
                font_main = ImageFont.truetype(fp, self._config["font_size"]) if fp else ImageFont.load_default()
                font_sub = ImageFont.truetype(fp, self._config["sub_font_size"]) if fp else ImageFont.load_default()
            except: font_main = font_sub = ImageFont.load_default()
            hex_c = self._config["color"].lstrip('#')
            cr, cg, cb = int(hex_c[0:2], 16), int(hex_c[2:4], 16), int(hex_c[4:6], 16)
            hex_bg = self._config["bg_color"].lstrip('#')
            br, bg_g, bb = int(hex_bg[0:2], 16), int(hex_bg[2:4], 16), int(hex_bg[4:6], 16)
            bg_a = int(255 * self._config["bg_opacity"])
            anim = self._config["animation"]
            alpha = 255
            show, hide = self._config["show_time"], self._config["hide_time"]
            fade_dur = 0.5
            if anim == "fade":
                if tiempo < show + fade_dur: alpha = int(255 * (tiempo - show) / fade_dur)
                elif tiempo > hide - fade_dur: alpha = int(255 * (hide - tiempo) / fade_dur)
            alpha = max(0, min(255, alpha))
            style = self._config["style"]
            title_bb = draw.textbbox((0, 0), self._config["title"], font=font_main)
            sub_bb = draw.textbbox((0, 0), self._config["subtitle"], font=font_sub)
            tw, th = title_bb[2] - title_bb[0], title_bb[3] - title_bb[1]
            sw, sh = sub_bb[2] - sub_bb[0], sub_bb[3] - sub_bb[1]
            py = int(h * self._config["pos_y"] / 100)
            if style == "center":
                tx, ty = (w - tw) // 2, py - th
                sx, sy = (w - sw) // 2, py + 5
                draw.rectangle([tx - 20, ty - 10, tx + tw + 20, sy + sh + 10], fill=(br, bg_g, bb, bg_a))
            elif style == "lower-third":
                tx, ty = 40, h - 120
                sx, sy = 40, h - 70
                draw.rectangle([30, ty - 10, max(tw, sw) + 60, h - 50], fill=(br, bg_g, bb, bg_a))
            else:
                tx, ty = (w - tw) // 2, py - th
                sx, sy = (w - sw) // 2, py + 5
            draw.text((tx, ty), self._config["title"], fill=(cr, cg, cb, alpha), font=font_main)
            draw.text((sx, sy), self._config["subtitle"], fill=(cr, cg, cb, int(alpha * 0.8)), font=font_sub)
            combined = Image.alpha_composite(img, overlay)
            return cv2.cvtColor(np.array(combined.convert('RGB')), cv2.COLOR_RGB2BGR)
        except: return frame

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Título:"))
        t_edit = QLineEdit(self._config["title"])
        t_edit.textChanged.connect(lambda v: self._update_config("title", v, app))
        layout.addWidget(t_edit)

        layout.addWidget(QLabel("Subtítulo:"))
        s_edit = QLineEdit(self._config["subtitle"])
        s_edit.textChanged.connect(lambda v: self._update_config("subtitle", v, app))
        layout.addWidget(s_edit)

        style_combo = QComboBox()
        style_combo.addItems(["center", "lower-third"])
        style_combo.setCurrentText(self._config["style"])
        style_combo.currentTextChanged.connect(lambda v: self._update_config("style", v, app))
        layout.addWidget(style_combo)

        for label_text, key, lo, hi in [("Mostrar (s)", "show_time", 0.0, 300.0), ("Ocultar (s)", "hide_time", 0.0, 300.0)]:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.addWidget(QLabel(f"{label_text}:"))
            spin = QDoubleSpinBox()
            spin.setRange(lo, hi)
            spin.setSingleStep(0.5)
            spin.setValue(self._config[key])
            spin.valueChanged.connect(lambda v, k=key: self._update_config(k, v, app))
            rl.addWidget(spin)
            layout.addWidget(row)

        return content
