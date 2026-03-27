#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Comandos (Command Pattern) para Undo/Redo.

Cada accion del usuario se encapsula en un objeto Command que sabe
como ejecutarse y como deshacerse. El CommandManager mantiene las pilas
de undo y redo.
"""

from __future__ import annotations
import copy
from typing import Optional, Dict, Any, List, Callable
from abc import ABC, abstractmethod


class Command(ABC):
    """Clase base abstracta para todos los comandos."""

    def __init__(self, description: str = ""):
        self.description: str = description
        self._executed: bool = False

    @abstractmethod
    def execute(self):
        """Ejecuta el comando."""
        pass

    @abstractmethod
    def undo(self):
        """Deshace el comando."""
        pass

    def redo(self):
        """Re-ejecuta el comando. Por defecto llama a execute()."""
        self.execute()

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.description}')"


class CommandManager:
    """
    Gestor de comandos con pilas de undo/redo.
    
    Mantiene un historial limitado de comandos ejecutados
    y permite navegar hacia atras (undo) y adelante (redo).
    """

    def __init__(self, max_history: int = 100):
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []
        self._max_history: int = max_history
        self._on_change_callbacks: List[Callable] = []

    def execute(self, command: Command):
        """Ejecuta un comando y lo agrega al historial."""
        command.execute()
        command._executed = True
        self._undo_stack.append(command)
        self._redo_stack.clear()  # Nueva accion invalida el redo
        
        # Limitar historial
        if len(self._undo_stack) > self._max_history:
            self._undo_stack.pop(0)
            
        self._notify_change()

    def undo(self) -> Optional[str]:
        """
        Deshace el ultimo comando.
        
        Returns:
            Descripcion del comando deshecho, o None si no hay nada que deshacer
        """
        if not self._undo_stack:
            return None
            
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        self._notify_change()
        return command.description

    def redo(self) -> Optional[str]:
        """
        Rehace el ultimo comando deshecho.
        
        Returns:
            Descripcion del comando rehecho, o None si no hay nada que rehacer
        """
        if not self._redo_stack:
            return None
            
        command = self._redo_stack.pop()
        command.redo()
        self._undo_stack.append(command)
        self._notify_change()
        return command.description

    @property
    def can_undo(self) -> bool:
        """Indica si hay comandos para deshacer."""
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        """Indica si hay comandos para rehacer."""
        return len(self._redo_stack) > 0

    @property
    def undo_description(self) -> str:
        """Descripcion del proximo comando a deshacer."""
        if self._undo_stack:
            return self._undo_stack[-1].description
        return ""

    @property
    def redo_description(self) -> str:
        """Descripcion del proximo comando a rehacer."""
        if self._redo_stack:
            return self._redo_stack[-1].description
        return ""

    def get_history(self) -> List[str]:
        """Retorna la lista de descripciones del historial."""
        return [cmd.description for cmd in self._undo_stack]

    def clear(self):
        """Limpia todo el historial."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._notify_change()

    def on_change(self, callback: Callable):
        """Registra un callback que se ejecuta cuando cambia el historial."""
        self._on_change_callbacks.append(callback)

    def _notify_change(self):
        """Notifica a los observadores que el historial cambio."""
        for cb in self._on_change_callbacks:
            try:
                cb()
            except Exception:
                pass


# =============================================================================
# Comandos concretos de uso comun
# =============================================================================

class AddClipCommand(Command):
    """Comando para agregar un clip al timeline."""

    def __init__(self, timeline, clip, track_index: int):
        super().__init__(f"Agregar clip '{clip.name}'")
        self.timeline = timeline
        self.clip = clip
        self.track_index = track_index

    def execute(self):
        self.timeline.add_clip(self.clip, self.track_index)

    def undo(self):
        self.timeline.remove_clip(self.clip.clip_id)


class RemoveClipCommand(Command):
    """Comando para eliminar un clip del timeline."""

    def __init__(self, timeline, clip_id: str):
        super().__init__("Eliminar clip")
        self.timeline = timeline
        self.clip_id = clip_id
        self._removed_clip = None
        self._track_index = 0

    def execute(self):
        result = self.timeline.find_clip(self.clip_id)
        if result:
            self._removed_clip, track = result
            self._track_index = track.index
            self.description = f"Eliminar clip '{self._removed_clip.name}'"
        self.timeline.remove_clip(self.clip_id)

    def undo(self):
        if self._removed_clip:
            self.timeline.add_clip(self._removed_clip, self._track_index)


class MoveClipCommand(Command):
    """Comando para mover un clip en el timeline."""

    def __init__(self, timeline, clip_id: str, new_start: float, new_track: int = None):
        super().__init__("Mover clip")
        self.timeline = timeline
        self.clip_id = clip_id
        self.new_start = new_start
        self.new_track = new_track
        self._old_start: float = 0.0
        self._old_track: int = 0

    def execute(self):
        result = self.timeline.find_clip(self.clip_id)
        if result:
            clip, track = result
            self._old_start = clip.start_time
            self._old_track = track.index
            self.description = f"Mover clip '{clip.name}'"
        self.timeline.move_clip(self.clip_id, self.new_start, self.new_track)

    def undo(self):
        self.timeline.move_clip(self.clip_id, self._old_start, self._old_track)


class SplitClipCommand(Command):
    """Comando para dividir un clip."""

    def __init__(self, timeline, clip_id: str, split_time: float):
        super().__init__("Dividir clip")
        self.timeline = timeline
        self.clip_id = clip_id
        self.split_time = split_time
        self._new_clip_id: str = ""
        self._original_duration: float = 0.0
        self._original_trim_end: float = 0.0
        self._original_name: str = ""

    def execute(self):
        result = self.timeline.find_clip(self.clip_id)
        if result:
            clip, _ = result
            self._original_duration = clip.duration
            self._original_trim_end = clip.trim_end
            self._original_name = clip.name
            
        new_clip = self.timeline.split_clip(self.clip_id, self.split_time)
        if new_clip:
            self._new_clip_id = new_clip.clip_id
            self.description = f"Dividir clip '{self._original_name}'"

    def undo(self):
        # Eliminar el segundo clip
        if self._new_clip_id:
            self.timeline.remove_clip(self._new_clip_id)
        # Restaurar el clip original
        result = self.timeline.find_clip(self.clip_id)
        if result:
            clip, _ = result
            clip.duration = self._original_duration
            clip.trim_end = self._original_trim_end
            clip.name = self._original_name


class TrimClipCommand(Command):
    """Comando para recortar un clip."""

    def __init__(self, timeline, clip_id: str, new_trim_start: float = None, new_trim_end: float = None):
        super().__init__("Recortar clip")
        self.timeline = timeline
        self.clip_id = clip_id
        self.new_trim_start = new_trim_start
        self.new_trim_end = new_trim_end
        self._old_trim_start: float = 0.0
        self._old_trim_end: float = 0.0
        self._old_duration: float = 0.0
        self._old_start_time: float = 0.0

    def execute(self):
        result = self.timeline.find_clip(self.clip_id)
        if result:
            clip, _ = result
            self._old_trim_start = clip.trim_start
            self._old_trim_end = clip.trim_end
            self._old_duration = clip.duration
            self._old_start_time = clip.start_time
            self.description = f"Recortar clip '{clip.name}'"
            clip.trim(self.new_trim_start, self.new_trim_end)

    def undo(self):
        result = self.timeline.find_clip(self.clip_id)
        if result:
            clip, _ = result
            clip.trim_start = self._old_trim_start
            clip.trim_end = self._old_trim_end
            clip.duration = self._old_duration
            clip.start_time = self._old_start_time


class ChangePropertyCommand(Command):
    """Comando generico para cambiar una propiedad de un objeto."""

    def __init__(self, obj: Any, property_name: str, new_value: Any, description: str = ""):
        super().__init__(description or f"Cambiar {property_name}")
        self.obj = obj
        self.property_name = property_name
        self.new_value = new_value
        self._old_value = None

    def execute(self):
        self._old_value = getattr(self.obj, self.property_name, None)
        setattr(self.obj, self.property_name, self.new_value)

    def undo(self):
        if self._old_value is not None:
            setattr(self.obj, self.property_name, self._old_value)


class AddModuleCommand(Command):
    """Comando para agregar un modulo."""

    def __init__(self, module_manager, module_type: str, description: str = ""):
        super().__init__(description or f"Agregar modulo {module_type}")
        self.module_manager = module_manager
        self.module_type = module_type
        self._module = None

    def execute(self):
        self._module = self.module_manager.create_module_instance(self.module_type)
        if self._module:
            self.module_manager.add_module_instance(self._module)

    def undo(self):
        if self._module:
            self.module_manager.remove_module_instance(self._module)


class RemoveModuleCommand(Command):
    """Comando para eliminar un modulo."""

    def __init__(self, module_manager, module, description: str = ""):
        super().__init__(description or f"Eliminar modulo {module.nombre}")
        self.module_manager = module_manager
        self.module = module

    def execute(self):
        self.module_manager.remove_module_instance(self.module)

    def undo(self):
        self.module_manager.add_module_instance(self.module)


class CompositeCommand(Command):
    """Comando compuesto que ejecuta multiples comandos como una sola accion."""

    def __init__(self, commands: List[Command], description: str = ""):
        super().__init__(description or "Accion compuesta")
        self.commands = commands

    def execute(self):
        for cmd in self.commands:
            cmd.execute()

    def undo(self):
        for cmd in reversed(self.commands):
            cmd.undo()
