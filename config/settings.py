"""
Django settings for MediConnect.

Project: MediConnect
Description: AI-Assisted Healthcare & Telemedicine Platform
"""

from pathlib import Path
import os

from dotenv import load_dotenv

# ==========================================================
# BASE DIRECTORY
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Load local secrets and settings from .env (never committed).
load_dotenv(BASE_DIR / ".env")


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
    "accounts.apps.AccountsConfig",
    "dashboard.apps.DashboardConfig",
    "notifications.apps.NotificationsConfig",
]

SITE_ID = 1


# ==========================================================
# MIDDLEWARE
# ==========================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
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
USE_TZ = True


# ==========================================================
# STATIC FILES
# ==========================================================

STATIC_URL = "static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]


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
    EMAIL_BACKEND    = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST       = "smtp.sendgrid.net"
    EMAIL_PORT       = 587
    EMAIL_USE_TLS    = True
    EMAIL_HOST_USER  = "apikey"          # literal string — SendGrid requires this
    EMAIL_HOST_PASSWORD = SENDGRID_API_KEY
else:
    # No API key set → fall back to console so dev still works.
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
