#!/usr/bin/env python3
"""
Módulo de flujo de partículas (Particle Flow Visualizer)
Inspirado en wav2bar-reborn: vo_particle_flow

Emite partículas reactivas al audio con física básica.
"""

import numpy as np
import cv2
import random

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QSlider, QSpinBox, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt

from modules.core.base import Module


class Particle:
    """Partícula individual con física básica."""
    __slots__ = ['x', 'y', 'vx', 'vy', 'life', 'max_life', 'size', 'color', 'alpha']

    def __init__(self, x, y, vx, vy, life, size, color):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.size = size
        self.color = color
        self.alpha = 1.0

    def update(self, dt, gravity=0.0, friction=0.98):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += gravity * dt
        self.vx *= friction
        self.vy *= friction
        self.life -= dt
        self.alpha = max(0, self.life / self.max_life)
        self.size = max(1, self.size * 0.998)


class ParticleFlowModule(Module):
    """Visualizador de flujo de partículas reactivas al audio."""

    module_type = "audio"
    module_category = "visualization"
    module_tags = ["particles", "flow", "wav2bar", "audio", "reactive"]
    module_version = "1.0.0"
    module_author = "Soundvi (wav2bar-reborn)"

    def __init__(self):
        super().__init__(
            nombre="Flujo de Partículas (wav2bar)",
            descripcion="Partículas reactivas al audio con física básica"
        )
        self._audio_data = None
        self._duration = 0.0
        self._particles = []
        self._last_time = -1
        self._config = {
            "max_particles": 500,
            "emit_rate": 20,
            "particle_life": 2.0,
            "particle_size": 4,
            "speed": 150,
            "gravity": 50,
            "friction": 0.98,
            "opacity": 0.85,
            "emit_mode": "center",  # center, bottom, sides
            "color_r": 100, "color_g": 200, "color_b": 255,
            "color_variation": 50,
            "glow": True,
            "energy_threshold": 0.1,
            "size_by_energy": True,
        }

    def prepare_audio(self, audio_path, mel_data, sr, hop, duration, fps, **kwargs):
        try:
            import librosa
            offset = kwargs.get('audio_offset', 0.0)
            y, sr = librosa.load(audio_path, sr=22050, mono=True, offset=offset, duration=duration)
            S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
            # Global energy per frame
            energy = np.mean(S, axis=0)
            energy = np.power(np.maximum(energy, 1e-10), 0.4)
            mx = np.max(energy)
            if mx > 0:
                energy /= mx

            # Also get bass and treble
            freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
            bass_idx = np.where(freqs < 250)[0]
            treble_idx = np.where(freqs > 4000)[0]
            bass = np.mean(S[bass_idx, :], axis=0) if len(bass_idx) > 0 else energy
            treble = np.mean(S[treble_idx, :], axis=0) if len(treble_idx) > 0 else energy
            for arr in [bass, treble]:
                mx = np.max(arr)
                if mx > 0:
                    arr /= mx

            from scipy.interpolate import interp1d
            n_frames = int(duration * fps)
            x_old = np.linspace(0, 1, len(energy))
            x_new = np.linspace(0, 1, n_frames)
            self._audio_data = np.zeros((n_frames, 3))
            for idx, arr in enumerate([energy, bass, treble]):
                f = interp1d(x_old, arr[:len(x_old)], kind='linear', fill_value='extrapolate')
                self._audio_data[:, idx] = np.clip(f(x_new), 0, 1)
            self._duration = duration
            self._particles = []
            self._last_time = -1
        except Exception as e:
            print(f"[ParticleFlowModule] Error: {e}")

    def _emit_particles(self, energy, bass, w, h):
        """Emite nuevas partículas basadas en la energía del audio."""
        threshold = self._config.get("energy_threshold", 0.1)
        if energy < threshold:
            return

        n_emit = int(self._config["emit_rate"] * energy)
        mode = self._config.get("emit_mode", "center")
        speed = self._config.get("speed", 150)
        var = self._config.get("color_variation", 50)

        for _ in range(n_emit):
            if len(self._particles) >= self._config["max_particles"]:
                break

            if mode == "center":
                px, py = w / 2, h / 2
                angle = random.uniform(0, 2 * np.pi)
                sp = speed * (0.5 + energy * 0.5) * random.uniform(0.5, 1.5)
                vx = sp * np.cos(angle)
                vy = sp * np.sin(angle)
            elif mode == "bottom":
                px = random.uniform(0, w)
                py = h
                vx = random.uniform(-speed * 0.3, speed * 0.3)
                vy = -speed * (0.5 + bass * 0.5) * random.uniform(0.5, 1.5)
            else:  # sides
                side = random.choice([0, w])
                px = side
                py = random.uniform(h * 0.2, h * 0.8)
                direction = 1 if side == 0 else -1
                vx = direction * speed * random.uniform(0.5, 1.5)
                vy = random.uniform(-speed * 0.3, speed * 0.3)

            cr = min(255, max(0, self._config["color_r"] + random.randint(-var, var)))
            cg = min(255, max(0, self._config["color_g"] + random.randint(-var, var)))
            cb = min(255, max(0, self._config["color_b"] + random.randint(-var, var)))

            size = self._config["particle_size"]
            if self._config.get("size_by_energy", True):
                size = max(1, int(size * (0.5 + energy)))

            p = Particle(
                x=px, y=py, vx=vx, vy=vy,
                life=self._config["particle_life"] * random.uniform(0.5, 1.5),
                size=size,
                color=(cb, cg, cr)
            )
            self._particles.append(p)

    def render(self, frame, tiempo, **kwargs):
        if not self.habilitado or self._audio_data is None:
            return frame
        try:
            h, w = frame.shape[:2]
            fps = kwargs.get('fps', 30)
            fi = min(int(tiempo * fps), len(self._audio_data) - 1)
            energy, bass, treble = self._audio_data[fi]

            dt = 1.0 / fps

            # Emit new particles
            self._emit_particles(energy, bass, w, h)

            # Update particles
            gravity = self._config.get("gravity", 50)
            friction = self._config.get("friction", 0.98)
            alive = []
            for p in self._particles:
                p.update(dt, gravity, friction)
                if p.life > 0 and 0 <= p.x < w and 0 <= p.y < h:
                    alive.append(p)
            self._particles = alive

            # Draw particles
            overlay = frame.copy()
            glow = self._config.get("glow", True)
            for p in self._particles:
                x, y = int(p.x), int(p.y)
                size = max(1, int(p.size))
                color = tuple(int(c * p.alpha) for c in p.color)

                if glow and size > 2:
                    # Glow effect
                    glow_size = size * 2
                    glow_color = tuple(int(c * p.alpha * 0.3) for c in p.color)
                    cv2.circle(overlay, (x, y), glow_size, glow_color, -1)

                cv2.circle(overlay, (x, y), size, color, -1)

            alpha = self._config.get("opacity", 0.85)
            return cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
        except Exception as e:
            return frame

    
    def get_config(self):
        """Retorna la configuración actual del módulo."""
        return dict(self._config)
    def get_config_widgets(self, parent, app):
        content = QWidget(parent)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        # Max particles
        row_layout = lambda: None  # placeholder
        layout.addWidget(QLabel("Máx. partículas:"))
        max_spin = QSpinBox()
        max_spin.setRange(50, 2000)
        max_spin.setValue(self._config["max_particles"])
        max_spin.valueChanged.connect(lambda v: self._update_config("max_particles", v, app))
        layout.addWidget(max_spin)

        # Emit rate
        layout.addWidget(QLabel("Tasa de emisión:"))
        rate_slider = QSlider(Qt.Orientation.Horizontal)
        rate_slider.setRange(1, 100)
        rate_slider.setValue(self._config["emit_rate"])
        rate_slider.valueChanged.connect(lambda v: self._update_config("emit_rate", v, app))
        layout.addWidget(rate_slider)

        # Speed
        layout.addWidget(QLabel("Velocidad:"))
        speed_slider = QSlider(Qt.Orientation.Horizontal)
        speed_slider.setRange(10, 500)
        speed_slider.setValue(self._config["speed"])
        speed_slider.valueChanged.connect(lambda v: self._update_config("speed", v, app))
        layout.addWidget(speed_slider)

        # Emit mode
        layout.addWidget(QLabel("Modo emisión:"))
        mode_combo = QComboBox()
        mode_combo.addItems(["center", "bottom", "sides"])
        mode_combo.setCurrentText(self._config["emit_mode"])
        mode_combo.currentTextChanged.connect(lambda v: self._update_config("emit_mode", v, app))
        layout.addWidget(mode_combo)

        # Glow
        glow_cb = QCheckBox("Efecto glow")
        glow_cb.setChecked(self._config["glow"])
        glow_cb.toggled.connect(lambda v: self._update_config("glow", v, app))
        layout.addWidget(glow_cb)

        return content
