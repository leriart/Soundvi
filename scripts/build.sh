#!/bin/bash
# Script de build universal para GitHub Actions
# Funciona en Linux, macOS y Windows (con Git Bash/WSL)

set -e  # Exit on error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Soundvi Build Script ===${NC}"

# Parse arguments
PLATFORM=""
VERSION=""
MODE="onedir"
CLEAN=false
APPIMAGE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --platform)
            PLATFORM="$2"
            shift 2
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        --onefile)
            MODE="onefile"
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        --appimage)
            APPIMAGE=true
            shift
            ;;
        *)
            echo -e "${RED}Error: Argumento desconocido: $1${NC}"
            exit 1
            ;;
    esac
done

# Validar argumentos requeridos
if [ -z "$PLATFORM" ]; then
    echo -e "${RED}Error: --platform es requerido${NC}"
    exit 1
fi

if [ -z "$VERSION" ]; then
    echo -e "${RED}Error: --version es requerido${NC}"
    exit 1
fi

# Mostrar configuración
echo -e "${YELLOW}Configuración:${NC}"
echo "  Plataforma: $PLATFORM"
echo "  Versión:    $VERSION"
echo "  Modo:       $MODE"
echo "  Clean:      $CLEAN"
echo "  AppImage:   $APPIMAGE"

# Construir comando para build.py
BUILD_CMD="python build.py --platform $PLATFORM --version $VERSION"

if [ "$MODE" = "onefile" ]; then
    BUILD_CMD="$BUILD_CMD --onefile"
fi

if [ "$CLEAN" = true ]; then
    BUILD_CMD="$BUILD_CMD --clean"
fi

if [ "$APPIMAGE" = true ] && [ "$PLATFORM" = "linux" ]; then
    BUILD_CMD="$BUILD_CMD --appimage"
fi

# Ejecutar build
echo -e "\n${YELLOW}Ejecutando: $BUILD_CMD${NC}"
eval $BUILD_CMD

# Verificar resultados
if [ -d "dist" ]; then
    echo -e "\n${GREEN}✅ Build exitoso!${NC}"
    echo -e "${YELLOW}Archivos generados:${NC}"
    
    # Listar archivos con tamaño
    find dist -type f | while read file; do
        if command -v du >/dev/null 2>&1; then
            size=$(du -h "$file" 2>/dev/null | cut -f1)
            echo "  - $file ($size)"
        else
            echo "  - $file"
        fi
    done
    
    # Contar archivos
    file_count=$(find dist -type f | wc -l)
    echo -e "\n${GREEN}Total: $file_count archivos${NC}"
    
    # Crear checksum si hay archivos
    if [ $file_count -gt 0 ]; then
        echo -e "\n${YELLOW}Generando checksums...${NC}"
        if command -v sha256sum >/dev/null 2>&1; then
            (cd dist && sha256sum * > SHA256SUMS)
            echo "  Checksums guardados en: dist/SHA256SUMS"
        fi
    fi
    
    exit 0
else
    echo -e "\n${RED}❌ Error: No se creó el directorio dist/${NC}"
    echo "Directorio actual:"
    pwd
    ls -la
    exit 1
fi