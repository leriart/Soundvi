# Sistema de Guardado/Carga .soundvi

## Visión General

El sistema de guardado/carga de Soundvi utiliza un formato propietario `.soundvi` que combina compresión ZIP con cifrado básico para proteger los proyectos del usuario.

## Arquitectura

### Flujo de Guardado

```
ProjectManager.save_project()
    │
    ├── Si .soundvi:
    │   ├── Serializar datos del proyecto (JSON)
    │   ├── Crear estructura de directorios temporal
    │   ├── Copiar medios embebidos (opcional)
    │   ├── Calcular checksums SHA-256
    │   ├── Comprimir con ZIP (DEFLATE)
    │   ├── Cifrar con PBKDF2 + XOR
    │   └── Escribir archivo final
    │
    └── Si .svproj (legacy):
        └── Escribir JSON directamente
```

### Flujo de Carga

```
ProjectManager.load_project()
    │
    ├── Si .soundvi:
    │   ├── Leer archivo binario
    │   ├── Verificar magic bytes (SNDV)
    │   ├── Extraer salt y HMAC
    │   ├── Derivar clave (PBKDF2-HMAC-SHA256)
    │   ├── Verificar integridad (HMAC)
    │   ├── Descifrar datos XOR
    │   ├── Descomprimir ZIP
    │   ├── Verificar checksums
    │   ├── Restaurar proyecto
    │   └── Extraer medios embebidos a temporal
    │
    └── Si .svproj:
        └── Leer y parsear JSON
```

## Formato Binario

```
Offset  Tamaño  Campo
0       4       Magic bytes: "SNDV"
4       1       Versión del formato (2)
5       16      Salt (aleatorio)
21      32      HMAC-SHA256 de los datos cifrados
53      N       Datos cifrados (ZIP comprimido)
```

## Cifrado

### Derivación de clave
- **Algoritmo**: PBKDF2-HMAC-SHA256
- **Iteraciones**: 100,000
- **Salt**: 16 bytes aleatorios
- **Longitud de clave**: 32 bytes

### Cifrado de datos
- **Algoritmo**: XOR con clave derivada extendida
- **Integridad**: HMAC-SHA256 sobre datos cifrados

### Compatibilidad legacy
Si el descifrado falla, el sistema intenta abrir el archivo como ZIP sin cifrar para mantener compatibilidad con versiones anteriores.

## Contenido del Proyecto

Cada archivo `.soundvi` contiene:

| Archivo | Contenido |
|---------|----------|
| `manifest.json` | Metadatos, versiones, checksums, estructura |
| `config/project.json` | Configuración general del proyecto |
| `config/timeline.json` | Estado completo del timeline (tracks, clips) |
| `config/modules.json` | Módulos activos y su configuración |
| `config/render.json` | Parámetros de exportación |
| `config/media_library.json` | Referencias a archivos de medios |
| `media/audio/` | Archivos de audio embebidos |
| `media/images/` | Imágenes embebidas |
| `history/actions.json` | Historial de undo/redo |

## Medios Embebidos

Cuando `embed_media=True`:
- Los archivos de audio se copian a `media/audio/`
- Las imágenes se copian a `media/images/`
- Se calculan checksums SHA-256 para verificación
- Al cargar, se extraen a un directorio temporal persistente

## Manejo de Errores

- **Contraseña incorrecta**: HMAC no coincide → retorna None
- **Archivo corrupto**: Magic bytes incorrectos o HMAC inválido
- **Versión incompatible**: Se verifica la versión del formato
- **Checksums erróneos**: Se genera advertencia pero se intenta cargar
- **Fallback**: Si el .soundvi falla al guardar, se intenta .svproj
