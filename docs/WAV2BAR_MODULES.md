# Módulos wav2bar-reborn para Soundvi

## Introducción

Estos módulos están inspirados en el proyecto **wav2bar-reborn**, una aplicación de visualización de audio construida con Tauri + Svelte + Pixi.js. Los conceptos clave han sido adaptados a la arquitectura de Soundvi (Python + PyQt6 + OpenCV).

## Módulos Integrados

### 1. Barras Rectas (`StraightBarModule`)
**Ubicación**: `modules/audio/visualization/straight_bar_module.py`

Visualiza el espectro de audio como barras verticales.

**Características**:
- Escalado logarítmico de frecuencias (mapeo perceptual)
- Suavizado temporal configurable (reduce parpadeo)
- Gradientes de color entre dos colores
- Sombras con offset y transparencia
- Bordes redondeados opcionales
- Modo espejo (reflejo debajo de las barras)
- Rango de frecuencias configurable (50 Hz - 16 kHz)

**Parámetros clave**:
- `n_bars`: Número de barras (8-256)
- `smoothing`: Suavizado temporal (0-0.95)
- `height_ratio`: Altura máxima relativa al frame
- `log_scale`: Escala logarítmica vs lineal
- `power_scale`: Exponente para compresión dinámica

---

### 2. Barras Circulares (`CircularBarModule`)
**Ubicación**: `modules/audio/visualization/circular_bar_module.py`

Barras dispuestas en círculo alrededor de un punto central.

**Características**:
- Disposición radial de barras
- Barras espejo interiores
- Círculo interior decorativo
- Velocidad de rotación configurable
- Gradientes de color radiales

---

### 3. Flujo de Partículas (`ParticleFlowModule`)
**Ubicación**: `modules/audio/visualization/particle_flow_module.py`

Sistema de partículas reactivas al audio con física básica.

**Características**:
- Física de partículas (gravedad, fricción, velocidad)
- Modos de emisión: centro, fondo, lados
- Efecto glow para partículas
- Tamaño proporcional a la energía del audio
- Variación de color por partícula
- Umbral de energía para emisión

**Análisis de audio**:
- Energía global del espectro
- Energía de bajos (<250 Hz)
- Energía de agudos (>4000 Hz)

---

### 4. Onda de Audio (`WaveVisualizerModule`)
**Ubicación**: `modules/audio/visualization/wave_visualizer_module.py`

Forma de onda suavizada basada en el espectro de frecuencias.

**Características**:
- Línea de onda suavizada
- Relleno semitransparente
- Espejo vertical
- Efecto glow en la línea
- Amplitud y suavizado configurables

---

### 5. Filtros SVG (`SVGFilterModule`)
**Ubicación**: `modules/video/effects/svg_filter_module.py`

Filtros de procesamiento de imagen inspirados en filtros SVG.

**Filtros disponibles**:
| Filtro | Descripción |
|--------|----------|
| `invert` | Inversión de colores |
| `desaturate` | Desaturación a escala de grises |
| `sepia` | Tono sepia cálido |
| `posterize` | Posterización (reducción de niveles de color) |
| `chromatic_aberration` | Aberración cromática (separación de canales RGB) |
| `thermal` | Mapa térmico (JET colormap) |
| `emboss` | Efecto relieve/grabado |
| `sharpen` | Enfoque/afilado |

**Modo reactivo**: La intensidad del filtro puede ser controlada por la energía del audio.

---

### 6. Sombras y Bordes (`ShadowBorderModule`)
**Ubicación**: `modules/video/effects/shadow_border_module.py`

Decoracines de borde y sombra para el video.

**Características**:
- Bordes con color, grosor y radio configurables
- Sombra interior tipo viñeta
- Tamaño y transparencia de sombra ajustables

---

### 7. Imagen/Forma (`ImageShapeModule`)
**Ubicación**: `modules/video/generators/image_shape_module.py`

Permite colocar imágenes que reaccionan al audio.

**Características**:
- Carga de imágenes PNG/JPG (con soporte alfa)
- Reactividad al audio (escala, rotación, opacidad)
- Máscara circular opcional
- Posicionamiento libre
- Soporte para imágenes transparentes

---

### 8. Temporizador Visual (`TimerVisualizerModule`)
**Ubicación**: `modules/utility/timer_module.py`

Barra de progreso temporal.

**Modos**:
- `bar`: Barra de progreso rectangular
- `line_point`: Línea con punto indicador
- `circle`: Arco circular de progreso

**Características**:
- Texto de tiempo actual/total
- Colores configurables (fondo, relleno, punto)
- Posición y tamaño ajustables

## Procesamiento de Audio

Todos los módulos de audio siguen un pipeline común:

1. **Carga**: `librosa.load()` a 22050 Hz mono
2. **STFT**: Short-Time Fourier Transform (n_fft=2048, hop=512)
3. **Bandas**: Mapeo a bandas de frecuencia (logarítmico)
4. **Normalización**: Compresión de rango dinámico con exponente configurable
5. **Interpolación**: Adaptación al número de frames del video
6. **Suavizado**: Filtro temporal para evitar parpadeo

## Crear un Módulo Nuevo

```python
from modules.core.base import Module
import numpy as np

class MiModulo(Module):
    module_type = "audio"         # audio, video, text, utility, export
    module_category = "visualization"  # subcategoría
    module_tags = ["mi_tag"]      # para búsqueda
    module_version = "1.0.0"

    def __init__(self):
        super().__init__(nombre="Mi Módulo", descripcion="Descripción")
        self._config = {"param1": 0.5}

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado:
            return frame
        # Procesar frame aquí
        return frame

    def get_config_widgets(self, parent, app):
        # Retornar QWidget con controles
        from PyQt6.QtWidgets import QWidget
        return QWidget(parent)
```

Colocar el archivo en la carpeta correspondiente (`modules/audio/visualization/`, etc.) y el sistema lo detectará automáticamente.
