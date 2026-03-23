from utils.fonts import get_default_font
import tkinter as tk
import ttkbootstrap as tb
from PIL import Image, ImageTk
import os
import threading
import time

class LoadingOverlay:
    """Overlay de carga con efecto de fade in/out y el texto 'cagando....'"""
    def __init__(self, root, app):
        self.root = root
        self.app = app
        self.overlay = None
        self.opacity = 0.0
        self.is_showing = False
        
        # Guardar imágenes
        self.logo_img = None
        
    def _create_overlay(self):
        if self.overlay:
            return
            
        # Crear Toplevel sin bordes y superpuesto
        self.overlay = tk.Toplevel(self.root)
        self.overlay.overrideredirect(True)
        self.overlay.attributes('-alpha', 0.0)  # Inicia invisible
        
        # Color de fondo igual al tema actual
        bg_color = tb.Style().colors.bg
        self.overlay.configure(bg=bg_color)
        
        # Frame central para mantener todo centrado
        center_frame = tk.Frame(self.overlay, bg=bg_color)
        center_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Intentar cargar logo
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logos", "Cagando.png")
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                # Hacer el logo mucho mas grande
                img.thumbnail((250, 250), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(img)
                
                logo_label = tk.Label(center_frame, image=self.logo_img, bg=bg_color)
                logo_label.pack(pady=(0, 15))
            except Exception as e:
                print(f"Error cargando logo para overlay: {e}")
                
        # Texto "cagando...."
        text_label = tk.Label(
            center_frame, 
            text="cagando....", 
            font=(get_default_font(), 16, "bold"),
            bg=bg_color,
            fg=tb.Style().colors.primary
        )
        text_label.pack()
        
    def _update_geometry(self):
        # -- AGREGADO: Checar si la ventana existe antes de modificar --
        if not self.overlay or not self.overlay.winfo_exists():
            return
            
        # Posicionar exactamente sobre la ventana principal
        x = self.root.winfo_rootx()
        y = self.root.winfo_rooty()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        
        self.overlay.geometry(f"{w}x{h}+{x}+{y}")
        
    def _fade_in(self):
        if not self.overlay or not self.is_showing:
            return
            
        self.opacity += 0.05
        if self.opacity >= 0.85:  # Opacidad máxima 85% para ver algo detrás
            self.opacity = 0.85
            self.overlay.attributes('-alpha', self.opacity)
        else:
            self.overlay.attributes('-alpha', self.opacity)
            self.root.after(15, self._fade_in)
            
    def _fade_out(self):
        if not self.overlay or self.is_showing:
            return
            
        self.opacity -= 0.05
        if self.opacity <= 0.0:
            self.opacity = 0.0
            self.overlay.attributes('-alpha', 0.0)
            self.overlay.destroy()
            self.overlay = None
        else:
            self.overlay.attributes('-alpha', self.opacity)
            self.root.after(15, self._fade_out)
            
    def show(self):
        self.root.after(0, self._show_internal)
        
    def _show_internal(self):
        """Muestra el overlay de carga con animación"""
        if self.is_showing:
            return
            
        self.is_showing = True
        self.opacity = 0.0
        self._create_overlay()
        self._update_geometry()
        
        # Mantener sobre la app pero debajo de otros programas
        self.overlay.transient(self.root)
        self.overlay.lift()
        
        # Iniciar animación
        self._fade_in()
        
        # Actualizar posición si se mueve la ventana
        self.root.bind('<Configure>', lambda e: self._update_geometry(), add='+')
        
    def hide(self):
        self.root.after(0, self._hide_internal)
        
    def _hide_internal(self):
        """Oculta el overlay de carga con animación"""
        if not self.is_showing:
            return
            
        self.is_showing = False
        self._fade_out()
        
