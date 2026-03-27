#!/usr/bin/env python3
"""
Loading Overlay - PyQt6 Implementation.

Provides a loading overlay widget compatible with the Qt6 architecture.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt


class LoadingOverlay(QWidget):
    """Overlay de carga translucido con barra de progreso."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 180);")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel("Cargando...")
        self._label.setStyleSheet("color: white; font-size: 14pt; font-weight: bold;")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._label)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # Indeterminate mode
        self._progress.setFixedWidth(300)
        self._progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 5px;
                background: #333;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #0078d7;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self._progress, alignment=Qt.AlignmentFlag.AlignCenter)

        self.hide()

    def show_loading(self, message: str = "Cargando..."):
        """Muestra el overlay con un mensaje."""
        self._label.setText(message)
        if self.parent():
            self.setGeometry(self.parent().rect())
        self.show()
        self.raise_()

    def hide_loading(self):
        """Oculta el overlay."""
        self.hide()

    def set_progress(self, value: int, maximum: int = 100):
        """Configura el progreso determinado."""
        self._progress.setRange(0, maximum)
        self._progress.setValue(value)

    def set_indeterminate(self):
        """Modo indeterminado."""
        self._progress.setRange(0, 0)

    # Legacy compatibility
    def show_with_message(self, msg="Cargando..."):
        self.show_loading(msg)

    def update_text(self, text: str):
        self._label.setText(text)


__all__ = ["LoadingOverlay"]
