"""
SafraLog — config/celery.py
"""
import os

from celery import Celery
from celery.utils.log import get_task_logger

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("safralog")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

logger = get_task_logger(__name__)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    logger.info(f"Request: {self.request!r}")
