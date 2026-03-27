#!/usr/bin/env python3
"""
Test simple para verificar que PyInstaller puede construir un ejecutable básico.
"""

import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt6.QtGui import QAction, QActionGroup

print("[✓] Test de imports de Qt exitoso:")
print(f"  QApplication: {QApplication}")
print(f"  QAction: {QAction}")
print(f"  QActionGroup: {QActionGroup}")
print(f"  QMainWindow: {QMainWindow}")
print(f"  QLabel: {QLabel}")

# Verificar que podemos crear una aplicación simple
app = QApplication([])
window = QMainWindow()
window.setWindowTitle("Test Qt")
label = QLabel("[✓] Qt funciona correctamente", window)
window.setCentralWidget(label)
window.show()

print("\n[✓] Aplicación Qt creada exitosamente")
print("  Cierra la ventana para continuar...")

sys.exit(app.exec())