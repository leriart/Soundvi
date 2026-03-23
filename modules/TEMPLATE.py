#!/usr/bin/env python3
"""
Plantilla para crear nuevos modulos en Soundvi.

Instrucciones:
1. Copia este archivo y renombralo (ej: `mi_efecto_module.py`).
2. Cambia el nombre de la clase `MiEfectoModule`.
3. Implementa los metodos: `__init__`, `prepare_audio`, `render` y `get_config_widgets`.
4. ¡Listo! El sistema lo detectará automaticamente al arrancar.
"""

import tkinter as tk
import ttkbootstrap as tb
import numpy as np
import cv2

from modules.base import Module

class MiEfectoModule(Module):
    """
    Plantilla de Módulo Plug & Play para Soundvi.
    Todo el estado, física, lógica y widgets deben vivir aquí.
    """
    
    def __init__(self):
        super().__init__(
            nombre="Nombre De Tu Efecto", 
            descripcion="Descripción breve de lo que hace el efecto"
        )
        
        # 1. Configuración por defecto interna
        self._config = {
            "parametro_ejemplo": 50,
            "color_r": 255,
            "color_g": 255,
            "color_b": 255,
            "opacidad": 1.0,
        }
        
        # Opcional: Instancia de tu propio "Motor" si requiere lógica pesada
        self.engine_listo = False
        
    def prepare_audio(self, audio_path: str, mel_data: np.ndarray, sr: int, hop: int, duration: float, fps: int):
        """
        Se llama cada vez que el usuario carga un nuevo archivo de audio.
        Aquí debes procesar el audio si tu módulo reacciona al sonido.
        """
        print(f"[{self.nombre}] Procesando nuevo audio...")
        # Lógica de preprocesamiento (ej: calcular picos, transientes, etc.)
        self.engine_listo = True
    
    def render(self, frame: np.ndarray, tiempo: float, **kwargs) -> np.ndarray:
        """
        El núcleo de renderizado.
        Se llama por cada frame del video y de la vista previa (Preview).
        
        Parametros:
            frame: np.ndarray -> La imagen de fondo (BGR) en la que debes pintar.
            tiempo: float -> Segundo actual del video.
            kwargs: dict -> Puede contener el `fps` actual.
        """
        if not self.habilitado or not self.engine_listo:
            return frame
            
        # EJEMPLO: Dibujar un circulo rebotando o estático usando self._config
        height, width = frame.shape[:2]
        
        radio = self._config["parametro_ejemplo"]
        centro_x = int(width / 2)
        centro_y = int(height / 2 + np.sin(tiempo * 5) * 50)  # Movimiento simple con el tiempo
        
        color_bgr = (
            self._config["color_b"],
            self._config["color_g"],
            self._config["color_r"]
        )
        
        # Opacidad
        opacidad = self._config["opacidad"]
        
        if opacidad < 1.0:
            overlay = frame.copy()
            cv2.circle(overlay, (centro_x, centro_y), radio, color_bgr, -1)
            cv2.addWeighted(overlay, opacidad, frame, 1 - opacidad, 0, frame)
        else:
            cv2.circle(frame, (centro_x, centro_y), radio, color_bgr, -1)
            
        return frame
    
    def get_config_widgets(self, parent: tk.Frame, app) -> tk.Frame:
        """
        Crea los controles visuales que aparecerán en la barra lateral.
        Estos controles deben modificar `self._config`.
        """
        # Contenedor para los widgets
        frame = tb.Frame(parent)
        
        tb.Label(frame, text="Configuración de Mi Efecto:", font=("", 9, "bold")).pack(anchor="w", pady=(5,0))
        
        # -- Ejemplo: Un Slider --
        row_param = tb.Frame(frame)
        row_param.pack(fill=tk.X, pady=2)
        tb.Label(row_param, text="Radio:").pack(side=tk.LEFT, padx=2)
        
        param_var = tk.IntVar(value=self._config["parametro_ejemplo"])
        scale = tb.Scale(row_param, from_=10, to=200, variable=param_var, orient=tk.HORIZONTAL)
        scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        val_label = tb.Label(row_param, text=f"{param_var.get()}")
        val_label.pack(side=tk.LEFT)
        
        # Actualizar config interna cuando cambie
        def update_param(*args):
            val = param_var.get()
            self._config["parametro_ejemplo"] = val
            val_label.config(text=str(val))
            # Si es necesario forzar a la app a redibujar el preview
            if hasattr(app, "update_preview"):
                app.update_preview()
                
        param_var.trace_add("write", update_param)
        
        return frame
