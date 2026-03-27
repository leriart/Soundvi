# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- Sistema de temas.

Replica el estilo oscuro de ttkbootstrap "darkly" para Qt6 mediante
QSS (Qt Style Sheets).  Permite cambiar de tema en caliente sin
reiniciar la aplicacion.
"""

from __future__ import annotations

from typing import Dict, Optional
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt


# ---------------------------------------------------------------------------
#  Paletas de colores
# ---------------------------------------------------------------------------
class Paleta:
    """Almacena los colores de un tema."""

    def __init__(self, nombre: str, colores: Dict[str, str]):
        self.nombre = nombre
        self._c = colores

    def __getattr__(self, item: str) -> str:
        if item.startswith("_") or item == "nombre":
            return super().__getattribute__(item)
        return self._c.get(item, "#FFFFFF")

    def color(self, clave: str) -> str:
        return self._c.get(clave, "#FFFFFF")


# -- Paleta oscura (similar a darkly de ttkbootstrap) -------------------------
DARKLY = Paleta("darkly", {
    "fondo":            "#212529",
    "fondo_alt":        "#2B3035",
    "fondo_panel":      "#343A40",
    "fondo_input":      "#3B4148",
    "borde":            "#495057",
    "texto":            "#DEE2E6",
    "texto_secundario": "#ADB5BD",
    "texto_deshabilitado": "#6C757D",
    "primario":         "#375A7F",
    "primario_hover":   "#2E4D6E",
    "exito":            "#00BC8C",
    "info":             "#3498DB",
    "advertencia":      "#F39C12",
    "peligro":          "#E74C3C",
    "acento":           "#00BC8C",
    "seleccion":        "#375A7F",
    "seleccion_texto":  "#FFFFFF",
    "scrollbar":        "#495057",
    "scrollbar_hover":  "#6C757D",
    "tooltip_fondo":    "#F8F9FA",
    "tooltip_texto":    "#212529",
    "menu_fondo":       "#2B3035",
    "menu_hover":       "#375A7F",
})

# -- Paleta clara (alternativa) -----------------------------------------------
CLARO = Paleta("claro", {
    "fondo":            "#F8F9FA",
    "fondo_alt":        "#E9ECEF",
    "fondo_panel":      "#FFFFFF",
    "fondo_input":      "#FFFFFF",
    "borde":            "#CED4DA",
    "texto":            "#212529",
    "texto_secundario": "#6C757D",
    "texto_deshabilitado": "#ADB5BD",
    "primario":         "#0D6EFD",
    "primario_hover":   "#0B5ED7",
    "exito":            "#198754",
    "info":             "#0DCAF0",
    "advertencia":      "#FFC107",
    "peligro":          "#DC3545",
    "acento":           "#0D6EFD",
    "seleccion":        "#0D6EFD",
    "seleccion_texto":  "#FFFFFF",
    "scrollbar":        "#CED4DA",
    "scrollbar_hover":  "#ADB5BD",
    "tooltip_fondo":    "#212529",
    "tooltip_texto":    "#F8F9FA",
    "menu_fondo":       "#FFFFFF",
    "menu_hover":       "#0D6EFD",
})

# Registro de temas disponibles
TEMAS: Dict[str, Paleta] = {
    "darkly": DARKLY,
    "claro":  CLARO,
}


# ---------------------------------------------------------------------------
#  Generador de QSS
# ---------------------------------------------------------------------------
def generar_qss(paleta: Paleta) -> str:
    """Genera una hoja de estilos QSS completa a partir de una Paleta."""
    p = paleta
    return f"""
    /* ================================================================
       Soundvi Qt6 Theme -- {p.nombre}
       Generado automaticamente. No editar a mano (o si, no soy tu jefe).
       ================================================================ */

    /* -- Base --------------------------------------------------------- */
    QWidget {{
        background-color: {p.fondo};
        color: {p.texto};
        font-family: "Segoe UI", "Noto Sans", "DejaVu Sans", sans-serif;
        font-size: 13px;
    }}

    /* -- Ventana principal -------------------------------------------- */
    QMainWindow {{
        background-color: {p.fondo};
    }}

    QMainWindow::separator {{
        background-color: {p.borde};
        width: 2px;
        height: 2px;
    }}

    /* -- Menu bar ----------------------------------------------------- */
    QMenuBar {{
        background-color: {p.fondo_alt};
        color: {p.texto};
        border-bottom: 1px solid {p.borde};
        padding: 2px;
    }}

    QMenuBar::item:selected {{
        background-color: {p.menu_hover};
        color: {p.seleccion_texto};
        border-radius: 3px;
    }}

    QMenu {{
        background-color: {p.menu_fondo};
        color: {p.texto};
        border: 1px solid {p.borde};
        padding: 4px;
    }}

    QMenu::item:selected {{
        background-color: {p.menu_hover};
        color: {p.seleccion_texto};
        border-radius: 3px;
    }}

    QMenu::separator {{
        height: 1px;
        background-color: {p.borde};
        margin: 4px 8px;
    }}

    /* -- Toolbar ------------------------------------------------------ */
    QToolBar {{
        background-color: {p.fondo_alt};
        border-bottom: 1px solid {p.borde};
        spacing: 4px;
        padding: 2px;
    }}

    QToolButton {{
        background-color: transparent;
        color: {p.texto};
        border: 1px solid transparent;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 16px;
    }}

    QToolButton:hover {{
        background-color: {p.primario};
        color: {p.seleccion_texto};
    }}

    QToolButton:pressed {{
        background-color: {p.primario_hover};
    }}

    /* -- Dock widgets ------------------------------------------------- */
    QDockWidget {{
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
        color: {p.texto};
        font-weight: bold;
    }}

    QDockWidget::title {{
        background-color: {p.fondo_alt};
        padding: 6px;
        border: 1px solid {p.borde};
        border-bottom: 2px solid {p.acento};
    }}

    QDockWidget::close-button, QDockWidget::float-button {{
        background-color: transparent;
        border: none;
        padding: 2px;
    }}

    /* -- Tab widget --------------------------------------------------- */
    QTabWidget::pane {{
        border: 1px solid {p.borde};
        background-color: {p.fondo_panel};
    }}

    QTabBar::tab {{
        background-color: {p.fondo_alt};
        color: {p.texto_secundario};
        padding: 8px 16px;
        border: 1px solid {p.borde};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        margin-right: 2px;
    }}

    QTabBar::tab:selected {{
        background-color: {p.fondo_panel};
        color: {p.texto};
        border-bottom: 2px solid {p.acento};
    }}

    QTabBar::tab:hover:!selected {{
        background-color: {p.fondo_panel};
    }}

    /* -- Botones ------------------------------------------------------ */
    QPushButton {{
        background-color: {p.primario};
        color: {p.seleccion_texto};
        border: none;
        border-radius: 4px;
        padding: 6px 16px;
        font-weight: bold;
    }}

    QPushButton:hover {{
        background-color: {p.primario_hover};
    }}

    QPushButton:pressed {{
        background-color: {p.fondo_alt};
    }}

    QPushButton:disabled {{
        background-color: {p.borde};
        color: {p.texto_deshabilitado};
    }}

    QPushButton[flat="true"] {{
        background-color: transparent;
        color: {p.texto};
        border: 1px solid {p.borde};
    }}

    /* -- Inputs ------------------------------------------------------- */
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
        background-color: {p.fondo_input};
        color: {p.texto};
        border: 1px solid {p.borde};
        border-radius: 4px;
        padding: 4px 8px;
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {p.acento};
    }}

    /* -- ComboBox ----------------------------------------------------- */
    QComboBox {{
        background-color: {p.fondo_input};
        color: {p.texto};
        border: 1px solid {p.borde};
        border-radius: 4px;
        padding: 4px 8px;
    }}

    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {p.menu_fondo};
        color: {p.texto};
        border: 1px solid {p.borde};
        selection-background-color: {p.seleccion};
        selection-color: {p.seleccion_texto};
    }}

    /* -- Slider ------------------------------------------------------- */
    QSlider::groove:horizontal {{
        height: 6px;
        background: {p.borde};
        border-radius: 3px;
    }}

    QSlider::handle:horizontal {{
        background: {p.acento};
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }}

    QSlider::handle:horizontal:hover {{
        background: {p.primario};
    }}

    QSlider::sub-page:horizontal {{
        background: {p.acento};
        border-radius: 3px;
    }}

    /* -- ScrollBars --------------------------------------------------- */
    QScrollBar:vertical {{
        background: {p.fondo};
        width: 10px;
        border: none;
    }}

    QScrollBar::handle:vertical {{
        background: {p.scrollbar};
        border-radius: 5px;
        min-height: 30px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {p.scrollbar_hover};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background: {p.fondo};
        height: 10px;
        border: none;
    }}

    QScrollBar::handle:horizontal {{
        background: {p.scrollbar};
        border-radius: 5px;
        min-width: 30px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background: {p.scrollbar_hover};
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* -- GroupBox ------------------------------------------------------ */
    QGroupBox {{
        border: 1px solid {p.borde};
        border-radius: 4px;
        margin-top: 12px;
        padding-top: 16px;
        font-weight: bold;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 2px 8px;
        color: {p.acento};
    }}

    /* -- CheckBox / RadioButton --------------------------------------- */
    QCheckBox, QRadioButton {{
        spacing: 8px;
        color: {p.texto};
    }}

    QCheckBox::indicator, QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border: 2px solid {p.borde};
        border-radius: 3px;
        background-color: {p.fondo_input};
    }}

    QRadioButton::indicator {{
        border-radius: 9px;
    }}

    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background-color: {p.acento};
        border-color: {p.acento};
    }}

    /* -- ProgressBar -------------------------------------------------- */
    QProgressBar {{
        background-color: {p.fondo_input};
        border: 1px solid {p.borde};
        border-radius: 4px;
        text-align: center;
        color: {p.texto};
        height: 20px;
    }}

    QProgressBar::chunk {{
        background-color: {p.acento};
        border-radius: 3px;
    }}

    /* -- StatusBar ---------------------------------------------------- */
    QStatusBar {{
        background-color: {p.fondo_alt};
        color: {p.texto_secundario};
        border-top: 1px solid {p.borde};
    }}

    /* -- Label -------------------------------------------------------- */
    QLabel {{
        background-color: transparent;
        color: {p.texto};
    }}

    QLabel[heading="true"] {{
        font-size: 15px;
        font-weight: bold;
        color: {p.acento};
    }}

    /* -- Frame -------------------------------------------------------- */
    QFrame[panel="true"] {{
        background-color: {p.fondo_panel};
        border: 1px solid {p.borde};
        border-radius: 4px;
    }}

    /* -- ToolTip ------------------------------------------------------ */
    QToolTip {{
        background-color: {p.tooltip_fondo};
        color: {p.tooltip_texto};
        border: 1px solid {p.borde};
        padding: 4px;
        border-radius: 3px;
    }}

    /* -- Splitter ----------------------------------------------------- */
    QSplitter::handle {{
        background-color: {p.borde};
    }}

    QSplitter::handle:horizontal {{
        width: 3px;
    }}

    QSplitter::handle:vertical {{
        height: 3px;
    }}

    /* -- TreeView / ListView ------------------------------------------ */
    QTreeView, QListView, QTableView {{
        background-color: {p.fondo_panel};
        color: {p.texto};
        border: 1px solid {p.borde};
        alternate-background-color: {p.fondo_alt};
    }}

    QTreeView::item:selected, QListView::item:selected, QTableView::item:selected {{
        background-color: {p.seleccion};
        color: {p.seleccion_texto};
    }}

    QHeaderView::section {{
        background-color: {p.fondo_alt};
        color: {p.texto};
        border: 1px solid {p.borde};
        padding: 4px;
        font-weight: bold;
    }}
    """


# ---------------------------------------------------------------------------
#  Administrador de temas
# ---------------------------------------------------------------------------
class AdministradorTemas:
    """Gestiona el tema activo y permite cambiar en caliente."""

    _instancia: Optional["AdministradorTemas"] = None
    _tema_actual: str = "darkly"

    def __new__(cls):
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
        return cls._instancia

    @property
    def tema_actual(self) -> str:
        return self._tema_actual

    @property
    def paleta(self) -> Paleta:
        return TEMAS.get(self._tema_actual, DARKLY)

    def aplicar_tema(self, nombre: str, app: Optional[QApplication] = None):
        """Cambia el tema activo y aplica el QSS a la aplicacion."""
        if nombre not in TEMAS:
            nombre = "darkly"
        self._tema_actual = nombre
        paleta = TEMAS[nombre]
        qss = generar_qss(paleta)

        objetivo = app or QApplication.instance()
        if objetivo:
            objetivo.setStyleSheet(qss)
            # Tambien configurar la QPalette nativa para widgets que no respeten QSS
            qp = QPalette()
            qp.setColor(QPalette.ColorRole.Window, QColor(paleta.fondo))
            qp.setColor(QPalette.ColorRole.WindowText, QColor(paleta.texto))
            qp.setColor(QPalette.ColorRole.Base, QColor(paleta.fondo_input))
            qp.setColor(QPalette.ColorRole.AlternateBase, QColor(paleta.fondo_alt))
            qp.setColor(QPalette.ColorRole.ToolTipBase, QColor(paleta.tooltip_fondo))
            qp.setColor(QPalette.ColorRole.ToolTipText, QColor(paleta.tooltip_texto))
            qp.setColor(QPalette.ColorRole.Text, QColor(paleta.texto))
            qp.setColor(QPalette.ColorRole.Button, QColor(paleta.primario))
            qp.setColor(QPalette.ColorRole.ButtonText, QColor(paleta.seleccion_texto))
            qp.setColor(QPalette.ColorRole.Highlight, QColor(paleta.seleccion))
            qp.setColor(QPalette.ColorRole.HighlightedText, QColor(paleta.seleccion_texto))
            objetivo.setPalette(qp)

    def listar_temas(self) -> list:
        return list(TEMAS.keys())

    def aplicar_tema_desde_preferencias(self, app: Optional[QApplication] = None):
        """
        Lee el tema guardado en user_preferences.json y lo aplica.
        Si no hay preferencia guardada, usa 'darkly'.
        """
        from gui.qt6.profile_selector import obtener_tema_guardado
        tema = obtener_tema_guardado()
        self.aplicar_tema(tema, app)
