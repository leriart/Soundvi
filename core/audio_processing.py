#!/usr/bin/env python3
import numpy as np
from scipy.interpolate import interp1d
from scipy.signal import savgol_filter

def get_audio_features(audio_path, target_sr=22050, hop_length=512):
    """Extrae características espectrales del audio para visualización."""
    from librosa import load, stft, fft_frequencies
    y, sr = load(audio_path, sr=target_sr, mono=True)
    n_fft = 2048
    S = np.abs(stft(y, n_fft=n_fft, hop_length=hop_length))
    freqs = fft_frequencies(sr=sr, n_fft=n_fft)
    n_bars = 64
    corte_bajo, corte_alto = 50, 10000
    bordes = np.logspace(np.log10(corte_bajo), np.log10(corte_alto), n_bars + 1)
    bandas = np.zeros((n_bars, S.shape[1]))
    for i in range(n_bars):
        idx = np.where((freqs >= bordes[i]) & (freqs < bordes[i+1]))[0]
        if len(idx) > 0: bandas[i] = np.sqrt(np.mean(S[idx, :]**2, axis=0))
    bandas = np.power(np.maximum(bandas, 1e-10), 1.2)
    for i in range(n_bars):
        b_max = np.percentile(bandas[i], 99)
        if b_max > 0: bandas[i] = np.clip(bandas[i] / b_max * 100.0, 0, 100)
    x = np.arange(bandas.shape[1])
    f = interp1d(x, bandas, kind='linear', axis=1, fill_value="extrapolate")
    x_new = np.linspace(0, x[-1], bandas.shape[1] * 4)
    return f(x_new), sr, hop_length // 4

def compute_bar_heights(bands, duration, video_fps, hop_length, sr):
    """Devuelve las alturas de las barras para visualización."""
    # La física ahora se calcula en los módulos individuales
    return bands.T

def safe_volume_control(audio_data, sample_rate, target_volume=100, normalize=True, protection=True):
    datos = audio_data.astype(np.float32)
    if normalize:
        mx = np.max(np.abs(datos))
        if mx > 0: datos *= 0.8 / mx
    return datos * (target_volume / 100.0)
