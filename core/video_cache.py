#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cache de frames para VideoClip.
Implementa cache LRU real usando OrderedDict para mejorar rendimiento de preview.
"""

from __future__ import annotations
from collections import OrderedDict
from typing import Optional
import numpy as np


class FrameCache:
    """
    Cache LRU para frames de video usando OrderedDict.
    Cachea una cantidad especifica de frames globalmente.
    """
    
    def __init__(self, capacity: int = 300):
        self._cache = OrderedDict()
        self.capacity = capacity
        
    def get_frame(self, clip_id: str, time: float, width: int, height: int) -> Optional[np.ndarray]:
        """
        Obtiene un frame del cache.
        Actualiza su posicion como 'recientemente usado'.
        """
        key = self._make_key(clip_id, time, width, height)
        if key in self._cache:
            # Mover al final (mas recientemente usado)
            self._cache.move_to_end(key)
            return self._cache[key]
        return None
    
    def set_frame(self, clip_id: str, time: float, width: int, height: int, frame: np.ndarray):
        """
        Almacena un frame en el cache.
        Mantiene el limite maximo eliminando el elemento mas antiguo.
        """
        key = self._make_key(clip_id, time, width, height)
        self._cache[key] = frame
        self._cache.move_to_end(key)
        
        # Limitar tamaño del cache (LRU)
        if len(self._cache) > self.capacity:
            # Eliminar el primer elemento (menos recientemente usado)
            self._cache.popitem(last=False)
    
    def clear_clip(self, clip_id: str):
        """Limpia todos los frames de un clip especifico."""
        keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{clip_id}:")]
        for key in keys_to_remove:
            del self._cache[key]
    
    def clear_all(self):
        """Limpia todo el cache."""
        self._cache.clear()
    
    def _make_key(self, clip_id: str, time: float, width: int, height: int) -> str:
        """
        Crea una clave unica para el cache.
        Redondea el tiempo a ~30 fps (pasos de 0.033s) para aumentar
        la probabilidad de hits en el cache durante scrubbing.
        """
        # Redondear tiempo en pasos de 1/30s (0.033)
        rounded_time = round(time * 30) / 30.0
        return f"{clip_id}:{rounded_time:.3f}:{width}:{height}"


# Cache global singleton
_global_cache = FrameCache(capacity=300)


def get_global_cache() -> FrameCache:
    """Obtiene el cache global de frames."""
    return _global_cache


def cached_get_frame(clip, time_in_clip: float, width: int = 0, height: int = 0) -> Optional[np.ndarray]:
    """
    Obtiene un frame usando el cache global.
    Si no esta cacheado, llama a _get_frame_at_time_impl en el clip.
    """
    cache = get_global_cache()
    clip_id = getattr(clip, 'clip_id', str(id(clip)))
    
    # Intentar obtener del cache
    cached_frame = cache.get_frame(clip_id, time_in_clip, width, height)
    if cached_frame is not None:
        return cached_frame.copy()
    
    # Si no esta en cache, obtener el frame llamando a la implementacion real
    frame = clip._get_frame_at_time_impl(time_in_clip, width, height)
    
    # Almacenar en cache si es valido
    if frame is not None:
        cache.set_frame(clip_id, time_in_clip, width, height, frame)
    
    return frame
