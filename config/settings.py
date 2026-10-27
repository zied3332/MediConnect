
from pathlib import Path
import os
import sys

from dotenv import load_dotenv

# ==========================================================
# BASE DIRECTORY
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Load local secrets and settings from .env (never committed).
load_dotenv(BASE_DIR / ".env")

# Patient-brief generation: server-side secrets, never exposed in templates.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


# ==========================================================
# SECURITY & DEVELOPMENT
# ==========================================================

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    os.environ.get(
        "DJANGO_SECRET_KEY",
        "django-insecure-mediconnect-local-development-only",
    ),
)

DEBUG = env_bool("DEBUG", True)

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS = [RENDER_EXTERNAL_HOSTNAME, "localhost", "127.0.0.1"]
    CSRF_TRUSTED_ORIGINS = [f"https://{RENDER_EXTERNAL_HOSTNAME}"]
    # Render ends HTTPS before Django. Without this line, Django thinks the
    # site is HTTP, and Google login builds a wrong redirect address.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
# ==========================================================
# APPLICATIONS
# ==========================================================

INSTALLED_APPS = [
    # Django built-in applications
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # Third-party applications
    "rest_framework",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",

    # MediConnect applications
    "core.apps.CoreConfig",
    "specialty.apps.SpecialtyConfig",
    "availability.apps.AvailabilityConfig",
    "accounts.apps.AccountsConfig",
    "dashboard.apps.DashboardConfig",
    "notifications.apps.NotificationsConfig",
    "appointments.apps.AppointmentsConfig",
    "consultations",
    "medical_records",
]

SITE_ID = 1


# ==========================================================
# MIDDLEWARE
# ==========================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ==========================================================
# URL CONFIGURATION
# ==========================================================

ROOT_URLCONF = "config.urls"


# ==========================================================
# TEMPLATES
# ==========================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "core.preferences.preferences_context",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "notifications.context_processors.unread_notifications",
            ],
        },
    },
]


# ==========================================================
# WSGI APPLICATION
# ==========================================================

WSGI_APPLICATION = "config.wsgi.application"


# ==========================================================
# DATABASE — PostgreSQL
# ==========================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "mediconnect"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}


# ==========================================================
# CUSTOM USER MODEL
# ==========================================================

AUTH_USER_MODEL = "accounts.User"


# ==========================================================
# AUTHENTICATION URLS
# ==========================================================

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "core:home"


# ==========================================================
# PASSWORD VALIDATION
# ==========================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ==========================================================
# INTERNATIONALIZATION
# ==========================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
LANGUAGES = [("en", "English"), ("fr", "Français"), ("ar", "العربية")]
LOCALE_PATHS = [BASE_DIR / "locale"]
LANGUAGE_COOKIE_NAME = "django_language"
USE_TZ = True


# ==========================================================
# STATIC FILES
# ==========================================================

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

if not DEBUG:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }


# ==========================================================
# MEDIA FILES — uploaded documents
# ==========================================================

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# ==========================================================
# EMAIL — SendGrid via SMTP
# Set SENDGRID_API_KEY in your environment (or .env file).
# Set DEFAULT_FROM_EMAIL to your verified sender address.
# ==========================================================
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")

if SENDGRID_API_KEY:
    EMAIL_BACKEND = "anymail.backends.sendgrid.EmailBackend"
    ANYMAIL = {"SENDGRID_API_KEY": SENDGRID_API_KEY}
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL",
    "MediConnect <noreply@mediconnect.com>",
)


# ==========================================================
# EMAIL CONFIRMATION TOKEN EXPIRY
# 3 days (in seconds) — reuses Django's password reset timeout
# ==========================================================

PASSWORD_RESET_TIMEOUT = 60 * 60 * 24 * 3  # 3 days


# ==========================================================
# CELERY — background tasks (no-show risk, reminders)
# On Windows without Redis set CELERY_TASK_ALWAYS_EAGER=True in .env:
# tasks then run directly inside the web process.
# ==========================================================

from celery.schedules import crontab  # noqa: E402

RUNNING_TESTS = len(sys.argv) > 1 and sys.argv[1] == "test"

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", False) or RUNNING_TESTS
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_IGNORE_RESULT = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
# Fail fast when Redis is down instead of blocking the booking request.
CELERY_BROKER_CONNECTION_TIMEOUT = 2
CELERY_TASK_PUBLISH_RETRY_POLICY = {
    "max_retries": 1,
    "interval_start": 0,
    "interval_step": 0.5,
    "interval_max": 0.5,
}
CELERY_BEAT_SCHEDULE = {
    "send-appointment-reminders": {
        "task": "appointments.tasks.send_reminders",
        "schedule": crontab(minute=0),  # every hour
    },
}


# ==========================================================
# AI — no-show risk model (python manage.py train_noshow_model)
# ==========================================================

NOSHOW_DATASET_PATH = BASE_DIR / "appointments" / "ml" / "data" / "noshow.csv"
NOSHOW_MODEL_PATH = BASE_DIR / "appointments" / "ml" / "model.joblib"
NOSHOW_METRICS_PATH = BASE_DIR / "appointments" / "ml" / "metrics.json"


# ==========================================================
# DEFAULT PRIMARY KEY
# ==========================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ==========================================================
# AUTHENTICATION BACKENDS
# ==========================================================

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]


# ==========================================================
# ALLAUTH — Google OAuth
# ==========================================================

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id":     os.environ.get("GOOGLE_CLIENT_ID", ""),
            "secret":        os.environ.get("GOOGLE_CLIENT_SECRET", ""),
            "key":           "",
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "FETCH_USERINFO": True,
    }
}

# After Google login, create/update our custom User automatically.
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_LOGIN_ON_GET = True        # skip the allauth "confirm" interstitial
ACCOUNT_EMAIL_VERIFICATION = "none"     # we handle email verification ourselves
ACCOUNT_USER_MODEL_USERNAME_FIELD = "username"
ACCOUNT_EMAIL_FIELD = "email"
SOCIALACCOUNT_ADAPTER = "accounts.adapter.MediConnectSocialAccountAdapter"

# Link Google accounts to existing accounts by matching email address
# If you create an account with user@gmail.com, then login with Google using
# the same email, it will log you into your existing account instead of creating
# a duplicate.
ACCOUNT_UNIQUE_EMAIL = True              # enforce unique emails
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True  # match social login by email
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True  # auto-connect if email matches

# Where allauth redirects after a successful social login.
# Our adapter overrides this per-user, but this is the fallback.
LOGIN_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_REDIRECT_URL = "core:home"
