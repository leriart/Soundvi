#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de logging estructurado para Soundvi.
Reemplaza prints() por logging profesional.
"""

import logging
import sys
from typing import Optional
from datetime import datetime


def setup_logging(level: int = logging.INFO, log_file: Optional[str] = None) -> logging.Logger:
    """
    Configura el sistema de logging.
    
    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
        log_file: Archivo para logs (opcional)
        
    Returns:
        Logger configurado
    """
    # Crear formateador
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configurar handler de consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Configurar handlers
    handlers = [console_handler]
    
    # Agregar handler de archivo si se especifica
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Configurar logger raíz
    logging.basicConfig(
        level=level,
        handlers=handlers
    )
    
    # Logger para Soundvi
    logger = logging.getLogger('soundvi')
    
    # Mensaje de inicio
    logger.info("=" * 60)
    logger.info("Soundvi Logger inicializado")
    logger.info(f"Nivel: {logging.getLevelName(level)}")
    if log_file:
        logger.info(f"Log file: {log_file}")
    logger.info("=" * 60)
    
    return logger


# Logger global
_logger = None


def get_logger(name: str = 'soundvi') -> logging.Logger:
    """
    Obtiene un logger por nombre.
    
    Args:
        name: Nombre del logger (ej: 'soundvi.timeline')
        
    Returns:
        Logger configurado
    """
    global _logger
    
    # Configurar logger global si no está configurado
    if _logger is None:
        _logger = setup_logging()
    
    return logging.getLogger(name)


# Funciones helper para logging común
def log_error(context: str, error: Exception, details: Optional[str] = None):
    """Log de error con contexto."""
    logger = get_logger('soundvi.error')
    msg = f"{context}: {error}"
    if details:
        msg += f" | Details: {details}"
    logger.error(msg, exc_info=True)


def log_performance(operation: str, duration_ms: float, details: Optional[str] = None):
    """Log de métricas de rendimiento."""
    logger = get_logger('soundvi.performance')
    msg = f"{operation}: {duration_ms:.1f}ms"
    if details:
        msg += f" | {details}"
    logger.info(msg)


def log_user_action(action: str, details: Optional[dict] = None):
    """Log de acciones del usuario."""
    logger = get_logger('soundvi.user')
    msg = f"User action: {action}"
    if details:
        details_str = ', '.join(f"{k}={v}" for k, v in details.items())
        msg += f" | {details_str}"
    logger.info(msg)


# Decorador para logging de funciones
def log_function_call(func):
    """Decorador para loggear llamadas a funciones."""
    def wrapper(*args, **kwargs):
        logger = get_logger(f'soundvi.{func.__module__}.{func.__name__}')
        
        # Log de entrada
        arg_str = ', '.join([str(a) for a in args[:3]])
        if len(args) > 3:
            arg_str += f"... (+{len(args)-3} más)"
        
        logger.debug(f"Calling {func.__name__}({arg_str})")
        
        try:
            # Ejecutar función
            start_time = datetime.now()
            result = func(*args, **kwargs)
            end_time = datetime.now()
            
            # Log de éxito
            duration_ms = (end_time - start_time).total_seconds() * 1000
            logger.debug(f"{func.__name__} completed in {duration_ms:.1f}ms")
            
            return result
            
        except Exception as e:
            # Log de error
            logger.error(f"{func.__name__} failed: {e}", exc_info=True)
            raise
    
    return wrapper


# Inicializar logging automáticamente al importar
get_logger()