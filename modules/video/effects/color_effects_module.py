#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Efectos de Color Avanzados -- LUTs, curvas de color, correccion de color.

Modulo de efectos de color profesionales que incluye:
- Aplicacion de LUTs (Look-Up Tables) predefinidas
- Curvas de color por canal (R, G, B)
- Correccion de balance de blancos
- Mezclador de canales
- Efectos de tonificacion (split toning)
- Vineteo configurable
"""

from __future__ import annotations

import numpy as np
import cv2

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QComboBox, QGroupBox
)
from PyQt6.QtCore import Qt

from modules.core.base import Module


class ColorEffectsModule(Module):
    """
    Modulo de efectos de color avanzados con LUTs, curvas y correccion.
    """

    module_type = "video"
    module_category = "effects"
    module_tags = ["color", "lut", "curves", "correction", "grading", "advanced"]
    module_version = "1.0"
    module_author = "Soundvi"

    PRESET_LUTS = {
        "Normal": None,
        "Cinematico": {"shadows": (10, 15, 30), "highlights": (255, 240, 220), "saturation": 0.85},
        "Vintage": {"shadows": (30, 20, 10), "highlights": (240, 230, 200), "saturation": 0.7},
        "Frio": {"shadows": (0, 10, 30), "highlights": (220, 230, 255), "saturation": 0.9},
        "Calido": {"shadows": (20, 10, 0), "highlights": (255, 240, 220), "saturation": 1.1},
        "Desaturado": {"shadows": (0, 0, 0), "highlights": (255, 255, 255), "saturation": 0.3},
        "Neon": {"shadows": (20, 0, 30), "highlights": (200, 255, 250), "saturation": 1.5},
        "Sepia": {"shadows": (20, 10, 0), "highlights": (230, 200, 160), "saturation": 0.4},
        "Noir": {"shadows": (0, 0, 0), "highlights": (200, 200, 200), "saturation": 0.0},
        "Teal & Orange": {"shadows": (0, 40, 50), "highlights": (255, 180, 100), "saturation": 1.2},
        "Cyberpunk": {"shadows": (40, 0, 60), "highlights": (0, 255, 200), "saturation": 1.4},
        "Pastel": {"shadows": (30, 30, 40), "highlights": (255, 240, 250), "saturation": 0.6},
    }

    def __init__(self):
        super().__init__(nombre="Efectos de Color", descripcion="LUTs, curvas y correccion de color avanzada", capa=80)
        
        self.config = {
            "lut_preset": "Normal",
            "lut_intensity": 1.0,
            "curve_r_shadows": 0, "curve_r_midtones": 128, "curve_r_highlights": 255,
            "curve_g_shadows": 0, "curve_g_midtones": 128, "curve_g_highlights": 255,
            "curve_b_shadows": 0, "curve_b_midtones": 128, "curve_b_highlights": 255,
            "white_balance": 0, "tint": 0, "vibrance": 0,
            "channel_r_to_r": 100, "channel_g_to_g": 100, "channel_b_to_b": 100,
            "shadow_hue": 0, "shadow_saturation": 0,
            "highlight_hue": 0, "highlight_saturation": 0,
            "vignette_amount": 0, "vignette_size": 70,
            "opacity": 1.0,
        }
        self._cached_lut: np.ndarray | None = None
        self._cached_lut_key: str = ""
        self._vignette_mask: np.ndarray | None = None
        self._vignette_size_cache: tuple = (0, 0, 0)

    def render(self, frame: np.ndarray, tiempo: float, **kwargs) -> np.ndarray:
        if not self.habilitado:
            return frame
        original = frame.copy() if self.config["opacity"] < 1.0 else None
        result = frame.copy()
        result = self._apply_lut_preset(result)
        result = self._apply_color_curves(result)
        result = self._apply_white_balance(result)
        result = self._apply_vibrance(result)
        result = self._apply_channel_mixer(result)
        result = self._apply_split_toning(result)
        result = self._apply_vignette(result)
        opacity = self.config.get("opacity", 1.0)
        if opacity < 1.0 and original is not None:
            result = cv2.addWeighted(result, opacity, original, 1.0 - opacity, 0)
        return result

    def _apply_lut_preset(self, frame):
        preset_name = self.config.get("lut_preset", "Normal")
        intensity = self.config.get("lut_intensity", 1.0)
        if preset_name == "Normal" or preset_name not in self.PRESET_LUTS:
            return frame
        preset = self.PRESET_LUTS[preset_name]
        if preset is None: return frame
        shadows = np.array(preset["shadows"], dtype=np.float32)
        highlights = np.array(preset["highlights"], dtype=np.float32)
        saturation = preset.get("saturation", 1.0)
        frame_float = frame.astype(np.float32) / 255.0
        luminance = np.mean(frame_float, axis=2, keepdims=True)
        shadow_influence = (1.0 - luminance) ** 2
        highlight_influence = luminance ** 2
        result = frame_float.copy()
        shadow_color = shadows / 255.0
        highlight_color = highlights / 255.0
        for c in range(3):
            result[:, :, c] = (result[:, :, c] * (1.0 - shadow_influence[:, :, 0] * 0.3) + shadow_color[c] * shadow_influence[:, :, 0] * 0.3)
            result[:, :, c] = (result[:, :, c] * (1.0 - highlight_influence[:, :, 0] * 0.3) + highlight_color[c] * highlight_influence[:, :, 0] * 0.3)
        if saturation != 1.0:
            hsv = cv2.cvtColor((result * 255).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation, 0, 255)
            result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32) / 255.0
        result = frame_float * (1.0 - intensity) + result * intensity
        return np.clip(result * 255, 0, 255).astype(np.uint8)

    def _apply_color_curves(self, frame):
        default_vals = [0, 128, 255]
        r_vals = [self.config.get(f"curve_r_{p}", d) for p, d in zip(["shadows", "midtones", "highlights"], default_vals)]
        g_vals = [self.config.get(f"curve_g_{p}", d) for p, d in zip(["shadows", "midtones", "highlights"], default_vals)]
        b_vals = [self.config.get(f"curve_b_{p}", d) for p, d in zip(["shadows", "midtones", "highlights"], default_vals)]
        if r_vals == default_vals and g_vals == default_vals and b_vals == default_vals:
            return frame
        x_points = [0, 128, 255]
        for channel, vals in enumerate([b_vals, g_vals, r_vals]):
            lut = np.interp(np.arange(256), x_points, vals).astype(np.uint8)
            frame[:, :, channel] = cv2.LUT(frame[:, :, channel], lut)
        return frame

    def _apply_white_balance(self, frame):
        wb = self.config.get("white_balance", 0)
        tint = self.config.get("tint", 0)
        if wb == 0 and tint == 0: return frame
        result = frame.astype(np.float32)
        if wb != 0:
            factor = wb / 100.0 * 30
            result[:, :, 0] -= factor
            result[:, :, 2] += factor
        if tint != 0:
            factor = tint / 100.0 * 20
            result[:, :, 1] -= factor
        return np.clip(result, 0, 255).astype(np.uint8)

    def _apply_vibrance(self, frame):
        vibrance = self.config.get("vibrance", 0)
        if vibrance == 0: return frame
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
        sat = hsv[:, :, 1] / 255.0
        factor = 1.0 + (vibrance / 100.0) * (1.0 - sat)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * factor, 0, 255)
        return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    def _apply_channel_mixer(self, frame):
        r_to_r = self.config.get("channel_r_to_r", 100) / 100.0
        g_to_g = self.config.get("channel_g_to_g", 100) / 100.0
        b_to_b = self.config.get("channel_b_to_b", 100) / 100.0
        if r_to_r == 1.0 and g_to_g == 1.0 and b_to_b == 1.0: return frame
        result = frame.astype(np.float32)
        result[:, :, 2] *= r_to_r
        result[:, :, 1] *= g_to_g
        result[:, :, 0] *= b_to_b
        return np.clip(result, 0, 255).astype(np.uint8)

    def _apply_split_toning(self, frame):
        sh_sat = self.config.get("shadow_saturation", 0)
        hl_sat = self.config.get("highlight_saturation", 0)
        if sh_sat == 0 and hl_sat == 0: return frame
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
        luminance = hsv[:, :, 2] / 255.0
        result = frame.astype(np.float32)
        if sh_sat > 0:
            sh_hue = self.config.get("shadow_hue", 0)
            shadow_mask = ((1.0 - luminance) ** 2 * sh_sat / 100.0)[:, :, np.newaxis]
            shadow_color = self._hue_to_bgr(sh_hue)
            result = result * (1.0 - shadow_mask * 0.5) + shadow_color * shadow_mask * 0.5 * 255
        if hl_sat > 0:
            hl_hue = self.config.get("highlight_hue", 0)
            highlight_mask = (luminance ** 2 * hl_sat / 100.0)[:, :, np.newaxis]
            highlight_color = self._hue_to_bgr(hl_hue)
            result = result * (1.0 - highlight_mask * 0.5) + highlight_color * highlight_mask * 0.5 * 255
        return np.clip(result, 0, 255).astype(np.uint8)

    def _apply_vignette(self, frame):
        amount = self.config.get("vignette_amount", 0)
        if amount == 0: return frame
        h, w = frame.shape[:2]
        size = self.config.get("vignette_size", 70)
        cache_key = (h, w, size)
        if self._vignette_mask is None or self._vignette_size_cache != cache_key:
            Y, X = np.mgrid[0:h, 0:w].astype(np.float32)
            cx, cy = w / 2, h / 2
            dist = np.sqrt((X - cx) ** 2 / (cx ** 2) + (Y - cy) ** 2 / (cy ** 2))
            radius = size / 100.0
            mask = 1.0 - np.clip((dist - radius) / (1.0 - radius + 0.01), 0, 1)
            mask = mask ** 1.5
            self._vignette_mask = mask
            self._vignette_size_cache = cache_key
        intensity = amount / 100.0
        mask = 1.0 - (1.0 - self._vignette_mask) * intensity
        mask_3ch = np.stack([mask] * 3, axis=-1).astype(np.float32)
        result = frame.astype(np.float32) * mask_3ch
        return result.astype(np.uint8)

    @staticmethod
    def _hue_to_bgr(hue: int) -> np.ndarray:
        h = (hue % 360) / 2
        hsv = np.uint8([[[int(h), 255, 255]]])
        bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        return bgr[0, 0].astype(np.float32) / 255.0

    def get_config_widgets(self, parent, app):
        """Crea los widgets de configuracion."""
        content = QWidget(parent)
        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # -- LUT Preset --
        lut_group = QGroupBox("LUT / Preset")
        lut_layout = QVBoxLayout(lut_group)
        preset_combo = QComboBox()
        preset_combo.addItems(list(self.PRESET_LUTS.keys()))
        preset_combo.setCurrentText(self.config.get("lut_preset", "Normal"))
        preset_combo.currentTextChanged.connect(lambda v: self._update_config("lut_preset", v, app))
        lut_layout.addWidget(preset_combo)

        int_row = QWidget()
        irl = QHBoxLayout(int_row)
        irl.setContentsMargins(0, 0, 0, 0)
        irl.addWidget(QLabel("Intensidad:"))
        int_slider = QSlider(Qt.Orientation.Horizontal)
        int_slider.setRange(0, 100)
        int_slider.setValue(int(self.config.get("lut_intensity", 1.0) * 100))
        int_slider.valueChanged.connect(lambda v: self._update_config("lut_intensity", v / 100.0, app))
        irl.addWidget(int_slider)
        lut_layout.addWidget(int_row)
        main_layout.addWidget(lut_group)

        # -- Balance de blancos --
        wb_group = QGroupBox("Balance de Blancos")
        wb_layout = QVBoxLayout(wb_group)
        for label_text, key, lo, hi in [
            ("Temperatura:", "white_balance", -100, 100),
            ("Tint:", "tint", -100, 100),
            ("Vibrance:", "vibrance", -100, 100),
        ]:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(label_text)
            lbl.setFixedWidth(80)
            rl.addWidget(lbl)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(lo, hi)
            slider.setValue(self.config.get(key, 0))
            slider.valueChanged.connect(lambda v, k=key: self._update_config(k, v, app))
            rl.addWidget(slider)
            wb_layout.addWidget(row)
        main_layout.addWidget(wb_group)

        # -- Mezclador de canales --
        mix_group = QGroupBox("Mezclador de Canales")
        mix_layout = QVBoxLayout(mix_group)
        for label_text, key in [("Rojo:", "channel_r_to_r"), ("Verde:", "channel_g_to_g"), ("Azul:", "channel_b_to_b")]:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(label_text)
            lbl.setFixedWidth(50)
            rl.addWidget(lbl)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 200)
            slider.setValue(self.config.get(key, 100))
            slider.valueChanged.connect(lambda v, k=key: self._update_config(k, v, app))
            rl.addWidget(slider)
            mix_layout.addWidget(row)
        main_layout.addWidget(mix_group)

        # -- Vineteo --
        vig_group = QGroupBox("Vineteo")
        vig_layout = QVBoxLayout(vig_group)
        for label_text, key, lo, hi, default in [
            ("Cantidad:", "vignette_amount", 0, 100, 0),
            ("Tama\u00f1o:", "vignette_size", 10, 100, 70),
        ]:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(label_text)
            lbl.setFixedWidth(70)
            rl.addWidget(lbl)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(lo, hi)
            slider.setValue(self.config.get(key, default))
            slider.valueChanged.connect(lambda v, k=key: self._update_config(k, v, app))
            rl.addWidget(slider)
            vig_layout.addWidget(row)
        main_layout.addWidget(vig_group)

        # -- Opacidad --
        op_row = QWidget()
        orl = QHBoxLayout(op_row)
        orl.setContentsMargins(0, 0, 0, 0)
        orl.addWidget(QLabel("Opacidad:"))
        op_slider = QSlider(Qt.Orientation.Horizontal)
        op_slider.setRange(0, 100)
        op_slider.setValue(int(self.config.get("opacity", 1.0) * 100))
        op_slider.valueChanged.connect(lambda v: self._update_config("opacity", v / 100.0, app))
        orl.addWidget(op_slider)
        main_layout.addWidget(op_row)

        return content
