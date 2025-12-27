# src/handlers/__init__.py
from .events import router as events_router
from .main import router as main_router
from .schedule import router as schedule_router
from .tasks import router as tasks_router

__all__ = ['main_router', 'schedule_router', 'tasks_router', 'events_router']
