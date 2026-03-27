#!/usr/bin/env python3
"""
Soundvi App - PyQt6 Implementation.

This module re-exports the Qt6 main window as the primary application
interface. The legacy ttkbootstrap implementation has been removed.
"""

from gui.qt6.main_window import VentanaPrincipalQt6 as SoundviApp

__all__ = ["SoundviApp"]
