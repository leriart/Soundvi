#!/usr/bin/env python3
from __future__ import annotations
from utils.fonts import get_default_font
"""
Clase base para el sistema de modulos de Soundvi.

Todos los modulos (CAVA, Subtitulos, etc.) deben heredar de ``Module``
e implementar los metodos abstractos.

NUEVAS CARACTERISTICAS:
- Checkbox para activar/desactivar modulo
- Ocultar/mostrar configuraciones al desactivar
- Soporte para capas (z-index)
- Selector de color integrado
- Area separada para modulos activos/inactivos
"""


from abc import ABC, abstractmethod
from typing import Any, Optional
import tkinter as tk

import numpy as np

try:
    import ttkbootstrap as tb
except ImportError:
    import tkinter.ttk as tb


class Module(ABC):
    """
    Clase base abstracta para modulos de Soundvi.

    Cada modulo representa una capa visual que se puede activar/desactivar
    y tiene sus propias configuraciones.
    """

    def __init__(self, nombre: str, descripcion: str = "", capa: int = 0):
        self.nombre = nombre
        self.descripcion = descripcion
        self.capa = capa  # Z-index: mayor valor = mas arriba
        self._habilitado = False
        self._config: dict[str, Any] = {}
        self._config_frame: Optional[tk.Frame] = None
        self._color_var: Optional[tk.StringVar] = None

    # -- Propiedades ----------------------------------------------------------

    @property
    def habilitado(self) -> bool:
        return self._habilitado

    @habilitado.setter
    def habilitado(self, valor: bool):
        old_value = self._habilitado
        self._habilitado = valor
        
        # Ocultar/mostrar configuraciones si hay un frame de config
        if self._config_frame is not None and old_value != valor:
            if valor:
                self._config_frame.pack(fill=tk.X, pady=5)
            else:
                self._config_frame.pack_forget()

    # -- Metodos abstractos ---------------------------------------------------

    @abstractmethod
    def render(self, frame: np.ndarray, tiempo: float, **kwargs) -> np.ndarray:
        """
        Renderiza este modulo sobre el frame dado.

        Parametros
        ----------
        frame : np.ndarray
            Frame BGR de OpenCV (alto, ancho, 3).
        tiempo : float
            Tiempo actual en segundos.
        **kwargs :
            Datos adicionales (alturas CAVA, subtitulos, etc.)

        Devuelve
        --------
        np.ndarray : Frame con el modulo renderizado.
        """
        ...

    @abstractmethod
    def get_config_widgets(self, parent, app) -> Any:
        """
        Crea y devuelve los widgets de configuracion de este modulo
        para insertarlos en el sidebar.

        Parametros
        ----------
        parent : tk.Frame
            Contenedor padre donde insertar los widgets.
        app :
            Referencia a la aplicacion principal (para acceder a variables tk).

        Devuelve
        --------
        El frame o widget raiz creado.
        """
        ...

    # -- Metodos para UI mejorada ---------------------------------------------

    def create_module_frame(self, parent, app, on_refresh=None) -> tk.Frame:
        """
        Crea un frame estandarizado para el modulo con:
        - Checkbox para activar/desactivar
        - Nombre y descripcion
        - Boton para eliminar el modulo (si no es el unico o base)
        - Contenedor plegable para configuraciones
        - Selector de color (opcional)
        - Control de capa
        
        Args:
            parent: Frame padre
            app: Instancia principal de la app
            on_refresh: Callback opcional a llamar cuando el estado cambia
            
        Returns:
            Frame principal del modulo
        """
        # Frame principal del modulo
        main_frame = tb.Frame(parent)
        
        # Frame de encabezado con checkbox
        header_frame = tb.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Checkbox para activar/desactivar
        enabled_var = tk.BooleanVar(value=self._habilitado)
        
        def toggle_enabled():
            self.habilitado = enabled_var.get()
            app.trigger_auto_save()
            if on_refresh:
                # Usar loading overlay si el on_refresh es asincrono o pesado
                # pero generalmente actualizar la UI es muy rapido.
                on_refresh()
        
        checkbox = tb.Checkbutton(
            header_frame,
            text=self.nombre,
            variable=enabled_var,
            command=toggle_enabled,
            bootstyle="primary-round-toggle"
        )
        checkbox.pack(side=tk.LEFT, padx=(0, 10))
        
        # Boton Eliminar
        def delete_module():
            app.module_manager.remove_module_instance(self)
            app.trigger_auto_save()
            if on_refresh:
                app.loading_overlay.show()
                app.root.after(100, lambda: [on_refresh(), app.loading_overlay.hide()])

        delete_btn = tb.Button(
            header_frame,
            text="🗑",
            bootstyle="danger-outline",
            command=delete_module,
            width=2
        )
        delete_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Control de capa
        layer_frame = tb.Frame(header_frame)
        layer_frame.pack(side=tk.RIGHT)

        # Descripcion (opcional), al final para que no empuje a los demas
        if self.descripcion:
            desc_label = tb.Label(
                header_frame,
                text=self.descripcion[:20] + "..." if len(self.descripcion) > 20 else self.descripcion,
                font=(get_default_font(), 8),
                foreground="gray"
            )
            desc_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        tb.Label(layer_frame, text="Capa:", font=(get_default_font(), 8)).pack(side=tk.LEFT)
        self._capa_var = tk.IntVar(value=self.capa)
        layer_spin = tb.Spinbox(
            layer_frame,
            from_=0,
            to=10,
            textvariable=self._capa_var,
            width=3,
            command=lambda: self._update_layer(self._capa_var.get(), app)
        )
        # Añadir evento por si el usuario escribe en el spinbox
        self._capa_var.trace_add("write", lambda *a: self._update_layer(self._capa_var.get(), app))
        layer_spin.pack(side=tk.LEFT, padx=(2, 0))
        
        # Frame para configuraciones (inicialmente visible si esta habilitado)
        self._config_frame = tb.LabelFrame(main_frame, text=f"Configuración {self.nombre}")
        if self._habilitado:
            self._config_frame.pack(fill=tk.X, pady=5)
        
        # Llamar al metodo especifico del modulo para crear widgets de config
        config_content = self.get_config_widgets(self._config_frame, app)
        if config_content:
            config_content.pack(fill=tk.X, padx=5, pady=5)
        
        return main_frame
    
    def _update_layer(self, layer_value: str, app):
        """Actualiza la capa del modulo."""
        try:
            self.capa = int(layer_value)
            app.trigger_auto_save()
        except ValueError:
            pass
    
    def create_color_picker(self, parent, color_var: tk.StringVar, app, label: str = "Color:") -> tk.Frame:
        """
        Crea un selector de color estandarizado.
        
        Args:
            parent: Frame padre
            color_var: StringVar que contiene el color en formato "#RRGGBB"
            label: Etiqueta para el selector
            
        Returns:
            Frame con el selector de color
        """
        self._color_var = color_var
        color_frame = tb.Frame(parent)
        
        tb.Label(color_frame, text=label, font=(get_default_font(), 9)).pack(side=tk.LEFT, padx=(0, 5))
        
        # Boton para seleccionar color
        color_btn = tb.Button(
            color_frame,
            text="Seleccionar",
            command=lambda: self._pick_color(color_var, app),
            bootstyle="outline",
            width=10
        )
        color_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Muestra del color actual
        current_color = color_var.get()
        if not current_color or not current_color.startswith('#'):
            current_color = "#FFFFFF"
            
        color_preview = tk.Canvas(color_frame, width=20, height=20, highlightthickness=1, highlightbackground="gray")
        try:
            color_preview.config(bg=current_color)
        except:
            color_preview.config(bg="#FFFFFF")
            
        color_preview.pack(side=tk.LEFT)
        
        # Actualizar preview cuando cambia el color
        def update_preview(*args):
            new_color = color_var.get()
            if new_color and new_color.startswith('#') and len(new_color) == 7:
                try:
                    color_preview.config(bg=new_color)
                except: pass
        
        color_var.trace_add("write", update_preview)
        
        return color_frame
    
    def _pick_color(self, color_var: tk.StringVar, app=None):
        """Abre un dialogo personalizado para seleccionar color (ttkbootstrap)."""
        if app is None:
            # Fallback a tkinter nativo si no tenemos app (no deberia pasar)
            try:
                from tkinter import colorchooser
                color = colorchooser.askcolor(title=f"Color - {self.nombre}")
                if color[1]: color_var.set(color[1])
            except: pass
            return

        try:
            # Ventana Toplevel para seleccionar color
            top = tb.Toplevel(app.root)
            top.title(f"Seleccionar Color - {self.nombre}")
            top.geometry("320x350")
            top.resizable(False, False)
            top.transient(app.root)
            top.grab_set()
            
            # Marco principal
            frame = tb.Frame(top, padding=10)
            frame.pack(fill=tk.BOTH, expand=tk.YES)
            
            # Preview del color actual
            current_hex = color_var.get()
            if not current_hex or not current_hex.startswith('#'): current_hex = "#FFFFFF"
            
            preview = tk.Canvas(frame, height=60, bg=current_hex, highlightthickness=1, highlightbackground="gray")
            preview.pack(fill=tk.X, pady=(0, 10))
            
            # Variables de RGB
            try:
                r_val = int(current_hex[1:3], 16)
                g_val = int(current_hex[3:5], 16)
                b_val = int(current_hex[5:7], 16)
            except:
                r_val, g_val, b_val = 255, 255, 255
                
            r_var = tk.IntVar(value=r_val)
            g_var = tk.IntVar(value=g_val)
            b_var = tk.IntVar(value=b_val)
            hex_var = tk.StringVar(value=current_hex)
            
            def update_from_rgb(*args):
                h = f"#{r_var.get():02x}{g_var.get():02x}{b_var.get():02x}"
                hex_var.set(h)
                preview.config(bg=h)
                
            def update_from_hex(*args):
                h = hex_var.get()
                if len(h) == 7 and h.startswith('#'):
                    try:
                        r_var.set(int(h[1:3], 16))
                        g_var.set(int(h[3:5], 16))
                        b_var.set(int(h[5:7], 16))
                        preview.config(bg=h)
                    except: pass
            
            r_var.trace_add("write", update_from_rgb)
            g_var.trace_add("write", update_from_rgb)
            b_var.trace_add("write", update_from_rgb)
            
            # Sliders
            def create_rgb_slider(parent, label, var):
                row = tb.Frame(parent)
                row.pack(fill=tk.X, pady=5)
                tb.Label(row, text=label, width=2, font=(get_default_font(), 10, "bold")).pack(side=tk.LEFT)
                scale = tb.Scale(row, from_=0, to=255, variable=var, orient=tk.HORIZONTAL)
                scale.pack(side=tk.LEFT, fill=tk.X, expand=tk.YES, padx=5)
                tb.Label(row, textvariable=var, width=4).pack(side=tk.LEFT)
                return scale
                
            create_rgb_slider(frame, "R", r_var)
            create_rgb_slider(frame, "G", g_var)
            create_rgb_slider(frame, "B", b_var)
            
            # Hex Entry
            hex_frame = tb.Frame(frame)
            hex_frame.pack(fill=tk.X, pady=10)
            tb.Label(hex_frame, text="HEX:").pack(side=tk.LEFT)
            hex_entry = tb.Entry(hex_frame, textvariable=hex_var, width=10)
            hex_entry.pack(side=tk.LEFT, padx=5)
            hex_entry.bind("<KeyRelease>", update_from_hex)
            
            # Botones
            btn_frame = tb.Frame(frame)
            btn_frame.pack(fill=tk.X, pady=(10, 0))
            
            def apply_color():
                color_var.set(hex_var.get())
                top.destroy()
                
            tb.Button(btn_frame, text="Aceptar", bootstyle="success", command=apply_color).pack(side=tk.RIGHT, padx=2)
            tb.Button(btn_frame, text="Cancelar", bootstyle="secondary", command=top.destroy).pack(side=tk.RIGHT, padx=2)
            
        except Exception as e:
            print(f"Error en color picker custom: {e}")
            # Fallback fallback
            from tkinter import colorchooser
            color = colorchooser.askcolor(title=f"Color - {self.nombre}")
            if color[1]: color_var.set(color[1])

    # -- Metodos de utilidad --------------------------------------------------

    def enable(self):
        """Habilita este modulo."""
        self._habilitado = True
        print(f"[modulo] '{self.nombre}' habilitado")

    def disable(self):
        """Deshabilita este modulo."""
        self._habilitado = False
        print(f"[modulo] '{self.nombre}' deshabilitado")

    def get_config(self) -> dict:
        """Devuelve la configuracion actual del modulo."""
        return self._config.copy()

    def set_config(self, config: dict):
        """Establece la configuracion del modulo."""
        self._config.update(config)

    def _update_config(self, key: str, value: Any, app):
        """Actualiza la configuracion y notifica a la app para auto-guardado y preview."""
        self._config[key] = value
        if hasattr(app, 'trigger_auto_save'):
            app.trigger_auto_save()
        # Llamada directa a update_preview para refresco inmediato
        if hasattr(app, 'update_preview'):
            app.update_preview()

    def __repr__(self):
        estado = "habilitado" if self._habilitado else "deshabilitado"
        return f"<Module '{self.nombre}' capa={self.capa} [{estado}]>"
    
    def __lt__(self, other):
        """Comparacion para ordenar por capa (menor capa = mas abajo)."""
        return self.capa < other.capa