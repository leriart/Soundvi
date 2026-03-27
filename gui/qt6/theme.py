# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- Sistema de temas mejorado.

Paletas de colores optimizadas para mejor contraste y usabilidad.
Incluye temas: darkly (oscuro refinado), claro, midnight (azul profundo),
forest (verde naturaleza). Permite cambiar de tema en caliente sin
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


# -- Paleta oscura mejorada (contraste optimizado) -------------------------
DARKLY = Paleta("darkly", {
    "fondo":            "#1a1d23",
    "fondo_alt":        "#22272e",
    "fondo_panel":      "#2d333b",
    "fondo_input":      "#353b45",
    "borde":            "#444c56",
    "texto":            "#e6edf3",
    "texto_secundario": "#8b949e",
    "texto_deshabilitado": "#555d65",
    "primario":         "#2f81f7",
    "primario_hover":   "#1f6feb",
    "exito":            "#3fb950",
    "info":             "#58a6ff",
    "advertencia":      "#d29922",
    "peligro":          "#f85149",
    "acento":           "#3fb950",
    "seleccion":        "#264f78",
    "seleccion_texto":  "#ffffff",
    "scrollbar":        "#3b424a",
    "scrollbar_hover":  "#555d65",
    "tooltip_fondo":    "#2d333b",
    "tooltip_texto":    "#e6edf3",
    "menu_fondo":       "#22272e",
    "menu_hover":       "#2f81f7",
    "header_fondo":     "#161b22",
    "accent_glow":      "#3fb95040",
})

# -- Paleta clara mejorada -------------------------------------------------
CLARO = Paleta("claro", {
    "fondo":            "#ffffff",
    "fondo_alt":        "#f6f8fa",
    "fondo_panel":      "#ffffff",
    "fondo_input":      "#f6f8fa",
    "borde":            "#d0d7de",
    "texto":            "#1f2328",
    "texto_secundario": "#656d76",
    "texto_deshabilitado": "#8c959f",
    "primario":         "#0969da",
    "primario_hover":   "#0550ae",
    "exito":            "#1a7f37",
    "info":             "#0969da",
    "advertencia":      "#9a6700",
    "peligro":          "#cf222e",
    "acento":           "#0969da",
    "seleccion":        "#0969da",
    "seleccion_texto":  "#ffffff",
    "scrollbar":        "#d0d7de",
    "scrollbar_hover":  "#8c959f",
    "tooltip_fondo":    "#1f2328",
    "tooltip_texto":    "#f6f8fa",
    "menu_fondo":       "#ffffff",
    "menu_hover":       "#0969da",
    "header_fondo":     "#f6f8fa",
    "accent_glow":      "#0969da30",
})

# -- Paleta Midnight (azul profundo) ----------------------------------------
MIDNIGHT = Paleta("midnight", {
    "fondo":            "#0d1117",
    "fondo_alt":        "#161b22",
    "fondo_panel":      "#1c2128",
    "fondo_input":      "#21262d",
    "borde":            "#30363d",
    "texto":            "#c9d1d9",
    "texto_secundario": "#8b949e",
    "texto_deshabilitado": "#484f58",
    "primario":         "#58a6ff",
    "primario_hover":   "#388bfd",
    "exito":            "#56d364",
    "info":             "#79c0ff",
    "advertencia":      "#e3b341",
    "peligro":          "#ff7b72",
    "acento":           "#58a6ff",
    "seleccion":        "#1f3a5f",
    "seleccion_texto":  "#ffffff",
    "scrollbar":        "#21262d",
    "scrollbar_hover":  "#30363d",
    "tooltip_fondo":    "#1c2128",
    "tooltip_texto":    "#c9d1d9",
    "menu_fondo":       "#161b22",
    "menu_hover":       "#58a6ff",
    "header_fondo":     "#0d1117",
    "accent_glow":      "#58a6ff30",
})

# -- Paleta Forest (verde naturaleza) ---------------------------------------
FOREST = Paleta("forest", {
    "fondo":            "#1a2119",
    "fondo_alt":        "#212b20",
    "fondo_panel":      "#283428",
    "fondo_input":      "#2e3b2d",
    "borde":            "#3d4f3c",
    "texto":            "#d4e8d0",
    "texto_secundario": "#8ba888",
    "texto_deshabilitado": "#556653",
    "primario":         "#4caf50",
    "primario_hover":   "#388e3c",
    "exito":            "#66bb6a",
    "info":             "#42a5f5",
    "advertencia":      "#ffa726",
    "peligro":          "#ef5350",
    "acento":           "#81c784",
    "seleccion":        "#2e6b30",
    "seleccion_texto":  "#ffffff",
    "scrollbar":        "#2e3b2d",
    "scrollbar_hover":  "#3d4f3c",
    "tooltip_fondo":    "#283428",
    "tooltip_texto":    "#d4e8d0",
    "menu_fondo":       "#212b20",
    "menu_hover":       "#4caf50",
    "header_fondo":     "#151c14",
    "accent_glow":      "#81c78430",
})

# Registro de temas disponibles
TEMAS: Dict[str, Paleta] = {
    "darkly":   DARKLY,
    "claro":    CLARO,
    "midnight": MIDNIGHT,
    "forest":   FOREST,
}

# Nombres amigables para la UI
TEMAS_NOMBRES: Dict[str, str] = {
    "darkly":   "Oscuro",
    "claro":    "Claro",
    "midnight": "Midnight",
    "forest":   "Forest",
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
       ================================================================ */

    /* -- Base --------------------------------------------------------- */
    QWidget {{
        background-color: {p.fondo};
        color: {p.texto};
        font-family: "JetBrains Mono", "Cascadia Code", "Consolas", "Segoe UI", sans-serif;
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

    QMainWindow::separator:hover {{
        background-color: {p.acento};
    }}

    /* -- Menu bar ----------------------------------------------------- */
    QMenuBar {{
        background-color: {p.header_fondo};
        color: {p.texto};
        border-bottom: 1px solid {p.borde};
        padding: 3px 6px;
        font-size: 13px;
    }}

    QMenuBar::item {{
        padding: 4px 10px;
        border-radius: 4px;
    }}

    QMenuBar::item:selected {{
        background-color: {p.menu_hover};
        color: {p.seleccion_texto};
    }}

    QMenu {{
        background-color: {p.menu_fondo};
        color: {p.texto};
        border: 1px solid {p.borde};
        border-radius: 6px;
        padding: 6px 4px;
    }}

    QMenu::item {{
        padding: 6px 24px 6px 12px;
        border-radius: 4px;
        margin: 1px 4px;
    }}

    QMenu::item:selected {{
        background-color: {p.menu_hover};
        color: {p.seleccion_texto};
    }}

    QMenu::separator {{
        height: 1px;
        background-color: {p.borde};
        margin: 4px 12px;
    }}

    /* -- Toolbar ------------------------------------------------------ */
    QToolBar {{
        background-color: {p.header_fondo};
        border-bottom: 1px solid {p.borde};
        spacing: 4px;
        padding: 3px 6px;
    }}

    QToolButton {{
        background-color: transparent;
        color: {p.texto};
        border: 1px solid transparent;
        border-radius: 5px;
        padding: 5px 10px;
        font-size: 13px;
    }}

    QToolButton:hover {{
        background-color: {p.primario};
        color: {p.seleccion_texto};
        border: 1px solid {p.primario};
    }}

    QToolButton:pressed {{
        background-color: {p.primario_hover};
    }}

    QToolButton:disabled {{
        color: {p.texto_deshabilitado};
    }}

    /* -- Dock widgets ------------------------------------------------- */
    QDockWidget {{
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
        color: {p.texto};
        font-weight: bold;
        font-size: 12px;
    }}

    QDockWidget::title {{
        background-color: {p.header_fondo};
        padding: 7px 10px;
        border: 1px solid {p.borde};
        border-bottom: 2px solid {p.acento};
        font-size: 12px;
    }}

    QDockWidget::close-button, QDockWidget::float-button {{
        background-color: transparent;
        border: none;
        padding: 3px;
    }}

    QDockWidget::close-button:hover, QDockWidget::float-button:hover {{
        background-color: {p.fondo_panel};
        border-radius: 3px;
    }}

    /* -- Tab widget (dock tabs at bottom) ----------------------------- */
    QTabWidget::pane {{
        border: 1px solid {p.borde};
        background-color: {p.fondo_panel};
        border-radius: 0px;
    }}

    QTabBar {{
        qproperty-drawBase: 0;
    }}

    QTabBar::tab {{
        background-color: {p.fondo_alt};
        color: {p.texto_secundario};
        padding: 8px 18px;
        border: 1px solid {p.borde};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
        font-size: 12px;
        min-width: 60px;
    }}

    QTabBar::tab:selected {{
        background-color: {p.fondo_panel};
        color: {p.texto};
        border-bottom: 2px solid {p.acento};
        font-weight: bold;
    }}

    QTabBar::tab:hover:!selected {{
        background-color: {p.fondo_panel};
        color: {p.texto};
    }}

    /* -- Botones ------------------------------------------------------ */
    QPushButton {{
        background-color: {p.primario};
        color: {p.seleccion_texto};
        border: none;
        border-radius: 6px;
        padding: 7px 18px;
        font-weight: bold;
        font-size: 13px;
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

    QPushButton[flat="true"]:hover {{
        border-color: {p.acento};
        background-color: {p.accent_glow};
    }}

    /* -- Inputs ------------------------------------------------------- */
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
        background-color: {p.fondo_input};
        color: {p.texto};
        border: 1px solid {p.borde};
        border-radius: 5px;
        padding: 5px 10px;
        selection-background-color: {p.seleccion};
        selection-color: {p.seleccion_texto};
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
        border-radius: 5px;
        padding: 5px 10px;
        min-height: 20px;
    }}

    QComboBox:hover {{
        border-color: {p.acento};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {p.menu_fondo};
        color: {p.texto};
        border: 1px solid {p.borde};
        border-radius: 4px;
        selection-background-color: {p.seleccion};
        selection-color: {p.seleccion_texto};
        padding: 4px;
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
        border: 2px solid {p.fondo};
    }}

    QSlider::handle:horizontal:hover {{
        background: {p.primario};
        border: 2px solid {p.acento};
    }}

    QSlider::sub-page:horizontal {{
        background: {p.acento};
        border-radius: 3px;
    }}

    /* -- ScrollBars --------------------------------------------------- */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        border: none;
        margin: 0;
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

    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}

    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        border: none;
        margin: 0;
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

    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}

    /* -- GroupBox ------------------------------------------------------ */
    QGroupBox {{
        border: 1px solid {p.borde};
        border-radius: 6px;
        margin-top: 14px;
        padding-top: 18px;
        font-weight: bold;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 2px 10px;
        color: {p.acento};
    }}

    /* -- CheckBox / RadioButton --------------------------------------- */
    QCheckBox, QRadioButton {{
        spacing: 8px;
        color: {p.texto};
    }}

    QCheckBox::indicator, QRadioButton::indicator {{
        width: 18px;
        height: 18px;
        border: 2px solid {p.borde};
        border-radius: 4px;
        background-color: {p.fondo_input};
    }}

    QRadioButton::indicator {{
        border-radius: 10px;
    }}

    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background-color: {p.acento};
        border-color: {p.acento};
    }}

    QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
        border-color: {p.acento};
    }}

    /* -- ProgressBar -------------------------------------------------- */
    QProgressBar {{
        background-color: {p.fondo_input};
        border: 1px solid {p.borde};
        border-radius: 5px;
        text-align: center;
        color: {p.texto};
        height: 22px;
    }}

    QProgressBar::chunk {{
        background-color: {p.acento};
        border-radius: 4px;
    }}

    /* -- StatusBar ---------------------------------------------------- */
    QStatusBar {{
        background-color: {p.header_fondo};
        color: {p.texto_secundario};
        border-top: 1px solid {p.borde};
        font-size: 12px;
        padding: 2px;
    }}

    QStatusBar::item {{
        border: none;
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
        border-radius: 6px;
    }}

    /* -- ToolTip ------------------------------------------------------ */
    QToolTip {{
        background-color: {p.tooltip_fondo};
        color: {p.tooltip_texto};
        border: 1px solid {p.borde};
        padding: 6px 10px;
        border-radius: 5px;
        font-size: 12px;
    }}

    /* -- Splitter ----------------------------------------------------- */
    QSplitter::handle {{
        background-color: {p.borde};
    }}

    QSplitter::handle:hover {{
        background-color: {p.acento};
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
        border-radius: 4px;
        alternate-background-color: {p.fondo_alt};
        outline: none;
    }}

    QTreeView::item, QListView::item, QTableView::item {{
        padding: 3px 6px;
        border-radius: 3px;
    }}

    QTreeView::item:selected, QListView::item:selected, QTableView::item:selected {{
        background-color: {p.seleccion};
        color: {p.seleccion_texto};
    }}

    QTreeView::item:hover, QListView::item:hover {{
        background-color: {p.accent_glow};
    }}

    QHeaderView::section {{
        background-color: {p.header_fondo};
        color: {p.texto};
        border: 1px solid {p.borde};
        padding: 5px 8px;
        font-weight: bold;
        font-size: 12px;
    }}

    /* -- Dialog -------------------------------------------------------- */
    QDialog {{
        background-color: {p.fondo};
    }}

    /* -- MessageBox --------------------------------------------------- */
    QMessageBox {{
        background-color: {p.fondo};
    }}

    QMessageBox QPushButton {{
        min-width: 80px;
        min-height: 28px;
    }}

    /* -- Dock Tab Bar (fix z-index / visibility) ---------------------- */
    /* Asegura que las pestanas de dock widgets tabulados en la parte
       inferior siempre sean visibles y nunca queden ocultas detras
       de otros elementos al cambiar de vista (timeline, mixer, etc.) */
    QTabBar {{
        qproperty-drawBase: 0;
    }}

    QDockWidget > QTabBar {{
        background-color: {p.header_fondo};
    }}

    QMainWindow > QTabBar {{
        background-color: {p.header_fondo};
        min-height: 28px;
    }}

    QMainWindow > QTabBar::tab {{
        min-height: 24px;
        min-width: 70px;
        padding: 6px 14px;
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
            # Configurar la QPalette nativa
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
            qp.setColor(QPalette.ColorRole.PlaceholderText, QColor(paleta.texto_deshabilitado))
            objetivo.setPalette(qp)

    def listar_temas(self) -> list:
        return list(TEMAS.keys())

    def listar_temas_nombres(self) -> Dict[str, str]:
        """Retorna dict {clave: nombre_amigable}."""
        return dict(TEMAS_NOMBRES)

    def aplicar_tema_desde_preferencias(self, app: Optional[QApplication] = None):
        """Lee el tema guardado en preferencias y lo aplica."""
        try:
            from utils.config import load_user_prefs
            prefs = load_user_prefs()
            tema = prefs.get("tema", "darkly")
        except Exception:
            tema = "darkly"
        self.aplicar_tema(tema, app)
