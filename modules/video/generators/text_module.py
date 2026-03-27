#!/usr/bin/env python3
"""
Módulo Generador de Texto/Títulos.
Categorizado: video/generators
"""
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QComboBox, QLineEdit, QSpinBox
)
from PyQt6.QtCore import Qt

from modules.core.base import Module
from utils.fonts import get_font_path, get_default_font

class TextGeneratorModule(Module):
    module_type = "video"
    module_category = "generators"
    module_tags = ["text", "title", "generator", "overlay"]
    module_version = "1.0.0"

    def __init__(self):
        super().__init__(nombre="Generador de Texto", descripcion="Texto personalizable sobre el video")
        self._config = {
            "text": "Soundvi", "font_size": 48, "color": "#FFFFFF",
            "pos_x": 50, "pos_y": 50, "opacity": 1.0,
            "shadow": True, "animation": "none",
        }

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado or not self._config["text"]: return frame
        try:
            h, w = frame.shape[:2]
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert('RGBA')
            txt = Image.new('RGBA', img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(txt)
            font_path = get_font_path(get_default_font())
            try: font = ImageFont.truetype(font_path, self._config["font_size"]) if font_path else ImageFont.load_default()
            except: font = ImageFont.load_default()
            text = self._config["text"]
            anim = self._config["animation"]
            if anim == "typewriter":
                chars = int(tiempo * 10) % (len(text) + 10)
                text = text[:chars]
            bbox = draw.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            px = int(w * self._config["pos_x"] / 100 - tw / 2)
            py = int(h * self._config["pos_y"] / 100 - th / 2)
            if anim == "bounce":
                py += int(np.sin(tiempo * 3) * 20)
            hex_c = self._config["color"].lstrip('#')
            r, g, b = int(hex_c[0:2], 16), int(hex_c[2:4], 16), int(hex_c[4:6], 16)
            alpha = int(255 * self._config["opacity"])
            if self._config["shadow"]:
                draw.text((px + 2, py + 2), text, fill=(0, 0, 0, alpha), font=font)
            draw.text((px, py), text, fill=(r, g, b, alpha), font=font)
            combined = Image.alpha_composite(img, txt)
            return cv2.cvtColor(np.array(combined.convert('RGB')), cv2.COLOR_RGB2BGR)
        except: return frame

    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Texto:"))
        text_edit = QLineEdit(self._config["text"])
        text_edit.textChanged.connect(lambda v: self._update_config("text", v, app))
        layout.addWidget(text_edit)

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(QLabel("Tamaño:"))
        sz_spin = QSpinBox()
        sz_spin.setRange(10, 200)
        sz_spin.setValue(self._config["font_size"])
        sz_spin.valueChanged.connect(lambda v: self._update_config("font_size", v, app))
        rl.addWidget(sz_spin)
        layout.addWidget(row)

        # Color picker
        color_picker = self.create_color_picker(content, self._config["color"], app)
        color_picker.on_color_change(lambda hex_val: self._update_config("color", hex_val, app))
        layout.addWidget(color_picker)

        # Animation
        anim_combo = QComboBox()
        anim_combo.addItems(["none", "typewriter", "bounce"])
        anim_combo.setCurrentText(self._config["animation"])
        anim_combo.currentTextChanged.connect(lambda v: self._update_config("animation", v, app))
        layout.addWidget(anim_combo)

        for label_text, key in [("Pos X %", "pos_x"), ("Pos Y %", "pos_y")]:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.addWidget(QLabel(f"{label_text}:"))
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(self._config[key])
            slider.valueChanged.connect(lambda v, k=key: self._update_config(k, v, app))
            rl.addWidget(slider)
            layout.addWidget(row)

        return content
