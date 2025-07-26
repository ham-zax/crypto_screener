from .celery_config import celery_app
from . import scheduled_tasks

__all__ = ('celery_app', 'scheduled_tasks')