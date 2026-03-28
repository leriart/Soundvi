#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de archivos .soundvi - Proyectos comprimidos y cifrados.

Formato .soundvi (ZIP cifrado con estructura interna):
  ├── manifest.json          # Metadatos, checksums, estructura
  ├── config/
  │   ├── project.json       # Config principal del proyecto
  │   ├── timeline.json      # Timeline serializado
  │   ├── modules.json       # Módulos activos y su configuración
  │   └── render.json        # Configuración de render
  ├── media/                 # Archivos de medios (incrustados)
  │   ├── audio/
  │   └── images/
  ├── cache/
  │   └── thumbnails/
  └── history/
      └── actions.json       # Historial de undo/redo

Cifrado: XOR con derivación de clave PBKDF2-like (hashlib).
Compresión: ZIP_DEFLATED (zlib).
"""

import os
import json
import zipfile
import tempfile
import shutil
import hashlib
import hmac
import struct
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    import zlib
    COMPRESSION = zipfile.ZIP_DEFLATED
except ImportError:
    COMPRESSION = zipfile.ZIP_STORED

# -- Constantes del formato --
SOUNDVI_MAGIC = b"SNDV"          # Magic bytes al inicio
SOUNDVI_FORMAT_VERSION = 2        # Versión del formato
ENCRYPTION_ITERATIONS = 100_000   # Iteraciones para derivación de clave
SALT_SIZE = 16                    # Bytes de salt


# =============================================================================
# Cifrado básico (XOR con clave derivada de PBKDF2-HMAC-SHA256)
# =============================================================================

def _derive_key(password: str, salt: bytes, length: int = 32) -> bytes:
    """Deriva una clave de cifrado usando PBKDF2-HMAC-SHA256."""
    return hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        ENCRYPTION_ITERATIONS,
        dklen=length
    )


def _xor_crypt(data: bytes, key: bytes) -> bytes:
    """Cifra/descifra datos con XOR usando la clave extendida."""
    key_len = len(key)
    return bytes(b ^ key[i % key_len] for i, b in enumerate(data))


def _compute_checksum(data: bytes) -> str:
    """Calcula SHA-256 de los datos."""
    return hashlib.sha256(data).hexdigest()


def encrypt_data(data: bytes, password: str) -> bytes:
    """
    Cifra datos con contraseña.

    Formato de salida:
      MAGIC (4B) | VERSION (1B) | SALT (16B) | HMAC (32B) | ENCRYPTED_DATA
    """
    salt = os.urandom(SALT_SIZE)
    key = _derive_key(password, salt)

    # Cifrar
    encrypted = _xor_crypt(data, key)

    # HMAC de integridad
    mac = hmac.new(key, encrypted, hashlib.sha256).digest()

    # Ensamblar
    header = SOUNDVI_MAGIC + struct.pack('B', SOUNDVI_FORMAT_VERSION) + salt + mac
    return header + encrypted


def decrypt_data(raw: bytes, password: str) -> Optional[bytes]:
    """
    Descifra datos protegidos con contraseña.

    Returns:
        Datos descifrados o None si la contraseña es incorrecta / datos corruptos.
    """
    min_size = len(SOUNDVI_MAGIC) + 1 + SALT_SIZE + 32
    if len(raw) < min_size:
        return None

    # Verificar magic
    offset = 0
    magic = raw[offset:offset + 4]
    offset += 4
    if magic != SOUNDVI_MAGIC:
        return None

    # Versión
    version = struct.unpack('B', raw[offset:offset + 1])[0]
    offset += 1
    if version > SOUNDVI_FORMAT_VERSION:
        print(f"[decrypt] Versión de formato no soportada: {version}")
        return None

    # Salt
    salt = raw[offset:offset + SALT_SIZE]
    offset += SALT_SIZE

    # HMAC esperado
    expected_mac = raw[offset:offset + 32]
    offset += 32

    # Datos cifrados
    encrypted = raw[offset:]

    # Derivar clave y verificar HMAC
    key = _derive_key(password, salt)
    actual_mac = hmac.new(key, encrypted, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_mac, actual_mac):
        print("[decrypt] HMAC no coincide: contraseña incorrecta o datos corruptos")
        return None

    # Descifrar
    return _xor_crypt(encrypted, key)


# =============================================================================
# Clase principal SoundviProject
# =============================================================================

class SoundviProject:
    """Maneja archivos .soundvi comprimidos y opcionalmente cifrados."""

    VERSION = "2.0.0"
    EXTENSION = ".soundvi"
    MANIFEST_FILE = "manifest.json"
    CONFIG_DIR = "config/"
    MEDIA_DIR = "media/"
    MEDIA_AUDIO_DIR = "media/audio/"
    MEDIA_IMAGES_DIR = "media/images/"
    CACHE_DIR = "cache/"
    THUMBNAILS_DIR = "cache/thumbnails/"
    HISTORY_DIR = "history/"

    # Contraseña por defecto para cifrado básico (protección mínima)
    DEFAULT_PASSWORD = "Soundvi2025!SecureProject"

    def __init__(self, password: Optional[str] = None):
        self.password = password or self.DEFAULT_PASSWORD
        self.temp_dir = None
        self.project_data = {}

    # -----------------------------------------------------------------
    # Crear proyecto
    # -----------------------------------------------------------------
    def create_project(self, project_data: Dict[str, Any],
                       output_path: str,
                       embed_media: bool = False) -> bool:
        """
        Crea un nuevo archivo .soundvi.

        Args:
            project_data: Datos completos del proyecto
            output_path: Ruta de salida
            embed_media: Si True, incrusta archivos de medios

        Returns:
            True si se creó exitosamente
        """
        if not output_path.endswith(self.EXTENSION):
            output_path += self.EXTENSION

        try:
            self.temp_dir = tempfile.mkdtemp(prefix="soundvi_create_")
            self._prepare_structure(project_data, embed_media)

            # Crear ZIP en memoria
            zip_buffer_path = output_path + ".tmp"
            with zipfile.ZipFile(zip_buffer_path, 'w', COMPRESSION, compresslevel=6) as zipf:
                for root, dirs, files in os.walk(self.temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, self.temp_dir)
                        zipf.write(file_path, arcname)
                zipf.comment = f"Soundvi Project v{self.VERSION}".encode('utf-8')

            # Leer ZIP, cifrar y escribir archivo final
            with open(zip_buffer_path, 'rb') as f:
                zip_data = f.read()

            encrypted = encrypt_data(zip_data, self.password)
            with open(output_path, 'wb') as f:
                f.write(encrypted)

            # Limpieza
            os.remove(zip_buffer_path)
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir = None

            print(f"[SoundviProject] Proyecto creado: {output_path} "
                  f"({os.path.getsize(output_path) / 1024:.1f} KB)")
            return True

        except Exception as e:
            print(f"[SoundviProject] Error creando proyecto: {e}")
            import traceback
            traceback.print_exc()
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            return False

    def _prepare_structure(self, project_data: Dict[str, Any], embed_media: bool):
        """Prepara la estructura de directorios con todos los datos."""
        # Crear directorios
        for d in [self.CONFIG_DIR, self.MEDIA_AUDIO_DIR, self.MEDIA_IMAGES_DIR,
                  self.THUMBNAILS_DIR, self.HISTORY_DIR]:
            os.makedirs(os.path.join(self.temp_dir, d), exist_ok=True)

        # -- Manifest --
        media_files = []
        media_checksums = {}

        manifest = {
            "format_version": SOUNDVI_FORMAT_VERSION,
            "app_version": self.VERSION,
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat(),
            "project_name": project_data.get("project_name", "Sin nombre"),
            "author": project_data.get("author", ""),
            "description": project_data.get("description", ""),
            "encrypted": True,
            "embedded_media": embed_media,
            "structure": {
                "config": ["project.json", "timeline.json", "modules.json", "render.json"],
                "media": media_files,
                "history": ["actions.json"]
            },
            "checksums": {}
        }

        # -- Config: project.json --
        project_config = project_data.get("project_config", {})
        project_config["modified_at"] = time.time()
        self._write_json(self.CONFIG_DIR + "project.json", project_config)

        # -- Config: timeline.json --
        timeline_data = project_data.get("timeline", {})
        self._write_json(self.CONFIG_DIR + "timeline.json", timeline_data)

        # -- Config: modules.json --
        modules_data = project_data.get("modules", [])
        self._write_json(self.CONFIG_DIR + "modules.json", modules_data)

        # -- Config: render.json --
        render_data = project_data.get("render_config", project_data.get("render_settings", {}))
        self._write_json(self.CONFIG_DIR + "render.json", render_data)

        # -- Media --
        media_library = project_data.get("media_library", [])
        for media in media_library:
            media_path = media.get("path", "")
            if not media_path:
                continue
            if embed_media and os.path.exists(media_path):
                basename = os.path.basename(media_path)
                ext = os.path.splitext(basename)[1].lower()
                if ext in ('.wav', '.mp3', '.flac', '.ogg', '.aac', '.m4a'):
                    dest_subdir = self.MEDIA_AUDIO_DIR
                else:
                    dest_subdir = self.MEDIA_IMAGES_DIR
                dest = os.path.join(self.temp_dir, dest_subdir, basename)
                # Evitar duplicados
                counter = 1
                while os.path.exists(dest):
                    name, ext_f = os.path.splitext(basename)
                    dest = os.path.join(self.temp_dir, dest_subdir, f"{name}_{counter}{ext_f}")
                    counter += 1
                shutil.copy2(media_path, dest)
                rel_path = os.path.relpath(dest, self.temp_dir)
                media_files.append(rel_path)
                # Checksum del archivo embebido
                with open(dest, 'rb') as mf:
                    media_checksums[rel_path] = _compute_checksum(mf.read())
                # Actualizar referencia en media para que apunte al embebido
                media["embedded"] = True
                media["embedded_path"] = rel_path
            else:
                media["embedded"] = False

        # Guardar la lista de medios como referencia
        self._write_json(self.CONFIG_DIR + "media_library.json", media_library)

        # -- History --
        history_data = {
            "undo_stack": project_data.get("undo_stack", []),
            "redo_stack": project_data.get("redo_stack", []),
            "last_action": project_data.get("last_action", ""),
            "action_count": project_data.get("action_count", 0)
        }
        self._write_json(self.HISTORY_DIR + "actions.json", history_data)

        # -- Checksums de configuración --
        for config_file in ["project.json", "timeline.json", "modules.json", "render.json", "media_library.json"]:
            fp = os.path.join(self.temp_dir, self.CONFIG_DIR, config_file)
            if os.path.exists(fp):
                with open(fp, 'rb') as cf:
                    manifest["checksums"][f"config/{config_file}"] = _compute_checksum(cf.read())

        manifest["checksums"].update(media_checksums)
        manifest["structure"]["media"] = media_files

        # Escribir manifest final
        self._write_json(self.MANIFEST_FILE, manifest)

    def _write_json(self, relative_path: str, data: Any):
        """Escribe un archivo JSON en el directorio temporal."""
        full_path = os.path.join(self.temp_dir, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    # -----------------------------------------------------------------
    # Cargar proyecto
    # -----------------------------------------------------------------
    def load_project(self, project_path: str) -> Optional[Dict[str, Any]]:
        """
        Carga un archivo .soundvi.

        Returns:
            Datos completos del proyecto o None si hay error.
        """
        if not os.path.exists(project_path):
            print(f"[SoundviProject] Archivo no encontrado: {project_path}")
            return None

        try:
            # Leer y descifrar
            with open(project_path, 'rb') as f:
                raw = f.read()

            zip_data = decrypt_data(raw, self.password)
            if zip_data is None:
                print(f"[SoundviProject] Error descifrando: contraseña incorrecta o archivo corrupto")
                # Intentar como ZIP sin cifrado (compatibilidad legacy)
                return self._load_legacy_zip(project_path)

            # Extraer ZIP a temporal
            self.temp_dir = tempfile.mkdtemp(prefix="soundvi_load_")
            zip_path = os.path.join(self.temp_dir, "project.zip")
            with open(zip_path, 'wb') as f:
                f.write(zip_data)

            with zipfile.ZipFile(zip_path, 'r') as zipf:
                zipf.extractall(self.temp_dir)

            os.remove(zip_path)

            # Leer manifest
            manifest = self._read_json(self.MANIFEST_FILE)
            if manifest is None:
                print("[SoundviProject] No se encontró manifest.json")
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                return None

            # Verificar checksums
            checksums = manifest.get("checksums", {})
            for rel_path, expected_hash in checksums.items():
                fp = os.path.join(self.temp_dir, rel_path)
                if os.path.exists(fp):
                    with open(fp, 'rb') as cf:
                        actual = _compute_checksum(cf.read())
                    if actual != expected_hash:
                        print(f"[SoundviProject] ADVERTENCIA: checksum no coincide para {rel_path}")

            # Construir datos del proyecto
            project_data = {
                "manifest": manifest,
                "project_config": self._read_json(self.CONFIG_DIR + "project.json") or {},
                "timeline": self._read_json(self.CONFIG_DIR + "timeline.json") or {},
                "modules": self._read_json(self.CONFIG_DIR + "modules.json") or [],
                "render_config": self._read_json(self.CONFIG_DIR + "render.json") or {},
                "media_library": self._read_json(self.CONFIG_DIR + "media_library.json") or [],
                "history": self._read_json(self.HISTORY_DIR + "actions.json") or {},
            }

            # Procesar medios embebidos: copiar a directorio persistente
            if manifest.get("embedded_media", False):
                persistent_media_dir = tempfile.mkdtemp(prefix="soundvi_media_")
                for media_item in project_data["media_library"]:
                    if media_item.get("embedded", False):
                        embedded_path = media_item.get("embedded_path", "")
                        src = os.path.join(self.temp_dir, embedded_path)
                        if os.path.exists(src):
                            basename = os.path.basename(src)
                            dest = os.path.join(persistent_media_dir, basename)
                            shutil.copy2(src, dest)
                            media_item["extracted_path"] = dest
                            media_item["path"] = dest

            # Limpiar temporal
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir = None

            print(f"[SoundviProject] Proyecto cargado: {project_path}")
            return project_data

        except Exception as e:
            print(f"[SoundviProject] Error cargando proyecto: {e}")
            import traceback
            traceback.print_exc()
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            return None

    def _load_legacy_zip(self, project_path: str) -> Optional[Dict[str, Any]]:
        """Intenta cargar un archivo .soundvi legacy (ZIP sin cifrado)."""
        try:
            self.temp_dir = tempfile.mkdtemp(prefix="soundvi_legacy_")
            with zipfile.ZipFile(project_path, 'r') as zipf:
                zipf.extractall(self.temp_dir)

            manifest = self._read_json(self.MANIFEST_FILE)
            if manifest is None:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                return None

            project_data = {
                "manifest": manifest,
                "project_config": self._read_json(self.CONFIG_DIR + "project.json") or {},
                "timeline": self._read_json(self.CONFIG_DIR + "timeline.json") or {},
                "modules": self._read_json(self.CONFIG_DIR + "modules.json") or [],
                "render_config": self._read_json(self.CONFIG_DIR + "render.json") or {},
                "media_library": [],
                "history": self._read_json(self.HISTORY_DIR + "actions.json") or {},
            }

            # Buscar medios
            media_dir = os.path.join(self.temp_dir, self.MEDIA_DIR)
            if os.path.exists(media_dir):
                for root, _, files in os.walk(media_dir):
                    for f in files:
                        fp = os.path.join(root, f)
                        project_data["media_library"].append({
                            "path": fp, "name": f, "embedded": True,
                            "size": os.path.getsize(fp)
                        })

            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir = None
            print(f"[SoundviProject] Proyecto legacy cargado: {project_path}")
            return project_data

        except Exception as e:
            print(f"[SoundviProject] Error cargando proyecto legacy: {e}")
            if self.temp_dir:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            return None

    def _read_json(self, relative_path: str) -> Optional[Any]:
        """Lee un archivo JSON desde el directorio temporal."""
        full_path = os.path.join(self.temp_dir, relative_path)
        if not os.path.exists(full_path):
            return None
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[SoundviProject] Error leyendo {relative_path}: {e}")
            return None

    # -----------------------------------------------------------------
    # Información rápida del proyecto
    # -----------------------------------------------------------------
    def get_project_info(self, project_path: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información del proyecto sin cargarlo completamente.
        Intenta descifrar solo el manifest.
        """
        try:
            with open(project_path, 'rb') as f:
                raw = f.read()

            zip_data = decrypt_data(raw, self.password)
            if zip_data is None:
                return None

            import io
            with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zipf:
                with zipf.open(self.MANIFEST_FILE) as mf:
                    manifest = json.load(mf)

            return {
                "file": project_path,
                "size": os.path.getsize(project_path),
                "project_name": manifest.get("project_name", "Sin nombre"),
                "author": manifest.get("author", ""),
                "description": manifest.get("description", ""),
                "created": manifest.get("created", ""),
                "modified": manifest.get("modified", ""),
                "version": manifest.get("app_version", ""),
                "encrypted": manifest.get("encrypted", False),
                "embedded_media": manifest.get("embedded_media", False),
                "media_count": len(manifest.get("structure", {}).get("media", [])),
            }
        except Exception as e:
            print(f"[SoundviProject] Error obteniendo info: {e}")
            return None

    # -----------------------------------------------------------------
    # Extraer medios
    # -----------------------------------------------------------------
    def extract_media(self, project_path: str, output_dir: str) -> List[str]:
        """Extrae medios embebidos de un proyecto .soundvi."""
        extracted = []
        try:
            data = self.load_project(project_path)
            if data is None:
                return extracted
            for item in data.get("media_library", []):
                if item.get("embedded", False):
                    src = item.get("extracted_path", item.get("path", ""))
                    if src and os.path.exists(src):
                        dest = os.path.join(output_dir, os.path.basename(src))
                        shutil.copy2(src, dest)
                        extracted.append(dest)
            print(f"[SoundviProject] {len(extracted)} medios extraídos a {output_dir}")
        except Exception as e:
            print(f"[SoundviProject] Error extrayendo medios: {e}")
        return extracted

    # -----------------------------------------------------------------
    # Validación
    # -----------------------------------------------------------------
    @staticmethod
    def is_valid_soundvi(filepath: str) -> bool:
        """Verifica rápidamente si un archivo es un .soundvi válido."""
        try:
            with open(filepath, 'rb') as f:
                magic = f.read(4)
            return magic == SOUNDVI_MAGIC
        except Exception:
            return False


# =============================================================================
# Funciones de conveniencia
# =============================================================================

def create_soundvi_project(project_data: Dict[str, Any],
                           output_path: str,
                           password: Optional[str] = None,
                           embed_media: bool = False) -> bool:
    """Crea un nuevo proyecto .soundvi."""
    project = SoundviProject(password)
    return project.create_project(project_data, output_path, embed_media)


def load_soundvi_project(project_path: str,
                         password: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Carga un proyecto .soundvi."""
    project = SoundviProject(password)
    return project.load_project(project_path)


def convert_json_to_soundvi(json_path: str,
                            soundvi_path: str,
                            embed_media: bool = False) -> bool:
    """Convierte un proyecto JSON legacy a formato .soundvi."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        return create_soundvi_project(json_data, soundvi_path, embed_media=embed_media)
    except Exception as e:
        print(f"[convert_json_to_soundvi] Error: {e}")
        return False


if __name__ == "__main__":
    # Prueba rápida
    test_data = {
        "project_name": "Proyecto de Prueba",
        "author": "Usuario Soundvi",
        "description": "Prueba del formato .soundvi v2 con cifrado",
        "project_config": {
            "resolution": "1920x1080", "fps": 30, "duration": 60.0,
            "created_at": time.time()
        },
        "timeline": {"tracks": [], "duration": 60.0},
        "modules": [
            {"type": "straight_bar", "enabled": True, "config": {}},
            {"type": "circular_bar", "enabled": False, "config": {}}
        ],
        "render_config": {"codec": "h264", "bitrate": "10M"},
        "media_library": [],
        "undo_stack": [],
        "redo_stack": []
    }

    test_path = "/tmp/test_project.soundvi"
    print("=== Creando proyecto de prueba ===")
    ok = create_soundvi_project(test_data, test_path)
    print(f"Creado: {ok}")

    if ok:
        print("\n=== Cargando proyecto ===")
        loaded = load_soundvi_project(test_path)
        print(f"Cargado: {loaded is not None}")
        if loaded:
            print(f"Nombre: {loaded['manifest']['project_name']}")
            print(f"Módulos: {len(loaded['modules'])}")

        print("\n=== Validando archivo ===")
        print(f"Válido: {SoundviProject.is_valid_soundvi(test_path)}")
        print(f"Inválido: {SoundviProject.is_valid_soundvi('/tmp/nonexistent.soundvi')}")

        print("\n=== Info rápida ===")
        sp = SoundviProject()
        info = sp.get_project_info(test_path)
        print(f"Info: {info}")
