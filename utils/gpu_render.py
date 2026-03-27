#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Soporte para Renderizado Acelerado por GPU.

Detecta automaticamente la disponibilidad de CUDA (NVIDIA) u OpenCL
y proporciona funciones de procesamiento de imagen acelerado.
Incluye fallback transparente a CPU si la GPU no esta disponible.
"""

from __future__ import annotations
import os
import subprocess
from typing import Optional, Dict, Any, List, Tuple

import numpy as np
import cv2


# -- Estado global de GPU --
_gpu_info: Dict[str, Any] = {
    "cuda_available": False,
    "opencl_available": False,
    "gpu_name": "",
    "cuda_version": "",
    "opencv_cuda": False,
    "opencv_opencl": False,
    "detected": False,
}


def detect_gpu() -> Dict[str, Any]:
    """
    Detecta la GPU disponible y sus capacidades.
    
    Verifica:
    1. CUDA (NVIDIA) via nvidia-smi
    2. OpenCL via cv2.ocl
    3. OpenCV con soporte CUDA compilado
    
    Returns:
        Diccionario con informacion de la GPU
    """
    global _gpu_info
    
    if _gpu_info["detected"]:
        return _gpu_info
    
    # -- Detectar NVIDIA CUDA --
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(",")
            if len(parts) >= 1:
                _gpu_info["cuda_available"] = True
                _gpu_info["gpu_name"] = parts[0].strip()
                if len(parts) >= 2:
                    _gpu_info["cuda_version"] = parts[1].strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    
    # -- Detectar OpenCL --
    try:
        if cv2.ocl.haveOpenCL():
            cv2.ocl.setUseOpenCL(True)
            _gpu_info["opencl_available"] = True
            _gpu_info["opencv_opencl"] = cv2.ocl.useOpenCL()
    except Exception:
        pass
    
    # -- Detectar OpenCV CUDA --
    try:
        if hasattr(cv2, 'cuda') and cv2.cuda.getCudaEnabledDeviceCount() > 0:
            _gpu_info["opencv_cuda"] = True
    except Exception:
        pass
    
    _gpu_info["detected"] = True
    
    # Log de deteccion
    if _gpu_info["cuda_available"]:
        print(f"[GPU] NVIDIA GPU detectada: {_gpu_info['gpu_name']}")
    if _gpu_info["opencl_available"]:
        print(f"[GPU] OpenCL disponible")
    if _gpu_info["opencv_cuda"]:
        print(f"[GPU] OpenCV CUDA habilitado")
    if not any([_gpu_info["cuda_available"], _gpu_info["opencl_available"]]):
        print("[GPU] No se detecto GPU. Usando CPU.")
    
    return _gpu_info


def get_gpu_info() -> Dict[str, Any]:
    """Retorna la informacion de GPU detectada."""
    if not _gpu_info["detected"]:
        detect_gpu()
    return _gpu_info.copy()


def is_gpu_available() -> bool:
    """Verifica si hay alguna GPU disponible para renderizado."""
    info = get_gpu_info()
    return info["cuda_available"] or info["opencl_available"]


class GPUAccelerator:
    """
    Acelerador de procesamiento de imagen por GPU.
    
    Proporciona operaciones de imagen aceleradas con fallback automatico a CPU.
    Usa OpenCV UMat (OpenCL) para aceleracion transparente o CUDA directo.
    """

    def __init__(self):
        self._info = detect_gpu()
        self._use_opencl = self._info["opencv_opencl"]
        self._use_cuda = self._info["opencv_cuda"]
        self._enabled = self._use_opencl or self._use_cuda

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def to_gpu(self, frame: np.ndarray):
        """
        Transfiere un frame a la GPU si esta disponible.
        
        Returns:
            UMat (OpenCL) o GpuMat (CUDA) del frame
        """
        if self._use_cuda:
            try:
                gpu_frame = cv2.cuda_GpuMat()
                gpu_frame.upload(frame)
                return gpu_frame
            except Exception:
                pass
                
        if self._use_opencl:
            try:
                return cv2.UMat(frame)
            except Exception:
                pass
        
        return frame

    def to_cpu(self, gpu_frame) -> np.ndarray:
        """Transfiere un frame de vuelta a CPU."""
        if isinstance(gpu_frame, cv2.UMat):
            return gpu_frame.get()
        if hasattr(cv2, 'cuda') and isinstance(gpu_frame, cv2.cuda.GpuMat):
            return gpu_frame.download()
        return gpu_frame

    def resize(self, frame: np.ndarray, width: int, height: int,
               interpolation: int = cv2.INTER_LINEAR) -> np.ndarray:
        """Redimensiona un frame (acelerado por GPU si esta disponible)."""
        if self._use_opencl:
            try:
                umat = cv2.UMat(frame)
                result = cv2.resize(umat, (width, height), interpolation=interpolation)
                return result.get()
            except Exception:
                pass
        
        return cv2.resize(frame, (width, height), interpolation=interpolation)

    def blur(self, frame: np.ndarray, kernel_size: int) -> np.ndarray:
        """Aplica desenfoque gaussiano acelerado."""
        ksize = max(3, kernel_size) | 1  # Asegurar impar
        
        if self._use_opencl:
            try:
                umat = cv2.UMat(frame)
                result = cv2.GaussianBlur(umat, (ksize, ksize), 0)
                return result.get()
            except Exception:
                pass
        
        return cv2.GaussianBlur(frame, (ksize, ksize), 0)

    def color_convert(self, frame: np.ndarray, code: int) -> np.ndarray:
        """Conversion de espacio de color acelerada."""
        if self._use_opencl:
            try:
                umat = cv2.UMat(frame)
                result = cv2.cvtColor(umat, code)
                return result.get()
            except Exception:
                pass
        
        return cv2.cvtColor(frame, code)

    def blend(self, frame_a: np.ndarray, frame_b: np.ndarray,
              alpha: float) -> np.ndarray:
        """Mezcla dos frames con alpha acelerado."""
        if self._use_opencl:
            try:
                umat_a = cv2.UMat(frame_a)
                umat_b = cv2.UMat(frame_b)
                result = cv2.addWeighted(umat_a, 1.0 - alpha, umat_b, alpha, 0)
                return result.get()
            except Exception:
                pass
        
        return cv2.addWeighted(frame_a, 1.0 - alpha, frame_b, alpha, 0)

    def warp_affine(self, frame: np.ndarray, matrix: np.ndarray,
                    size: Tuple[int, int]) -> np.ndarray:
        """Transformacion afin acelerada."""
        if self._use_opencl:
            try:
                umat = cv2.UMat(frame)
                result = cv2.warpAffine(umat, matrix, size)
                return result.get()
            except Exception:
                pass
        
        return cv2.warpAffine(frame, matrix, size)

    def apply_lut(self, frame: np.ndarray, lut: np.ndarray) -> np.ndarray:
        """Aplica una tabla de lookup (LUT) para correccion de color."""
        if self._use_opencl:
            try:
                umat = cv2.UMat(frame)
                result = cv2.LUT(umat, lut)
                return result.get()
            except Exception:
                pass
        
        return cv2.LUT(frame, lut)

    def get_status(self) -> str:
        """Retorna un string descriptivo del estado de GPU."""
        if self._use_cuda:
            return f"CUDA activo ({self._info['gpu_name']})"
        elif self._use_opencl:
            return "OpenCL activo"
        else:
            return "CPU (sin aceleracion GPU)"


# -- Instancia global del acelerador --
_accelerator: Optional[GPUAccelerator] = None


def get_accelerator() -> GPUAccelerator:
    """Obtiene la instancia global del acelerador GPU."""
    global _accelerator
    if _accelerator is None:
        _accelerator = GPUAccelerator()
    return _accelerator


def get_ffmpeg_gpu_args(codec: str = "") -> List[str]:
    """
    Genera los argumentos de FFmpeg para codificacion acelerada por GPU.
    
    Args:
        codec: Codec GPU preferido (ej: h264_nvenc)
        
    Returns:
        Lista de argumentos para FFmpeg
    """
    info = get_gpu_info()
    
    if codec:
        return ["-c:v", codec, "-pix_fmt", "yuv420p"]
    
    if info["cuda_available"]:
        return ["-c:v", "h264_nvenc", "-pix_fmt", "yuv420p", "-preset", "p4"]
    
    # Fallback a CPU
    return ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast"]
