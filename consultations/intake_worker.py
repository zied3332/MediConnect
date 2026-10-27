"""Dedicated worker: never executes API calls inside a web request.

Redis is the default. A local filesystem broker supports the Windows demo
when Docker/WSL is unavailable; only UUID task arguments enter the queue.
"""
import os
from pathlib import Path

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
from django.conf import settings  # noqa: E402

broker = os.environ.get('ORIENTATION_BROKER_URL', settings.CELERY_BROKER_URL)
app = Celery('orientation', broker=broker, include=['consultations.intake_tasks'], set_as_current=False)
app.conf.update(broker_read_url=broker, broker_write_url=broker,
    task_always_eager=False, task_ignore_result=True,
    task_serializer='json', accept_content=['json'], task_default_queue='orientation',
    task_publish_retry=False, broker_connection_timeout=2,
    broker_connection_retry_on_startup=True, worker_hijack_root_logger=False,
    worker_redirect_stdouts=False, worker_send_task_events=False, task_send_sent_event=False)
if broker == 'filesystem://':
    root = Path(settings.BASE_DIR) / '.orientation-queue'
    for directory in ('messages', 'control'):
        (root / directory).mkdir(parents=True, exist_ok=True)
    app.conf.broker_transport_options = {'data_folder_in': str(root/'messages'),
        'data_folder_out': str(root/'messages'), 'control_folder': str(root/'control'),
        'store_processed': False, 'polling_interval': 0.5}
