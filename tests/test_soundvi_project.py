#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests completos para el sistema de guardado/carga .soundvi
y la integración de módulos wav2bar-reborn.
"""

import os
import sys
import json
import tempfile
import shutil
import time

# Agregar raíz del proyecto al path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from core.soundvi_project import (
    SoundviProject, create_soundvi_project, load_soundvi_project,
    encrypt_data, decrypt_data, _compute_checksum, SOUNDVI_MAGIC,
    convert_json_to_soundvi
)
from core.project_manager import ProjectManager, MediaItem
from core.timeline import Timeline


class TestResults:
    """Acumulador de resultados de tests."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, name):
        self.passed += 1
        print(f"  ✅ {name}")

    def fail(self, name, msg=""):
        self.failed += 1
        self.errors.append(f"{name}: {msg}")
        print(f"  ❌ {name}: {msg}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"RESULTADOS: {self.passed}/{total} tests pasados")
        if self.errors:
            print("Errores:")
            for e in self.errors:
                print(f"  - {e}")
        print(f"{'='*60}")
        return self.failed == 0


results = TestResults()


# ============================================================
# Test 1: Cifrado y descifrado
# ============================================================
def test_encryption():
    print("\n--- Test: Cifrado y Descifrado ---")

    # Cifrado normal
    data = b"Hello, Soundvi! Este es un test de cifrado."
    password = "test_password_123"

    encrypted = encrypt_data(data, password)
    assert encrypted != data, "Los datos cifrados no deben ser iguales a los originales"
    assert encrypted[:4] == SOUNDVI_MAGIC, "Debe tener magic bytes"

    decrypted = decrypt_data(encrypted, password)
    assert decrypted == data, "Los datos descifrados deben ser iguales a los originales"
    results.ok("Cifrado/Descifrado básico")

    # Contraseña incorrecta
    wrong_decrypt = decrypt_data(encrypted, "wrong_password")
    assert wrong_decrypt is None, "Contraseña incorrecta debe retornar None"
    results.ok("Contraseña incorrecta retorna None")

    # Datos corruptos
    corrupted = encrypted[:10] + b"CORRUPT" + encrypted[17:]
    corrupt_result = decrypt_data(corrupted, password)
    assert corrupt_result is None, "Datos corruptos deben retornar None"
    results.ok("Datos corruptos retorna None")

    # Datos vacíos
    empty_result = decrypt_data(b"", password)
    assert empty_result is None, "Datos vacíos deben retornar None"
    results.ok("Datos vacíos retorna None")

    # Datos grandes
    big_data = os.urandom(1024 * 100)  # 100KB
    big_encrypted = encrypt_data(big_data, password)
    big_decrypted = decrypt_data(big_encrypted, password)
    assert big_decrypted == big_data, "Datos grandes deben descifrar correctamente"
    results.ok("Cifrado/Descifrado datos grandes (100KB)")


# ============================================================
# Test 2: Crear y cargar proyecto .soundvi
# ============================================================
def test_create_load_project():
    print("\n--- Test: Crear y Cargar Proyecto .soundvi ---")

    test_data = {
        "project_name": "Proyecto Test",
        "author": "Tester",
        "description": "Proyecto para testing completo",
        "project_config": {
            "resolution": "1920x1080",
            "fps": 30,
            "duration": 120.0,
            "created_at": time.time(),
            "video_metadata": {"test": True}
        },
        "render_config": {
            "codec": "h264",
            "bitrate": "10M",
            "output_format": "mp4"
        },
        "timeline": {
            "tracks": [
                {"track_id": "t1", "track_type": "video", "name": "Video 1",
                 "index": 0, "clips": [], "muted": False}
            ],
            "duration": 120.0
        },
        "modules": [
            {"type": "straight_bar_module_StraightBarModule",
             "name": "Barras Rectas", "enabled": True,
             "config": {"n_bars": 64, "smoothing": 0.3}},
            {"type": "circular_bar_module_CircularBarModule",
             "name": "Barras Circulares", "enabled": False,
             "config": {"n_bars": 48}}
        ],
        "media_library": [],
        "undo_stack": [],
        "redo_stack": [],
    }

    with tempfile.TemporaryDirectory(prefix="soundvi_test_") as tmpdir:
        path = os.path.join(tmpdir, "test_project.soundvi")

        # Crear
        ok = create_soundvi_project(test_data, path)
        assert ok, "Debe crear exitosamente"
        assert os.path.exists(path), "Archivo debe existir"
        results.ok("Crear proyecto .soundvi")

        # Verificar que es un archivo .soundvi válido
        assert SoundviProject.is_valid_soundvi(path), "Debe ser un .soundvi válido"
        results.ok("Validación de archivo .soundvi")

        # Verificar tamaño > 0
        size = os.path.getsize(path)
        assert size > 100, f"Tamaño debe ser > 100 bytes (actual: {size})"
        results.ok(f"Tamaño del archivo: {size} bytes")

        # Cargar
        loaded = load_soundvi_project(path)
        assert loaded is not None, "Debe cargar exitosamente"
        results.ok("Cargar proyecto .soundvi")

        # Verificar datos
        manifest = loaded.get("manifest", {})
        assert manifest.get("project_name") == "Proyecto Test"
        results.ok("Nombre del proyecto correcto")

        assert manifest.get("author") == "Tester"
        results.ok("Autor correcto")

        assert manifest.get("encrypted") == True
        results.ok("Marcado como cifrado")

        modules = loaded.get("modules", [])
        assert len(modules) == 2, f"Debe tener 2 módulos (tiene {len(modules)})"
        results.ok("Módulos restaurados correctamente")

        timeline = loaded.get("timeline", {})
        assert "tracks" in timeline
        results.ok("Timeline restaurado")

        # Info rápida
        sp = SoundviProject()
        info = sp.get_project_info(path)
        assert info is not None
        assert info["project_name"] == "Proyecto Test"
        results.ok("Info rápida del proyecto")


# ============================================================
# Test 3: Proyecto con medios embebidos
# ============================================================
def test_embedded_media():
    print("\n--- Test: Proyecto con Medios Embebidos ---")

    with tempfile.TemporaryDirectory(prefix="soundvi_media_test_") as tmpdir:
        # Crear archivo de audio de prueba
        audio_path = os.path.join(tmpdir, "test_audio.wav")
        with open(audio_path, 'wb') as f:
            f.write(b"RIFF" + b"\x00" * 100)  # Fake WAV header

        # Crear imagen de prueba
        img_path = os.path.join(tmpdir, "test_image.png")
        with open(img_path, 'wb') as f:
            f.write(b"\x89PNG" + b"\x00" * 100)  # Fake PNG header

        test_data = {
            "project_name": "Proyecto con Medios",
            "author": "Tester",
            "description": "",
            "project_config": {"created_at": time.time()},
            "timeline": {"tracks": []},
            "modules": [],
            "render_config": {},
            "media_library": [
                {"path": audio_path, "name": "Audio Test", "media_type": "audio",
                 "file_size": os.path.getsize(audio_path)},
                {"path": img_path, "name": "Image Test", "media_type": "image",
                 "file_size": os.path.getsize(img_path)},
            ],
            "undo_stack": [],
            "redo_stack": [],
        }

        path = os.path.join(tmpdir, "media_project.soundvi")

        # Crear con medios embebidos
        ok = create_soundvi_project(test_data, path, embed_media=True)
        assert ok, "Debe crear con medios embebidos"
        results.ok("Crear proyecto con medios embebidos")

        # Cargar y verificar medios
        loaded = load_soundvi_project(path)
        assert loaded is not None
        media = loaded.get("media_library", [])
        assert len(media) == 2, f"Debe tener 2 medios (tiene {len(media)})"
        results.ok("Medios restaurados")

        # Verificar que los archivos embebidos fueron extraídos
        for m in media:
            if m.get("embedded", False):
                extracted = m.get("path", "")
                assert os.path.exists(extracted), f"Archivo extraído debe existir: {extracted}"
        results.ok("Archivos embebidos extraídos correctamente")


# ============================================================
# Test 4: ProjectManager completo
# ============================================================
def test_project_manager():
    print("\n--- Test: ProjectManager ---")

    pm = ProjectManager()
    assert pm.project_name == "Nuevo proyecto"
    assert pm.is_modified == False
    results.ok("Estado inicial del ProjectManager")

    # Modificar
    pm.mark_modified()
    assert pm.is_modified == True
    results.ok("mark_modified funciona")

    # Nuevo proyecto
    pm.new_project()
    assert pm.project_name == "Nuevo proyecto"
    assert pm.is_modified == False
    results.ok("new_project limpia estado")

    with tempfile.TemporaryDirectory(prefix="soundvi_pm_test_") as tmpdir:
        # Guardar como .soundvi
        path = os.path.join(tmpdir, "pm_test.soundvi")
        pm.project_name = "PM Test Project"
        pm.author = "PM Tester"
        pm.description = "Test del ProjectManager"
        pm.modules_state = [
            {"type": "test_module", "enabled": True, "config": {"param1": 42}}
        ]

        ok = pm.save_project(path)
        assert ok, "Debe guardar .soundvi"
        assert os.path.exists(path)
        results.ok("ProjectManager guarda .soundvi")

        # Cargar
        pm2 = ProjectManager()
        ok = pm2.load_project(path)
        assert ok, "Debe cargar .soundvi"
        assert pm2.project_name == "PM Test Project"
        assert pm2.author == "PM Tester"
        assert len(pm2.modules_state) == 1
        assert pm2.modules_state[0]["config"]["param1"] == 42
        results.ok("ProjectManager carga .soundvi correctamente")

        # Guardar como .svproj (legacy)
        json_path = os.path.join(tmpdir, "pm_test.svproj")
        pm.project_path = json_path
        ok = pm.save_project()
        assert ok, "Debe guardar .svproj"
        results.ok("ProjectManager guarda .svproj")

        # Cargar legacy
        pm3 = ProjectManager()
        ok = pm3.load_project(json_path)
        assert ok, "Debe cargar .svproj"
        assert pm3.project_name == "PM Test Project"
        results.ok("ProjectManager carga .svproj correctamente")

        # Summary
        summary = pm2.get_project_summary()
        assert "name" in summary
        assert summary["name"] == "PM Test Project"
        results.ok("get_project_summary funciona")


# ============================================================
# Test 5: Proyecto vacío
# ============================================================
def test_empty_project():
    print("\n--- Test: Proyecto Vacío ---")

    with tempfile.TemporaryDirectory(prefix="soundvi_empty_") as tmpdir:
        path = os.path.join(tmpdir, "empty.soundvi")

        # Crear proyecto vacío
        data = {
            "project_name": "Vacío",
            "project_config": {},
            "timeline": {},
            "modules": [],
            "media_library": [],
            "undo_stack": [],
            "redo_stack": [],
        }

        ok = create_soundvi_project(data, path)
        assert ok
        results.ok("Crear proyecto vacío")

        loaded = load_soundvi_project(path)
        assert loaded is not None
        assert loaded["manifest"]["project_name"] == "Vacío"
        results.ok("Cargar proyecto vacío")


# ============================================================
# Test 6: Archivo corrupto
# ============================================================
def test_corrupt_file():
    print("\n--- Test: Archivo Corrupto ---")

    with tempfile.TemporaryDirectory(prefix="soundvi_corrupt_") as tmpdir:
        # Archivo random
        path = os.path.join(tmpdir, "corrupt.soundvi")
        with open(path, 'wb') as f:
            f.write(os.urandom(500))

        loaded = load_soundvi_project(path)
        assert loaded is None, "Archivo corrupto debe retornar None"
        results.ok("Archivo corrupto manejado correctamente")

        # Archivo vacío
        empty_path = os.path.join(tmpdir, "empty.soundvi")
        with open(empty_path, 'wb') as f:
            f.write(b"")

        loaded = load_soundvi_project(empty_path)
        assert loaded is None
        results.ok("Archivo vacío manejado correctamente")

        # Archivo inexistente
        loaded = load_soundvi_project(os.path.join(tmpdir, "nonexistent.soundvi"))
        assert loaded is None
        results.ok("Archivo inexistente manejado correctamente")

        # is_valid_soundvi
        assert not SoundviProject.is_valid_soundvi(path)
        assert not SoundviProject.is_valid_soundvi(empty_path)
        assert not SoundviProject.is_valid_soundvi(os.path.join(tmpdir, "nope.soundvi"))
        results.ok("is_valid_soundvi detecta archivos inválidos")


# ============================================================
# Test 7: Conversión JSON a .soundvi
# ============================================================
def test_json_conversion():
    print("\n--- Test: Conversión JSON a .soundvi ---")

    with tempfile.TemporaryDirectory(prefix="soundvi_conv_") as tmpdir:
        json_data = {
            "project_name": "Converted Project",
            "project_config": {"resolution": "1280x720"},
            "timeline": {"tracks": []},
            "modules": [{"type": "test", "enabled": True}],
            "media_library": [],
        }
        json_path = os.path.join(tmpdir, "original.json")
        with open(json_path, 'w') as f:
            json.dump(json_data, f)

        soundvi_path = os.path.join(tmpdir, "converted.soundvi")
        ok = convert_json_to_soundvi(json_path, soundvi_path)
        assert ok
        results.ok("Conversión JSON a .soundvi")

        loaded = load_soundvi_project(soundvi_path)
        assert loaded is not None
        assert loaded["manifest"]["project_name"] == "Converted Project"
        results.ok("Proyecto convertido se carga correctamente")


# ============================================================
# Test 8: MediaItem serialización
# ============================================================
def test_media_item():
    print("\n--- Test: MediaItem ---")

    item = MediaItem("/tmp/test.mp4", "Video Test", "video")
    item.tags = ["test", "demo"]
    item.favorite = True
    item.duration = 30.5

    d = item.to_dict()
    assert d["name"] == "Video Test"
    assert d["favorite"] == True
    assert d["duration"] == 30.5
    results.ok("MediaItem.to_dict()")

    item2 = MediaItem.from_dict(d)
    assert item2.name == "Video Test"
    assert item2.favorite == True
    assert item2.duration == 30.5
    assert item2.tags == ["test", "demo"]
    results.ok("MediaItem.from_dict()")


# ============================================================
# Test 9: Módulos wav2bar-reborn se cargan
# ============================================================
def test_wav2bar_modules_load():
    print("\n--- Test: Módulos wav2bar-reborn ---")

    modules_to_check = [
        ("modules.audio.visualization.straight_bar_module", "StraightBarModule"),
        ("modules.audio.visualization.circular_bar_module", "CircularBarModule"),
        ("modules.audio.visualization.particle_flow_module", "ParticleFlowModule"),
        ("modules.audio.visualization.wave_visualizer_module", "WaveVisualizerModule"),
        ("modules.video.effects.svg_filter_module", "SVGFilterModule"),
        ("modules.video.effects.shadow_border_module", "ShadowBorderModule"),
        ("modules.video.generators.image_shape_module", "ImageShapeModule"),
        ("modules.utility.timer_module", "TimerVisualizerModule"),
    ]

    for mod_path, class_name in modules_to_check:
        try:
            mod = __import__(mod_path, fromlist=[class_name])
            cls = getattr(mod, class_name)
            instance = cls()
            assert instance.nombre, f"Módulo {class_name} debe tener nombre"
            assert instance.module_type in ("audio", "video", "utility")
            assert hasattr(instance, 'render')
            assert hasattr(instance, 'get_config_widgets')
            assert hasattr(instance, '_config')
            results.ok(f"Módulo {class_name} carga correctamente")
        except Exception as e:
            results.fail(f"Módulo {class_name}", str(e))


# ============================================================
# Test 10: Módulos wav2bar renderizado básico
# ============================================================
def test_wav2bar_render():
    print("\n--- Test: Renderizado básico de módulos wav2bar ---")

    import numpy as np

    # Frame de prueba (negro 320x240)
    frame = np.zeros((240, 320, 3), dtype=np.uint8)

    # StraightBarModule
    try:
        from modules.audio.visualization.straight_bar_module import StraightBarModule
        m = StraightBarModule()
        # Sin datos de audio, debe devolver el frame sin cambios
        result = m.render(frame, 0.0, fps=30)
        assert result.shape == frame.shape
        results.ok("StraightBarModule.render sin audio")

        m.habilitado = True
        result = m.render(frame, 0.0, fps=30)
        assert result.shape == frame.shape
        results.ok("StraightBarModule.render habilitado sin datos")
    except Exception as e:
        results.fail("StraightBarModule.render", str(e))

    # CircularBarModule
    try:
        from modules.audio.visualization.circular_bar_module import CircularBarModule
        m = CircularBarModule()
        result = m.render(frame, 0.0, fps=30)
        assert result.shape == frame.shape
        results.ok("CircularBarModule.render sin audio")
    except Exception as e:
        results.fail("CircularBarModule.render", str(e))

    # ParticleFlowModule
    try:
        from modules.audio.visualization.particle_flow_module import ParticleFlowModule
        m = ParticleFlowModule()
        result = m.render(frame, 0.0, fps=30)
        assert result.shape == frame.shape
        results.ok("ParticleFlowModule.render sin audio")
    except Exception as e:
        results.fail("ParticleFlowModule.render", str(e))

    # WaveVisualizerModule
    try:
        from modules.audio.visualization.wave_visualizer_module import WaveVisualizerModule
        m = WaveVisualizerModule()
        result = m.render(frame, 0.0, fps=30)
        assert result.shape == frame.shape
        results.ok("WaveVisualizerModule.render sin audio")
    except Exception as e:
        results.fail("WaveVisualizerModule.render", str(e))

    # SVGFilterModule
    try:
        from modules.video.effects.svg_filter_module import SVGFilterModule
        m = SVGFilterModule()
        m.habilitado = True
        m._config["filter_type"] = "invert"
        result = m.render(frame, 0.0, fps=30)
        assert result.shape == frame.shape
        results.ok("SVGFilterModule.render con filtro invert")

        m._config["filter_type"] = "sepia"
        result = m.render(frame.copy() + 50, 0.0, fps=30)
        assert result.shape == frame.shape
        results.ok("SVGFilterModule.render con filtro sepia")
    except Exception as e:
        results.fail("SVGFilterModule.render", str(e))

    # ShadowBorderModule
    try:
        from modules.video.effects.shadow_border_module import ShadowBorderModule
        m = ShadowBorderModule()
        m.habilitado = True
        result = m.render(frame, 0.0, fps=30)
        assert result.shape == frame.shape
        results.ok("ShadowBorderModule.render")
    except Exception as e:
        results.fail("ShadowBorderModule.render", str(e))

    # TimerVisualizerModule
    try:
        from modules.utility.timer_module import TimerVisualizerModule
        m = TimerVisualizerModule()
        m.habilitado = True
        m._duration = 60.0
        result = m.render(frame, 15.0, fps=30)
        assert result.shape == frame.shape
        results.ok("TimerVisualizerModule.render")
    except Exception as e:
        results.fail("TimerVisualizerModule.render", str(e))


# ============================================================
# Test 11: Proyecto grande (stress test)
# ============================================================
def test_large_project():
    print("\n--- Test: Proyecto Grande ---")

    with tempfile.TemporaryDirectory(prefix="soundvi_large_") as tmpdir:
        # Muchos módulos y medios
        modules = []
        for i in range(50):
            modules.append({
                "type": f"module_{i}",
                "name": f"Módulo {i}",
                "enabled": i % 2 == 0,
                "config": {f"param_{j}": j * i for j in range(10)}
            })

        media = []
        for i in range(20):
            fp = os.path.join(tmpdir, f"media_{i}.dat")
            with open(fp, 'wb') as f:
                f.write(os.urandom(1024))  # 1KB each
            media.append({
                "path": fp, "name": f"Media {i}",
                "media_type": "audio", "file_size": 1024
            })

        data = {
            "project_name": "Proyecto Grande",
            "project_config": {"resolution": "3840x2160"},
            "timeline": {
                "tracks": [
                    {"track_id": f"t{i}", "track_type": "video",
                     "name": f"Track {i}", "index": i, "clips": []}
                    for i in range(10)
                ]
            },
            "modules": modules,
            "media_library": media,
            "render_config": {"codec": "h265", "bitrate": "20M"},
            "undo_stack": [],
            "redo_stack": [],
        }

        path = os.path.join(tmpdir, "large.soundvi")
        ok = create_soundvi_project(data, path, embed_media=True)
        assert ok
        size = os.path.getsize(path)
        results.ok(f"Proyecto grande creado ({size / 1024:.1f} KB)")

        loaded = load_soundvi_project(path)
        assert loaded is not None
        assert len(loaded["modules"]) == 50
        results.ok("Proyecto grande cargado correctamente")


# ============================================================
# Ejecutar todos los tests
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  SOUNDVI - Suite de Tests Completa")
    print("=" * 60)

    test_encryption()
    test_create_load_project()
    test_embedded_media()
    test_project_manager()
    test_empty_project()
    test_corrupt_file()
    test_json_conversion()
    test_media_item()
    test_wav2bar_modules_load()
    test_wav2bar_render()
    test_large_project()

    success = results.summary()
    sys.exit(0 if success else 1)
