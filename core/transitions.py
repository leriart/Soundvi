#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Transiciones entre clips.

Implementa transiciones visuales profesionales entre dos clips contiguos:
- Fade (fundido a negro / fundido cruzado)
- Dissolve (disolucion)
- Wipe (barrido en varias direcciones)
- Slide (deslizamiento)
- Zoom (acercamiento/alejamiento)
- Push (empujar)

Cada transicion se aplica en la zona de superposicion entre dos clips.
"""

from __future__ import annotations
import math
import numpy as np
import cv2
from typing import Optional, Dict, Any, Tuple


class TransitionType:
    """Tipos de transicion disponibles."""
    FADE = "fade"
    CROSSFADE = "crossfade"
    DISSOLVE = "dissolve"
    WIPE_LEFT = "wipe_left"
    WIPE_RIGHT = "wipe_right"
    WIPE_UP = "wipe_up"
    WIPE_DOWN = "wipe_down"
    WIPE_DIAGONAL = "wipe_diagonal"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    PUSH_LEFT = "push_left"
    PUSH_RIGHT = "push_right"
    IRIS_OPEN = "iris_open"
    IRIS_CLOSE = "iris_close"
    BLUR_TRANSITION = "blur_transition"
    
    ALL_TYPES = [
        FADE, CROSSFADE, DISSOLVE,
        WIPE_LEFT, WIPE_RIGHT, WIPE_UP, WIPE_DOWN, WIPE_DIAGONAL,
        SLIDE_LEFT, SLIDE_RIGHT, SLIDE_UP, SLIDE_DOWN,
        ZOOM_IN, ZOOM_OUT,
        PUSH_LEFT, PUSH_RIGHT,
        IRIS_OPEN, IRIS_CLOSE,
        BLUR_TRANSITION,
    ]
    
    # Nombres legibles para la UI
    DISPLAY_NAMES = {
        FADE: "Fundido a negro",
        CROSSFADE: "Fundido cruzado",
        DISSOLVE: "Disolucion",
        WIPE_LEFT: "Barrido izquierda",
        WIPE_RIGHT: "Barrido derecha",
        WIPE_UP: "Barrido arriba",
        WIPE_DOWN: "Barrido abajo",
        WIPE_DIAGONAL: "Barrido diagonal",
        SLIDE_LEFT: "Deslizar izquierda",
        SLIDE_RIGHT: "Deslizar derecha",
        SLIDE_UP: "Deslizar arriba",
        SLIDE_DOWN: "Deslizar abajo",
        ZOOM_IN: "Zoom acercar",
        ZOOM_OUT: "Zoom alejar",
        PUSH_LEFT: "Empujar izquierda",
        PUSH_RIGHT: "Empujar derecha",
        IRIS_OPEN: "Iris abrir",
        IRIS_CLOSE: "Iris cerrar",
        BLUR_TRANSITION: "Transicion desenfoque",
    }


class Transition:
    """
    Representa una transicion entre dos clips.
    
    Atributos:
        transition_type: Tipo de transicion
        duration: Duracion de la transicion en segundos
        easing: Funcion de suavizado ("linear", "ease_in", "ease_out", "ease_in_out")
        color: Color para transiciones que lo usan (fade a color)
        softness: Suavidad del borde de la transicion (0.0 - 1.0)
    """

    def __init__(self, transition_type: str = TransitionType.CROSSFADE,
                 duration: float = 1.0, easing: str = "linear"):
        self.transition_type: str = transition_type
        self.duration: float = max(0.1, duration)
        self.easing: str = easing
        self.color: Tuple[int, int, int] = (0, 0, 0)  # Color para fade
        self.softness: float = 0.1  # Suavidad del borde

    def apply(self, frame_out: np.ndarray, frame_in: np.ndarray, 
              progress: float) -> np.ndarray:
        """
        Aplica la transicion entre dos frames.
        
        Args:
            frame_out: Frame del clip que sale (clip A)
            frame_in: Frame del clip que entra (clip B)
            progress: Progreso de la transicion (0.0 = clip A, 1.0 = clip B)
            
        Returns:
            Frame con la transicion aplicada
        """
        progress = max(0.0, min(1.0, progress))
        
        # Aplicar easing al progreso
        progress = self._apply_easing(progress)
        
        h, w = frame_out.shape[:2]
        
        # Asegurar que ambos frames tengan el mismo tamano
        if frame_in.shape[:2] != (h, w):
            frame_in = cv2.resize(frame_in, (w, h))
        
        # Seleccionar metodo de transicion
        method = self._get_transition_method()
        return method(frame_out, frame_in, progress, w, h)

    def _apply_easing(self, t: float) -> float:
        """Aplica funcion de suavizado al progreso."""
        if self.easing == "ease_in":
            return t * t
        elif self.easing == "ease_out":
            return 1.0 - (1.0 - t) ** 2
        elif self.easing == "ease_in_out":
            if t < 0.5:
                return 2.0 * t * t
            else:
                return 1.0 - (-2.0 * t + 2.0) ** 2 / 2.0
        return t  # Lineal

    def _get_transition_method(self):
        """Retorna el metodo de transicion correspondiente al tipo."""
        methods = {
            TransitionType.FADE: self._fade,
            TransitionType.CROSSFADE: self._crossfade,
            TransitionType.DISSOLVE: self._dissolve,
            TransitionType.WIPE_LEFT: self._wipe_left,
            TransitionType.WIPE_RIGHT: self._wipe_right,
            TransitionType.WIPE_UP: self._wipe_up,
            TransitionType.WIPE_DOWN: self._wipe_down,
            TransitionType.WIPE_DIAGONAL: self._wipe_diagonal,
            TransitionType.SLIDE_LEFT: self._slide_left,
            TransitionType.SLIDE_RIGHT: self._slide_right,
            TransitionType.SLIDE_UP: self._slide_up,
            TransitionType.SLIDE_DOWN: self._slide_down,
            TransitionType.ZOOM_IN: self._zoom_in,
            TransitionType.ZOOM_OUT: self._zoom_out,
            TransitionType.PUSH_LEFT: self._push_left,
            TransitionType.PUSH_RIGHT: self._push_right,
            TransitionType.IRIS_OPEN: self._iris_open,
            TransitionType.IRIS_CLOSE: self._iris_close,
            TransitionType.BLUR_TRANSITION: self._blur_transition,
        }
        return methods.get(self.transition_type, self._crossfade)

    # -- Implementaciones de transiciones --

    def _fade(self, out_f, in_f, p, w, h):
        """Fundido a color (negro por defecto)."""
        color_frame = np.full_like(out_f, self.color[::-1])  # BGR
        if p < 0.5:
            # Primera mitad: out -> color
            t = p * 2.0
            return cv2.addWeighted(out_f, 1.0 - t, color_frame, t, 0)
        else:
            # Segunda mitad: color -> in
            t = (p - 0.5) * 2.0
            return cv2.addWeighted(color_frame, 1.0 - t, in_f, t, 0)

    def _crossfade(self, out_f, in_f, p, w, h):
        """Fundido cruzado directo entre dos clips."""
        return cv2.addWeighted(out_f, 1.0 - p, in_f, p, 0)

    def _dissolve(self, out_f, in_f, p, w, h):
        """Disolucion con ruido (mas organica que crossfade)."""
        # Generar mascara de ruido
        noise = np.random.random((h, w)).astype(np.float32)
        mask = (noise < p).astype(np.float32)
        
        # Suavizar bordes
        if self.softness > 0:
            kernel_size = max(3, int(self.softness * 50) | 1)
            mask = cv2.GaussianBlur(mask, (kernel_size, kernel_size), 0)
        
        mask_3ch = np.stack([mask] * 3, axis=-1)
        result = out_f.astype(np.float32) * (1.0 - mask_3ch) + in_f.astype(np.float32) * mask_3ch
        return result.astype(np.uint8)

    def _wipe_left(self, out_f, in_f, p, w, h):
        """Barrido de derecha a izquierda."""
        edge = int(w * p)
        soft_px = max(1, int(self.softness * w * 0.1))
        mask = np.zeros((h, w), dtype=np.float32)
        mask[:, :edge] = 1.0
        if soft_px > 0 and edge > 0:
            start = max(0, edge - soft_px)
            end = min(w, edge + soft_px)
            gradient = np.linspace(0, 1, end - start)
            mask[:, start:end] = gradient
        mask_3ch = np.stack([mask] * 3, axis=-1)
        result = out_f.astype(np.float32) * (1.0 - mask_3ch) + in_f.astype(np.float32) * mask_3ch
        return result.astype(np.uint8)

    def _wipe_right(self, out_f, in_f, p, w, h):
        """Barrido de izquierda a derecha."""
        return self._wipe_left(out_f, in_f, 1.0 - p, w, h)

    def _wipe_up(self, out_f, in_f, p, w, h):
        """Barrido de abajo hacia arriba."""
        edge = int(h * p)
        mask = np.zeros((h, w), dtype=np.float32)
        mask[:edge, :] = 1.0
        mask_3ch = np.stack([mask] * 3, axis=-1)
        result = out_f.astype(np.float32) * (1.0 - mask_3ch) + in_f.astype(np.float32) * mask_3ch
        return result.astype(np.uint8)

    def _wipe_down(self, out_f, in_f, p, w, h):
        """Barrido de arriba hacia abajo."""
        return self._wipe_up(out_f, in_f, 1.0 - p, w, h)

    def _wipe_diagonal(self, out_f, in_f, p, w, h):
        """Barrido diagonal."""
        y_coords, x_coords = np.mgrid[0:h, 0:w]
        diagonal = (x_coords / w + y_coords / h) / 2.0
        mask = (diagonal < p).astype(np.float32)
        if self.softness > 0:
            kernel = max(3, int(self.softness * 30) | 1)
            mask = cv2.GaussianBlur(mask, (kernel, kernel), 0)
        mask_3ch = np.stack([mask] * 3, axis=-1)
        result = out_f.astype(np.float32) * (1.0 - mask_3ch) + in_f.astype(np.float32) * mask_3ch
        return result.astype(np.uint8)

    def _slide_left(self, out_f, in_f, p, w, h):
        """El clip B se desliza desde la derecha."""
        offset = int(w * (1.0 - p))
        result = out_f.copy()
        if offset < w:
            result[:, :w - offset] = in_f[:, offset:]
        return result

    def _slide_right(self, out_f, in_f, p, w, h):
        """El clip B se desliza desde la izquierda."""
        offset = int(w * (1.0 - p))
        result = out_f.copy()
        if offset < w:
            result[:, offset:] = in_f[:, :w - offset]
        return result

    def _slide_up(self, out_f, in_f, p, w, h):
        """El clip B se desliza desde abajo."""
        offset = int(h * (1.0 - p))
        result = out_f.copy()
        if offset < h:
            result[:h - offset, :] = in_f[offset:, :]
        return result

    def _slide_down(self, out_f, in_f, p, w, h):
        """El clip B se desliza desde arriba."""
        offset = int(h * (1.0 - p))
        result = out_f.copy()
        if offset < h:
            result[offset:, :] = in_f[:h - offset, :]
        return result

    def _zoom_in(self, out_f, in_f, p, w, h):
        """Zoom acercandose durante la transicion."""
        scale = 1.0 + p * 0.5
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, 0, scale)
        zoomed_out = cv2.warpAffine(out_f, M, (w, h))
        return cv2.addWeighted(zoomed_out, 1.0 - p, in_f, p, 0)

    def _zoom_out(self, out_f, in_f, p, w, h):
        """Zoom alejandose durante la transicion."""
        scale = 1.5 - p * 0.5
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, 0, scale)
        zoomed_in = cv2.warpAffine(in_f, M, (w, h))
        return cv2.addWeighted(out_f, 1.0 - p, zoomed_in, p, 0)

    def _push_left(self, out_f, in_f, p, w, h):
        """Clip A es empujado por clip B desde la derecha."""
        offset = int(w * p)
        result = np.zeros_like(out_f)
        # Clip A se mueve a la izquierda
        if offset < w:
            result[:, :w - offset] = out_f[:, offset:]
        # Clip B entra desde la derecha
        if offset > 0:
            result[:, w - offset:] = in_f[:, :offset]
        return result

    def _push_right(self, out_f, in_f, p, w, h):
        """Clip A es empujado por clip B desde la izquierda."""
        offset = int(w * p)
        result = np.zeros_like(out_f)
        if offset < w:
            result[:, offset:] = out_f[:, :w - offset]
        if offset > 0:
            result[:, :offset] = in_f[:, w - offset:]
        return result

    def _iris_open(self, out_f, in_f, p, w, h):
        """Transicion tipo iris que se abre desde el centro."""
        mask = np.zeros((h, w), dtype=np.float32)
        center = (w // 2, h // 2)
        max_radius = int(math.sqrt(w * w + h * h) / 2)
        radius = int(max_radius * p)
        cv2.circle(mask, center, radius, 1.0, -1)
        if self.softness > 0:
            kernel = max(3, int(self.softness * 40) | 1)
            mask = cv2.GaussianBlur(mask, (kernel, kernel), 0)
        mask_3ch = np.stack([mask] * 3, axis=-1)
        result = out_f.astype(np.float32) * (1.0 - mask_3ch) + in_f.astype(np.float32) * mask_3ch
        return result.astype(np.uint8)

    def _iris_close(self, out_f, in_f, p, w, h):
        """Transicion tipo iris que se cierra hacia el centro."""
        return self._iris_open(out_f, in_f, 1.0 - p, w, h)

    def _blur_transition(self, out_f, in_f, p, w, h):
        """Transicion con desenfoque intermedio."""
        blur_amount = int(50 * (1.0 - abs(2.0 * p - 1.0)))
        blur_amount = max(1, blur_amount) | 1
        if p < 0.5:
            blurred = cv2.GaussianBlur(out_f, (blur_amount, blur_amount), 0)
            t = p * 2.0
            return cv2.addWeighted(out_f, 1.0 - t, blurred, t, 0)
        else:
            blurred = cv2.GaussianBlur(in_f, (blur_amount, blur_amount), 0)
            t = (p - 0.5) * 2.0
            return cv2.addWeighted(blurred, 1.0 - t, in_f, t, 0)

    # -- Serializacion --

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_type": self.transition_type,
            "duration": self.duration,
            "easing": self.easing,
            "color": list(self.color),
            "softness": self.softness,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transition':
        t = cls(
            transition_type=data.get("transition_type", TransitionType.CROSSFADE),
            duration=data.get("duration", 1.0),
            easing=data.get("easing", "linear"),
        )
        t.color = tuple(data.get("color", [0, 0, 0]))
        t.softness = data.get("softness", 0.1)
        return t

    def __repr__(self):
        name = TransitionType.DISPLAY_NAMES.get(self.transition_type, self.transition_type)
        return f"Transition('{name}', dur={self.duration:.1f}s)"
