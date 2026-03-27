#!/usr/bin/env python3
"""
Mapeo y remapeo de bandas de frecuencia.

Proporciona distribucion logaritmica de bandas identica a CAVA y funciones
auxiliares para remapear / interpolar cuando la cantidad de barras de origen
difiere de la objetivo.
"""

import numpy as np


# -- Calculo de bandas --------------------------------------------------------

def calculate_frequency_bands(
    low_freq: float = 50,
    high_freq: float = 10000,
    n_bars: int = 64,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Devuelve (bordes_banda, centros_banda) usando una escala logaritmica.
    """
    edges = np.logspace(np.log10(low_freq), np.log10(high_freq), n_bars + 1)
    centers = np.sqrt(edges[:-1] * edges[1:])  # media geometrica
    return edges, centers


def map_stft_to_bars(
    stft: np.ndarray,
    freqs: np.ndarray,
    low_freq: float = 50,
    high_freq: float = 10000,
    n_bars: int = 64,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Mapea una matriz de magnitud STFT (bins_freq, frames_tiempo) a
    (n_bars, frames_tiempo) usando bandas logaritmicas de frecuencia.

    Devuelve (bandas, bordes, centros).
    """
    edges, centers = calculate_frequency_bands(low_freq, high_freq, n_bars)
    n_frames = stft.shape[1]
    bands = np.zeros((n_bars, n_frames))

    for i in range(n_bars):
        idx = np.where((freqs >= edges[i]) & (freqs < edges[i + 1]))[0]
        if len(idx) > 0:
            bands[i] = np.mean(stft[idx, :], axis=0)
        else:
            mas_cercano = np.argmin(np.abs(freqs - centers[i]))
            bands[i] = stft[mas_cercano, :]

    return bands, edges, centers


# -- Remapeo ------------------------------------------------------------------

def remap_frequency_bands(
    bands: np.ndarray,
    source_centers: np.ndarray,
    target_n_bars: int,
    low_freq: float | None = None,
    high_freq: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Reduce la cantidad de bandas desde *source_centers* a *target_n_bars*
    usando promedio ponderado.
    """
    n_source, n_frames = bands.shape
    if low_freq is None:
        low_freq = source_centers[0]
    if high_freq is None:
        high_freq = source_centers[-1]

    target_edges = np.logspace(
        np.log10(low_freq), np.log10(high_freq), target_n_bars + 1
    )
    target_centers = np.sqrt(target_edges[:-1] * target_edges[1:])
    remapeado = np.zeros((target_n_bars, n_frames))

    for i in range(target_n_bars):
        idx = np.where(
            (source_centers >= target_edges[i])
            & (source_centers < target_edges[i + 1])
        )[0]
        if len(idx) > 0:
            pesos = 1.0 / (
                1.0
                + np.abs(source_centers[idx] - target_centers[i])
                / target_centers[i]
            )
            pesos /= pesos.sum()
            for j, si in enumerate(idx):
                remapeado[i] += pesos[j] * bands[si]
        else:
            mas_cercano = np.argmin(np.abs(source_centers - target_centers[i]))
            remapeado[i] = bands[mas_cercano]

    return remapeado, target_centers


def interpolate_frequency_bands(
    bands: np.ndarray,
    source_centers: np.ndarray,
    target_centers: np.ndarray,
) -> np.ndarray:
    """
    Aumenta la cantidad de bandas via interpolacion logaritmica.
    """
    n_frames = bands.shape[1]
    n_target = len(target_centers)
    log_src = np.log10(source_centers)
    log_tgt = np.log10(target_centers)
    resultado = np.zeros((n_target, n_frames))
    for frame in range(n_frames):
        resultado[:, frame] = np.interp(log_tgt, log_src, bands[:, frame])
    return resultado


def adaptive_remap(
    bands: np.ndarray,
    source_centers: np.ndarray,
    target_n_bars: int,
    low_freq: float | None = None,
    high_freq: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Elige la mejor estrategia de remapeo automaticamente.
    """
    n_source = bands.shape[0]
    if low_freq is None:
        low_freq = source_centers[0]
    if high_freq is None:
        high_freq = source_centers[-1]

    if target_n_bars <= n_source:
        return remap_frequency_bands(
            bands, source_centers, target_n_bars, low_freq, high_freq
        )

    target_edges = np.logspace(
        np.log10(low_freq), np.log10(high_freq), target_n_bars + 1
    )
    target_centers = np.sqrt(target_edges[:-1] * target_edges[1:])
    return interpolate_frequency_bands(bands, source_centers, target_centers), target_centers
