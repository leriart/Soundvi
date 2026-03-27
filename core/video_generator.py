#!/usr/bin/env python3
"""
Pipeline de generación de video de alto nivel.
"""

from __future__ import annotations
import os
import subprocess as sp
import time
import numpy as np
import cv2

from utils.ffmpeg import get_ffmpeg_path

def generate_video(
    media_path: str,
    audio_path: str,
    output_path: str,
    width: int,
    height: int,
    fps: int,
    fade_duration: float,
    active_modules: list,
    progress_callback: callable = None,
    use_gpu: bool = False,
    gpu_codec: str = "h264_nvenc",
    _retry_cpu: bool = True
) -> bool:
    """
    Genera un video, con fallback a CPU si la GPU falla.
    """
    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path or not os.path.isfile(ffmpeg_path):
        print(f"[Error] FFmpeg inválido: {ffmpeg_path}")
        return False
        
    print(f"\n[Generador] Iniciando generacion en: {output_path}")
    print(f" - Media: {media_path}\n - Audio: {audio_path}\n - GPU: {use_gpu} ({gpu_codec})\n - Módulos: {len(active_modules)}")

    try:
        from moviepy.editor import AudioFileClip
        duration = AudioFileClip(audio_path).duration
    except:
        from pydub import AudioSegment
        duration = AudioSegment.from_file(audio_path).duration_seconds

    total_frames = int(duration * fps)
    
    cap = cv2.VideoCapture(media_path)
    es_gif = media_path.lower().endswith(".gif")
    frames_fondo = []
    if es_gif:
        while True:
            ok, frame = cap.read()
            if not ok: break
            frames_fondo.append(cv2.resize(frame, (width, height)))
    else:
        ok, frame = cap.read()
        fondo_estatico = cv2.resize(frame, (width, height)) if ok else np.zeros((height, width, 3), dtype=np.uint8)
    cap.release()

    vparams = ["-c:v", gpu_codec, "-pix_fmt", "yuv420p"] if use_gpu else ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast"]
    
    cmd = [
        ffmpeg_path, "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{width}x{height}", "-pix_fmt", "bgr24", "-r", str(fps),
        "-i", "-",
        "-i", audio_path
    ]
    
    filter_chain = []
    if fade_duration > 0:
        fade_out_start = max(0, duration - fade_duration)
        filter_chain.append(f"fade=t=in:st=0:d={fade_duration}")
        filter_chain.append(f"fade=t=out:st={fade_out_start}:d={fade_duration}")
    
    if filter_chain:
        cmd.extend(["-filter_complex", f"[0:v]{','.join(filter_chain)}[v]", "-map", "[v]", "-map", "1:a"])
    else:
        cmd.extend(["-map", "0:v", "-map", "1:a"])

    cmd.extend([*vparams, "-c:a", "aac", "-b:a", "192k", "-shortest", output_path])

    try:
        proc = sp.Popen(cmd, stdin=sp.PIPE, stderr=sp.PIPE)
    except Exception as e:
        print(f"[Error] Fallo al iniciar FFmpeg: {e}")
        return False

    # --- BUCLE DE RENDERIZADO ---
    start_time = time.time()
    pipe_roto = False
    
    for fi in range(total_frames):
        try:
            if es_gif:
                frame_base = frames_fondo[fi % len(frames_fondo)].copy()
            else:
                frame_base = fondo_estatico.copy()

            for modulo in active_modules:
                frame_base = modulo.render(frame_base, fi / fps, fps=fps)

            proc.stdin.write(frame_base.tobytes())
            
            if progress_callback and fi % (fps//2) == 0:
                progress_callback((fi / total_frames) * 100.0)
                
        except BrokenPipeError:
            pipe_roto = True
            break
        except Exception as e:
            print(f"Error en el bucle de renderizado: {e}")
            pipe_roto = True
            break
            
    # --- MANEJO DE CIERRE Y FALLBACK ---
    stderr = None
    if proc.stdin:
        proc.stdin.close()
    if pipe_roto:
        stderr = proc.stderr.read()
    proc.wait(timeout=60)

    if pipe_roto:
        err_msg = stderr.decode(errors='ignore') if stderr else "Error desconocido"
        print(f"[Error] Pipe roto en FFmpeg.")
        print(f"[FFmpeg Log] {err_msg}")

        if use_gpu and _retry_cpu and ("Cannot load libcuda.so.1" in err_msg or "Error while opening encoder" in err_msg):
            print("\n[Generador] Falló la GPU. Reintentando con CPU...")
            return generate_video(
                media_path, audio_path, output_path, width, height, fps,
                fade_duration, active_modules, progress_callback,
                use_gpu=False, _retry_cpu=False
            )
        return False
    else:
        if progress_callback: progress_callback(100.0)
        print(f"[Generador] Éxito. Tiempo: {time.time() - start_time:.2f}s")
        return proc.returncode == 0
