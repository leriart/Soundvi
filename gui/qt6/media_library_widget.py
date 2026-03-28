# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- Biblioteca de Medios.

Panel que muestra los archivos multimedia del proyecto con thumbnails,
informacion de archivo, busqueda/filtrado, drag & drop al timeline,
y menu contextual. Integrado con core/project_manager.py (MediaItem).
"""

from __future__ import annotations

import os
import sys
import time
import logging
import hashlib
from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QMenu,
    QFrame, QSizePolicy, QFileDialog, QAbstractItemView,
    QToolTip, QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import (
    QFont, QPixmap, QImage, QIcon, QAction, QColor, QPainter,
    QCursor, QBrush
)

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _RAIZ) if _RAIZ not in sys.path else None

from gui.qt6.base import ICONOS_UNICODE

log = logging.getLogger("soundvi.qt6.media_library")

# Extensiones soportadas
_EXT_VIDEO = {".mp4", ".avi", ".mkv", ".mov", ".webm", ".flv", ".wmv"}
_EXT_AUDIO = {".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a", ".wma"}
_EXT_IMAGEN = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}

# Directorio de cache de thumbnails
_CACHE_DIR = os.path.join(_RAIZ, ".thumb_cache")


def _detectar_tipo(ruta: str) -> str:
    """Detecta el tipo de archivo multimedia."""
    ext = os.path.splitext(ruta)[1].lower()
    if ext in _EXT_VIDEO:
        return "video"
    elif ext in _EXT_AUDIO:
        return "audio"
    elif ext in _EXT_IMAGEN:
        return "imagen"
    return "otro"


def _formato_tamano(bytes_size: int) -> str:
    """Formatea un tamano en bytes a formato legible."""
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.1f} MB"
    return f"{bytes_size / (1024 * 1024 * 1024):.2f} GB"


def _generar_thumbnail(ruta: str, ancho: int = 120, alto: int = 80) -> Optional[QPixmap]:
    """
    Genera un thumbnail para un archivo multimedia.
    Usa cache en disco para evitar regenerar.
    """
    tipo = _detectar_tipo(ruta)

    # Verificar cache
    os.makedirs(_CACHE_DIR, exist_ok=True)
    hash_ruta = hashlib.md5(ruta.encode()).hexdigest()
    cache_path = os.path.join(_CACHE_DIR, f"{hash_ruta}.png")

    if os.path.isfile(cache_path):
        pix = QPixmap(cache_path)
        if not pix.isNull():
            return pix

    pixmap = None

    if tipo == "imagen":
        # Cargar imagen directamente
        pix = QPixmap(ruta)
        if not pix.isNull():
            pixmap = pix.scaled(ancho, alto, Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation)

    elif tipo == "video":
        # Intentar extraer primer frame con OpenCV
        try:
            import cv2
            cap = cv2.VideoCapture(ruta)
            ret, frame = cap.read()
            cap.release()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame.shape
                img = QImage(frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
                pix = QPixmap.fromImage(img)
                pixmap = pix.scaled(ancho, alto, Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)
        except ImportError:
            pass

    elif tipo == "audio":
        # Generar un icono de onda simplificado
        pixmap = _generar_icono_audio(ancho, alto)

    # Placeholder si no se pudo generar
    if pixmap is None:
        pixmap = _generar_placeholder(ancho, alto, tipo)

    # Guardar en cache
    if pixmap and not pixmap.isNull():
        pixmap.save(cache_path, "PNG")

    return pixmap


def _generar_icono_audio(ancho: int, alto: int) -> QPixmap:
    """Genera un icono placeholder para archivos de audio."""
    pixmap = QPixmap(ancho, alto)
    pixmap.fill(QColor("#2B3035"))
    painter = QPainter(pixmap)
    painter.setPen(QColor("#00BC8C"))
    # Dibujar barras simples de waveform
    import random
    random.seed(42)
    bw = max(2, ancho // 30)
    for i in range(0, ancho, bw + 1):
        h = random.randint(alto // 6, alto - 10)
        y = (alto - h) // 2
        painter.fillRect(i, y, bw, h, QColor("#00BC8C"))
    # Icono central
    painter.setFont(QFont("Segoe UI", 20))
    painter.setPen(QColor("#DEE2E6"))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "AUD")
    painter.end()
    return pixmap


def _generar_placeholder(ancho: int, alto: int, tipo: str) -> QPixmap:
    """Genera un placeholder para tipos desconocidos."""
    pixmap = QPixmap(ancho, alto)
    pixmap.fill(QColor("#343A40"))
    painter = QPainter(pixmap)
    painter.setPen(QColor("#6C757D"))
    iconos = {"video": "VID", "audio": "AUD", "imagen": "IMG", "otro": "???"}
    painter.setFont(QFont("Segoe UI", 18))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, iconos.get(tipo, "OTRO"))
    painter.end()
    return pixmap


class MediaListWidget(QListWidget):
    """QListWidget personalizado que exporta URLs para drag & drop."""
    def mimeData(self, items):
        mime = super().mimeData(items)
        from PyQt6.QtCore import QUrl
        urls = []
        for item in items:
            ruta = item.data(Qt.ItemDataRole.UserRole)
            if ruta:
                urls.append(QUrl.fromLocalFile(ruta))
        if urls:
            mime.setUrls(urls)
        return mime

class MediaLibraryWidget(QFrame):
    """
    Biblioteca de medios con thumbnails, busqueda, filtrado,
    drag & drop y menu contextual.
    Integrado con ProjectManager para guardar/cargar proyectos.
    """

    # Senales
    archivo_importado = pyqtSignal(str)      # ruta del archivo importado
    archivo_seleccionado = pyqtSignal(str)   # ruta del archivo seleccionado
    archivo_drag_started = pyqtSignal(str)   # ruta al iniciar drag al timeline
    media_library_changed = pyqtSignal()     # cuando cambia la biblioteca

    def __init__(self, project_manager=None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._project_manager = project_manager
        self._archivos: List[Dict[str, Any]] = []  # lista de {path, name, type, size, ...}
        self._construir_ui()
        
        # Cargar archivos del project manager si está disponible
        if self._project_manager and hasattr(self._project_manager, 'media_library'):
            self._cargar_desde_project_manager()

    # -- Construccion de UI ----------------------------------------------------

    def _construir_ui(self):
        """Construye la interfaz de la biblioteca de medios."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Titulo
        titulo = QLabel(f"{ICONOS_UNICODE['open']}  Biblioteca de Medios")
        titulo.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(titulo)

        # Barra superior: busqueda + filtro + importar
        barra_sup = QHBoxLayout()
        barra_sup.setSpacing(4)

        self._busqueda = QLineEdit()
        self._busqueda.setPlaceholderText("\u2315 Buscar...")
        self._busqueda.setClearButtonEnabled(True)
        self._busqueda.textChanged.connect(self._filtrar)
        barra_sup.addWidget(self._busqueda, 3)

        self._filtro_tipo = QComboBox()
        self._filtro_tipo.addItems(["Todos", "Video", "Audio", "Imagen"])
        self._filtro_tipo.currentTextChanged.connect(self._filtrar)
        barra_sup.addWidget(self._filtro_tipo, 1)

        btn_importar = QPushButton(f"{ICONOS_UNICODE['open']}  Importar")
        btn_importar.setToolTip("Importar archivos multimedia al proyecto")
        btn_importar.clicked.connect(self._importar_archivos)
        barra_sup.addWidget(btn_importar, 1)

        layout.addLayout(barra_sup)

        # Lista de archivos con thumbnails
        self._lista = MediaListWidget()
        self._lista.setViewMode(QListWidget.ViewMode.IconMode)
        self._lista.setIconSize(QSize(120, 80))
        self._lista.setGridSize(QSize(140, 110))
        self._lista.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._lista.setSpacing(6)
        self._lista.setWrapping(True)
        self._lista.setWordWrap(True)
        # FIX BUG 1: Evitar que los items se muevan libremente fuera de la
        # cuadrícula.  Movement.Static mantiene los items anclados al grid;
        # UniformItemSizes garantiza tamaño homogéneo para un layout correcto.
        self._lista.setMovement(QListWidget.Movement.Static)
        self._lista.setUniformItemSizes(True)
        self._lista.setDragEnabled(True)
        self._lista.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._lista.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._lista.customContextMenuRequested.connect(self._on_menu_contextual)
        self._lista.itemClicked.connect(self._on_item_clicked)
        self._lista.itemDoubleClicked.connect(self._on_item_doble_click)
        self._lista.setStyleSheet("""
            QListWidget {
                background-color: #2B3035;
                border: 1px solid #495057;
                border-radius: 4px;
            }
            QListWidget::item {
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 4px;
            }
            QListWidget::item:hover {
                border-color: #495057;
                background-color: #343A40;
            }
            QListWidget::item:selected {
                border-color: #00BC8C;
                background-color: #375A7F;
            }
        """)
        layout.addWidget(self._lista)

        # Barra inferior: info
        self._lbl_info = QLabel("Sin archivos importados")
        self._lbl_info.setStyleSheet("color: #6C757D; font-size: 11px; padding: 2px;")
        layout.addWidget(self._lbl_info)

    # -- Importacion de archivos -----------------------------------------------

    def _importar_archivos(self):
        """Abre dialogo para importar archivos multimedia."""
        archivos, _ = QFileDialog.getOpenFileNames(
            self, "Importar medios", "",
            "Media (*.mp4 *.avi *.mkv *.mov *.mp3 *.wav *.flac *.ogg "
            "*.png *.jpg *.jpeg *.gif *.bmp *.webm *.webp);;Todos (*)"
        )
        if archivos:
            for ruta in archivos:
                self._agregar_archivo(ruta)

    def _agregar_archivo(self, ruta: str):
        """Agrega un archivo a la biblioteca."""
        if not os.path.isfile(ruta):
            return

        # Evitar duplicados
        for arch in self._archivos:
            if arch["path"] == ruta:
                return

        nombre = os.path.basename(ruta)
        tipo = _detectar_tipo(ruta)
        tamano = os.path.getsize(ruta)

        info = {
            "path": ruta,
            "name": nombre,
            "type": tipo,
            "size": tamano,
            "added_at": time.time(),
        }
        self._archivos.append(info)

        # Generar thumbnail y agregar a la lista
        thumb = _generar_thumbnail(ruta)
        item = QListWidgetItem()
        item.setText(nombre[:20])
        if thumb:
            item.setIcon(QIcon(thumb))

        tooltip = (
            f"Nombre: {nombre}\n"
            f"Tipo: {tipo}\n"
            f"Tamano: {_formato_tamano(tamano)}\n"
            f"Ruta: {ruta}"
        )
        item.setToolTip(tooltip)
        item.setData(Qt.ItemDataRole.UserRole, ruta)
        self._lista.addItem(item)

        self.archivo_importado.emit(ruta)
        self._actualizar_info()

    def _agregar_item_a_lista(self, archivo_info: dict):
        """Agrega un item a la lista desde un diccionario de información."""
        ruta = archivo_info.get("path", "")
        nombre = archivo_info.get("name", os.path.basename(ruta))
        tipo = archivo_info.get("type", _detectar_tipo(ruta))
        
        # Generar thumbnail y agregar a la lista
        thumb = _generar_thumbnail(ruta) if ruta and os.path.isfile(ruta) else None
        item = QListWidgetItem()
        item.setText(nombre[:20])
        if thumb:
            item.setIcon(QIcon(thumb))

        tooltip = (
            f"Nombre: {nombre}\n"
            f"Tipo: {tipo}\n"
            f"Ruta: {ruta}"
        )
        item.setToolTip(tooltip)
        item.setData(Qt.ItemDataRole.UserRole, ruta)
        self._lista.addItem(item)
        
        self.archivo_importado.emit(ruta)

    def importar_desde_media_item(self, media_item):
        """Importa desde un objeto MediaItem del ProjectManager."""
        if hasattr(media_item, "path"):
            self._agregar_archivo(media_item.path)

    # -- Filtrado --------------------------------------------------------------

    def _filtrar(self):
        """Filtra los items de la lista segun busqueda y tipo."""
        texto = self._busqueda.text().strip().lower()
        tipo_filtro = self._filtro_tipo.currentText().lower()

        for i in range(self._lista.count()):
            item = self._lista.item(i)
            ruta = item.data(Qt.ItemDataRole.UserRole)

            # Buscar en nombre
            nombre_coincide = not texto or texto in item.text().lower()

            # Filtrar por tipo
            tipo_arch = _detectar_tipo(ruta) if ruta else "otro"
            tipo_coincide = tipo_filtro == "todos" or tipo_arch == tipo_filtro

            item.setHidden(not (nombre_coincide and tipo_coincide))

    # -- Eventos ---------------------------------------------------------------

    def _on_item_clicked(self, item: QListWidgetItem):
        """Maneja click en un archivo."""
        ruta = item.data(Qt.ItemDataRole.UserRole)
        if ruta:
            self.archivo_seleccionado.emit(ruta)

    def _on_item_doble_click(self, item: QListWidgetItem):
        """Doble click: emitir senal para agregar al timeline."""
        ruta = item.data(Qt.ItemDataRole.UserRole)
        if ruta:
            self.archivo_drag_started.emit(ruta)

    def _on_menu_contextual(self, pos):
        """Menu contextual para archivos."""
        item = self._lista.itemAt(pos)
        if item is None:
            # Menu vacio: solo importar
            menu = QMenu(self)
            act = QAction(f"{ICONOS_UNICODE['open']}  Importar archivos...", self)
            act.triggered.connect(self._importar_archivos)
            menu.addAction(act)
            menu.exec(self._lista.viewport().mapToGlobal(pos))
            return

        ruta = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)

        # Agregar al timeline
        act_agregar = QAction("▶  Agregar al timeline", self)
        act_agregar.triggered.connect(lambda: self.archivo_drag_started.emit(ruta))
        menu.addAction(act_agregar)

        menu.addSeparator()

        # Renombrar (solo visual)
        act_rename = QAction("✎  Renombrar", self)
        act_rename.triggered.connect(lambda: self._renombrar_item(item))
        menu.addAction(act_rename)

        # Propiedades
        act_props = QAction("ℹ  Propiedades", self)
        act_props.triggered.connect(lambda: self._mostrar_propiedades(ruta))
        menu.addAction(act_props)

        menu.addSeparator()

        # Eliminar de la biblioteca
        act_del = QAction(f"{ICONOS_UNICODE['trash']}  Eliminar de biblioteca", self)
        act_del.triggered.connect(lambda: self._eliminar_archivo(ruta, item))
        menu.addAction(act_del)

        menu.exec(self._lista.viewport().mapToGlobal(pos))

    def _renombrar_item(self, item: QListWidgetItem):
        """Permite renombrar visualmente un item."""
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        self._lista.editItem(item)

    def _mostrar_propiedades(self, ruta: str):
        """Muestra las propiedades del archivo."""
        if not os.path.isfile(ruta):
            return

        nombre = os.path.basename(ruta)
        tipo = _detectar_tipo(ruta)
        tamano = _formato_tamano(os.path.getsize(ruta))

        info = (
            f"Archivo: {nombre}\n"
            f"Tipo: {tipo}\n"
            f"Tamano: {tamano}\n"
            f"Ruta: {ruta}"
        )

        # Intentar obtener mas info de video
        if tipo == "video":
            try:
                import cv2
                cap = cv2.VideoCapture(ruta)
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                dur = frames / fps if fps > 0 else 0
                cap.release()
                info += (
                    f"\n\nResolucion: {w}x{h}"
                    f"\nFPS: {fps:.1f}"
                    f"\nDuracion: {dur:.1f}s"
                    f"\nFrames: {frames}"
                )
            except Exception:
                pass

        QMessageBox.information(self, "Propiedades", info)

    def _eliminar_archivo(self, ruta: str, item: QListWidgetItem):
        """Elimina un archivo de la biblioteca (no del disco)."""
        self._archivos = [a for a in self._archivos if a["path"] != ruta]
        row = self._lista.row(item)
        self._lista.takeItem(row)
        self._actualizar_info()

    def _actualizar_info(self):
        """Actualiza la barra de informacion."""
        total = len(self._archivos)
        if total == 0:
            self._lbl_info.setText("Sin archivos importados")
        else:
            tamano_total = sum(a["size"] for a in self._archivos)
            self._lbl_info.setText(
                f"{total} archivos | {_formato_tamano(tamano_total)} total"
            )

    # -- API publica -----------------------------------------------------------

    def get_archivos(self) -> List[Dict[str, Any]]:
        """Retorna la lista de archivos importados."""
        return list(self._archivos)

    def limpiar(self):
        """Limpia la biblioteca de medios."""
        self._archivos.clear()
        self._lista.clear()
        self._actualizar_info()
        self.media_library_changed.emit()

    def agregar_archivo(self, ruta: str, nombre: str = "", tipo: str = ""):
        """Agrega un archivo a la biblioteca."""
        if not os.path.exists(ruta):
            return False
        
        # Verificar si ya existe
        for archivo in self._archivos:
            if archivo["path"] == ruta:
                return False
        
        # Determinar tipo si no se especifica
        if not tipo:
            tipo = _detectar_tipo(ruta)
        
        # Obtener tamaño
        tamano = os.path.getsize(ruta) if os.path.exists(ruta) else 0
        
        # Agregar a la lista
        archivo_info = {
            "path": ruta,
            "name": nombre or os.path.basename(ruta),
            "type": tipo,
            "size": tamano,
            "added_at": time.time()
        }
        
        self._archivos.append(archivo_info)
        self._agregar_item_lista(archivo_info)
        self._actualizar_info()
        self.media_library_changed.emit()
        return True

    # -- Integración con ProjectManager ----------------------------------------

    def _cargar_desde_project_manager(self):
        """Carga archivos desde el ProjectManager."""
        if not self._project_manager or not hasattr(self._project_manager, 'media_library'):
            return
        
        self.limpiar()
        
        for media_item in self._project_manager.media_library:
            archivo_info = {
                "path": media_item.path,
                "name": media_item.name,
                "type": media_item.media_type,
                "size": media_item.file_size,
                "added_at": media_item.added_at,
                "duration": media_item.duration,
                "width": media_item.width,
                "height": media_item.height,
                "embedded": media_item.embedded,
                "embedded_path": media_item.embedded_path
            }
            self._archivos.append(archivo_info)
            self._agregar_item_a_lista(archivo_info)
        
        self._actualizar_info()

    def sincronizar_con_project_manager(self):
        """
        Sincroniza la biblioteca de medios con el ProjectManager.
        
        Returns:
            Lista de MediaItem actualizada
        """
        if not self._project_manager:
            return []
        
        from core.project_manager import MediaItem
        
        media_items = []
        for archivo in self._archivos:
            media_item = MediaItem(
                path=archivo["path"],
                name=archivo["name"],
                media_type=archivo["type"]
            )
            media_item.file_size = archivo.get("size", 0)
            media_item.added_at = archivo.get("added_at", time.time())
            media_item.duration = archivo.get("duration", 0.0)
            media_item.width = archivo.get("width", 0)
            media_item.height = archivo.get("height", 0)
            media_item.embedded = archivo.get("embedded", False)
            media_item.embedded_path = archivo.get("embedded_path", "")
            
            media_items.append(media_item)
        
        return media_items

    def set_project_manager(self, project_manager):
        """Establece el ProjectManager para sincronización."""
        self._project_manager = project_manager
        if project_manager:
            self._cargar_desde_project_manager()
