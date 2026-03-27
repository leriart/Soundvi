#!/usr/bin/env python3
"""
Sidebar - PyQt6 Implementation.
Re-exports from gui.qt6.sidebar_widget.
"""

from gui.qt6.sidebar_widget import SidebarWidget

def build_sidebar(parent, app):
    """Compatibility wrapper for legacy code."""
    return SidebarWidget(parent)

__all__ = ["build_sidebar", "SidebarWidget"]
