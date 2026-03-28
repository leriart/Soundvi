# Sistema de Tracks por Tipo en Soundvi

## Introducción

Soundvi ahora implementa un sistema de tracks especializados que separa automáticamente los diferentes tipos de contenido:

1. **Tracks de Multimedia** (video) - Para videos, imágenes y GIFs
2. **Tracks de Audio** - Para archivos de sonido
3. **Tracks de Subtítulos** - Para texto y subtítulos (módulos)
4. **Tracks de Efectos** - Para efectos visuales (módulos)

## Características Principales

### 1. Asignación Automática
- Los archivos se asignan automáticamente al track correcto según su tipo
- Si no hay un track compatible disponible, se crea uno nuevo automáticamente
- El sistema detecta el tipo de archivo por su extensión

### 2. Validación de Tipos
Cada track solo acepta tipos específicos de contenido:

| Tipo de Track | Tipos Aceptados | Descripción |
|---------------|-----------------|-------------|
| **Multimedia** | `video`, `image`, `gif`, `color` | Videos, imágenes, GIFs animados, fondos de color |
| **Audio** | `audio`, `video` | Archivos de audio y audio extraído de videos |
| **Subtítulos** | Módulos de texto | Texto, subtítulos, títulos, créditos (como módulos) |
| **Efectos** | Módulos de efectos | Efectos visuales, transiciones, filtros (como módulos) |

### 3. Múltiples Tracks por Tipo
- Puedes tener tantos tracks de cada tipo como necesites
- Los tracks nuevos se numeran automáticamente (Multimedia 1, Multimedia 2, etc.)
- La interfaz muestra iconos y conteos para cada tipo

### 4. Interfaz Mejorada
- **Iconos visuales**: 🎥 Multimedia, ♪ Audio, 📄 Subtítulos, ★ Efectos
- **Tooltips informativos**: Muestran los tipos permitidos en cada track
- **Menús contextuales**: Con opciones para agregar tracks específicos
- **Validación en tiempo real**: Muestra advertencias cuando se intenta agregar un archivo incompatible

## Cómo Usar el Sistema

### Agregar Archivos
1. **Drag & Drop**: Arrastra archivos al timeline
2. **Asignación automática**: Los archivos se colocan en el track correcto automáticamente
3. **Validación**: Si intentas colocar un archivo de audio en un track de multimedia, el sistema te avisará y lo moverá al track correcto

### Agregar Tracks Manualmente
1. Haz clic en el botón **"+ Pista"** en la barra de herramientas
2. Selecciona el tipo de track que necesitas
3. El nuevo track aparecerá con el nombre y icono apropiados

### Trabajar con Módulos
1. Los módulos de texto/subtítulos van automáticamente a tracks de subtítulos
2. Los módulos de efectos van automáticamente a tracks de efectos
3. Puedes arrastrar módulos entre tracks compatibles

## Detalles Técnicos

### Detección de Tipos de Archivo
El sistema usa la función `detect_source_type()` en `video_clip.py` para determinar el tipo de archivo:

```python
def detect_source_type(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    video_exts = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.webm', '.flv'}
    image_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    gif_exts = {'.gif'}
    audio_exts = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac'}
    
    if ext in video_exts: return 'video'
    elif ext in image_exts: return 'image'
    elif ext in gif_exts: return 'gif'
    elif ext in audio_exts: return 'audio'
    return 'video'  # Por defecto
```

### Validación en Tracks
Cada track tiene un método `_is_clip_type_allowed()` que verifica la compatibilidad:

```python
def _is_clip_type_allowed(self, clip: VideoClip) -> bool:
    if self.track_type == 'video':
        return clip.source_type in ['video', 'image', 'gif', 'color']
    elif self.track_type == 'audio':
        return clip.source_type in ['audio', 'video']
    # ... etc.
```

### Asignación Automática
El timeline tiene un método `_add_clip_to_compatible_track()` que:
1. Determina el tipo de track necesario para el clip
2. Busca tracks existentes del tipo correcto
3. Si no hay tracks disponibles, crea uno nuevo
4. Agrega el clip al track compatible

## Mensajes de Error y Ayuda

El sistema incluye mensajes de error útiles:
- **Archivo incompatible**: Cuando intentas agregar un archivo a un track incorrecto
- **Límites de perfil**: Cuando alcanzas el límite de tracks permitidos por el perfil activo
- **Ayuda contextual**: Diálogos de ayuda que explican los tipos de tracks

## Compatibilidad con Proyectos Existentes

El sistema es compatible con proyectos creados antes de esta actualización:
- Los tracks existentes mantienen su funcionalidad
- Los clips existentes se validan según las nuevas reglas
- No se pierde información al actualizar

## Ventajas del Nuevo Sistema

1. **Organización automática**: No necesitas pensar en qué track usar
2. **Prevención de errores**: El sistema evita que coloques archivos en lugares incorrectos
3. **Interfaz más clara**: Iconos y nombres descriptivos hacen que sea fácil entender qué hay en cada track
4. **Flexibilidad**: Puedes tener tantos tracks como necesites de cada tipo
5. **Consistencia**: Todos los proyectos siguen la misma estructura organizativa

## Ejemplos de Uso

### Ejemplo 1: Proyecto de Video Musical
- **Track 1 (Multimedia)**: Video principal
- **Track 2 (Audio)**: Pista de audio principal
- **Track 3 (Audio)**: Efectos de sonido
- **Track 4 (Subtítulos)**: Letra de la canción
- **Track 5 (Efectos)**: Efectos visuales sincronizados

### Ejemplo 2: Tutorial con Capturas de Pantalla
- **Track 1 (Multimedia)**: Capturas de pantalla (imágenes)
- **Track 2 (Audio)**: Narración
- **Track 3 (Subtítulos)**: Texto explicativo
- **Track 4 (Efectos)**: Flechas y resaltados

### Ejemplo 3: Presentación con Múltiples Videos
- **Track 1-3 (Multimedia)**: Videos de diferentes ángulos
- **Track 4 (Audio)**: Música de fondo
- **Track 5 (Subtítulos)**: Títulos y créditos
- **Track 6 (Efectos)**: Transiciones entre videos

## Conclusión

El nuevo sistema de tracks por tipo hace que Soundvi sea más intuitivo y organizado. Al separar automáticamente los diferentes tipos de contenido, reduces errores y mejoras el flujo de trabajo. La interfaz visual con iconos y tooltips hace que sea fácil entender y usar el sistema, incluso para usuarios nuevos.