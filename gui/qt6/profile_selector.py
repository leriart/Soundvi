# -*- coding: utf-8 -*-
"""
Soundvi Qt6 -- Selector de perfil mejorado al inicio.

Dialogo modal con tarjetas visuales atractivas para seleccion de perfil,
selector de tema visual, y deteccion de usuario nuevo con experiencia
paso a paso. Se muestra en el primer inicio o cuando el usuario quiere
cambiar de perfil desde el menu de configuracion.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QCheckBox, QWidget, QSizePolicy, QGridLayout,
    QGroupBox, QGraphicsDropShadowEffect, QApplication,
    QStackedWidget, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QFont, QColor, QPixmap

# Ruta raiz del proyecto
_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _RAIZ) if _RAIZ not in sys.path else None

from core.profiles import ProfileManager, Perfil
from utils.config import (
    load_user_prefs, save_user_prefs, is_first_launch,
    get_user_prefs_path
)


# ---------------------------------------------------------------------------
#  Funciones de compatibilidad (delegates al nuevo sistema de config)
# ---------------------------------------------------------------------------

def cargar_preferencias() -> Dict[str, Any]:
    """Carga preferencias de usuario. Delegate al nuevo sistema."""
    return load_user_prefs()


def guardar_preferencias(prefs: Dict[str, Any]):
    """Guarda preferencias de usuario. Delegate al nuevo sistema."""
    save_user_prefs(prefs)


def es_primer_inicio() -> bool:
    """Retorna True si es el primer inicio."""
    return is_first_launch()


def obtener_tema_guardado() -> str:
    """Retorna el tema guardado en preferencias, o 'darkly' por defecto."""
    prefs = load_user_prefs()
    return prefs.get("tema", "darkly")


def obtener_perfil_guardado() -> str:
    """Retorna el perfil guardado en preferencias, o '' si no existe."""
    prefs = load_user_prefs()
    return prefs.get("perfil", "")


# ---------------------------------------------------------------------------
#  Datos descriptivos de perfiles para la UI
# ---------------------------------------------------------------------------

PERFILES_UI_INFO: Dict[str, Dict[str, Any]] = {
    "basico": {
        "icono": "▶",  # Triangulo de reproduccion (U+25B6)
        "titulo": "Novato",
        "subtitulo": "Interfaz simplificada",
        "descripcion": "Ideal para comenzar. Solo las herramientas\nesenciales con guías paso a paso.",
        "color_acento": "#00BC8C",
        "color_fondo": "#1a3a2a",
        "caracteristicas": [
            "✓ Cortar y recortar video",
            "✓ Preview en tiempo real",
            "✓ Exportación rápida",
            "✓ Asistente guiado",
        ],
        "recomendado_para": "Usuarios que nunca han editado video",
    },
    "creador": {
        "icono": "✦",  # Estrella de cuatro puntas (U+2726)
        "titulo": "Intermedio",
        "subtitulo": "Balance perfecto",
        "descripcion": "Para creadores de contenido. Transiciones,\nefectos, audio y subtítulos.",
        "color_acento": "#3498DB",
        "color_fondo": "#1a2a3a",
        "caracteristicas": [
            "✓ Transiciones y efectos",
            "✓ Color grading básico",
            "✓ Subtítulos con IA",
            "✓ Inspector de propiedades",
        ],
        "recomendado_para": "Creadores de contenido y YouTubers",
    },
    "profesional": {
        "icono": "26A1",
        "titulo": "Profesional",
        "subtitulo": "Todas las opciones",
        "descripcion": "Sin restricciones. Keyframes, audio reactivo,\nGPU, todo desbloqueado.",
        "color_acento": "#E74C3C",
        "color_fondo": "#3a1a1a",
        "caracteristicas": [
            "✓ Audio reactivo avanzado",
            "✓ Keyframes y animación",
            "✓ Aceleración GPU",
            "✓ Consola Python",
        ],
        "recomendado_para": "Editores experimentados y profesionales",
    },
    "personalizado": {
        "icono": "⚙",
        "titulo": "Personalizado",
        "subtitulo": "Tú decides",
        "descripcion": "Selecciona exactamente los módulos y\npaneles que necesitas.",
        "color_acento": "#F39C12",
        "color_fondo": "#3a2a1a",
        "caracteristicas": [
            "✓ Módulos a la carta",
            "✓ Paneles configurables",
            "✓ Sin límites predefinidos",
            "✓ Control total",
        ],
        "recomendado_para": "Usuarios que saben lo que quieren",
    },
}


# ---------------------------------------------------------------------------
#  Widget: Tarjeta de perfil
# ---------------------------------------------------------------------------

class TarjetaPerfil(QFrame):
    """Tarjeta visual moderna para un perfil individual."""

    seleccionado = pyqtSignal(str)

    def __init__(self, clave: str, info: Dict[str, Any],
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._clave = clave
        self._info = info
        self._activo = False

        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(210, 320)
        self.setObjectName(f"tarjeta_{clave}")
        self._construir_ui()
        self._actualizar_estilo()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        # Icono grande
        icono_lbl = QLabel(self._info["icono"])
        icono_lbl.setFont(QFont("Segoe UI Emoji", 32))
        icono_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icono_lbl.setStyleSheet("background: transparent;")
        layout.addWidget(icono_lbl)

        # Titulo
        titulo_lbl = QLabel(self._info["titulo"])
        titulo_lbl.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        titulo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo_lbl.setStyleSheet(
            f"color: {self._info['color_acento']}; background: transparent;"
        )
        layout.addWidget(titulo_lbl)

        # Subtitulo
        sub_lbl = QLabel(self._info["subtitulo"])
        sub_lbl.setFont(QFont("Segoe UI", 9))
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_lbl.setStyleSheet("color: #ADB5BD; background: transparent;")
        layout.addWidget(sub_lbl)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {self._info['color_acento']}40;")
        layout.addWidget(sep)

        # Descripcion
        desc_lbl = QLabel(self._info["descripcion"])
        desc_lbl.setWordWrap(True)
        desc_lbl.setFont(QFont("Segoe UI", 9))
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setStyleSheet("color: #8E959C; background: transparent;")
        layout.addWidget(desc_lbl)

        layout.addSpacing(2)

        # Caracteristicas
        for feat in self._info["caracteristicas"]:
            feat_lbl = QLabel(feat)
            feat_lbl.setFont(QFont("Segoe UI", 8))
            feat_lbl.setStyleSheet(
                "color: #CED4DA; background: transparent; padding-left: 4px;"
            )
            layout.addWidget(feat_lbl)

        layout.addStretch()

        # Recomendado para
        rec_lbl = QLabel(f"→ {self._info.get('recomendado_para', '')}")
        rec_lbl.setFont(QFont("Segoe UI", 8))
        rec_lbl.setWordWrap(True)
        rec_lbl.setStyleSheet("color: #6C757D; background: transparent; font-style: italic;")
        layout.addWidget(rec_lbl)

    def _actualizar_estilo(self):
        acento = self._info["color_acento"]
        fondo_card = self._info["color_fondo"]
        if self._activo:
            self.setStyleSheet(f"""
                QFrame#{self.objectName()} {{
                    background-color: {fondo_card};
                    border: 2px solid {acento};
                    border-radius: 12px;
                }}
            """)
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(25)
            shadow.setColor(QColor(acento))
            shadow.setOffset(0, 0)
            self.setGraphicsEffect(shadow)
        else:
            self.setStyleSheet(f"""
                QFrame#{self.objectName()} {{
                    background-color: #2B3035;
                    border: 1px solid #495057;
                    border-radius: 12px;
                }}
                QFrame#{self.objectName()}:hover {{
                    border: 1px solid {acento}80;
                    background-color: #343A40;
                }}
            """)
            self.setGraphicsEffect(None)

    def set_activo(self, activo: bool):
        self._activo = activo
        self._actualizar_estilo()

    def mousePressEvent(self, event):
        self.seleccionado.emit(self._clave)
        super().mousePressEvent(event)

    @property
    def clave_perfil(self) -> str:
        return self._clave


# ---------------------------------------------------------------------------
#  Widget: Selector de tema mejorado
# ---------------------------------------------------------------------------

class SelectorTema(QFrame):
    """Widget para elegir entre todos los temas disponibles con preview visual."""

    tema_cambiado = pyqtSignal(str)

    def __init__(self, tema_actual: str = "darkly",
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._tema = tema_actual
        self.setObjectName("selectorTema")
        self._construir_ui()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Título
        lbl = QLabel("✎ Tema visual:")
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #ADB5BD; background: transparent;")
        layout.addWidget(lbl)

        # Grid de botones de temas
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(8)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        
        # Obtener todos los temas disponibles
        from .theme import AdministradorTemas
        tema_manager = AdministradorTemas()
        temas = tema_manager.listar_temas_nombres()
        
        # Crear botones para cada tema
        self.botones_temas = {}
        temas_items = list(temas.items())
        
        for i, (tema_id, tema_nombre) in enumerate(temas_items):
            row = i // 2
            col = i % 2
            
            btn = QPushButton(tema_nombre)
            btn.setFixedSize(140, 40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("tema_id", tema_id)
            btn.clicked.connect(lambda checked, tid=tema_id: self._seleccionar(tid))
            
            self.botones_temas[tema_id] = btn
            grid_layout.addWidget(btn, row, col)
        
        layout.addWidget(grid_widget)
        
        # Información
        info = QLabel("Los cambios se aplican inmediatamente")
        info.setFont(QFont("Segoe UI", 9))
        info.setStyleSheet("color: #6C757D; background: transparent;")
        layout.addWidget(info)
        
        self._actualizar_botones()

    def _seleccionar(self, tema: str):
        self._tema = tema
        self._actualizar_botones()
        self.tema_cambiado.emit(tema)
        
        # Aplicar tema inmediatamente
        from .theme import AdministradorTemas
        tema_manager = AdministradorTemas()
        tema_manager.aplicar_tema(tema)
        
        # Guardar en preferencias
        try:
            from utils.config import load_user_prefs, save_user_prefs
            prefs = load_user_prefs()
            prefs["tema"] = tema
            save_user_prefs(prefs)
        except Exception:
            pass  # Silenciar errores de configuración

    def _actualizar_botones(self):
        """Actualiza los estilos de todos los botones según el tema activo."""
        from .theme import TEMAS
        
        tema_activo = TEMAS.get(self._tema, TEMAS.get("darkly"))
        
        for tema_id, btn in self.botones_temas.items():
            if tema_id == self._tema:
                # Botón activo
                estilo = f"""
                    QPushButton {{
                        background-color: {tema_activo.primario};
                        color: #FFFFFF;
                        border: 2px solid {tema_activo.primario};
                        border-radius: 8px;
                        font-weight: bold;
                        font-size: 12px;
                    }}
                    QPushButton:hover {{
                        background-color: {tema_activo.primario_hover};
                        border: 2px solid {tema_activo.primario_hover};
                    }}
                """
            else:
                # Botón inactivo
                estilo = f"""
                    QPushButton {{
                        background-color: {tema_activo.fondo_input};
                        color: {tema_activo.texto_secundario};
                        border: 1px solid {tema_activo.borde};
                        border-radius: 8px;
                        font-size: 12px;
                    }}
                    QPushButton:hover {{
                        border: 1px solid {tema_activo.primario};
                        background-color: {tema_activo.fondo_panel};
                    }}
                """
            btn.setStyleSheet(estilo)

    @property
    def tema_seleccionado(self) -> str:
        return self._tema


# ---------------------------------------------------------------------------
#  Dialogo principal: Selector de perfil con asistente para nuevos usuarios
# ---------------------------------------------------------------------------

class MenuQueQuieresHacer(QDialog):
    """
    Menu principal de seleccion de perfil mejorado con tarjetas visuales,
    selector de tema, y experiencia paso a paso para nuevos usuarios.
    
    Para usuarios nuevos: muestra un wizard de 3 pasos
      1. Bienvenida + logo Zoundvi
      2. Selección de nivel (novato/intermedio/profesional/personalizado)
      3. Selección de tema visual
    
    Para usuarios existentes: muestra directamente la selección de perfil + tema.
    """

    perfil_elegido = pyqtSignal(str)

    def __init__(self, profile_manager: ProfileManager,
                 primer_inicio: bool = False,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._pm = profile_manager
        self._primer_inicio = primer_inicio
        self._seleccion: Optional[str] = None
        self._tarjetas: dict[str, TarjetaPerfil] = {}
        self._paso_actual = 0

        self.setWindowTitle("Soundvi — Configuración inicial" if primer_inicio
                           else "Soundvi — Selección de perfil")
        self.setMinimumSize(QSize(1000, 700))
        self.setModal(True)

        # Cargar preferencias previas
        self._prefs = cargar_preferencias()
        self._tema_inicial = self._prefs.get("tema", "darkly")

        if primer_inicio:
            self._construir_ui_wizard()
        else:
            self._construir_ui_directa()

        self._aplicar_estilo_dialogo()

    def _aplicar_estilo_dialogo(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #212529;
            }
        """)

    # ======================================================================
    #  UI para PRIMER INICIO (wizard paso a paso)
    # ======================================================================

    def _construir_ui_wizard(self):
        """Construye la UI del wizard para usuarios nuevos."""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Progress bar en la parte superior
        self._progress = QProgressBar()
        self._progress.setRange(0, 3)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4)
        self._progress.setStyleSheet("""
            QProgressBar {
                background-color: #343A40;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #00BC8C;
            }
        """)
        layout.addWidget(self._progress)

        # Stacked widget para los pasos
        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        # Paso 0: Bienvenida
        self._stack.addWidget(self._crear_paso_bienvenida())
        # Paso 1: Seleccion de nivel
        self._stack.addWidget(self._crear_paso_nivel())
        # Paso 2: Seleccion de tema
        self._stack.addWidget(self._crear_paso_tema())

        self._stack.setCurrentIndex(0)

    def _crear_paso_bienvenida(self) -> QWidget:
        """Paso 0: Bienvenida con Zoundvi."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(60, 40, 60, 40)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Logo Zoundvi
        logo_path = os.path.join(_RAIZ, "multimedia", "zoundvi", "zoundvi_logo.png")
        if os.path.isfile(logo_path):
            logo_lbl = QLabel()
            pixmap = QPixmap(logo_path).scaled(
                160, 160, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            logo_lbl.setPixmap(pixmap)
            logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_lbl.setStyleSheet("background: transparent;")
            layout.addWidget(logo_lbl)

        layout.addSpacing(8)

        # Titulo
        titulo = QLabel("¡Bienvenido a Soundvi!")
        titulo.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setStyleSheet("color: #00BC8C; background: transparent;")
        layout.addWidget(titulo)

        # Subtitulo
        sub = QLabel("Editor de video modular con visualización de audio reactivo")
        sub.setFont(QFont("Segoe UI", 13))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color: #ADB5BD; background: transparent;")
        layout.addWidget(sub)

        layout.addSpacing(12)

        # Descripcion
        desc = QLabel(
            "Soundvi se adapta a tu nivel de experiencia.\n"
            "En los siguientes pasos configuraremos tu experiencia ideal.\n\n"
            "No te preocupes, siempre puedes cambiar esto después."
        )
        desc.setFont(QFont("Segoe UI", 11))
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #DEE2E6; background: transparent;")
        layout.addWidget(desc)

        layout.addStretch()

        # Boton continuar
        btn = QPushButton("➡  Comenzar configuracion")
        btn.setFixedSize(280, 48)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        btn.setStyleSheet("""
            QPushButton {
                background-color: #00BC8C;
                color: #FFFFFF;
                border-radius: 10px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #00A37A; }
        """)
        btn.clicked.connect(lambda: self._ir_a_paso(1))
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(20)

        return page

    def _crear_paso_nivel(self) -> QWidget:
        """Paso 1: Seleccion de nivel de usuario."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        # Header
        header = QLabel("Paso 1 de 2 — Elige tu nivel de experiencia")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.setStyleSheet("color: #DEE2E6; background: transparent;")
        layout.addWidget(header)

        sub = QLabel("Esto determina qué herramientas verás y cómo se comporta la interfaz")
        sub.setFont(QFont("Segoe UI", 10))
        sub.setStyleSheet("color: #6C757D; background: transparent;")
        layout.addWidget(sub)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(2)
        sep.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 transparent, stop:0.3 #00BC8C, stop:0.7 #00BC8C, stop:1 transparent);"
        )
        layout.addWidget(sep)
        layout.addSpacing(4)

        # Tarjetas en fila horizontal
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(14)
        cards_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        orden = ["basico", "creador", "profesional", "personalizado"]
        for clave in orden:
            if clave not in PERFILES_UI_INFO:
                continue
            tarjeta = TarjetaPerfil(clave, PERFILES_UI_INFO[clave])
            tarjeta.seleccionado.connect(self._seleccionar)
            self._tarjetas[clave] = tarjeta
            cards_layout.addWidget(tarjeta)

        layout.addLayout(cards_layout)

        # Panel de personalizacion (para perfil personalizado)
        self._panel_personalizacion = QGroupBox("  Personalizar módulos y funciones")
        self._panel_personalizacion.setStyleSheet("""
            QGroupBox {
                border: 1px solid #495057;
                border-radius: 6px;
                padding-top: 24px;
                margin-top: 8px;
                color: #F39C12;
                font-weight: bold;
                font-size: 12px;
                background-color: #2B3035;
            }
        """)
        lay_pers = QGridLayout(self._panel_personalizacion)
        lay_pers.setSpacing(8)

        self._chks_funciones: Dict[str, QCheckBox] = {}
        opciones = {
            "Inspector Avanzado": "inspector",
            "Mezclador de Audio": "audio_mixer",
            "Transiciones": "transiciones",
            "Efectos Visuales": "efectos_video",
            "Subtítulos con IA": "subtitulos_ia",
            "Audio Reactivo": "audio_reactivo",
        }
        c, r = 0, 0
        for text, key in opciones.items():
            chk = QCheckBox(text)
            chk.setChecked(True)
            chk.setStyleSheet("color: #DEE2E6; background: transparent;")
            lay_pers.addWidget(chk, r, c)
            self._chks_funciones[key] = chk
            c += 1
            if c > 2:
                c = 0
                r += 1

        self._panel_personalizacion.setVisible(False)
        layout.addWidget(self._panel_personalizacion)

        layout.addStretch()

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_atras = QPushButton("← Atrás")
        btn_atras.setFixedSize(110, 40)
        btn_atras.setStyleSheet("""
            QPushButton { background-color: #495057; color: #DEE2E6;
                          border-radius: 6px; font-size: 12px; }
            QPushButton:hover { background-color: #6C757D; }
        """)
        btn_atras.clicked.connect(lambda: self._ir_a_paso(0))
        btn_layout.addWidget(btn_atras)

        btn_layout.addSpacing(12)

        self._btn_siguiente_nivel = QPushButton("Siguiente →")
        self._btn_siguiente_nivel.setFixedSize(160, 40)
        self._btn_siguiente_nivel.setEnabled(False)
        self._btn_siguiente_nivel.setStyleSheet("""
            QPushButton {
                background-color: #00BC8C; color: #FFFFFF;
                border-radius: 6px; font-weight: bold; font-size: 13px;
            }
            QPushButton:hover { background-color: #00A37A; }
            QPushButton:disabled { background-color: #495057; color: #6C757D; }
        """)
        self._btn_siguiente_nivel.clicked.connect(lambda: self._ir_a_paso(2))
        btn_layout.addWidget(self._btn_siguiente_nivel)

        layout.addLayout(btn_layout)

        return page

    def _crear_paso_tema(self) -> QWidget:
        """Paso 2: Seleccion de tema y confirmacion."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(60, 30, 60, 30)
        layout.setSpacing(16)

        # Header
        header = QLabel("Paso 2 de 2 — Elige tu tema visual")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.setStyleSheet("color: #DEE2E6; background: transparent;")
        layout.addWidget(header)

        sub = QLabel("Puedes cambiar esto en cualquier momento desde Configuración")
        sub.setFont(QFont("Segoe UI", 10))
        sub.setStyleSheet("color: #6C757D; background: transparent;")
        layout.addWidget(sub)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(2)
        sep.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 transparent, stop:0.3 #3498DB, stop:0.7 #3498DB, stop:1 transparent);"
        )
        layout.addWidget(sep)

        layout.addSpacing(16)

        # Tema selector grande con previews
        tema_container = QHBoxLayout()
        tema_container.setSpacing(24)
        tema_container.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Tarjeta tema oscuro
        self._tema_cards: Dict[str, QFrame] = {}
        self._card_oscuro = self._crear_tarjeta_tema(
            "darkly", "○  Tema Oscuro",
            "Colores oscuros refinados.\nIdeal para sesiones largas.",
            "#1a1d23", "#e6edf3", "#2f81f7"
        )
        self._tema_cards["darkly"] = self._card_oscuro
        tema_container.addWidget(self._card_oscuro)

        # Tarjeta tema claro
        self._card_claro = self._crear_tarjeta_tema(
            "claro", "●  Tema Claro",
            "Colores claros para ambientes\nbien iluminados.",
            "#ffffff", "#1f2328", "#0969da"
        )
        self._tema_cards["claro"] = self._card_claro
        tema_container.addWidget(self._card_claro)

        # Tarjeta tema midnight
        self._card_midnight = self._crear_tarjeta_tema(
            "midnight", "\u263D  Midnight",
            "Azul profundo, ideal para\nambientes oscuros.",
            "#0d1117", "#c9d1d9", "#58a6ff"
        )
        self._tema_cards["midnight"] = self._card_midnight
        tema_container.addWidget(self._card_midnight)

        # Tarjeta tema forest
        self._card_forest = self._crear_tarjeta_tema(
            "forest", "\u2618  Forest",
            "Verde naturaleza, suave\npara la vista.",
            "#1a2119", "#d4e8d0", "#4caf50"
        )
        self._tema_cards["forest"] = self._card_forest
        tema_container.addWidget(self._card_forest)

        layout.addLayout(tema_container)

        layout.addSpacing(12)

        # Recordar seleccion
        self._chk_recordar = QCheckBox(
            "  Recordar mi selección (no mostrar de nuevo al iniciar)"
        )
        self._chk_recordar.setChecked(True)
        self._chk_recordar.setStyleSheet(
            "color: #6C757D; background: transparent; font-size: 11px;"
        )
        layout.addWidget(self._chk_recordar, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()

        # Resumen de seleccion
        self._lbl_resumen = QLabel("")
        self._lbl_resumen.setFont(QFont("Segoe UI", 11))
        self._lbl_resumen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_resumen.setStyleSheet("color: #ADB5BD; background: transparent;")
        layout.addWidget(self._lbl_resumen)

        layout.addSpacing(8)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_atras = QPushButton("← Atrás")
        btn_atras.setFixedSize(110, 40)
        btn_atras.setStyleSheet("""
            QPushButton { background-color: #495057; color: #DEE2E6;
                          border-radius: 6px; font-size: 12px; }
            QPushButton:hover { background-color: #6C757D; }
        """)
        btn_atras.clicked.connect(lambda: self._ir_a_paso(1))
        btn_layout.addWidget(btn_atras)

        btn_layout.addSpacing(12)

        self._btn_finalizar = QPushButton("➡  Empezar a editar!")
        self._btn_finalizar.setFixedSize(220, 48)
        self._btn_finalizar.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._btn_finalizar.setStyleSheet("""
            QPushButton {
                background-color: #00BC8C; color: #FFFFFF;
                border-radius: 10px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #00A37A; }
        """)
        self._btn_finalizar.clicked.connect(self._aceptar)
        btn_layout.addWidget(self._btn_finalizar)

        layout.addLayout(btn_layout)

        return page

    def _crear_tarjeta_tema(self, clave: str, titulo: str, descripcion: str,
                            color_fondo: str, color_texto: str,
                            color_acento: str) -> QFrame:
        """Crea una tarjeta visual para seleccion de tema."""
        frame = QFrame()
        frame.setFixedSize(300, 200)
        frame.setCursor(Qt.CursorShape.PointingHandCursor)
        frame.setObjectName(f"tema_{clave}")
        frame.setProperty("tema_clave", clave)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        # Preview del tema
        preview = QFrame()
        preview.setFixedHeight(60)
        preview.setStyleSheet(f"""
            QFrame {{
                background-color: {color_fondo};
                border: 1px solid {color_acento};
                border-radius: 6px;
            }}
        """)
        pv_layout = QVBoxLayout(preview)
        pv_layout.setContentsMargins(8, 8, 8, 8)
        pv_lbl = QLabel("Preview de la interfaz")
        pv_lbl.setFont(QFont("Segoe UI", 9))
        pv_lbl.setStyleSheet(f"color: {color_texto}; background: transparent;")
        pv_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pv_layout.addWidget(pv_lbl)
        layout.addWidget(preview)

        # Titulo
        t_lbl = QLabel(titulo)
        t_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        t_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t_lbl.setStyleSheet(f"color: {color_acento}; background: transparent;")
        layout.addWidget(t_lbl)

        # Descripcion
        d_lbl = QLabel(descripcion)
        d_lbl.setFont(QFont("Segoe UI", 9))
        d_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d_lbl.setWordWrap(True)
        d_lbl.setStyleSheet("color: #ADB5BD; background: transparent;")
        layout.addWidget(d_lbl)

        # Inicializar estilo
        self._actualizar_estilo_tema(frame, clave == self._tema_inicial)

        # Evento click
        frame.mousePressEvent = lambda e, k=clave: self._seleccionar_tema(k)

        return frame

    def _seleccionar_tema(self, clave: str):
        """Selecciona un tema y actualiza las tarjetas."""
        self._tema_inicial = clave
        for k, card in self._tema_cards.items():
            self._actualizar_estilo_tema(card, k == clave)
        self._actualizar_resumen()

    def _actualizar_estilo_tema(self, frame: QFrame, activo: bool):
        """Actualiza el estilo de una tarjeta de tema."""
        clave = frame.property("tema_clave")
        _acento_map = {"darkly": "#2f81f7", "claro": "#0969da", "midnight": "#58a6ff", "forest": "#4caf50"}
        acento = _acento_map.get(clave, "#2f81f7")
        if activo:
            frame.setStyleSheet(f"""
                QFrame#{frame.objectName()} {{
                    background-color: #2B3035;
                    border: 2px solid {acento};
                    border-radius: 12px;
                }}
            """)
            shadow = QGraphicsDropShadowEffect(frame)
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(acento))
            shadow.setOffset(0, 0)
            frame.setGraphicsEffect(shadow)
        else:
            frame.setStyleSheet(f"""
                QFrame#{frame.objectName()} {{
                    background-color: #2B3035;
                    border: 1px solid #495057;
                    border-radius: 12px;
                }}
                QFrame#{frame.objectName()}:hover {{
                    border: 1px solid {acento}80;
                }}
            """)
            frame.setGraphicsEffect(None)

    def _actualizar_resumen(self):
        """Actualiza el label de resumen con la selección actual."""
        if hasattr(self, '_lbl_resumen') and self._seleccion:
            info = PERFILES_UI_INFO.get(self._seleccion, {})
            nivel = info.get("titulo", self._seleccion)
            tema = "Oscuro" if self._tema_inicial == "darkly" else "Claro"
            self._lbl_resumen.setText(
                f"≡ Resumen: Nivel {nivel}  •  Tema {tema}"
            )

    # ======================================================================
    #  UI DIRECTA (para cambio de perfil, no primer inicio)
    # ======================================================================

    def _construir_ui_directa(self):
        """Construye la UI directa (sin wizard) para cambio de perfil."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 28, 32, 24)

        # Header
        titulo = QLabel("♫  Soundvi — Seleccionar perfil")
        titulo.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setStyleSheet("color: #00BC8C; background: transparent;")
        layout.addWidget(titulo)

        sub = QLabel("Cambia tu nivel de usuario y tema visual")
        sub.setFont(QFont("Segoe UI", 11))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color: #ADB5BD; background: transparent;")
        layout.addWidget(sub)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(2)
        sep.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 transparent, stop:0.3 #00BC8C, stop:0.7 #00BC8C, stop:1 transparent);"
        )
        layout.addWidget(sep)
        layout.addSpacing(4)

        # Tarjetas
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(14)
        cards_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for clave in ["basico", "creador", "profesional", "personalizado"]:
            if clave not in PERFILES_UI_INFO:
                continue
            tarjeta = TarjetaPerfil(clave, PERFILES_UI_INFO[clave])
            tarjeta.seleccionado.connect(self._seleccionar)
            self._tarjetas[clave] = tarjeta
            cards_layout.addWidget(tarjeta)

        layout.addLayout(cards_layout)

        # Panel de personalizacion
        self._panel_personalizacion = QGroupBox("  Personalizar módulos y funciones")
        self._panel_personalizacion.setStyleSheet("""
            QGroupBox {
                border: 1px solid #495057; border-radius: 6px;
                padding-top: 24px; margin-top: 8px;
                color: #F39C12; font-weight: bold; font-size: 12px;
                background-color: #2B3035;
            }
        """)
        lay_pers = QGridLayout(self._panel_personalizacion)
        lay_pers.setSpacing(8)

        self._chks_funciones: Dict[str, QCheckBox] = {}
        opciones = {
            "Inspector Avanzado": "inspector",
            "Mezclador de Audio": "audio_mixer",
            "Transiciones": "transiciones",
            "Efectos Visuales": "efectos_video",
            "Subtítulos con IA": "subtitulos_ia",
            "Audio Reactivo": "audio_reactivo",
        }
        c, r = 0, 0
        for text, key in opciones.items():
            chk = QCheckBox(text)
            chk.setChecked(True)
            chk.setStyleSheet("color: #DEE2E6; background: transparent;")
            lay_pers.addWidget(chk, r, c)
            self._chks_funciones[key] = chk
            c += 1
            if c > 2:
                c = 0
                r += 1

        self._panel_personalizacion.setVisible(False)
        layout.addWidget(self._panel_personalizacion)

        layout.addSpacing(4)

        # Selector de tema
        self._selector_tema = SelectorTema(self._tema_inicial)
        layout.addWidget(self._selector_tema)

        layout.addSpacing(4)

        # Recordar
        self._chk_recordar = QCheckBox(
            "  Recordar mi selección (no mostrar de nuevo al iniciar)"
        )
        self._chk_recordar.setChecked(True)
        self._chk_recordar.setStyleSheet(
            "color: #6C757D; background: transparent; font-size: 11px;"
        )
        layout.addWidget(self._chk_recordar)

        layout.addStretch()

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setFixedSize(120, 40)
        btn_cancelar.setStyleSheet("""
            QPushButton { background-color: #495057; color: #DEE2E6;
                          border-radius: 6px; font-size: 13px; }
            QPushButton:hover { background-color: #6C757D; }
        """)
        btn_cancelar.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancelar)

        btn_layout.addSpacing(12)

        self._btn_aceptar = QPushButton("✓  Aplicar")
        self._btn_aceptar.setFixedSize(160, 40)
        self._btn_aceptar.setEnabled(False)
        self._btn_aceptar.setStyleSheet("""
            QPushButton {
                background-color: #00BC8C; color: #FFFFFF;
                border-radius: 6px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #00A37A; }
            QPushButton:disabled { background-color: #495057; color: #6C757D; }
        """)
        self._btn_aceptar.clicked.connect(self._aceptar)
        btn_layout.addWidget(self._btn_aceptar)

        layout.addLayout(btn_layout)

        # Pre-seleccionar perfil activo
        perfil_prev = self._prefs.get("perfil", "")
        activo = self._pm.perfil_activo
        if perfil_prev and perfil_prev in PERFILES_UI_INFO:
            self._seleccionar(perfil_prev)
        elif activo:
            self._seleccionar(activo.clave)

    # ======================================================================
    #  Logica comun
    # ======================================================================

    def _ir_a_paso(self, paso: int):
        """Navega a un paso del wizard."""
        if hasattr(self, '_stack'):
            self._paso_actual = paso
            self._stack.setCurrentIndex(paso)
            self._progress.setValue(paso)
            if paso == 2:
                self._actualizar_resumen()

    def _seleccionar(self, clave: str):
        """Selecciona un perfil."""
        self._seleccion = clave
        for k, tarjeta in self._tarjetas.items():
            tarjeta.set_activo(k == clave)

        self._panel_personalizacion.setVisible(clave == "personalizado")

        # Habilitar botones de avance
        if hasattr(self, '_btn_siguiente_nivel'):
            self._btn_siguiente_nivel.setEnabled(True)
        if hasattr(self, '_btn_aceptar'):
            self._btn_aceptar.setEnabled(True)

        self._actualizar_resumen()

    def _aceptar(self):
        """Acepta la seleccion y guarda preferencias."""
        if not self._seleccion:
            return

        # Aplicar personalizaciones si es personalizado
        if self._seleccion == "personalizado" and hasattr(self, '_chks_funciones'):
            perfil = self._pm.perfiles_disponibles.get("personalizado")
            if perfil:
                paneles = ["preview", "timeline", "media_library", "modules_sidebar"]
                if self._chks_funciones.get("inspector", None) and \
                   self._chks_funciones["inspector"].isChecked():
                    paneles.append("inspector")
                if self._chks_funciones.get("audio_mixer", None) and \
                   self._chks_funciones["audio_mixer"].isChecked():
                    paneles.append("audio_mixer")
                perfil.paneles_visibles = paneles

                for key in ["transiciones", "efectos_video", "subtitulos_ia", "audio_reactivo"]:
                    if key in self._chks_funciones:
                        perfil.funciones[key] = self._chks_funciones[key].isChecked()

        # Seleccionar perfil en el manager
        self._pm.seleccionar_perfil(self._seleccion)

        # Obtener tema seleccionado
        if hasattr(self, '_selector_tema'):
            tema = self._selector_tema.tema_seleccionado
        else:
            tema = self._tema_inicial

        # Guardar preferencias
        recordar = True
        if hasattr(self, '_chk_recordar'):
            recordar = self._chk_recordar.isChecked()

        prefs = cargar_preferencias()
        prefs["perfil"] = self._seleccion
        prefs["tema"] = tema
        prefs["recordar"] = recordar
        prefs["recordar_seleccion"] = recordar
        if "fecha_primera_configuracion" not in prefs:
            prefs["fecha_primera_configuracion"] = datetime.now().isoformat()
        prefs["fecha_ultima_modificacion"] = datetime.now().isoformat()
        guardar_preferencias(prefs)

        # Guardar seleccion en ProfileManager
        if recordar:
            self._pm.guardar_seleccion()

        self.perfil_elegido.emit(self._seleccion)
        self.accept()

    def get_perfil_seleccionado(self) -> Optional[str]:
        return self._seleccion

    def get_tema_seleccionado(self) -> str:
        if hasattr(self, '_selector_tema'):
            return self._selector_tema.tema_seleccionado
        return self._tema_inicial


# ---------------------------------------------------------------------------
#  Funcion de conveniencia
# ---------------------------------------------------------------------------

def mostrar_selector_perfil(profile_manager: ProfileManager,
                             primer_inicio: bool = False,
                             parent: Optional[QWidget] = None) -> Optional[str]:
    """
    Muestra el selector de perfil mejorado.
    Retorna la clave del perfil seleccionado o None si se cancelo.
    """
    dialogo = MenuQueQuieresHacer(profile_manager, primer_inicio, parent)
    resultado = dialogo.exec()
    if resultado == QDialog.DialogCode.Accepted:
        return dialogo.get_perfil_seleccionado()
    return None
