# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- Sidebar de modulos categorizados.

Panel lateral con QTreeWidget que muestra los modulos organizados
por tipo y categoria, con busqueda, filtrado, drag & drop y
menu contextual. Respeta el perfil activo (ProfileManager).
"""

from __future__ import annotations

import os
import sys
import logging
from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QLineEdit, QMenu,
    QFrame, QSizePolicy, QAbstractItemView, QToolTip
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QPoint
from PyQt6.QtGui import QFont, QDrag, QAction, QCursor, QPainter, QPen, QColor, QPixmap

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _RAIZ) if _RAIZ not in sys.path else None

from gui.qt6.base import ICONOS_UNICODE, PanelBase
from core.profiles import ProfileManager

log = logging.getLogger("soundvi.qt6.sidebar")

# Iconos Unicode para tipos de modulo (sin emojis)
_ICONOS_TIPO: Dict[str, str] = {
    "video":   "▣",   # U+25A3 White square containing black small square
    "audio":   "♫",   # U+266B Beamed eighth notes
    "text":    "℻",   # U+213B Facsimile sign
    "utility": "≡",   # U+2699 Gear
    "export":  "➡",   # U+27A1 Rightwards arrow
}

_ICONOS_CATEGORIA: Dict[str, str] = {
    "effects":        "★",   # U+2728 Sparkles (aceptable)
    "filters":        "⧉",   # U+29D6 Bowtie with left half black
    "generators":     "▦",   # U+25A6 Square with orthogonal crosshatch fill
    "transitions":    "⇄",   # U+21C4 Left right arrow
    "visualization":  "≡",   # U+2261 Identical to
    "analysis":       "∴",   # U+2234 Therefore
    "enhancement":    "↑",   # U+2191 Upwards arrow
    "subtitles":      "≣",   # U+2263 Strictly equivalent to
    "titles":         "\u2160",
    "captions":       "\u275D",
    "lower-thirds":   "\u2581",
    "watermark":      "\u2756",
    "timestamp":      "\u231A",
    "metadata":       "ℹ",
    "social":         "\u2302",
    "streaming":      "▶",
    "archive":        "\u2B07",
    "optimization":   "\u21BB",
}


class SidebarWidget(QFrame):
    """
    Sidebar de modulos categorizados para Soundvi Qt6.

    Muestra un arbol expandible con tipos y categorias de modulos,
    permite buscar, filtrar, hacer drag & drop y doble click
    para aplicar modulos al clip seleccionado.
    """

    # Senales
    modulo_seleccionado = pyqtSignal(str)        # type_key del modulo
    modulo_doble_click = pyqtSignal(str)         # type_key para aplicar a clip
    modulo_drag_started = pyqtSignal(str)        # type_key al iniciar drag
    favorito_toggled = pyqtSignal(str, bool)     # type_key, es_favorito

    def __init__(self, profile_manager: ProfileManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._pm = profile_manager
        self._favoritos: set = set()
        self._module_manager = None  # Se asigna externamente si esta disponible

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._construir_ui()
        self._poblar_arbol()

    # -- Construccion de UI ----------------------------------------------------

    def _construir_ui(self):
        """Construye la interfaz del sidebar."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Titulo
        titulo = QLabel("\u29C9  Modulos")
        titulo.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(titulo)

        # Barra de busqueda
        self._barra_busqueda = QLineEdit()
        self._barra_busqueda.setPlaceholderText("\u2315 Buscar modulos...")
        self._barra_busqueda.setClearButtonEnabled(True)
        self._barra_busqueda.textChanged.connect(self._filtrar_modulos)
        layout.addWidget(self._barra_busqueda)

        # Arbol de modulos
        self._arbol = QTreeWidget()
        self._arbol.setHeaderHidden(True)
        self._arbol.setAnimated(True)
        self._arbol.setIndentation(16)
        self._arbol.setRootIsDecorated(True)
        self._arbol.setAlternatingRowColors(True)
        self._arbol.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._arbol.setDragEnabled(True)
        self._arbol.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self._arbol.setStyleSheet("""
            QTreeWidget {
                background-color: #2B3035;
                border: 1px solid #495057;
                border-radius: 4px;
                font-size: 12px;
            }
            QTreeWidget::item {
                padding: 4px 2px;
                border-bottom: 1px solid #343A40;
            }
            QTreeWidget::item:hover {
                background-color: #343A40;
            }
            QTreeWidget::item:selected {
                background-color: #375A7F;
                color: #FFFFFF;
            }
        """)

        # Habilitar drag & drop de módulos al timeline
        self._arbol.startDrag = self._start_module_drag

        # Conexiones del arbol
        self._arbol.itemClicked.connect(self._on_item_clicked)
        self._arbol.itemDoubleClicked.connect(self._on_item_doble_click)
        self._arbol.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._arbol.customContextMenuRequested.connect(self._on_menu_contextual)

        layout.addWidget(self._arbol)

        # Barra inferior con info
        self._lbl_info = QLabel("0 modulos disponibles")
        self._lbl_info.setStyleSheet("color: #6C757D; font-size: 11px; padding: 2px;")
        layout.addWidget(self._lbl_info)

    # -- Poblado del arbol -----------------------------------------------------

    def _poblar_arbol(self):
        """Puebla el arbol con los modulos disponibles segun perfil."""
        self._arbol.clear()
        total_modulos = 0

        try:
            from modules.core.registry import MODULE_TYPES
            tipos = self._pm.filtrar_tipos_modulo(MODULE_TYPES)
        except ImportError:
            tipos = {}

        # Intentar cargar modulos categorizados del manager
        modulos_por_tipo = {}
        try:
            from modules.core.manager import CategorizedModuleManager
            if self._module_manager is None:
                self._module_manager = CategorizedModuleManager()
            modulos_por_tipo = self._module_manager.get_module_types_by_category()
        except Exception as e:
            log.warning("No se pudo cargar CategorizedModuleManager: %s", e)

        for tipo_clave, tipo_info in tipos.items():
            icono = _ICONOS_TIPO.get(tipo_clave, "\u29C9")
            nombre = tipo_info.get("name", tipo_clave.capitalize())
            desc = tipo_info.get("description", "")

            # Nodo raiz del tipo
            item_tipo = QTreeWidgetItem(self._arbol)
            item_tipo.setText(0, f"{icono}  {nombre}")
            item_tipo.setToolTip(0, desc)
            item_tipo.setFont(0, QFont("Segoe UI", 11, QFont.Weight.Bold))
            item_tipo.setData(0, Qt.ItemDataRole.UserRole, {"tipo": "categoria_raiz", "clave": tipo_clave})
            item_tipo.setExpanded(True)

            # Subcategorias con modulos reales
            categorias_tipo = modulos_por_tipo.get(tipo_clave, {})
            categorias_definidas = tipo_info.get("categories", [])

            for cat in categorias_definidas:
                modulos_cat = categorias_tipo.get(cat, [])
                if not modulos_cat:
                    continue  # No mostrar categorias vacias

                icono_cat = _ICONOS_CATEGORIA.get(cat, "\u2022")
                item_cat = QTreeWidgetItem(item_tipo)
                item_cat.setText(0, f"  {icono_cat}  {cat.capitalize()} ({len(modulos_cat)})")
                item_cat.setToolTip(0, f"Categoria: {cat} -- {len(modulos_cat)} modulos")
                item_cat.setData(0, Qt.ItemDataRole.UserRole, {"tipo": "categoria", "clave": f"{tipo_clave}/{cat}"})
                item_cat.setFont(0, QFont("Segoe UI", 10))

                # Modulos individuales
                for mod_key in modulos_cat:
                    item_mod = QTreeWidgetItem(item_cat)
                    # Nombre legible del modulo
                    nombre_mod = mod_key.replace("_module", "").replace("_", " ").title()
                    es_fav = mod_key in self._favoritos
                    prefijo_fav = "\u2605 " if es_fav else ""
                    item_mod.setText(0, f"    {prefijo_fav}{nombre_mod}")

                    # Obtener clase para tooltip
                    tooltip = f"Modulo: {mod_key}\nTipo: {tipo_clave}\nCategoria: {cat}"
                    if self._module_manager:
                        tipos_reg = self._module_manager._module_types
                        if mod_key in tipos_reg:
                            cls = tipos_reg[mod_key]
                            tags = getattr(cls, "module_tags", [])
                            if tags:
                                tooltip += f"\nTags: {', '.join(tags)}"

                    item_mod.setToolTip(0, tooltip)
                    item_mod.setData(0, Qt.ItemDataRole.UserRole, {"tipo": "modulo", "clave": mod_key})
                    total_modulos += 1

        self._lbl_info.setText(f"{total_modulos} modulos disponibles")

    # -- Busqueda / filtrado ---------------------------------------------------

    def _filtrar_modulos(self, texto: str):
        """Filtra el arbol segun el texto de busqueda."""
        texto = texto.strip().lower()

        def _filtrar_item(item: QTreeWidgetItem) -> bool:
            """Retorna True si el item o alguno de sus hijos coincide."""
            datos = item.data(0, Qt.ItemDataRole.UserRole)
            if datos and datos.get("tipo") == "modulo":
                coincide = texto in item.text(0).lower() or texto in item.toolTip(0).lower()
                item.setHidden(not coincide)
                return coincide

            # Para nodos padre: mostrar si algun hijo coincide
            alguno_visible = False
            for i in range(item.childCount()):
                hijo_visible = _filtrar_item(item.child(i))
                if hijo_visible:
                    alguno_visible = True

            item.setHidden(not alguno_visible and bool(texto))
            if alguno_visible:
                item.setExpanded(True)
            return alguno_visible

        if not texto:
            # Sin filtro: mostrar todo
            for i in range(self._arbol.topLevelItemCount()):
                item = self._arbol.topLevelItem(i)
                self._mostrar_recursivo(item)
            return

        for i in range(self._arbol.topLevelItemCount()):
            _filtrar_item(self._arbol.topLevelItem(i))

    def _mostrar_recursivo(self, item: QTreeWidgetItem):
        """Muestra un item y todos sus hijos."""
        item.setHidden(False)
        for i in range(item.childCount()):
            self._mostrar_recursivo(item.child(i))

    # -- Eventos del arbol -----------------------------------------------------

    def _on_item_clicked(self, item: QTreeWidgetItem, columna: int):
        """Maneja click en un item del arbol."""
        datos = item.data(0, Qt.ItemDataRole.UserRole)
        if datos and datos.get("tipo") == "modulo":
            self.modulo_seleccionado.emit(datos["clave"])

    def _on_item_doble_click(self, item: QTreeWidgetItem, columna: int):
        """Maneja doble click para aplicar modulo a clip seleccionado."""
        datos = item.data(0, Qt.ItemDataRole.UserRole)
        if datos and datos.get("tipo") == "modulo":
            self.modulo_doble_click.emit(datos["clave"])
            log.info("Doble click en modulo: %s", datos["clave"])

    def _on_menu_contextual(self, pos: QPoint):
        """Muestra menu contextual para modulos."""
        item = self._arbol.itemAt(pos)
        if item is None:
            return

        datos = item.data(0, Qt.ItemDataRole.UserRole)
        if not datos or datos.get("tipo") != "modulo":
            return

        clave = datos["clave"]
        menu = QMenu(self)

        # Accion: Aplicar a clip
        act_aplicar = QAction("▶  Aplicar a clip seleccionado", self)
        act_aplicar.triggered.connect(lambda: self.modulo_doble_click.emit(clave))
        menu.addAction(act_aplicar)

        menu.addSeparator()

        # Accion: Favorito
        es_fav = clave in self._favoritos
        txt_fav = "\u2606  Quitar de favoritos" if es_fav else "\u2605  Agregar a favoritos"
        act_fav = QAction(txt_fav, self)
        act_fav.triggered.connect(lambda: self._toggle_favorito(clave, item))
        menu.addAction(act_fav)

        menu.addSeparator()

        # Accion: Informacion
        act_info = QAction("ℹ  Informacion del modulo", self)
        act_info.triggered.connect(lambda: self._mostrar_info(clave))
        menu.addAction(act_info)

        menu.exec(self._arbol.viewport().mapToGlobal(pos))

    def _toggle_favorito(self, clave: str, item: QTreeWidgetItem):
        """Alterna el estado de favorito de un modulo."""
        if clave in self._favoritos:
            self._favoritos.discard(clave)
            es_fav = False
        else:
            self._favoritos.add(clave)
            es_fav = True

        # Actualizar texto del item
        nombre_mod = clave.replace("_module", "").replace("_", " ").title()
        prefijo = "\u2605 " if es_fav else ""
        item.setText(0, f"    {prefijo}{nombre_mod}")

        self.favorito_toggled.emit(clave, es_fav)

    def _mostrar_info(self, clave: str):
        """Muestra un tooltip con informacion detallada del modulo."""
        info = f"Modulo: {clave}"
        if self._module_manager and clave in self._module_manager._module_types:
            cls = self._module_manager._module_types[clave]
            info += f"\nClase: {cls.__name__}"
            info += f"\nTipo: {getattr(cls, 'module_type', '?')}"
            info += f"\nCategoria: {getattr(cls, 'module_category', '?')}"
            tags = getattr(cls, 'module_tags', [])
            if tags:
                info += f"\nTags: {', '.join(tags)}"

        QToolTip.showText(QCursor.pos(), info, self)

    # -- Drag & Drop de módulos al timeline ------------------------------------

    def _start_module_drag(self, supported_actions):
        """Inicia un drag de módulo desde el sidebar al timeline."""
        item = self._arbol.currentItem()
        if item is None:
            return

        datos = item.data(0, Qt.ItemDataRole.UserRole)
        if not datos or datos.get("tipo") != "modulo":
            return

        clave = datos["clave"]
        nombre = clave.replace("_module", "").replace("_", " ").title()

        drag = QDrag(self._arbol)
        mime = QMimeData()
        mime.setText(f"module:{clave}")
        drag.setMimeData(mime)

        # Crear pixmap de arrastre visual
        pixmap = QPixmap(120, 36)
        pixmap.fill(QColor("#2B3035"))
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor("#9B59B6"), 2))
        painter.drawRoundedRect(1, 1, 118, 34, 4, 4)
        painter.setPen(QPen(QColor("#DEE2E6")))
        painter.setFont(QFont("Segoe UI", 9))
        text = nombre[:16] if len(nombre) > 16 else nombre
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, f"⚡ {text}")
        painter.end()
        drag.setPixmap(pixmap)

        self.modulo_drag_started.emit(clave)
        drag.exec(Qt.DropAction.CopyAction)

    # -- API publica -----------------------------------------------------------

    def refrescar(self):
        """Refresca el arbol de modulos (ej. al cambiar perfil)."""
        self._poblar_arbol()

    def set_module_manager(self, manager):
        """Asigna el CategorizedModuleManager externo."""
        self._module_manager = manager
        self._poblar_arbol()

    def get_favoritos(self) -> set:
        """Retorna el conjunto de modulos marcados como favoritos."""
        return set(self._favoritos)
