"""
Event Bus Package
=================

Internal event system for decoupled app communication.
"""

from .bus import EventBus, event_bus, EventTypes

__all__ = ['EventBus', 'event_bus', 'EventTypes']
