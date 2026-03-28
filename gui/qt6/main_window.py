# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- Ventana principal (Paso 3 FINAL).

Integra todos los paneles de la migracion Qt6:
  Paso 1: Preview, Profile Selector, Plugin System, Theme
  Paso 2: Timeline, Inspector, Keyframe Editor, Transitions Panel
  Paso 3: Sidebar modulos, Media Library, Audio Mixer, Toolbar,
           Export Dialog, Settings Dialog

Barra de menus, toolbar personalizable, dock widgets reposicionables,
barra de estado con info del perfil activo.
Todo respeta el sistema de perfiles (ProfileManager).
"""

from __future__ import annotations

import os
import sys
import json
import logging
from typing import Optional

import numpy as np
import cv2

from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QToolBar, QStatusBar, QDockWidget,
    QMenuBar, QMenu, QFileDialog, QMessageBox, QSplitter,
    QFrame, QSizePolicy, QTabWidget
)
_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _RAIZ) if _RAIZ not in sys.path else None
from core.logger import get_logger
logger = get_logger(__name__)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QAction, QActionGroup
from PyQt6.QtGui import QFont, QIcon, QPixmap
from gui.qt6.base import (
    ICONOS_UNICODE, PanelBase, FabricaWidgets,
    UserLevelAdapter, NIVEL_NOVATO, NIVEL_INTERMEDIO, NIVEL_PROFESIONAL
)
from gui.qt6.theme import AdministradorTemas
from gui.qt6.preview_widget import PreviewWidget
from gui.qt6.plugin_system import RegistroPlugins
from gui.qt6.timeline_widget import TimelineWidget
from gui.qt6.inspector_widget import InspectorWidget
from gui.qt6.keyframe_editor import KeyframeEditorWidget
from gui.qt6.transitions_panel import TransitionsPanel
from gui.qt6.sidebar_widget import SidebarWidget
from gui.qt6.media_library_widget import MediaLibraryWidget
from gui.qt6.audio_mixer_widget import AudioMixerWidget
from gui.qt6.toolbar_widget import SoundviToolBar
from gui.qt6.export_dialog import ExportDialog
from gui.qt6.settings_dialog import SettingsDialog
from gui.qt6.about_dialog import AboutDialog
from gui.qt6.welcome_wizard import WelcomeWizard, PanelPrimerosPasos
from gui.qt6.scripting_panel import ScriptingPanel
from core.profiles import ProfileManager
from core.timeline import Timeline
from core.commands import CommandManager
from core.keyframes import KeyframeAnimator
from core.project_manager import ProjectManager
from core.project_history import project_history

log = logging.getLogger("soundvi.qt6.main")


# ---------------------------------------------------------------------------
#  Ventana principal
# ---------------------------------------------------------------------------
class VentanaPrincipalQt6(QMainWindow):
    """
    Ventana principal de Soundvi en Qt6 (Paso 3 FINAL).
    Integra todos los paneles, menus, toolbar personalizable,
    dialogos de exportacion y configuracion.
    Se adapta al perfil activo del usuario.
    """

    def __init__(self, profile_manager: ProfileManager):
        super().__init__()
        self._pm = profile_manager
        self._temas = AdministradorTemas()
        self._registro_plugins = RegistroPlugins()

        # Adaptador de nivel de usuario (central)
        self._adapter = UserLevelAdapter(profile_manager)

        # -- ProjectManager centralizado --
        self._project_manager = ProjectManager()

        # Sistemas de backend compartidos
        self._timeline = self._project_manager.timeline
        self._cmd_manager = self._project_manager.command_manager
        self._keyframe_animator = KeyframeAnimator()

        # -- Module Manager --
        self._module_manager = None
        try:
            from modules.core.manager import CategorizedModuleManager
            self._module_manager = CategorizedModuleManager()
            log.info("CategorizedModuleManager inicializado con %d tipos de modulos",
                     len(self._module_manager.get_module_types()))
        except Exception as e:
            log.warning("No se pudo inicializar CategorizedModuleManager: %s", e)
            try:
                from modules.manager import ModuleManager
                self._module_manager = ModuleManager()
                log.info("ModuleManager (legacy) inicializado")
            except Exception as e2:
                log.error("No se pudo inicializar ningun gestor de modulos: %s", e2)

        # Cache de instancias de módulos del timeline (item_id -> Module instance)
        self._timeline_module_cache: dict = {}

        self.setWindowTitle("Soundvi — Editor de Video Modular")
        self.setMinimumSize(QSize(900, 600))
        self.resize(1360, 860)

        # Icono de ventana (Zoundvi logo)
        _zoundvi_logo = os.path.join(_RAIZ, "multimedia", "zoundvi", "zoundvi_logo.png")
        _logo_fallback = os.path.join(_RAIZ, "logos", "logo.png")
        _icon_path = _zoundvi_logo if os.path.isfile(_zoundvi_logo) else _logo_fallback
        if os.path.isfile(_icon_path):
            self.setWindowIcon(QIcon(_icon_path))

        # Construir UI
        self._crear_menus()
        self._crear_toolbar()
        self._crear_status_bar()
        self._crear_paneles()
        self._crear_paneles_nivel()       # Primeros Pasos + Scripting
        self._conectar_senales()

        # Aplicar tema oscuro
        self._temas.aplicar_tema("darkly")

        # Aplicar restricciones de perfil y adaptaciones de nivel
        self._aplicar_perfil()
        self._aplicar_adaptaciones_nivel()

        # Registrar callback de undo/redo
        self._cmd_manager.on_change(self._on_historial_cambiado)

        # Conectar module manager con sidebar
        if self._module_manager is not None:
            self._panel_sidebar.set_module_manager(self._module_manager)
            # Cargar modulos guardados previamente
            try:
                loaded = self._module_manager.load_saved_modules()
                if loaded:
                    log.info("Cargados %d modulos guardados", len(loaded))
            except Exception as e:
                log.warning("Error cargando modulos guardados: %s", e)

        # Configurar plugin system con contexto
        self._registro_plugins.set_contexto({
            "profile_manager": self._pm,
            "timeline": self._timeline,
            "cmd_manager": self._cmd_manager,
            "module_manager": self._module_manager,
            "ventana": self,
        })
        # Buscar plugins en directorio modules/
        plugins_dir = os.path.join(_RAIZ, "modules")
        if os.path.isdir(plugins_dir):
            self._registro_plugins.agregar_directorio(plugins_dir)
            self._registro_plugins.descubrir_plugins()

        # Cargar mixer con tracks del timeline
        self._panel_mixer.cargar_desde_timeline(self._timeline)

        # Conectar cambio de nivel
        self._adapter.nivel_cambiado.connect(self._on_nivel_cambiado)

        # Mostrar wizard de bienvenida si es novato y primer inicio
        self._mostrar_wizard_si_necesario()

        # Actualizar preview inicial
        QTimer.singleShot(100, self._actualizar_preview)

        log.info("Ventana principal Qt6 FINAL inicializada (perfil: %s, nivel: %s)",
                 self._pm.perfil_activo.nombre if self._pm.perfil_activo else "ninguno",
                 self._adapter.nivel)

    # -- Menus -----------------------------------------------------------------
    def _crear_menus(self):
        menubar = self.menuBar()

        # File
        menu_file = menubar.addMenu("&File")
        self._agregar_accion(menu_file, "Nuevo proyecto", "Ctrl+N", self._nuevo_proyecto)
        self._agregar_accion(menu_file, "Abrir proyecto...", "Ctrl+O", self._abrir_proyecto)
        self._agregar_accion(menu_file, "Guardar proyecto", "Ctrl+S", self._guardar_proyecto)
        self._agregar_accion(menu_file, "Guardar como...", "Ctrl+Shift+S", self._guardar_como)
        menu_file.addSeparator()
        # Submenu de proyectos recientes
        self._menu_recientes = menu_file.addMenu("Proyectos recientes")
        self._actualizar_menu_recientes()
        menu_file.addSeparator()
        self._agregar_accion(menu_file, "Importar medios...", "Ctrl+I", self._importar_medios)
        self._act_export = self._agregar_accion(
            menu_file, f"{ICONOS_UNICODE['export']} Exportar video...", "Ctrl+E",
            self._abrir_exportar_dialog)
        menu_file.addSeparator()
        self._agregar_accion(menu_file, "Salir", "Ctrl+Q", self.close)

        # Edit
        menu_edit = menubar.addMenu("&Edit")
        self._act_undo = self._agregar_accion(
            menu_edit, f"{ICONOS_UNICODE['undo']} Deshacer", "Ctrl+Z", self._deshacer)
        self._act_redo = self._agregar_accion(
            menu_edit, f"{ICONOS_UNICODE['redo']} Rehacer", "Ctrl+Y", self._rehacer)
        menu_edit.addSeparator()
        self._agregar_accion(menu_edit, f"{ICONOS_UNICODE['cut']} Cortar clip", "Ctrl+X",
                             self._cortar_clip)
        self._agregar_accion(menu_edit, f"{ICONOS_UNICODE['copy']} Copiar clip", "Ctrl+C",
                             self._copiar_clip)
        self._agregar_accion(menu_edit, f"{ICONOS_UNICODE['paste']} Pegar clip", "Ctrl+V",
                             self._pegar_clip)
        menu_edit.addSeparator()
        self._agregar_accion(menu_edit, f"{ICONOS_UNICODE['settings']} Preferencias...", "",
                             self._abrir_settings_dialog)

        # View
        self._menu_view = menubar.addMenu("&View")
        self._acciones_view = {}
        
        # Submenú de temas
        self._menu_temas = self._menu_view.addMenu("✎ Cambiar tema")
        self._crear_menu_temas()

        # Modules
        self._menu_modules = menubar.addMenu("&Modules")
        self._agregar_accion(self._menu_modules, "Gestor de modulos...", "", self._gestor_modulos)
        self._agregar_accion(self._menu_modules, "Instalar plugin...", "", self._instalar_plugin)
        self._menu_modules.addSeparator()
        self._agregar_accion(self._menu_modules, "Cambiar perfil...", "", self._cambiar_perfil)

        # Help
        menu_help = menubar.addMenu("&Help")
        self._agregar_accion(menu_help, "Acerca de Soundvi", "", self._acerca_de)
        self._agregar_accion(menu_help, "Asistente de Bienvenida", "", self._mostrar_wizard)
        self._agregar_accion(menu_help, "Documentacion", "F1", lambda: None)
        self._agregar_accion(menu_help, "Reportar bug", "", lambda: None)

    def _agregar_accion(self, menu: QMenu, texto: str, atajo: str,
                        callback, visible: bool = True) -> QAction:
        accion = QAction(texto, self)
        if atajo:
            accion.setShortcut(QKeySequence(atajo))
        accion.triggered.connect(callback)
        accion.setVisible(visible)
        menu.addAction(accion)
        return accion
    
    def _crear_menu_temas(self):
        """Crea el submenú de temas con todos los temas disponibles."""
        from .theme import AdministradorTemas
        
        tema_manager = AdministradorTemas()
        temas = tema_manager.listar_temas_nombres()
        tema_actual = tema_manager.tema_actual
        
        # Grupo de acciones para selección exclusiva
        self._grupo_temas = QActionGroup(self)
        self._grupo_temas.setExclusive(True)
        
        for tema_id, tema_nombre in temas.items():
            accion = QAction(tema_nombre, self)
            accion.setCheckable(True)
            accion.setChecked(tema_id == tema_actual)
            accion.setProperty("tema_id", tema_id)
            accion.triggered.connect(lambda checked, tid=tema_id: self._cambiar_tema(tid))
            
            self._grupo_temas.addAction(accion)
            self._menu_temas.addAction(accion)
        
        self._menu_temas.addSeparator()
        
        # Acción para abrir selector avanzado
        accion_avanzado = QAction("✎ Selector avanzado...", self)
        accion_avanzado.triggered.connect(self._abrir_selector_temas_avanzado)
        self._menu_temas.addAction(accion_avanzado)
    
    def _cambiar_tema(self, tema_id: str):
        """Cambia el tema de la aplicación."""
        from .theme import AdministradorTemas
        from utils.config import load_user_prefs, save_user_prefs
        
        # Aplicar tema
        tema_manager = AdministradorTemas()
        tema_manager.aplicar_tema(tema_id)
        
        # Guardar preferencias
        try:
            prefs = load_user_prefs()
            prefs["tema"] = tema_id
            save_user_prefs(prefs)
        except Exception:
            pass  # Silenciar errores de configuración
        
        # Actualizar estado de checkboxes en el menú
        for accion in self._grupo_temas.actions():
            accion.setChecked(accion.property("tema_id") == tema_id)
    
    def _abrir_selector_temas_avanzado(self):
        """Abre el selector avanzado de temas."""
        try:
            from .theme_selector import mostrar_selector_temas
            dialog = mostrar_selector_temas(self)
            dialog.theme_changed.connect(self._actualizar_menu_temas)
        except ImportError:
            # Fallback al método básico
            self._cambiar_tema_dialogo_simple()
    
    def _actualizar_menu_temas(self, tema_id: str):
        """Actualiza el menú de temas después de un cambio."""
        for accion in self._grupo_temas.actions():
            accion.setChecked(accion.property("tema_id") == tema_id)
    
    def _cambiar_tema_dialogo_simple(self):
        """Diálogo simple para cambiar tema (fallback)."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QButtonGroup, QHBoxLayout
        from .theme import AdministradorTemas
        
        tema_manager = AdministradorTemas()
        temas = tema_manager.listar_temas_nombres()
        tema_actual = tema_manager.tema_actual
        
        dialog = QDialog(self)
        dialog.setWindowTitle("✎ Cambiar tema")
        dialog.setFixedSize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # Título
        titulo = QLabel("Selecciona un tema:")
        titulo.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(titulo)
        
        # Botones de temas
        grupo = QButtonGroup(dialog)
        botones_layout = QVBoxLayout()
        
        for tema_id, tema_nombre in temas.items():
            btn = QPushButton(tema_nombre)
            btn.setCheckable(True)
            btn.setChecked(tema_id == tema_actual)
            btn.setProperty("tema_id", tema_id)
            btn.clicked.connect(lambda checked, tid=tema_id: self._cambiar_tema(tid))
            
            grupo.addButton(btn)
            botones_layout.addWidget(btn)
        
        layout.addLayout(botones_layout)
        layout.addStretch()
        
        # Botones de acción
        btn_layout = QHBoxLayout()
        btn_aceptar = QPushButton("Aceptar")
        btn_aceptar.clicked.connect(dialog.accept)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(dialog.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_aceptar)
        btn_layout.addWidget(btn_cancelar)
        layout.addLayout(btn_layout)
        
        dialog.exec()

    # -- Toolbar ---------------------------------------------------------------
    def _crear_toolbar(self):
        """Crea la toolbar personalizable del Paso 3."""
        self._toolbar = SoundviToolBar(self._pm, self._adapter)
        self.addToolBar(self._toolbar)

        # Conectar acciones de la toolbar a metodos de la ventana
        acciones_map = {
            "new_project":  self._nuevo_proyecto,
            "open_project": self._abrir_proyecto,
            "save_project": self._guardar_proyecto,
            "import_media": self._importar_medios,
            "export_video": self._abrir_exportar_dialog,
            "undo":         self._deshacer,
            "redo":         self._rehacer,
            "split_clip":   self._dividir_clip,
            "delete_clip":  self._eliminar_clip_seleccionado,
            "play":         self._play,
            "pause":        self._pause,
            "stop":         self._stop,
            "zoom_in":      self._zoom_in,
            "zoom_out":     self._zoom_out,
            "zoom_fit":     self._zoom_fit,
            "settings":     self._abrir_settings_dialog,
            "profile":      self._cambiar_perfil,
        }

        for nombre, callback in acciones_map.items():
            self._toolbar.conectar_accion(nombre, callback)

    # -- Status bar ------------------------------------------------------------
    def _crear_status_bar(self):
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._lbl_perfil = QLabel()
        self._status.addPermanentWidget(self._lbl_perfil)
        self._actualizar_info_perfil()

    def _actualizar_info_perfil(self):
        perfil = self._pm.perfil_activo
        nivel_nombres = {
            NIVEL_NOVATO: "Novato",
            NIVEL_INTERMEDIO: "Intermedio",
            NIVEL_PROFESIONAL: "Profesional",
        }
        nivel_txt = nivel_nombres.get(self._adapter.nivel, self._adapter.nivel)
        if perfil:
            self._lbl_perfil.setText(
                f"  {perfil.icono} {perfil.nombre} ({nivel_txt})  |  Soundvi v4.8  "
            )
        else:
            self._lbl_perfil.setText("  Soundvi v4.8  ")
        self._status.showMessage("Listo.", 3000)

    # -- Paneles / Dock widgets ------------------------------------------------
    def _crear_paneles(self):
        # Widget central: Preview
        self._preview = PreviewWidget()
        self._preview.set_timeline(self._timeline)
        self.setCentralWidget(self._preview)

        # -- Dock: Sidebar de Modulos (izquierda) --
        # Sidebar debe empezar desde el borde izquierdo de la ventana
        self._panel_sidebar = SidebarWidget(self._pm)
        self._dock_sidebar = self._crear_dock("Modulos", self._panel_sidebar,
                                               Qt.DockWidgetArea.LeftDockWidgetArea)
        
        # Forzar que el sidebar esté pegado al borde izquierdo
        self._dock_sidebar.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )

        # -- Dock: Media Library (izquierda, tabulada con sidebar) --
        self._panel_media = MediaLibraryWidget(project_manager=self._project_manager)
        self._dock_media = self._crear_dock("Biblioteca", self._panel_media,
                                             Qt.DockWidgetArea.LeftDockWidgetArea)
        self.tabifyDockWidget(self._dock_sidebar, self._dock_media)
        self._dock_sidebar.raise_()

        # -- Dock: Transiciones (izquierda, tabulado) --
        self._panel_transiciones = TransitionsPanel(self._pm)
        self._dock_transiciones = self._crear_dock("Transiciones", self._panel_transiciones,
                                                    Qt.DockWidgetArea.LeftDockWidgetArea)
        self.tabifyDockWidget(self._dock_media, self._dock_transiciones)
        self._dock_sidebar.raise_()

        # -- Dock: Inspector (derecha) --
        self._panel_inspector = InspectorWidget(self._cmd_manager, self._pm, self._adapter)
        self._dock_inspector = self._crear_dock("Inspector", self._panel_inspector,
                                                 Qt.DockWidgetArea.RightDockWidgetArea)

        # -- Dock: Timeline (abajo) --
        self._panel_timeline = TimelineWidget(
            self._timeline, self._cmd_manager, self._pm
        )
        self._dock_timeline = self._crear_dock("Timeline", self._panel_timeline,
                                                Qt.DockWidgetArea.BottomDockWidgetArea)
        
        # Asegurar que el timeline sea visible y tenga tamaño adecuado
        log.info("Timeline dock creado - Altura mínima: %d", self._dock_timeline.minimumHeight())
        log.info("Timeline widget altura mínima: %d", self._panel_timeline.minimumHeight())
        
        # Forzar tamaño inicial y visibilidad
        self._dock_timeline.show()
        self._panel_timeline.show()
        
        # Usar timer para ajustar tamaño después de que la ventana se muestre
        QTimer.singleShot(100, self._ajustar_timeline_inicial)

        # -- Dock: Audio Mixer (abajo, tabulado con timeline) --
        self._panel_mixer = AudioMixerWidget(self._pm)
        self._dock_mixer = self._crear_dock("Audio Mixer", self._panel_mixer,
                                             Qt.DockWidgetArea.BottomDockWidgetArea)
        self.tabifyDockWidget(self._dock_timeline, self._dock_mixer)

        # -- Dock: Keyframe Editor (abajo, tabulado) --
        self._panel_keyframes = KeyframeEditorWidget(self._pm)
        self._dock_keyframes = self._crear_dock("Keyframes", self._panel_keyframes,
                                                 Qt.DockWidgetArea.BottomDockWidgetArea)
        self.tabifyDockWidget(self._dock_mixer, self._dock_keyframes)
        self._dock_timeline.raise_()

        # IMPORTANTE: Configurar esquinas para alinear timeline con sidebar
        # Esto hace que el timeline (dock inferior) se alinee con el sidebar (dock izquierdo)
        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)

        # Agregar acciones de visibilidad al menu View
        for dock in [self._dock_sidebar, self._dock_media, self._dock_transiciones,
                     self._dock_inspector, self._dock_timeline, self._dock_mixer,
                     self._dock_keyframes]:
            self._menu_view.addAction(dock.toggleViewAction())

    def _crear_dock(self, titulo: str, widget: QWidget,
                    area: Qt.DockWidgetArea) -> QDockWidget:
        dock = QDockWidget(titulo, self)
        dock.setWidget(widget)
        dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea |
            Qt.DockWidgetArea.BottomDockWidgetArea
        )
        
        # Configuración específica por área
        if area == Qt.DockWidgetArea.BottomDockWidgetArea:
            # Para docks inferiores
            dock.setMinimumHeight(180)
            widget.setMinimumHeight(150)
            
            # TIMELINE - ELEMENTO PRINCIPAL DEL EDITOR DE VIDEO
            if titulo == "Timeline":
                # Timeline con tamaño ajustado para dejar espacio a la preview
                dock.setMinimumHeight(150)
                dock.setMaximumHeight(350)
                widget.setMinimumHeight(280)
                
                # Timeline siempre visible y con prioridad
                dock.setVisible(True)
                dock.raise_()  # Traer al frente si está tabulado
                
                # Características especiales para timeline
                dock.setFeatures(
                    QDockWidget.DockWidgetFeature.DockWidgetMovable |
                    QDockWidget.DockWidgetFeature.DockWidgetClosable |
                    QDockWidget.DockWidgetFeature.DockWidgetFloatable
                )
                
                # Timeline obtiene más espacio por defecto
                log.info("Timeline configurado como elemento principal (300-600px)")
        else:
            # Para docks laterales (sidebar, inspector, etc.)
            # Se adaptan al timeline, no al revés
            dock.setMinimumWidth(180)
            dock.setMaximumWidth(350)  # Limitar ancho para no robar espacio
            dock.setMinimumHeight(80)
        
        self.addDockWidget(area, dock)
        
        return dock
    
    def resizeEvent(self, event):
        """Maneja el redimensionamiento de la ventana principal."""
        super().resizeEvent(event)
        # Ajustar timeline después de redimensionar
        self._ajustar_timeline_tamano()
    
    def _ajustar_timeline_inicial(self):
        """Ajusta el tamaño del timeline después de la inicialización."""
        try:
            if hasattr(self, '_dock_timeline') and self._dock_timeline.isVisible():
                # Timeline como elemento principal - tamaño generoso
                total_height = self.height()
                timeline_height = int(max(300, total_height * 0.4))  # 40% mínimo de la ventana
                
                self._dock_timeline.setMinimumHeight(timeline_height)
                
                widget = self._dock_timeline.widget()
                if widget:
                    widget.setMinimumHeight(timeline_height - 20)
                    
                    # Forzar actualización
                    widget.update()
                    widget.repaint()
                    
                    log.info("Timeline configurado como principal: %dpx (40%% ventana)",
                            timeline_height)
        except Exception as e:
            log.warning("Error ajustando timeline inicial: %s", e)
    
    def resizeEvent(self, event):
        """Maneja el redimensionamiento de la ventana principal."""
        super().resizeEvent(event)
        
        # Al redimensionar, asegurar que el timeline mantenga buen tamaño
        try:
            if hasattr(self, '_dock_timeline') and self._dock_timeline.isVisible():
                total_height = self.height()
                
                # Timeline debe mantener al menos 35-45% de la altura
                min_timeline_height = int(total_height * 0.35)
                max_timeline_height = int(total_height * 0.55)
                
                # Ajustar si está fuera de rango
                current_height = self._dock_timeline.height()
                if current_height < min_timeline_height or current_height > max_timeline_height:
                    target_height = int(total_height * 0.4)  # 40% ideal
                    self._dock_timeline.setMinimumHeight(target_height)
                    
                    log.debug("Timeline ajustado al redimensionar: %dpx", target_height)
        except Exception as e:
            # Silenciar errores en resize
            pass

    # -- Conectar senales entre widgets ----------------------------------------
    def _conectar_senales(self):
        """Conecta las senales entre los diferentes widgets."""
        # Timeline -> Preview: sincronizar playhead
        self._panel_timeline.playhead_changed.connect(self._on_playhead_changed)

        # Timeline -> Inspector: mostrar propiedades del clip seleccionado
        self._panel_timeline.clip_selected.connect(self._on_clip_selected)

        # Timeline -> Inspector: mostrar propiedades del módulo seleccionado
        self._panel_timeline.module_selected.connect(self._on_module_selected)

        # Preview -> Timeline: sincronizar playhead desde preview
        self._preview.tiempo_cambiado.connect(self._panel_timeline.set_playhead)
        self._preview.tiempo_cambiado.connect(self._panel_keyframes.set_playhead)
        # Preview tiempo cambiado -> actualizar frame
        self._preview.tiempo_cambiado.connect(self._actualizar_preview)

        # Inspector -> Preview: actualizar preview al cambiar propiedades
        # FIX BUG 2: invalidar cache de módulos antes de re-renderizar para
        # que los cambios de parámetros (pos_x, pos_y, etc.) se apliquen.
        self._panel_inspector.preview_requested.connect(self._invalidar_cache_y_preview)

        # Inspector -> Timeline: refrescar al cambiar propiedades de clip
        # Solo refrescar timeline si cambia una propiedad estructural
        self._panel_inspector.property_changed.connect(self._on_property_changed)

        # Transiciones -> Timeline: aplicar transicion
        self._panel_transiciones.transition_applied.connect(self._on_transicion_aplicada)

        # Keyframes -> actualizar preview
        self._panel_keyframes.keyframe_changed.connect(self._actualizar_preview)

        # Track cambiado -> refrescar inspector
        self._panel_timeline.track_changed.connect(
            lambda t: self._panel_inspector.mostrar_track(t) if t else None)
        
        # Clips cambiados -> actualizar duracion de preview
        self._panel_timeline.clips_changed.connect(self._actualizar_duracion_preview)

        # Sidebar -> aplicar modulo a clip seleccionado
        self._panel_sidebar.modulo_doble_click.connect(self._on_modulo_aplicado)

        # Media Library -> importar a timeline
        self._panel_media.archivo_importado.connect(
            lambda ruta: self._status.showMessage(f"Archivo importado: {os.path.basename(ruta)}", 3000))
        self._panel_media.archivo_drag_started.connect(self._on_media_agregar_timeline)

        # Audio Mixer -> actualizar tracks del timeline
        self._panel_mixer.track_volumen_changed.connect(self._on_mixer_volumen)
        self._panel_mixer.track_pan_changed.connect(self._on_mixer_pan)
        self._panel_mixer.track_mute_changed.connect(self._on_mixer_mute)
        self._panel_mixer.track_solo_changed.connect(self._on_mixer_solo)

    # -- Paneles dependientes del nivel ----------------------------------------
    def _crear_paneles_nivel(self):
        """Crea paneles que dependen del nivel: Primeros Pasos y Scripting."""
        # Panel de Primeros Pasos (novatos) - embebido en dock derecho
        self._panel_primeros_pasos = PanelPrimerosPasos()
        self._dock_primeros_pasos = self._crear_dock(
            "Primeros Pasos", self._panel_primeros_pasos,
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        self._panel_primeros_pasos.accion_solicitada.connect(
            self._on_primeros_pasos_accion
        )

        # Panel de Scripting (profesionales)
        self._panel_scripting = ScriptingPanel(contexto={
            "timeline": self._timeline,
            "cmd": self._cmd_manager,
        })
        self._dock_scripting = self._crear_dock(
            "Python Console", self._panel_scripting,
            Qt.DockWidgetArea.BottomDockWidgetArea
        )
        # Tabulado con timeline
        self.tabifyDockWidget(self._dock_keyframes, self._dock_scripting)

        # Agregar al menu View
        self._menu_view.addAction(self._dock_primeros_pasos.toggleViewAction())
        self._menu_view.addAction(self._dock_scripting.toggleViewAction())

    # -- Aplicar perfil --------------------------------------------------------
    def _aplicar_perfil(self):
        """Muestra/oculta paneles y menus segun el perfil activo."""
        pm = self._pm

        # Paneles basicos
        mapa_paneles = {
            "modules_sidebar": self._dock_sidebar,
            "inspector": self._dock_inspector,
            "media_library": self._dock_media,
            "timeline": self._dock_timeline,
            "audio_mixer": self._dock_mixer,
        }
        for nombre, dock in mapa_paneles.items():
            dock.setVisible(pm.panel_visible(nombre))

        # Transiciones
        trans_visible = pm.funcion_habilitada("transiciones")
        self._dock_transiciones.setVisible(trans_visible)

        # Keyframes: solo visible en perfil Profesional
        kf_visible = pm.funcion_habilitada("keyframes")
        self._dock_keyframes.setVisible(kf_visible)

        # Menu modules
        if not pm.menu_item_visible("Modules"):
            self._menu_modules.menuAction().setVisible(False)

        # Refrescar toolbar segun perfil
        self._toolbar.refrescar_perfil()

        self._actualizar_info_perfil()

    # -- Adaptaciones segun nivel de usuario -----------------------------------
    def _aplicar_adaptaciones_nivel(self):
        """Aplica adaptaciones de la interfaz segun el nivel del usuario."""
        nivel = self._adapter.nivel
        perfil = self._pm.perfil_activo
        ui_cfg = perfil.ui_config if perfil else {}

        # Panel Primeros Pasos: solo para novatos
        self._dock_primeros_pasos.setVisible(self._adapter.mostrar_primeros_pasos())

        # Panel Scripting: solo para profesionales
        self._dock_scripting.setVisible(self._adapter.mostrar_panel_scripting())

        # Actualizar contexto del scripting panel
        if self._adapter.mostrar_panel_scripting():
            self._panel_scripting.set_contexto({
                "timeline": self._timeline,
                "cmd": self._cmd_manager,
                "keyframes": self._keyframe_animator,
            })

        # --- Adaptaciones de UI segun ui_config del perfil ---

        # Tamaño de fuente base
        font_size = ui_cfg.get("font_size_base", 11)
        font = QFont("Segoe UI", font_size)
        QApplication.instance().setFont(font)

        # Tamaño de iconos en toolbar
        icon_size = ui_cfg.get("toolbar_icon_size", 28)
        self._toolbar.setIconSize(QSize(icon_size, icon_size))

        # Texto visible en toolbar
        if ui_cfg.get("toolbar_text_visible", True):
            self._toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        else:
            self._toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        # Simplificar menus para novatos
        if ui_cfg.get("simplificar_menus", False):
            # Ocultar menus avanzados
            if hasattr(self, '_menu_modules'):
                self._menu_modules.menuAction().setVisible(False)

        # Status bar detallada para novatos
        if ui_cfg.get("barra_estado_detallada", False):
            self._status.showMessage(
                "\u2022 Tip: Importa medios con Ctrl+I, luego arrastralos al timeline.", 8000
            )

        # Registrar atajos extra para profesionales
        self._configurar_atajos_nivel()

        # Actualizar status bar con info del nivel
        self._actualizar_info_perfil()

        log.info("Adaptaciones de nivel aplicadas: %s (font:%d, icons:%d)",
                 nivel, font_size, icon_size)

    def _configurar_atajos_nivel(self):
        """Configura atajos de teclado extra segun nivel."""
        atajos = self._adapter.obtener_atajos_extra()
        for atajo, desc in atajos.items():
            try:
                accion = QAction(desc, self)
                accion.setShortcut(QKeySequence(atajo))
                if "consola Python" in desc.lower() or "python" in desc.lower():
                    accion.triggered.connect(self._abrir_consola_python)
                elif "exportación rápida" in desc.lower():
                    accion.triggered.connect(self._abrir_exportar_dialog)
                elif "duplicar clip" in desc.lower():
                    accion.triggered.connect(lambda: self._status.showMessage(
                        "Duplicar clip: próximamente", 2000))
                self.addAction(accion)
            except Exception as e:
                log.warning("No se pudo registrar atajo %s: %s", atajo, e)

    def _on_nivel_cambiado(self, nuevo_nivel: str):
        """Se ejecuta cuando el nivel del usuario cambia dinámicamente."""
        log.info("Nivel cambiado dinámicamente a: %s", nuevo_nivel)
        self._aplicar_adaptaciones_nivel()
        # Actualizar inspector y toolbar
        self._panel_inspector.set_adapter(self._adapter)
        self._toolbar.set_adapter(self._adapter)
        self._status.showMessage(
            f"Interfaz actualizada para nivel: {nuevo_nivel}", 3000
        )

    def _mostrar_wizard_si_necesario(self):
        """Muestra el wizard de bienvenida si el usuario es novato."""
        if self._adapter.mostrar_wizard_bienvenida():
            # Verificar si ya completo el wizard antes
            try:
                from utils.config import load_user_prefs
                prefs = load_user_prefs()
                if prefs.get("wizard_completado"):
                    return
            except Exception:
                pass

            # Mostrar wizard con delay para que la ventana se muestre primero
            QTimer.singleShot(500, self._mostrar_wizard)

    def _mostrar_wizard(self):
        """Muestra el wizard de bienvenida."""
        wizard = WelcomeWizard(parent=self)
        wizard.wizard_completado.connect(self._on_wizard_completado)
        wizard.exec()

    def _on_wizard_completado(self):
        """Marca el wizard como completado en preferencias."""
        try:
            from utils.config import load_user_prefs, save_user_prefs
            prefs = load_user_prefs()
            prefs["wizard_completado"] = True
            save_user_prefs(prefs)
        except Exception as e:
            log.warning("No se pudo guardar estado del wizard: %s", e)
        self._status.showMessage("\u25B6 Bienvenido a Soundvi!", 5000)

    def _on_primeros_pasos_accion(self, accion: str):
        """Maneja acciones del panel de Primeros Pasos."""
        if accion == "import_media":
            self._importar_medios()
        elif accion == "export_video":
            self._abrir_exportar_dialog()
        elif accion == "open_modules":
            self._dock_sidebar.show()
            self._dock_sidebar.raise_()
        elif accion == "add_to_timeline":
            self._dock_timeline.show()
            self._dock_timeline.raise_()
            self._status.showMessage(
                "\u2022 Importa medios primero, luego arrastralos al timeline.", 5000
            )
        elif accion == "show_wizard":
            self._mostrar_wizard()

    def _abrir_consola_python(self):
        """Abre/muestra el panel de scripting Python."""
        self._dock_scripting.show()
        self._dock_scripting.raise_()

    # -- Callbacks de senales --------------------------------------------------
    def _on_playhead_changed(self, tiempo: float):
        """Sincroniza el playhead entre timeline y preview."""
        self._preview.set_tiempo(tiempo)
        self._panel_keyframes.set_playhead(tiempo)
        self._actualizar_preview()

    def _on_clip_selected(self, clip):
        """Muestra propiedades del clip seleccionado en el inspector."""
        if clip is not None:
            self._panel_inspector.set_objeto(clip)
            if hasattr(clip, 'keyframe_animator') and clip.keyframe_animator:
                self._panel_keyframes.set_animator(clip.keyframe_animator,
                                                    clip.duration)
        else:
            self._panel_inspector.limpiar()

    def _on_module_selected(self, module_item):
        """Muestra propiedades del módulo seleccionado en el inspector."""
        if module_item is not None:
            # Obtener o crear la instancia del módulo para el inspector
            mod_instance = None
            if self._module_manager is not None:
                mod_instance = self._get_or_create_timeline_module(module_item)
            self._panel_inspector.mostrar_modulo_timeline(
                module_item, mod_instance, self._module_manager
            )
        else:
            self._panel_inspector.limpiar()

    def _on_property_changed(self, prop, valor):
        """Maneja cambios de propiedades desde el inspector."""
        if prop in ("start_time", "duration", "enabled", "name"):
            self._panel_timeline.refrescar()
            
            # Si cambia start_time o duration, invalidar cache del módulo actual
            # para que re-procese el audio en su nueva posición temporal
            if prop in ("start_time", "duration"):
                obj = self._panel_inspector.objeto_actual
                if hasattr(obj, 'item_id') and hasattr(self, '_timeline_module_cache'):
                    self._timeline_module_cache.pop(obj.item_id, None)

    def _on_transicion_aplicada(self, tipo: str, duracion: float):
        """Aplica una transición al clip seleccionado en el timeline."""
        clips_sel = self._panel_timeline.get_selected_clips()
        
        trans_data = {
            'type': tipo,
            'duration': duracion,
            'easing': 'ease_in_out',
            'color': [0, 0, 0],
            'softness': 0.1,
        }
        
        # Tipos inherentemente de entrada
        in_types = {'fade_in', 'fade_from_color', 'iris_open', 'zoom_in',
                    'wipe_left', 'slide_left', 'push_left'}
        
        if clips_sel:
            for clip in clips_sel:
                if tipo in in_types:
                    clip.transition_in = trans_data.copy()
                else:
                    clip.transition_out = trans_data.copy()
            
            self._panel_timeline.refrescar()
            self._actualizar_preview()
            self._status.showMessage(
                f"Transición '{tipo}' ({duracion:.1f}s) aplicada a {len(clips_sel)} clip(s)", 3000)
        else:
            self._status.showMessage(
                f"Selecciona un clip para aplicar la transición '{tipo}'", 3000)

    def _on_historial_cambiado(self):
        """Actualiza estado de botones Undo/Redo."""
        if hasattr(self, '_act_undo'):
            self._act_undo.setEnabled(self._cmd_manager.can_undo)
            desc = self._cmd_manager.undo_description
            self._act_undo.setText(
                f"{ICONOS_UNICODE['undo']} Deshacer" + (f": {desc}" if desc else ""))
        if hasattr(self, '_act_redo'):
            self._act_redo.setEnabled(self._cmd_manager.can_redo)
            desc = self._cmd_manager.redo_description
            self._act_redo.setText(
                f"{ICONOS_UNICODE['redo']} Rehacer" + (f": {desc}" if desc else ""))

        # Actualizar toolbar
        self._toolbar.habilitar_accion("undo", self._cmd_manager.can_undo)
        self._toolbar.habilitar_accion("redo", self._cmd_manager.can_redo)

    
    def keyPressEvent(self, event):
        """Manejo de atajos de teclado globales."""
        # Ctrl+Z / Ctrl+Y para undo/redo
        if event.key() == Qt.Key.Key_Z and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._deshacer()
            event.accept()
        elif event.key() == Qt.Key.Key_Y and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._rehacer()
            event.accept()
        else:
            super().keyPressEvent(event)


    def _on_modulo_aplicado(self, type_key: str):
        """Aplica un modulo al clip seleccionado desde la sidebar."""
        import time
        
        if self._module_manager is None:
            self._status.showMessage("Gestor de modulos no disponible", 3000)
            return
        
        # Obtener clips seleccionados
        clips_sel = self._panel_timeline.get_selected_clips()
        if len(clips_sel) == 0:
            self._status.showMessage("Selecciona un clip para aplicar el modulo", 3000)
            return
        
        clip = clips_sel[0]
        
        # Crear instancia del modulo
        try:
            mod = self._module_manager.create_module_instance(type_key)
            if mod is not None:
                mod.habilitado = True
                self._module_manager.add_module_instance(mod)
                
                # También aplicar efecto al clip seleccionado
                effect_dict = {
                    "type": type_key,
                    "name": getattr(mod, 'nombre', type_key),
                    "clip_id": clip.id,
                    "timestamp": time.time(),
                    "applied": True
                }
                
                # Añadir configuración del módulo si existe
                if hasattr(mod, '_config'):
                    effect_dict.update(mod._config)
                
                # Aplicar al clip
                clip.add_module(effect_dict)
                
                # Actualizar timeline para mostrar indicador
                self._panel_timeline._refrescar_completo()
                
                self._status.showMessage(
                    f"Modulo '{mod.nombre}' aplicado a '{clip.name}'", 3000)
                
                # Refrescar sidebar para mostrar el estado actualizado
                self._panel_sidebar.refrescar()
                # Actualizar preview
                self._actualizar_preview()
                
                print(f"[DEBUG] Módulo aplicado: {type_key} -> clip '{clip.name}'")
            else:
                self._status.showMessage(
                    f"No se pudo crear modulo: {type_key}", 3000)
        except Exception as e:
            log.error("Error aplicando modulo %s: %s", type_key, e)
            self._status.showMessage(f"Error al aplicar modulo: {e}", 3000)
    def _on_media_agregar_timeline(self, ruta: str):
        """Agrega un archivo de medios al timeline en la posicion del playhead."""
        from core.video_clip import VideoClip, detect_source_type
        import os
        
        tipo = detect_source_type(ruta)
        
        # Encontrar track apropiado o crear uno
        tracks = self._timeline.get_tracks_by_type(tipo)
        track_index = -1
        if tracks:
            for i, t in enumerate(self._timeline.tracks):
                if t.track_id == tracks[0].track_id:
                    track_index = i
                    break
        
        if track_index == -1:
            track_index = len(self._timeline.tracks)
            self._panel_timeline._agregar_track(tipo)
            
        clip = VideoClip(
            source_path=ruta,
            source_type=tipo,
            track_index=track_index,
            start_time=self._timeline.playhead,
            duration=0.0,
            name=os.path.basename(ruta)
        )
        self._panel_timeline.agregar_clip(clip, track_index)
        # Actualizar duracion de la preview
        self._actualizar_duracion_preview()
        
        # Avanzar el playhead para evitar encimar clips
        duracion = max(1.0, clip.duration)
        self._panel_timeline.set_playhead(self._timeline.playhead + duracion)
        
        self._status.showMessage(
            f"Agregado al timeline: {os.path.basename(ruta)}", 3000)

    def _on_mixer_volumen(self, track_id: str, vol: float):
        """Actualiza volumen de un track desde el mixer."""
        for track in self._timeline.tracks:
            if track.track_id == track_id:
                track.volume = vol
                break

    def _on_mixer_pan(self, track_id: str, pan: float):
        """Actualiza pan de un track desde el mixer."""
        for track in self._timeline.tracks:
            if track.track_id == track_id:
                track.pan = pan
                break

    def _on_mixer_mute(self, track_id: str, muted: bool):
        """Actualiza mute de un track desde el mixer."""
        for track in self._timeline.tracks:
            if track.track_id == track_id:
                track.muted = muted
                break

    def _on_mixer_solo(self, track_id: str, solo: bool):
        """Actualiza solo de un track desde el mixer."""
        for track in self._timeline.tracks:
            if track.track_id == track_id:
                track.solo = solo
                break

    def _invalidar_cache_y_preview(self):
        """
        FIX BUG 2: Invalida el cache de módulos del timeline para el objeto
        actualmente inspeccionado y luego refresca el preview.  Esto garantiza
        que cualquier cambio de parámetro (pos_x, pos_y, color, etc.) se
        refleje de inmediato porque la instancia del módulo se recrea con los
        nuevos valores almacenados en ``mod_item.params``.
        """
        try:
            from core.video_cache import get_global_cache
            cache = get_global_cache()
            obj = self._panel_inspector.objeto_actual
            if isinstance(obj, VideoClip):
                clip_id = getattr(obj, 'clip_id', str(id(obj)))
                cache.clear_clip(clip_id)
            else:
                cache.clear_all()
            # Si es un ModuleTimelineItem, NO borrar su instancia cacheada
            # por defecto. set_config se encarga de aplicar los params en tiempo
            # real sin recrear (y sin volver a cargar el audio con librosa).
            # Solo se recrea si cambia algo estructural (start_time, etc).
        except Exception as e:
            log.debug("Error invalidando cache: %s", e)
        self._actualizar_preview()

    # FIX BUG 3: flag y timer para evitar renders simultáneos /
    # acumulados que hacen que el preview "avance" al aplicar rápido.
    _rendering: bool = False
    _preview_pending: bool = False

    def _actualizar_preview(self, *_args):
        """Actualiza el frame del preview con el estado actual.

        Incluye protección contra re-entrancia y debounce: si ya hay un
        render en curso, se marca como pendiente y se ejecutará una sola
        vez al terminar.  Esto evita que múltiples clics rápidos acumulen
        renders que hagan parecer que el preview se reproduce.
        """
        if not hasattr(self, '_preview') or not self._preview:
            return

        # Si ya estamos renderizando, solo marcar como pendiente
        if self._rendering:
            self._preview_pending = True
            return

        self._rendering = True
        self._preview_pending = False
        try:
            # Siempre usar el tiempo ACTUAL del playhead (no incremental)
            tiempo_actual = 0.0
            if hasattr(self._preview, 'get_tiempo_actual'):
                tiempo_actual = self._preview.get_tiempo_actual()

            # Renderizar el frame compuesto para este tiempo
            frame = self._render_frame_composito(tiempo_actual)

            if frame is not None and hasattr(self._preview, 'mostrar_frame'):
                self._preview.mostrar_frame(frame)
        finally:
            self._rendering = False

        # Si quedó un render pendiente, ejecutarlo *una sola vez* tras
        # un breve delay para que la UI respire.
        if self._preview_pending:
            self._preview_pending = False
            QTimer.singleShot(50, self._actualizar_preview)
    
    def _get_or_create_timeline_module(self, mod_item):
        """
        Obtiene o crea una instancia de módulo para un ModuleTimelineItem.
        Utiliza caché para evitar recrear módulos en cada frame.
        Aplica los parámetros del ModuleTimelineItem a la instancia.
        """
        item_id = mod_item.item_id
        cached = self._timeline_module_cache.get(item_id)
        
        if cached is not None:
            # Verificar que el tipo sigue siendo el mismo
            cached_type = getattr(cached, '_cached_module_type', None)
            if cached_type == mod_item.module_type:
                # Sincronizar parámetros si cambiaron
                if mod_item.params and hasattr(cached, 'set_config'):
                    cached.set_config(mod_item.params)
                return cached
            else:
                # Tipo cambió, recrear
                del self._timeline_module_cache[item_id]
        
        # Crear nueva instancia
        mod_instance = self._module_manager.create_module_instance(mod_item.module_type)
        if mod_instance is None:
            return None
        
        # Habilitar el módulo para que se renderice
        mod_instance.habilitado = True
        mod_instance._habilitado = True
        
        # Aplicar parámetros del ModuleTimelineItem
        if mod_item.params:
            if hasattr(mod_instance, 'set_config'):
                mod_instance.set_config(mod_item.params)
            elif hasattr(mod_instance, '_config'):
                mod_instance._config.update(mod_item.params)
        
        # Para módulos de audio (waveform), preparar audio si hay clips disponibles
        if hasattr(mod_instance, 'prepare_audio') and self._timeline:
            self._prepare_module_audio(mod_instance, mod_item)
        
        # Guardar referencia del tipo para validación de caché
        mod_instance._cached_module_type = mod_item.module_type
        self._timeline_module_cache[item_id] = mod_instance
        return mod_instance

    def _prepare_module_audio(self, mod_instance, mod_item):
        """Prepara el audio de un módulo que lo requiera (ej: waveform)."""
        try:
            # Buscar clips de audio activos en el rango del módulo
            audio_clips = self._timeline.get_audio_clips_at_time(mod_item.start_time)
            if not audio_clips:
                # Buscar cualquier clip de audio en el timeline
                for track in self._timeline.tracks:
                    for clip in track.clips:
                        if clip.source_type in ('audio', 'video') and clip.source_path:
                            audio_clips = [{
                                'path': clip.source_path,
                                'clip_start': clip.start_time,
                                'clip_duration': clip.duration,
                            }]
                            break
                    if audio_clips:
                        break
            
            if audio_clips:
                audio_path = audio_clips[0]['path']
                clip_start = audio_clips[0]['clip_start']
                trim_start = audio_clips[0].get('trim_start', 0.0)
                fps = getattr(self._preview, '_fps', 30)
                duration = mod_item.duration
                
                # Calcular el offset del audio en base a la posición del módulo respecto al clip
                audio_offset = trim_start + max(0, mod_item.start_time - clip_start)
                
                try:
                    mod_instance.prepare_audio(
                        audio_path=audio_path,
                        mel_data=None,
                        sr=None,
                        hop=None,
                        duration=duration,
                        fps=fps,
                        audio_offset=audio_offset
                    )
                except Exception as e:
                    log.debug("Error preparando audio para módulo '%s': %s",
                             mod_item.module_type, e)
        except Exception as e:
            log.debug("Error buscando audio para módulo: %s", e)

    def _render_frame_composito(self, tiempo: float) -> Optional[np.ndarray]:
        """
        Renderiza un frame compuesto del timeline para un tiempo dado.
        Incluye transiciones de clip y módulos posicionados en el timeline.
        
        Args:
            tiempo: Tiempo en segundos desde el inicio del timeline
            
        Returns:
            Frame numpy BGR o None si no hay contenido
        """
        try:
            # Tamaño de preview por defecto
            preview_width = 1280
            preview_height = 720
            
            # Usar el método del timeline que ya aplica transiciones
            frame_composito = self._timeline.get_composite_frame(
                tiempo, preview_width, preview_height
            )
            
            # FIX BUG 2: Eliminado el gate ``has_content`` que impedía que los
            # módulos (globales y de timeline) se renderizaran cuando el frame
            # base era negro (sin clips de video).  Ahora los módulos siempre
            # se aplican, lo que permite que generen contenido propio (formas,
            # texto, waveforms, etc.) y que los cambios de pos_x/pos_y se
            # reflejen inmediatamente.

            # Aplicar módulos globales activos (del ModuleManager)
            if self._module_manager is not None:
                try:
                    frame_composito = self._module_manager.render_all(
                        frame_composito, tiempo, fps=self._preview._fps
                    )
                except Exception as e:
                    log.warning("Error aplicando modulos globales: %s", e)

            # Aplicar módulos posicionados en el timeline
            active_tl_modules = self._timeline.get_active_modules_at_time(tiempo)
            if active_tl_modules and self._module_manager is not None:
                for mod_item in active_tl_modules:
                    try:
                        mod_instance = self._get_or_create_timeline_module(mod_item)
                        if mod_instance and hasattr(mod_instance, 'render'):
                            # Tiempo relativo dentro del módulo
                            mod_time = tiempo - mod_item.start_time
                            frame_composito = mod_instance.render(
                                frame_composito, mod_time, fps=self._preview._fps
                            )
                    except Exception as e:
                        log.debug("Error aplicando módulo timeline '%s': %s",
                                 mod_item.module_type, e)
            
            return frame_composito
            
        except Exception as e:
            logger.error(f"Error renderizando frame: {e}")
            try:
                return np.zeros((720, 1280, 3), dtype=np.uint8)
            except Exception:
                return None

    # -- Callbacks de menu / toolbar -------------------------------------------
    def _nuevo_proyecto(self):
        """Crea un nuevo proyecto vacío usando ProjectManager."""
        self._project_manager.new_project()
        self._timeline = self._project_manager.timeline
        self._cmd_manager = self._project_manager.command_manager
        self._panel_timeline.set_timeline(self._timeline)
        self._panel_inspector.limpiar()
        self._panel_media.limpiar()
        self._panel_mixer.cargar_desde_timeline(self._timeline)
        if hasattr(self._preview, 'set_timeline'):
            self._preview.set_timeline(self._timeline)
        self._toolbar.habilitar_accion("undo", False)
        self._toolbar.habilitar_accion("redo", False)
        self._actualizar_titulo_ventana()
        self._status.showMessage("Nuevo proyecto creado.", 3000)

    def _abrir_proyecto(self):
        """Abre un proyecto .soundvi o .svproj usando ProjectManager."""
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Abrir proyecto Soundvi", "",
            "Proyectos Soundvi (*.soundvi *.svproj *.json);;Soundvi Projects (*.soundvi);;Legacy (*.svproj *.json);;Todos (*)"
        )
        if not ruta:
            return

        ok = self._project_manager.load_project(ruta)
        if ok:
            self._timeline = self._project_manager.timeline
            self._cmd_manager = self._project_manager.command_manager
            self._panel_timeline.set_timeline(self._timeline)
            self._panel_mixer.cargar_desde_timeline(self._timeline)
            if hasattr(self._preview, 'set_timeline'):
                self._preview.set_timeline(self._timeline)
            self._actualizar_duracion_preview()
            self._actualizar_titulo_ventana()
            # Restaurar módulos desde el estado guardado
            self._restaurar_modulos_desde_proyecto()
            # Sincronizar biblioteca de medios
            if hasattr(self._panel_media, 'set_project_manager'):
                self._panel_media.set_project_manager(self._project_manager)
            # Registrar en historial y actualizar menu
            project_history.add_project(ruta, self._project_manager.project_name)
            self._actualizar_menu_recientes()
            self._status.showMessage(
                f"Proyecto abierto: {self._project_manager.project_name}", 3000)
        else:
            QMessageBox.warning(
                self, "Error al abrir",
                f"No se pudo abrir el proyecto:\n{ruta}\n\n"
                "Revisa que el archivo no esté corrupto.")

    def _sincronizar_modules_state(self):
        """Sincroniza el estado de los módulos activos al ProjectManager antes de guardar."""
        if self._module_manager is not None:
            try:
                modules_state = []
                for mod in self._module_manager.get_active_modules():
                    mod_type = None
                    for t_name, t_class in self._module_manager._module_types.items():
                        if isinstance(mod, t_class):
                            mod_type = t_name
                            break
                    if mod_type:
                        modules_state.append({
                            "type": mod_type,
                            "name": getattr(mod, 'nombre', ''),
                            "enabled": getattr(mod, 'habilitado', True),
                            "layer": getattr(mod, 'capa', 0),
                            "config": mod.get_config() if hasattr(mod, 'get_config') else {},
                        })
                self._project_manager.modules_state = modules_state
            except Exception as e:
                log.warning("Error sincronizando estado de módulos: %s", e)

    def _restaurar_modulos_desde_proyecto(self):
        """Restaura instancias de módulos desde el estado guardado en el proyecto."""
        if self._module_manager is None:
            return
        try:
            modules_state = self._project_manager.modules_state
            if not modules_state:
                return
            for mod_data in modules_state:
                mod_type = mod_data.get("type", "")
                if not mod_type:
                    continue
                mod = self._module_manager.create_module_instance(mod_type)
                if mod:
                    mod.nombre = mod_data.get("name", mod.nombre)
                    mod.habilitado = mod_data.get("enabled", True)
                    mod.capa = mod_data.get("layer", 0)
                    config = mod_data.get("config", {})
                    if config and hasattr(mod, 'set_config'):
                        mod.set_config(config)
                    self._module_manager.add_module_instance(mod)
            log.info("Restaurados %d módulos desde el proyecto", len(modules_state))
        except Exception as e:
            log.warning("Error restaurando módulos desde proyecto: %s", e)

    def _guardar_proyecto(self):
        """Guarda el proyecto actual en formato .soundvi."""
        if not self._project_manager.project_path:
            self._guardar_como()
            return
        
        # Sincronizar módulos antes de guardar
        self._sincronizar_modules_state()
        
        # Sincronizar biblioteca de medios antes de guardar
        if hasattr(self._panel_media, 'sincronizar_con_project_manager'):
            media_items = self._panel_media.sincronizar_con_project_manager()
            if media_items:
                self._project_manager.media_library = media_items
        
        # Guardar directamente sin preguntar (Ctrl+S rápido)
        # embed_media=False por defecto para guardado rápido
        ok = self._project_manager.save_project()
        
        if ok:
            # Registrar en historial y actualizar menu
            project_history.add_project(
                self._project_manager.project_path,
                self._project_manager.project_name)
            self._actualizar_menu_recientes()
            # Guardar modulos activos
            if self._module_manager is not None:
                try:
                    self._module_manager.save_all_modules()
                except Exception as e:
                    log.warning("Error guardando modulos: %s", e)
            self._actualizar_titulo_ventana()
            
            # Mostrar información del guardado
            file_size = os.path.getsize(self._project_manager.project_path) if os.path.exists(self._project_manager.project_path) else 0
            size_mb = file_size / 1024 / 1024
            self._status.showMessage(
                f"Proyecto guardado: {os.path.basename(self._project_manager.project_path)} ({size_mb:.2f} MB)",
                5000)
        else:
            QMessageBox.warning(
                self, "Error al guardar",
                "No se pudo guardar el proyecto.\nVerifica permisos de escritura.")

    def _guardar_como(self):
        """Guarda el proyecto con un nuevo nombre/ruta en formato .soundvi."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        
        # Diálogo para guardar como .soundvi
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar proyecto como", "",
            "Soundvi Projects (*.soundvi);;Todos los archivos (*)"
        )
        if not ruta:
            return
        
        # Forzar formato .soundvi siempre
        if not ruta.endswith('.soundvi'):
            ruta += '.soundvi'
        
        # Actualizar nombre del proyecto
        self._project_manager.project_name = os.path.splitext(os.path.basename(ruta))[0]
        
        # Guardado directo sin preguntar
        embed_media = False
        
        # Sincronizar módulos antes de guardar
        self._sincronizar_modules_state()
        
        # Sincronizar biblioteca de medios antes de guardar
        if hasattr(self._panel_media, 'sincronizar_con_project_manager'):
            media_items = self._panel_media.sincronizar_con_project_manager()
            if media_items:
                self._project_manager.media_library = media_items
        
        # Guardar proyecto
        ok = self._project_manager.save_project(ruta, embed_media=embed_media)
        if ok:
            project_history.add_project(ruta, self._project_manager.project_name)
            self._actualizar_menu_recientes()
            if self._module_manager is not None:
                try:
                    self._module_manager.save_all_modules()
                except Exception as e:
                    log.warning("Error guardando modulos: %s", e)
            
            # Mostrar información del guardado
            file_size = os.path.getsize(ruta) if os.path.exists(ruta) else 0
            size_mb = file_size / 1024 / 1024
            self._status.showMessage(
                f"Proyecto guardado: {os.path.basename(ruta)} ({size_mb:.2f} MB)",
                5000)
            self._actualizar_titulo_ventana()
            self._status.showMessage(
                f"Guardado como: {os.path.basename(ruta)}", 3000)
        else:
            QMessageBox.warning(
                self, "Error al guardar",
                f"No se pudo guardar en:\n{ruta}\nVerifica permisos de escritura.")

    def _actualizar_titulo_ventana(self):
        """Actualiza el título de la ventana con el nombre del proyecto."""
        nombre = self._project_manager.project_name or "Sin titulo"
        try:
            mod_flag = self._project_manager.is_modified
        except TypeError:
            mod_flag = False
        modificado = " *" if mod_flag else ""
        self.setWindowTitle(f"Soundvi — {nombre}{modificado}")

    def _actualizar_menu_recientes(self):
        """Actualiza el submenú de proyectos recientes."""
        self._menu_recientes.clear()
        recientes = project_history.get_recent_projects(limit=10)
        if not recientes:
            act = QAction("(sin proyectos recientes)", self)
            act.setEnabled(False)
            self._menu_recientes.addAction(act)
            return
        for proyecto in recientes:
            ruta = proyecto.get("path", "")
            nombre = proyecto.get("name", os.path.basename(ruta))
            act = QAction(f"{nombre}  —  {ruta}", self)
            act.triggered.connect(lambda checked, r=ruta: self._abrir_proyecto_reciente(r))
            self._menu_recientes.addAction(act)
        self._menu_recientes.addSeparator()
        act_limpiar = QAction("Limpiar historial", self)
        act_limpiar.triggered.connect(self._limpiar_historial_recientes)
        self._menu_recientes.addAction(act_limpiar)

    def _abrir_proyecto_reciente(self, ruta: str):
        """Abre un proyecto desde el menú de recientes."""
        if not os.path.exists(ruta):
            QMessageBox.warning(self, "Archivo no encontrado",
                                f"El archivo ya no existe:\n{ruta}")
            project_history.remove_project(ruta)
            self._actualizar_menu_recientes()
            return
        ok = self._project_manager.load_project(ruta)
        if ok:
            self._timeline = self._project_manager.timeline
            self._cmd_manager = self._project_manager.command_manager
            self._panel_timeline.set_timeline(self._timeline)
            self._panel_mixer.cargar_desde_timeline(self._timeline)
            if hasattr(self._preview, 'set_timeline'):
                self._preview.set_timeline(self._timeline)
            self._actualizar_duracion_preview()
            self._actualizar_titulo_ventana()
            # Restaurar módulos desde el estado guardado
            self._restaurar_modulos_desde_proyecto()
            project_history.add_project(ruta, self._project_manager.project_name)
            self._actualizar_menu_recientes()
            self._status.showMessage(
                f"Proyecto abierto: {self._project_manager.project_name}", 3000)
        else:
            QMessageBox.warning(self, "Error al abrir",
                                f"No se pudo abrir: {ruta}")

    def _limpiar_historial_recientes(self):
        """Limpia el historial de proyectos recientes."""
        project_history.clear_history()
        self._actualizar_menu_recientes()
        self._status.showMessage("Historial de proyectos recientes limpiado.", 3000)

    def _importar_medios(self):
        """Abre el dialogo de importacion de medios."""
        self._panel_media._importar_archivos()

    def _abrir_exportar_dialog(self):
        """Abre el dialogo de exportacion de video."""
        dialog = ExportDialog(self._pm, parent=self)
        dialog.exportacion_completada.connect(
            lambda ruta: self._status.showMessage(
                f"Video exportado: {os.path.basename(ruta)}", 5000))
        dialog.exec()

    def _abrir_settings_dialog(self):
        """Abre el dialogo de configuracion."""
        dialog = SettingsDialog(self._pm, parent=self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()

    def _on_settings_changed(self, settings: dict):
        """Aplica cambios de configuracion y los persiste."""
        # Mapeo de temas
        tema_map = {"Oscuro": "darkly", "Claro": "claro", "Midnight": "midnight", "Forest": "forest"}
        tema_nombre = settings.get("tema", "Oscuro")
        tema_clave = tema_map.get(tema_nombre, "darkly")
        
        if tema_clave != self._temas.tema_actual:
            self._temas.aplicar_tema(tema_clave)
            # Guardar tema en preferencias de usuario
            try:
                from utils.config import load_user_prefs, save_user_prefs
                prefs = load_user_prefs()
                prefs["tema"] = tema_clave
                save_user_prefs(prefs)
            except Exception as e:
                log.warning("No se pudo guardar tema en preferencias: %s", e)

        # Actualizar snap del timeline
        self._timeline.snap_enabled = settings.get("snap_habilitado", True)

        self._status.showMessage("Configuracion aplicada.", 3000)

    def _deshacer(self):
        desc = self._cmd_manager.undo()
        if desc:
            self._panel_timeline.refrescar()
            self._status.showMessage(f"Deshacer: {desc}", 2000)
        else:
            self._status.showMessage("Nada que deshacer.", 2000)

    def _rehacer(self):
        desc = self._cmd_manager.redo()
        if desc:
            self._panel_timeline.refrescar()
            self._status.showMessage(f"Rehacer: {desc}", 2000)
        else:
            self._status.showMessage("Nada que rehacer.", 2000)

    def _dividir_clip(self):
        """Divide el clip seleccionado en la posicion del playhead."""
        self._panel_timeline.dividir_clip_en_playhead()

    def _eliminar_clip_seleccionado(self):
        """Elimina el clip seleccionado del timeline con confirmación segun nivel."""
        if self._adapter.confirmar_accion_destructiva(
            self, "Eliminar clip",
            "¿Estás seguro de que quieres eliminar el clip seleccionado?"
        ):
            self._panel_timeline.eliminar_clip_seleccionado()

    def _cortar_clip(self):
        self._panel_timeline.copiar_seleccion()
        self._panel_timeline.eliminar_clip_seleccionado()

    def _copiar_clip(self):
        self._panel_timeline.copiar_seleccion()

    def _pegar_clip(self):
        self._panel_timeline.pegar_clips()

    def _play(self):
        """Inicia la reproduccion."""
        if hasattr(self._preview, 'play'):
            self._preview.play()
        elif hasattr(self._preview, '_reproducir'):
            self._preview._reproducir()
        self._panel_mixer.iniciar_monitoreo()
        self._status.showMessage("Reproduciendo...", 2000)

    def _pause(self):
        """Pausa la reproduccion."""
        if hasattr(self._preview, 'pause'):
            self._preview.pause()
        elif hasattr(self._preview, '_pausar'):
            self._preview._pausar()
        self._panel_mixer.detener_monitoreo()
        self._status.showMessage("Pausado.", 2000)

    def _stop(self):
        """Detiene la reproduccion."""
        if hasattr(self._preview, 'stop'):
            self._preview.stop()
        elif hasattr(self._preview, '_detener'):
            self._preview._detener()
        self._panel_mixer.detener_monitoreo()
        self._status.showMessage("Detenido.", 2000)

    def _actualizar_duracion_preview(self):
        """Actualiza la duracion de la preview basada en el timeline."""
        if hasattr(self._preview, 'set_duracion') and hasattr(self._timeline, 'duration'):
            # Obtener la duracion maxima de todos los tracks
            max_duration = 0.0
            for track in self._timeline.tracks:
                track_duration = track.total_duration if hasattr(track, 'total_duration') else 0.0
                if track_duration > max_duration:
                    max_duration = track_duration
            
            # Si no hay clips, usar una duracion minima
            if max_duration <= 0:
                max_duration = 10.0  # 10 segundos por defecto
            
            # Establecer la duracion en la preview
            self._preview.set_duracion(max_duration, fps=30)

    def _zoom_in(self):
        """Acerca el zoom del timeline."""
        self._timeline.zoom_in()
        self._panel_timeline.refrescar()

    def _zoom_out(self):
        """Aleja el zoom del timeline."""
        self._timeline.zoom_out()
        self._panel_timeline.refrescar()

    def _zoom_fit(self):
        """Ajusta el zoom para ver todo el timeline."""
        self._timeline.zoom_to_fit(self._panel_timeline.width())
        self._panel_timeline.refrescar()

    def _gestor_modulos(self):
        """Muestra información sobre los módulos cargados."""
        if self._module_manager is not None:
            tipos = self._module_manager.get_module_types()
            activos = self._module_manager.get_active_modules()
            info = (f"Tipos de módulos disponibles: {len(tipos)}\n"
                    f"Módulos activos: {len(activos)}\n\n"
                    f"Los módulos están integrados en el panel 'Módulos' (sidebar izquierdo).\n"
                    f"Haz doble click en un módulo para activarlo.")
            if activos:
                info += "\n\nMódulos activos:\n"
                for m in activos:
                    info += f"  • {m.nombre} (capa {m.capa})\n"
        else:
            info = "El gestor de módulos no está disponible."
        QMessageBox.information(self, "⧉ Gestor de Módulos", info)

    def _instalar_plugin(self):
        """Permite instalar un plugin externo desde archivo .py."""
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar plugin", "",
            "Archivos Python (*.py);;Todos (*)"
        )
        if ruta and os.path.isfile(ruta):
            try:
                self._registro_plugins._cargar_plugin_desde_archivo(ruta)
                QMessageBox.information(
                    self, "Plugin instalado",
                    f"Plugin cargado desde:\n{os.path.basename(ruta)}\n\n"
                    "Revisa el panel de Módulos para activarlo.")
            except Exception as e:
                QMessageBox.warning(
                    self, "Error",
                    f"No se pudo cargar el plugin:\n{e}")

    def _cambiar_perfil(self):
        from gui.qt6.profile_selector import mostrar_selector_perfil
        from gui.qt6.theme import AdministradorTemas
        from utils.config import load_user_prefs
        resultado = mostrar_selector_perfil(self._pm, primer_inicio=False, parent=self)
        if resultado:
            # Actualizar nivel del adaptador (dispara senal nivel_cambiado)
            self._adapter.actualizar_nivel(self._pm)
            self._aplicar_perfil()
            self._aplicar_adaptaciones_nivel()
            self._panel_sidebar.refrescar()
            self._panel_mixer.cargar_desde_timeline(self._timeline)
            # Actualizar inspector y toolbar con nuevo adaptador
            self._panel_inspector.set_adapter(self._adapter)
            self._toolbar.set_adapter(self._adapter)
            # Aplicar tema si cambio
            temas = AdministradorTemas()
            prefs = load_user_prefs()
            tema_elegido = prefs.get("tema", "darkly")
            if tema_elegido != temas.tema_actual:
                temas.aplicar_tema(tema_elegido)
            self._status.showMessage(
                f"Perfil cambiado a: {self._pm.perfil_activo.nombre} "
                f"(nivel: {self._adapter.nivel})", 3000
            )

    def _acerca_de(self):
        """Muestra el dialogo About con Zoundvi."""
        dlg = AboutDialog(self)
        dlg.exec()

    # -- Cierre ----------------------------------------------------------------
    def closeEvent(self, event):
        # Easter egg: Zoundvi durmiendo en dialogo de salida
        import random
        _sleeping_path = os.path.join(_RAIZ, "multimedia", "zoundvi", "zoundvi_coffee.png")
        msg = QMessageBox(self)
        
        # Titulos aleatorios sarcásticos
        titulos = [
            "¿Ya te vas, cobarde?",
            "Hora de abandonar el barco",
            "Así que vas a huir...",
            "Ragequit mode: ON",
            "No me digas que te rindes",
            "Pero si apenas empezabas..."
        ]
        
        # Mensajes principales random
        mensajes = [
            "¿Seguro que quieres salir?\n\nZoundvi aún no termina su café (y tampoco tú tu video).",
            "¿Ya te vas?\n\nEsto es más triste que el final de Toy Story 3.",
            "¿Te rindes tan fácil?\n\nNi que fueras español en un Mundial.",
            "¿Salir ahora?\n\nPero si ni has guardado, animal.",
            "¿Cerrando la app?\n\nZoundvi te va a extrañar (no te creas).",
        ]
        
        # Textos informativos sarcásticos
        informativos = [
            "(Todo lo que no guardaste se irá a la verga)",
            "(Spoiler: vas a perder todo lo que hiciste)",
            "(Tu proyecto se autodestruirá en 3... 2... 1...)",
            "(RIP a las 3 horas que le dedicaste a esto)",
            "(F en el chat por tu trabajo no guardado)",
        ]
        
        msg.setWindowTitle(random.choice(titulos))
        msg.setText(random.choice(mensajes))
        msg.setInformativeText(random.choice(informativos))
        
        if os.path.isfile(_sleeping_path):
            px = QPixmap(_sleeping_path).scaled(
                80, 80, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            msg.setIconPixmap(px)
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        btn_yes = msg.button(QMessageBox.StandardButton.Yes)
        
        # Botones random sarcásticos
        btn_yes_texts = ["Me voy ALV", "Adiós mundo cruel", "Fuck this shit I'm out", 
                         "Chao pescao", "Ya me cansé", "Ragequit"]
        btn_no_texts = ["Nel pastel", "Mejor no", "Me quedo un rato más", 
                        "Todavía no", "Simón, sigo", "Aguanto vara"]
        
        btn_yes.setText(random.choice(btn_yes_texts))
        btn_no = msg.button(QMessageBox.StandardButton.No)
        btn_no.setText(random.choice(btn_no_texts))

        if msg.exec() == QMessageBox.StandardButton.Yes:
            self._panel_mixer.detener_monitoreo()
            self._pm.guardar_seleccion()
            # Guardar módulos activos al cerrar
            if self._module_manager is not None:
                try:
                    self._module_manager.save_all_modules()
                except Exception:
                    pass
            event.accept()
        else:
            event.ignore()

    # (nuevo proyecto movido arriba a la seccion de callbacks)
