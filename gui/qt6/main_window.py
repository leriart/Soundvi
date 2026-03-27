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

from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QToolBar, QStatusBar, QDockWidget,
    QMenuBar, QMenu, QFileDialog, QMessageBox, QSplitter,
    QFrame, QSizePolicy, QTabWidget
)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QIcon, QKeySequence, QPixmap

# Ruta raiz
_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _RAIZ) if _RAIZ not in sys.path else None

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

        # Sistemas de backend compartidos
        self._timeline = Timeline()
        self._cmd_manager = CommandManager()
        self._keyframe_animator = KeyframeAnimator()

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

        # Cargar mixer con tracks del timeline
        self._panel_mixer.cargar_desde_timeline(self._timeline)

        # Conectar cambio de nivel
        self._adapter.nivel_cambiado.connect(self._on_nivel_cambiado)

        # Mostrar wizard de bienvenida si es novato y primer inicio
        self._mostrar_wizard_si_necesario()

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
                f"  {perfil.icono} {perfil.nombre} ({nivel_txt})  |  Soundvi v5.1  "
            )
        else:
            self._lbl_perfil.setText("  Soundvi v5.1  ")
        self._status.showMessage("Listo.", 3000)

    # -- Paneles / Dock widgets ------------------------------------------------
    def _crear_paneles(self):
        # Widget central: Preview
        self._preview = PreviewWidget()
        self.setCentralWidget(self._preview)

        # -- Dock: Sidebar de Modulos (izquierda) --
        self._panel_sidebar = SidebarWidget(self._pm)
        self._dock_sidebar = self._crear_dock("Modulos", self._panel_sidebar,
                                               Qt.DockWidgetArea.LeftDockWidgetArea)

        # -- Dock: Media Library (izquierda, tabulada con sidebar) --
        self._panel_media = MediaLibraryWidget()
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
        self.addDockWidget(area, dock)
        return dock

    # -- Conectar senales entre widgets ----------------------------------------
    def _conectar_senales(self):
        """Conecta las senales entre los diferentes widgets."""
        # Timeline -> Preview: sincronizar playhead
        self._panel_timeline.playhead_changed.connect(self._on_playhead_changed)

        # Timeline -> Inspector: mostrar propiedades del clip seleccionado
        self._panel_timeline.clip_selected.connect(self._on_clip_selected)

        # Preview -> Timeline: sincronizar playhead desde preview
        self._preview.tiempo_cambiado.connect(self._panel_timeline.set_playhead)
        self._preview.tiempo_cambiado.connect(self._panel_keyframes.set_playhead)

        # Inspector -> Preview: actualizar preview al cambiar propiedades
        self._panel_inspector.preview_requested.connect(self._actualizar_preview)

        # Inspector -> Timeline: refrescar al cambiar propiedades de clip
        self._panel_inspector.property_changed.connect(
            lambda p, v: self._panel_timeline.refrescar())

        # Transiciones -> Timeline: aplicar transicion
        self._panel_transiciones.transition_applied.connect(self._on_transicion_aplicada)

        # Keyframes -> actualizar preview
        self._panel_keyframes.keyframe_changed.connect(self._actualizar_preview)

        # Track cambiado -> refrescar inspector
        self._panel_timeline.track_changed.connect(
            lambda t: self._panel_inspector.mostrar_track(t) if t else None)

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
                "💡 Tip: Importa medios con Ctrl+I, luego arrástralos al timeline.", 8000
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
            # Verificar si ya completó el wizard antes
            prefs_path = os.path.join(_RAIZ, "user_preferences.json")
            try:
                if os.path.isfile(prefs_path):
                    with open(prefs_path, "r", encoding="utf-8") as f:
                        prefs = json.load(f)
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
        prefs_path = os.path.join(_RAIZ, "user_preferences.json")
        try:
            prefs = {}
            if os.path.isfile(prefs_path):
                with open(prefs_path, "r", encoding="utf-8") as f:
                    prefs = json.load(f)
            prefs["wizard_completado"] = True
            with open(prefs_path, "w", encoding="utf-8") as f:
                json.dump(prefs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.warning("No se pudo guardar estado del wizard: %s", e)
        self._status.showMessage("¡Bienvenido a Soundvi! 🎬", 5000)

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
                "💡 Importa medios primero, luego arrástralos al timeline.", 5000
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

    def _on_transicion_aplicada(self, tipo: str, duracion: float):
        """Aplica una transicion entre clips seleccionados."""
        self._status.showMessage(
            f"Transicion aplicada: {tipo} ({duracion:.1f}s)", 3000)

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

    def _on_modulo_aplicado(self, type_key: str):
        """Aplica un modulo al clip seleccionado desde la sidebar."""
        self._status.showMessage(f"Modulo aplicado: {type_key}", 3000)

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

    def _actualizar_preview(self):
        """Actualiza el frame del preview con el estado actual."""
        # Placeholder - en implementacion completa renderizaria el frame compuesto
        pass

    # -- Callbacks de menu / toolbar -------------------------------------------
    def _nuevo_proyecto(self):
        self._timeline = Timeline()
        self._cmd_manager.clear()
        self._panel_timeline.set_timeline(self._timeline)
        self._panel_inspector.limpiar()
        self._panel_media.limpiar()
        self._panel_mixer.cargar_desde_timeline(self._timeline)
        self._status.showMessage("Nuevo proyecto creado.", 3000)

    def _abrir_proyecto(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Abrir proyecto Soundvi", "",
            "Proyectos Soundvi (*.svproj *.json);;Todos (*)"
        )
        if ruta:
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                if "tracks" in datos:
                    self._timeline = Timeline.from_dict(datos)
                    self._panel_timeline.set_timeline(self._timeline)
                    self._panel_mixer.cargar_desde_timeline(self._timeline)
                    self._status.showMessage(f"Proyecto abierto: {os.path.basename(ruta)}", 3000)
                else:
                    self._status.showMessage(f"Proyecto abierto: {os.path.basename(ruta)}", 3000)
            except Exception as e:
                import random
                titulos_error = ["Oops 💥", "Houston, we have a problem", "Error 69", "Algo salió mal", "Bruh momento"]
                QMessageBox.warning(self, random.choice(titulos_error), 
                    f"No se pudo abrir el proyecto:\n{e}\n\nPista: revisa que el archivo no esté corrupto.")
            

    def _guardar_proyecto(self):
        self._status.showMessage("Proyecto guardado.", 3000)

    def _guardar_como(self):
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar proyecto como", "",
            "Proyectos Soundvi (*.svproj);;JSON (*.json)"
        )
        if ruta:
            try:
                datos = self._timeline.to_dict()
                with open(ruta, "w", encoding="utf-8") as f:
                    json.dump(datos, f, indent=2, ensure_ascii=False)
                self._status.showMessage(f"Guardado como: {os.path.basename(ruta)}", 3000)
            except Exception as e:
                import random
                titulos_error_save = ["Save failed", "RIP archivo 💀", "Error al guardar", "Guardado? Nel", "F"]
                QMessageBox.warning(self, random.choice(titulos_error_save), 
                    f"No se pudo guardar:\n{e}\n\nSugerencia: verifica permisos de escritura o espacio en disco.")

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
        """Aplica cambios de configuracion."""
        # Cambiar tema si es necesario
        tema = settings.get("tema", "Oscuro")
        if tema == "Oscuro":
            self._temas.aplicar_tema("darkly")
        else:
            self._temas.aplicar_tema("claro")

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
        self._preview.play()
        self._panel_mixer.iniciar_monitoreo()
        self._status.showMessage("Reproduciendo...", 2000)

    def _pause(self):
        """Pausa la reproduccion."""
        self._preview.pause()
        self._panel_mixer.detener_monitoreo()
        self._status.showMessage("Pausado.", 2000)

    def _stop(self):
        """Detiene la reproduccion."""
        self._preview.stop()
        self._panel_mixer.detener_monitoreo()
        self._status.showMessage("Detenido.", 2000)

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
        QMessageBox.information(self, "Gestor de Módulos 📦",
                                "Los módulos ya están integrados en el sidebar.\n\n"
                                "Tip: Mira el panel 'Módulos' a la izquierda.\n"
                                "No es magia, pero casi. ✨")

    def _instalar_plugin(self):
        QMessageBox.information(self, "Instalador de Plugins 🔌",
                                "Sistema de plugins: Coming Soon™\n\n"
                                "Pronto podrás cargar archivos .py externos.\n"
                                "Mientras tanto, usa los módulos incluidos.\n\n"
                                "Status: En el backlog desde 2024 😅")

    def _cambiar_perfil(self):
        from gui.qt6.profile_selector import mostrar_selector_perfil, obtener_tema_guardado
        from gui.qt6.theme import AdministradorTemas
        resultado = mostrar_selector_perfil(self._pm, primer_inicio=False, parent=self)
        if resultado:
            # Actualizar nivel del adaptador (dispara señal nivel_cambiado)
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
            tema_elegido = obtener_tema_guardado()
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
            event.accept()
        else:
            event.ignore()
