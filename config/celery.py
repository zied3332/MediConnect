"""
Celery application for MediConnect.

Worker (Windows):  celery -A config worker --pool=solo -l info
Beat:              celery -A config beat -l info
With CELERY_TASK_ALWAYS_EAGER=True in .env, tasks run directly without Redis.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
