# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- Selector de temas mejorado.

Widget para seleccionar entre todos los temas disponibles con preview visual
y cambio en tiempo real. Incluye mini-previews de cada tema.
"""

from __future__ import annotations

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QSizePolicy, QScrollArea, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter, QPaintEvent, QLinearGradient, QBrush

from .theme import AdministradorTemas, TEMAS_NOMBRES


class ThemePreviewWidget(QFrame):
    """Mini preview visual de un tema."""
    
    clicked = pyqtSignal(str)  # Emite el nombre del tema al hacer clic
    
    def __init__(self, tema_id: str, tema_nombre: str, activo: bool = False,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.tema_id = tema_id
        self.tema_nombre = tema_nombre
        self.activo = activo
        self.hover = False
        
        self.setFixedSize(120, 100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName(f"theme_preview_{tema_id}")
        
        # Layout interno
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Nombre del tema
        self.label_nombre = QLabel(tema_nombre)
        self.label_nombre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_nombre.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        layout.addWidget(self.label_nombre)
        
        # Preview visual (área de dibujo)
        self.preview_area = QFrame()
        self.preview_area.setFixedHeight(60)
        self.preview_area.setObjectName("preview_area")
        layout.addWidget(self.preview_area)
        
        # Estado
        self.label_estado = QLabel("✓ Activo" if activo else "Seleccionar")
        self.label_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_estado.setFont(QFont("Segoe UI", 8))
        layout.addWidget(self.label_estado)
        
        self._actualizar_estilos()
    
    def enterEvent(self, event):
        self.hover = True
        self._actualizar_estilos()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self.hover = False
        self._actualizar_estilos()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.tema_id)
        super().mousePressEvent(event)
    
    def set_activo(self, activo: bool):
        self.activo = activo
        self.label_estado.setText("✓ Activo" if activo else "Seleccionar")
        self._actualizar_estilos()
    
    def _actualizar_estilos(self):
        """Actualiza los estilos según el estado."""
        from .theme import TEMAS
        
        tema = TEMAS.get(self.tema_id)
        if not tema:
            return
        
        # Estilo del widget principal
        if self.activo:
            border_color = tema.primario
            bg_color = tema.fondo_alt
            text_color = tema.texto
        elif self.hover:
            border_color = tema.borde
            bg_color = tema.fondo_input
            text_color = tema.texto
        else:
            border_color = tema.borde
            bg_color = tema.fondo
            text_color = tema.texto_secundario
        
        self.setStyleSheet(f"""
            QFrame#theme_preview_{self.tema_id} {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 8px;
            }}
        """)
        
        # Estilo del nombre
        self.label_nombre.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                background: transparent;
            }}
        """)
        
        # Estilo del estado
        estado_color = tema.exito if self.activo else tema.texto_secundario
        self.label_estado.setStyleSheet(f"""
            QLabel {{
                color: {estado_color};
                background: transparent;
            }}
        """)
        
        # Estilo del área de preview
        self.preview_area.setStyleSheet(f"""
            QFrame#preview_area {{
                background-color: {tema.fondo_panel};
                border: 1px solid {tema.borde};
                border-radius: 4px;
            }}
        """)


class ThemeSelectorWidget(QWidget):
    """Widget completo para selección de temas con previews."""
    
    theme_changed = pyqtSignal(str)  # Emite cuando se cambia el tema
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.tema_manager = AdministradorTemas()
        self.tema_actual = self.tema_manager.tema_actual()
        self.previews: Dict[str, ThemePreviewWidget] = {}
        
        self._construir_ui()
    
    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Título
        titulo = QLabel("🎨 Tema visual")
        titulo.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(titulo)
        
        # Descripción
        desc = QLabel("Selecciona un tema para cambiar la apariencia de la interfaz. Los cambios se aplican inmediatamente.")
        desc.setWordWrap(True)
        desc.setFont(QFont("Segoe UI", 9))
        layout.addWidget(desc)
        
        # Grid de previews de temas
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(12)
        
        temas = self.tema_manager.listar_temas_nombres()
        temas_items = list(temas.items())
        
        for i, (tema_id, tema_nombre) in enumerate(temas_items):
            row = i // 2
            col = i % 2
            
            preview = ThemePreviewWidget(
                tema_id=tema_id,
                tema_nombre=tema_nombre,
                activo=(tema_id == self.tema_actual)
            )
            preview.clicked.connect(self._on_tema_seleccionado)
            
            self.previews[tema_id] = preview
            grid_layout.addWidget(preview, row, col)
        
        # Asegurar que el grid se expanda uniformemente
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)
        
        layout.addWidget(grid_widget)
        
        # Información adicional
        info = QLabel("💡 El tema se guarda automáticamente y se usará en el próximo inicio.")
        info.setWordWrap(True)
        info.setFont(QFont("Segoe UI", 8))
        info.setStyleSheet("color: #6C757D;")
        layout.addWidget(info)
        
        layout.addStretch()
    
    def _on_tema_seleccionado(self, tema_id: str):
        """Maneja la selección de un tema."""
        if tema_id == self.tema_actual:
            return
        
        # Actualizar estado de previews
        for tid, preview in self.previews.items():
            preview.set_activo(tid == tema_id)
        
        # Cambiar tema
        self.tema_actual = tema_id
        self.tema_manager.aplicar_tema(tema_id)
        
        # Guardar preferencias
        try:
            from utils.config import load_user_prefs, save_user_prefs
            prefs = load_user_prefs()
            prefs["tema"] = tema_id
            save_user_prefs(prefs)
        except Exception:
            pass  # Silenciar errores de configuración
        
        # Emitir señal
        self.theme_changed.emit(tema_id)
        
        # Actualizar estilos de los previews (ya que el tema cambió)
        QTimer.singleShot(100, self._actualizar_previews_estilos)
    
    def _actualizar_previews_estilos(self):
        """Actualiza los estilos de todos los previews después de cambiar el tema."""
        for preview in self.previews.values():
            preview._actualizar_estilos()


class ThemeSelectorDialog(QFrame):
    """Diálogo flotante para selección rápida de temas."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._construir_ui()
    
    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Selector de temas
        self.selector = ThemeSelectorWidget()
        layout.addWidget(self.selector)
        
        # Estilo del diálogo
        self.setStyleSheet("""
            QFrame {
                background-color: #1a1d23;
                border: 2px solid #444c56;
                border-radius: 12px;
            }
        """)
        
        # Sombra
        self.setGraphicsEffect(self._crear_sombra())
    
    def _crear_sombra(self):
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 100))
        return shadow


# Función de conveniencia para mostrar el selector
def mostrar_selector_temas(parent: QWidget) -> ThemeSelectorDialog:
    """Muestra un diálogo flotante para selección de temas."""
    dialog = ThemeSelectorDialog(parent)
    dialog.move(parent.mapToGlobal(parent.rect().center()) - dialog.rect().center())
    dialog.show()
    return dialog