# Soundvi - Generador de Video con Visualizador

Soundvi es una aplicacion de escritorio para generar videos con visualizacion de audio, subtitulos SRT y mas. Cuenta con un sistema modular plug-and-play que permite extender facilmente sus funcionalidades.

## Caracteristicas principales

### Sistema modular plug-and-play
- **Deteccion automatica de modulos**: Los modulos en la carpeta `modules/` se detectan automaticamente al iniciar
- **Interfaz dinamica**: La sidebar genera controles especificos para cada modulo detectado
- **Arquitectura extensible**: Facil de agregar nuevos modulos visuales copiando la plantilla
- **Sin reinicios**: Recarga de modulos con boton en la interfaz

### Interfaz moderna con preview en tiempo real
- **Layout sidebar + preview**: Configuracion a la izquierda (30%), vista previa a la derecha (70%)
- **Preview en tiempo real**: Visualiza como quedara el video antes de compilar
- **Controles de reproduccion**: Play/Pause, adelantar, retroceder, reverse, volumen
- **Actualizacion en tiempo real**: Los cambios de configuracion se reflejan instantaneamente
- **Mantiene proporcion**: La preview respeta la proporcion de la resolucion configurada

### Modulos incluidos
- **Modulo Subtitulos**: Superposicion de archivos SRT con fuentes, colores y posicion personalizables
- **Modulo SubAuto**: Generacion automatica de subtitulos usando reconocimiento de voz Vosk
- **Modulo Waveform**: Visualizacion de forma de onda tradicional

### Rendimiento optimizado
- **Motor de render hibrido**: OpenCV + FFmpeg por tuberia
- **Aceleracion GPU**: Soporte para NVENC, QSV, VAAPI y VideoToolbox
- **Procesamiento no bloqueante**: No congela la interfaz durante el procesamiento
- **Cache eficiente**: Preprocesamiento de audio en segundo plano con cache LRU
- **Sincronizacion profesional**: Manejo preciso de tiempos de audio y video

## Estructura del proyecto

```
Soundvi-main/
├── main.py                 # Punto de entrada principal
├── config.json            # Configuracion persistente de la aplicacion
├── requirements.txt       # Dependencias de Python
├── README.md              # Documentacion
├── fonts/                 # Fuentes incluidas
├── logos/                 # Identidad visual
├── temp/                  # Archivos temporales
├── modules_config/        # Configuraciones por modulo
├── vosk_models/           # Modelos de lenguaje para reconocimiento de voz
├── core/                  # Nucleo de procesamiento
│   ├── audio_processing.py # Procesamiento de audio
│   ├── frequency_mapping.py # Mapeo de frecuencias
│   ├── video_generator.py  # Generador de video
│   └── wav2bar_engine.py  # Motor Wav2Bar unificado
├── modules/               # Sistema de modulos plug-and-play
│   ├── base.py            # Clase base abstracta para modulos
│   ├── manager.py         # Gestor de modulos con deteccion automatica
│   ├── loader.py          # Cargador dinamico de modulos
│   ├── TEMPLATE.py        # Plantilla para crear nuevos modulos
│   ├── subtitles_module.py # Modulo de subtitulos
│   ├── subauto_module.py  # Modulo de subtitulos automaticos
│   └── waveform_module.py # Modulo de forma de onda
├── gui/                   # Interfaz grafica
│   ├── app.py             # Aplicacion principal
│   ├── sidebar.py         # Barra lateral de configuracion dinamica
│   ├── preview.py         # Panel de preview en tiempo real
│   └── loading.py         # Overlay de carga
└── utils/                 # Utilidades
    ├── config.py          # Manejo de configuracion
    ├── ffmpeg.py          # Utilidades FFmpeg
    ├── fonts.py           # Manejo de fuentes
    ├── gpu.py             # Deteccion de aceleracion GPU
    └── subtitles.py       # Procesamiento de subtitulos
```

## Requisitos

### Software requerido
- **Python 3.10 o superior**
- **FFmpeg instalado en el sistema** (para generacion de video)

### Instalacion de FFmpeg

**Debian/Ubuntu:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Arch Linux / CachyOS:**
```bash
sudo pacman -S ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
```bash
choco install ffmpeg
```

## Instalacion

1. **Clonar o descargar el proyecto:**
```bash
git clone <repositorio>
cd Soundvi-main
```

2. **Crear y activar entorno virtual (recomendado):**
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# o
venv\Scripts\activate     # Windows
```

3. **Instalar dependencias de Python:**
```bash
pip install -r requirements.txt
```

4. **Descargar modelos de lenguaje para SubAuto (opcional):**
```bash
# Descargar modelo de espanol para Vosk
wget https://alphacephei.com/vosk/models/vosk-model-es-0.42.zip
unzip vosk-model-es-0.42.zip -d vosk_models/
```

5. **Ejecutar la aplicacion:**
```bash
python start.py  # Version optimizada
# o
python main.py   # Version original
```

## Uso basico

1. **Cargar archivos:**
   - Selecciona una imagen o GIF de fondo
   - Selecciona un archivo de audio (MP3, WAV, FLAC, etc.)

2. **Configurar parametros:**
   - **Pestaña Principal:** Resolucion, FPS, codec, fondo
   - **Modulos activos:** Selecciona que modulos aplicar (Wav2Bar, Subtitulos, etc.)
   - **Configuracion por modulo:** Cada modulo tiene sus propios controles

3. **Previsualizar:**
   - Usa los controles de reproduccion para ver el resultado
   - La preview mantiene la proporcion de la resolucion configurada
   - Los cambios se reflejan en tiempo real

4. **Generar video:**
   - Configura la ruta de salida
   - Haz clic en "Generar Video"
   - El progreso se muestra en la barra de estado

## Sistema de modulos

### Crear un nuevo modulo
1. Copia `modules/TEMPLATE.py` a un nuevo archivo en `modules/`
2. Modifica la clase para implementar tu funcionalidad
3. La aplicacion detectara automaticamente el nuevo modulo al reiniciar

### Estructura de un modulo
```python
class MiModulo(Module):
    name = "Mi Modulo"           # Nombre mostrado en la interfaz
    description = "Descripcion"  # Tooltip
    priority = 100               # Orden de renderizado (mayor = mas tarde)
    
    def get_widgets(self, parent):
        # Devuelve widgets para la sidebar
        pass
        
    def render(self, frame, audio_data, current_time, fps):
        # Renderiza sobre el frame
        return frame
```

### Modulos incluidos

#### SubtitlesModule
- **Formatos soportados:** SRT, VTT
- **Fuentes personalizables:** Sistema o archivos TTF/OTF
- **Posicionamiento:** Coordenadas X/Y normalizadas
- **Estilos:** Tamaño, color, sombra, salto de linea

#### SubAutoModule
- **Reconocimiento de voz:** Usa Vosk para transcripcion automatica
- **Modelos de lenguaje:** Español, ingles, y otros
- **Ajuste de precision:** Umbral de confianza configurable
- **Exportacion:** Genera archivos SRT automaticamente

#### WaveformModule
- **Forma de onda tradicional:** Representacion de amplitud
- **Estilos:** Relleno, linea, puntos
- **Colores:** Personalizables para fondo y linea
- **Suavizado:** Control de suavizado de la señal

## Parametros tecnicos

### Resolucion y formato
- **Resoluciones:** Desde 360p hasta 4K
- **FPS:** 24, 25, 30, 48, 50, 60, 120
- **Codecs de video:** H.264, H.265 (HEVC), VP9, AV1
- **Codecs de audio:** AAC, MP3, Opus, FLAC

### Aceleracion GPU
- **NVIDIA:** NVENC (H.264, H.265)
- **Intel:** QSV (Quick Sync Video)
- **AMD:** VAAPI (Video Acceleration API)
- **Apple:** VideoToolbox
- **Software:** x264, x265 (CPU)

### Procesamiento de audio
- **Formatos soportados:** MP3, WAV, FLAC, OGG, M4A, AAC
- **Frecuencias de muestreo:** 44.1kHz, 48kHz, 96kHz, 192kHz
- **Canales:** Mono, Estereo, 5.1, 7.1
- **Analisis espectral:** FFT con ventana de Hann

## Solucion de problemas

### Error al iniciar
- Verifica que FFmpeg este instalado: `ffmpeg -version`
- Verifica las dependencias: `pip list`
- Reinstala dependencias: `pip install -r requirements.txt --force-reinstall`

### Preview no muestra nada
- Asegurate de haber cargado un archivo de audio y una imagen/GIF de fondo
- Verifica que al menos un modulo este habilitado
- Revisa la consola para mensajes de error

### Generacion de video lenta
- Usa codecs de GPU si estan disponibles (NVENC, QSV, VAAPI)
- Reduce la resolucion o FPS
- Desactiva modulos que no necesites
- Cierra otras aplicaciones que consuman recursos

### Modulos no aparecen
- Verifica que los archivos .py esten en la carpeta `modules/`
- Los modulos deben heredar de `Module` en `modules/base.py`
- Revisa la consola para errores de importacion

### Problemas con SubAuto
- Asegurate de tener modelos de lenguaje descargados en `vosk_models/`
- Verifica que el audio tenga buena calidad y poco ruido de fondo
- Ajusta el umbral de confianza si hay muchos errores

## Desarrollo

### Ejecutar pruebas
```bash
# Verificar que todos los modulos se cargan correctamente
python -c "from modules.manager import ModuleManager; mm = ModuleManager(); print(f'Modulos cargados: {len(mm.get_module_types())}')"

# Probar el motor Wav2Bar
python -c "from core.wav2bar_engine import Wav2BarEngine; print('Wav2BarEngine importado correctamente')"
```

### Estructura de desarrollo
- **Modulos:** `modules/*.py` - Cada modulo es independiente
- **Core:** `core/*.py` - Motor de procesamiento
- **GUI:** `gui/*.py` - Interfaz de usuario
- **Utils:** `utils/*.py` - Funciones auxiliares

### Agregar nuevas funcionalidades
1. Crea un nuevo modulo en `modules/` basado en `TEMPLATE.py`
2. Implementa los metodos requeridos
3. Agrega widgets de configuracion en `get_widgets()`
4. Implementa la logica de renderizado en `render()`
5. La aplicacion detectara automaticamente el nuevo modulo

## Licencia y creditos

Soundvi es un proyecto de codigo abierto desarrollado para generacion de videos con visualizacion de audio.

### Tecnologias utilizadas
- **Interfaz grafica:** Tkinter con ttkbootstrap
- **Procesamiento de audio:** Librosa, PyDub, SciPy
- **Procesamiento de video:** OpenCV, MoviePy
- **Reconocimiento de voz:** Vosk
- **Renderizado:** FFmpeg, NumPy

### Nota del desarrollador
No lloren por mi, yo ya estoy muerto
