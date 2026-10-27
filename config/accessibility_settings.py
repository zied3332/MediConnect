"""Local-only Stage 5 audit settings. Never connects to the configured database."""
from .settings import *  # noqa: F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / ".audit.sqlite3"}}
SECRET_KEY = "local-accessibility-audit-only"
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
ANTHROPIC_API_KEY = ""
SENDGRID_API_KEY = ""
SOCIALACCOUNT_PROVIDERS = {"google": {"APP": {"client_id": "audit", "secret": "audit", "key": ""}}}
CELERY_TASK_ALWAYS_EAGER = True
MEDIA_ROOT = BASE_DIR / ".audit-media"
