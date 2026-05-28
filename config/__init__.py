"""
SafraLog — config/__init__.py
Carrega Celery automaticamente quando Django inicializa.
"""
from .celery import app as celery_app

__all__ = ["celery_app"]
