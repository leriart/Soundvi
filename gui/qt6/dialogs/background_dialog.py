#!/usr/bin/env python3
"""
Dialogo para seleccionar fondo (color, imagen, gradiente) para transiciones.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTabWidget, QWidget, QColorDialog, QFileDialog, QComboBox,
    QSpinBox, QGroupBox, QGridLayout
)
from PyQt6.QtGui import QColor, QPixmap, QPainter, QLinearGradient
from PyQt6.QtCore import Qt, QSize

class BackgroundDialog(QDialog):
    """Dialogo para seleccionar fondo para transiciones."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar fondo para transicion")
        self.setMinimumSize(500, 400)
        
        self._selection_type = "color"  # "color", "image", "gradient"
        self._selection_value = "#000000"  # Color hex, ruta de imagen, o tipo de gradiente
        
        self._construir_ui()
        
    def _construir_ui(self):
        layout = QVBoxLayout(self)
        
        # Tabs para diferentes tipos de fondo
        self._tabs = QTabWidget()
        
        # Tab de color
        color_tab = QWidget()
        color_layout = QVBoxLayout(color_tab)
        
        color_group = QGroupBox("Color solido")
        color_group_layout = QVBoxLayout(color_group)
        
        self._color_preview = QLabel()
        self._color_preview.setMinimumSize(200, 100)
        self._color_preview.setStyleSheet("background-color: #000000; border: 2px solid #495057; border-radius: 4px;")
        color_group_layout.addWidget(self._color_preview)
        
        self._btn_choose_color = QPushButton("Seleccionar color...")
        self._btn_choose_color.clicked.connect(self._elegir_color)
        color_group_layout.addWidget(self._btn_choose_color)
        
        color_layout.addWidget(color_group)
        color_layout.addStretch()
        
        # Tab de imagen
        image_tab = QWidget()
        image_layout = QVBoxLayout(image_tab)
        
        image_group = QGroupBox("Imagen de fondo")
        image_group_layout = QVBoxLayout(image_group)
        
        self._image_preview = QLabel()
        self._image_preview.setMinimumSize(200, 150)
        self._image_preview.setStyleSheet("background-color: #2B3035; border: 2px dashed #495057; border-radius: 4px;")
        self._image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_preview.setText("Sin imagen seleccionada")
        image_group_layout.addWidget(self._image_preview)
        
        self._btn_choose_image = QPushButton("Seleccionar imagen...")
        self._btn_choose_image.clicked.connect(self._elegir_imagen)
        image_group_layout.addWidget(self._btn_choose_image)
        
        image_layout.addWidget(image_group)
        image_layout.addStretch()
        
        # Tab de gradiente
        gradient_tab = QWidget()
        gradient_layout = QVBoxLayout(gradient_tab)
        
        gradient_group = QGroupBox("Gradiente")
        gradient_group_layout = QGridLayout(gradient_group)
        
        gradient_group_layout.addWidget(QLabel("Tipo:"), 0, 0)
        self._gradient_combo = QComboBox()
        self._gradient_combo.addItems(["Horizontal", "Vertical", "Diagonal", "Radial"])
        gradient_group_layout.addWidget(self._gradient_combo, 0, 1)
        
        gradient_group_layout.addWidget(QLabel("Color inicio:"), 1, 0)
        self._btn_gradient_start = QPushButton("#000000")
        self._btn_gradient_start.clicked.connect(lambda: self._elegir_color_gradiente("start"))
        self._btn_gradient_start.setStyleSheet("background-color: #000000; color: white;")
        gradient_group_layout.addWidget(self._btn_gradient_start, 1, 1)
        
        gradient_group_layout.addWidget(QLabel("Color fin:"), 2, 0)
        self._btn_gradient_end = QPushButton("#FFFFFF")
        self._btn_gradient_end.clicked.connect(lambda: self._elegir_color_gradiente("end"))
        self._btn_gradient_end.setStyleSheet("background-color: #FFFFFF; color: black;")
        gradient_group_layout.addWidget(self._btn_gradient_end, 2, 1)
        
        self._gradient_preview = QLabel()
        self._gradient_preview.setMinimumSize(200, 100)
        self._gradient_preview.setStyleSheet("border: 2px solid #495057; border-radius: 4px;")
        gradient_group_layout.addWidget(self._gradient_preview, 3, 0, 1, 2)
        
        # Actualizar preview del gradiente
        self._gradient_combo.currentTextChanged.connect(self._actualizar_gradiente_preview)
        self._actualizar_gradiente_preview()
        
        gradient_layout.addWidget(gradient_group)
        gradient_layout.addStretch()
        
        # Agregar tabs
        self._tabs.addTab(color_tab, "Color")
        self._tabs.addTab(image_tab, "Imagen")
        self._tabs.addTab(gradient_tab, "Gradiente")
        
        layout.addWidget(self._tabs)
        
        # Botones
        btn_layout = QHBoxLayout()
        self._btn_ok = QPushButton("Aceptar")
        self._btn_ok.clicked.connect(self.accept)
        self._btn_cancel = QPushButton("Cancelar")
        self._btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self._btn_ok)
        btn_layout.addWidget(self._btn_cancel)
        
        layout.addLayout(btn_layout)
        
        # Conectar cambio de tab
        self._tabs.currentChanged.connect(self._on_tab_changed)
        
    def _elegir_color(self):
        color = QColorDialog.getColor(QColor(self._selection_value), self, "Seleccionar color")
        if color.isValid():
            self._selection_value = color.name()
            self._color_preview.setStyleSheet(f"background-color: {color.name()}; border: 2px solid #495057; border-radius: 4px;")
    
    def _elegir_imagen(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar imagen", "", 
            "Imagenes (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_path:
            self._selection_value = file_path
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                # Escalar para preview
                scaled = pixmap.scaled(200, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self._image_preview.setPixmap(scaled)
                self._image_preview.setText("")
    
    def _elegir_color_gradiente(self, cual: str):
        if cual == "start":
            btn = self._btn_gradient_start
            current = QColor(btn.text())
        else:
            btn = self._btn_gradient_end
            current = QColor(btn.text())
            
        color = QColorDialog.getColor(current, self, f"Seleccionar color {cual}")
        if color.isValid():
            btn.setText(color.name())
            btn.setStyleSheet(f"background-color: {color.name()}; color: {'white' if color.lightness() < 128 else 'black'};")
            self._actualizar_gradiente_preview()
    
    def _actualizar_gradiente_preview(self):
        color_start = QColor(self._btn_gradient_start.text())
        color_end = QColor(self._btn_gradient_end.text())
        gradient_type = self._gradient_combo.currentText()
        
        # Crear pixmap para preview
        pixmap = QPixmap(200, 100)
        painter = QPainter(pixmap)
        
        if gradient_type == "Horizontal":
            gradient = QLinearGradient(0, 0, 200, 0)
        elif gradient_type == "Vertical":
            gradient = QLinearGradient(0, 0, 0, 100)
        elif gradient_type == "Diagonal":
            gradient = QLinearGradient(0, 0, 200, 100)
        else:  # Radial
            gradient = QLinearGradient(100, 50, 200, 50)
            gradient.setColorAt(0, color_start)
            gradient.setColorAt(1, color_end)
            # Para radial, simular con dos colores
            painter.fillRect(0, 0, 200, 100, color_start)
            painter.setBrush(color_end)
            painter.drawEllipse(50, 25, 100, 50)
            painter.end()
            self._gradient_preview.setPixmap(pixmap)
            return
        
        gradient.setColorAt(0, color_start)
        gradient.setColorAt(1, color_end)
        painter.fillRect(0, 0, 200, 100, gradient)
        painter.end()
        
        self._gradient_preview.setPixmap(pixmap)
    
    def _on_tab_changed(self, index: int):
        """Cuando cambia la pestaña, actualizar el tipo de seleccion."""
        if index == 0:  # Color
            self._selection_type = "color"
        elif index == 1:  # Imagen
            self._selection_type = "image"
        elif index == 2:  # Gradiente
            self._selection_type = "gradient"
            self._selection_value = f"{self._gradient_combo.currentText()}:{self._btn_gradient_start.text()}:{self._btn_gradient_end.text()}"
    
    def get_selection(self):
        """Retorna el tipo y valor de la seleccion."""
        if self._selection_type == "gradient":
            self._selection_value = f"{self._gradient_combo.currentText()}:{self._btn_gradient_start.text()}:{self._btn_gradient_end.text()}"
        return self._selection_type, self._selection_value
