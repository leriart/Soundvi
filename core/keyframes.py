#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Keyframes con Interpolacion.

Permite animar cualquier parametro numerico a lo largo del tiempo
usando keyframes con diferentes modos de interpolacion:
- Lineal
- Ease-In (aceleracion gradual)
- Ease-Out (desaceleracion gradual)
- Ease-In-Out (aceleracion + desaceleracion)
- Bezier cubico personalizado
- Constante (sin interpolacion, escalonado)
"""

from __future__ import annotations
import math
from typing import Optional, Dict, Any, List, Tuple


class InterpolationMode:
    """Modos de interpolacion disponibles."""
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    BEZIER = "bezier"
    CONSTANT = "constant"
    
    ALL_MODES = [LINEAR, EASE_IN, EASE_OUT, EASE_IN_OUT, BEZIER, CONSTANT]


def lerp(a: float, b: float, t: float) -> float:
    """Interpolacion lineal entre a y b con factor t (0-1)."""
    return a + (b - a) * t


def ease_in(t: float, power: float = 2.0) -> float:
    """Curva de aceleracion (potencia configurable)."""
    return t ** power


def ease_out(t: float, power: float = 2.0) -> float:
    """Curva de desaceleracion (potencia configurable)."""
    return 1.0 - (1.0 - t) ** power


def ease_in_out(t: float, power: float = 2.0) -> float:
    """Curva de aceleracion + desaceleracion."""
    if t < 0.5:
        return 0.5 * (2.0 * t) ** power
    else:
        return 1.0 - 0.5 * (2.0 * (1.0 - t)) ** power


def cubic_bezier(t: float, p1x: float, p1y: float, p2x: float, p2y: float) -> float:
    """
    Interpolacion con curva de Bezier cubica.
    
    p1x, p1y: Primer punto de control
    p2x, p2y: Segundo punto de control
    
    Los puntos de inicio (0,0) y fin (1,1) son implicitos.
    """
    # Resolver t para x usando Newton-Raphson
    cx = 3.0 * p1x
    bx = 3.0 * (p2x - p1x) - cx
    ax = 1.0 - cx - bx

    cy = 3.0 * p1y
    by = 3.0 * (p2y - p1y) - cy
    ay = 1.0 - cy - by

    # Buscar el valor de t que corresponde a la posicion x
    guess_t = t
    for _ in range(8):
        current_x = ((ax * guess_t + bx) * guess_t + cx) * guess_t
        dx = (3.0 * ax * guess_t + 2.0 * bx) * guess_t + cx
        if abs(dx) < 1e-7:
            break
        guess_t -= (current_x - t) / dx

    guess_t = max(0.0, min(1.0, guess_t))
    return ((ay * guess_t + by) * guess_t + cy) * guess_t


def interpolate(t: float, mode: str, bezier_points: Tuple[float, ...] = (0.25, 0.1, 0.25, 1.0)) -> float:
    """
    Aplica la funcion de interpolacion seleccionada.
    
    Args:
        t: Factor de interpolacion (0.0 a 1.0)
        mode: Modo de interpolacion
        bezier_points: Puntos de control para modo bezier (p1x, p1y, p2x, p2y)
        
    Returns:
        Factor interpolado (0.0 a 1.0)
    """
    t = max(0.0, min(1.0, t))
    
    if mode == InterpolationMode.LINEAR:
        return t
    elif mode == InterpolationMode.EASE_IN:
        return ease_in(t)
    elif mode == InterpolationMode.EASE_OUT:
        return ease_out(t)
    elif mode == InterpolationMode.EASE_IN_OUT:
        return ease_in_out(t)
    elif mode == InterpolationMode.BEZIER:
        return cubic_bezier(t, *bezier_points[:4])
    elif mode == InterpolationMode.CONSTANT:
        return 0.0 if t < 1.0 else 1.0
    else:
        return t  # Fallback lineal


class Keyframe:
    """
    Un keyframe individual que define un valor en un punto temporal.
    
    Atributos:
        time: Tiempo del keyframe (segundos)
        value: Valor en ese punto temporal
        interpolation: Modo de interpolacion HACIA el siguiente keyframe
        bezier_points: Puntos de control para bezier personalizado
    """

    def __init__(self, time: float, value: float, 
                 interpolation: str = InterpolationMode.LINEAR,
                 bezier_points: Tuple[float, ...] = (0.25, 0.1, 0.25, 1.0)):
        self.time: float = time
        self.value: float = value
        self.interpolation: str = interpolation
        self.bezier_points: Tuple[float, ...] = bezier_points

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time": self.time,
            "value": self.value,
            "interpolation": self.interpolation,
            "bezier_points": list(self.bezier_points),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Keyframe':
        return cls(
            time=data.get("time", 0.0),
            value=data.get("value", 0.0),
            interpolation=data.get("interpolation", InterpolationMode.LINEAR),
            bezier_points=tuple(data.get("bezier_points", (0.25, 0.1, 0.25, 1.0))),
        )

    def __repr__(self):
        return f"Keyframe(t={self.time:.2f}, v={self.value:.2f}, interp={self.interpolation})"


class KeyframeTrack:
    """
    Pista de keyframes para un parametro individual.
    
    Contiene una secuencia ordenada de keyframes y proporciona
    interpolacion entre ellos para obtener valores en cualquier tiempo.
    """

    def __init__(self, parameter_name: str, default_value: float = 0.0):
        self.parameter_name: str = parameter_name
        self.default_value: float = default_value
        self.keyframes: List[Keyframe] = []
        self.enabled: bool = True

    def add_keyframe(self, time: float, value: float, 
                     interpolation: str = InterpolationMode.LINEAR) -> Keyframe:
        """
        Agrega o actualiza un keyframe en el tiempo especificado.
        Si ya existe uno en ese tiempo exacto, lo actualiza.
        """
        # Buscar si ya existe en ese tiempo
        for kf in self.keyframes:
            if abs(kf.time - time) < 0.001:  # Tolerancia de 1ms
                kf.value = value
                kf.interpolation = interpolation
                return kf
                
        kf = Keyframe(time, value, interpolation)
        self.keyframes.append(kf)
        self._sort()
        return kf

    def remove_keyframe(self, time: float) -> bool:
        """Elimina el keyframe mas cercano al tiempo dado."""
        if not self.keyframes:
            return False
            
        closest_idx = 0
        closest_dist = float('inf')
        for i, kf in enumerate(self.keyframes):
            dist = abs(kf.time - time)
            if dist < closest_dist:
                closest_dist = dist
                closest_idx = i
                
        if closest_dist < 0.1:  # Tolerancia de 100ms
            self.keyframes.pop(closest_idx)
            return True
        return False

    def get_value_at(self, time: float) -> float:
        """
        Obtiene el valor interpolado en el tiempo especificado.
        
        Si no hay keyframes, retorna el valor por defecto.
        Si el tiempo esta antes del primer kf, retorna su valor.
        Si el tiempo esta despues del ultimo kf, retorna su valor.
        En otro caso, interpola entre los dos keyframes adyacentes.
        """
        if not self.enabled or not self.keyframes:
            return self.default_value
            
        # Antes del primer keyframe
        if time <= self.keyframes[0].time:
            return self.keyframes[0].value
            
        # Despues del ultimo keyframe
        if time >= self.keyframes[-1].time:
            return self.keyframes[-1].value
            
        # Buscar los dos keyframes adyacentes
        for i in range(len(self.keyframes) - 1):
            kf_a = self.keyframes[i]
            kf_b = self.keyframes[i + 1]
            
            if kf_a.time <= time <= kf_b.time:
                # Calcular factor t normalizado (0-1)
                dt = kf_b.time - kf_a.time
                if dt < 0.001:
                    return kf_b.value
                    
                t = (time - kf_a.time) / dt
                
                # Aplicar interpolacion
                t_curved = interpolate(t, kf_a.interpolation, kf_a.bezier_points)
                
                # Interpolar valor
                return lerp(kf_a.value, kf_b.value, t_curved)
                
        return self.default_value

    def _sort(self):
        """Ordena keyframes por tiempo."""
        self.keyframes.sort(key=lambda kf: kf.time)

    def clear(self):
        """Elimina todos los keyframes."""
        self.keyframes.clear()

    @property
    def has_keyframes(self) -> bool:
        return len(self.keyframes) > 0

    @property
    def time_range(self) -> Tuple[float, float]:
        """Retorna el rango temporal de los keyframes."""
        if not self.keyframes:
            return (0.0, 0.0)
        return (self.keyframes[0].time, self.keyframes[-1].time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter_name": self.parameter_name,
            "default_value": self.default_value,
            "enabled": self.enabled,
            "keyframes": [kf.to_dict() for kf in self.keyframes],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KeyframeTrack':
        track = cls(
            parameter_name=data.get("parameter_name", ""),
            default_value=data.get("default_value", 0.0),
        )
        track.enabled = data.get("enabled", True)
        for kf_data in data.get("keyframes", []):
            kf = Keyframe.from_dict(kf_data)
            track.keyframes.append(kf)
        track._sort()
        return track


class KeyframeAnimator:
    """
    Motor de animacion que gestiona multiples pistas de keyframes
    para animar parametros de modulos y clips.
    
    Uso tipico:
        animator = KeyframeAnimator()
        animator.add_track("opacity", default_value=1.0)
        animator.get_track("opacity").add_keyframe(0.0, 1.0)
        animator.get_track("opacity").add_keyframe(2.0, 0.0, "ease_out")
        
        # En cada frame:
        values = animator.get_values_at(current_time)
        # values = {"opacity": 0.5}  (si estamos en t=1.0)
    """

    def __init__(self):
        self.tracks: Dict[str, KeyframeTrack] = {}

    def add_track(self, parameter_name: str, default_value: float = 0.0) -> KeyframeTrack:
        """Agrega una pista de keyframes para un parametro."""
        if parameter_name in self.tracks:
            return self.tracks[parameter_name]
        track = KeyframeTrack(parameter_name, default_value)
        self.tracks[parameter_name] = track
        return track

    def remove_track(self, parameter_name: str) -> bool:
        """Elimina una pista de keyframes."""
        if parameter_name in self.tracks:
            del self.tracks[parameter_name]
            return True
        return False

    def get_track(self, parameter_name: str) -> Optional[KeyframeTrack]:
        """Obtiene una pista de keyframes por nombre."""
        return self.tracks.get(parameter_name)

    def get_value_at(self, parameter_name: str, time: float) -> Optional[float]:
        """Obtiene el valor interpolado de un parametro en un tiempo."""
        track = self.tracks.get(parameter_name)
        if track is None:
            return None
        return track.get_value_at(time)

    def get_values_at(self, time: float) -> Dict[str, float]:
        """
        Obtiene todos los valores interpolados en un tiempo dado.
        
        Returns:
            Diccionario {nombre_parametro: valor_interpolado}
        """
        values = {}
        for name, track in self.tracks.items():
            if track.enabled:
                values[name] = track.get_value_at(time)
        return values

    def has_animation(self) -> bool:
        """Indica si hay alguna pista con keyframes activos."""
        return any(track.has_keyframes for track in self.tracks.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tracks": {name: track.to_dict() for name, track in self.tracks.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KeyframeAnimator':
        animator = cls()
        for name, track_data in data.get("tracks", {}).items():
            track = KeyframeTrack.from_dict(track_data)
            animator.tracks[name] = track
        return animator

    def __repr__(self):
        animated = sum(1 for t in self.tracks.values() if t.has_keyframes)
        return f"KeyframeAnimator(tracks={len(self.tracks)}, animated={animated})"
