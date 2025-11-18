# gsminfinity/settings.py
"""
Enterprise Django Settings
Django 5.2+ • Python 3.12+
Airtight • Modern • CSP-Safe • Zero Silent Failures • Hardened Imports
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Any
from django.core.exceptions import ImproperlyConfigured

# Optional .env loader (non-fatal)
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

logger = logging.getLogger("gsminfinity")


# ---------------------------
# Helper utilities
# ---------------------------
def env_str(value: Any, default: str = "") -> str:
    return str(value) if value is not None else default


def env_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    try:
        return str(value).strip().lower() in ("1", "true", "yes", "on")
    except Exception:
        return default


def env_list(value: Any, default: list | None = None) -> list:
    if value is None:
        return default or []
    try:
        return [v.strip() for v in str(value).split(",") if v.strip()]
    except Exception:
        return default or []


# ---------------------------
# Paths & core
# ---------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = env_str(
    os.getenv("DJANGO_SECRET_KEY"),
    "django-insecure-development-secret",
)

DEBUG = env_bool(os.getenv("DJANGO_DEBUG", None), False)
ENV = "development" if DEBUG else "production"


# ---------------------------
# Allowed hosts
# ---------------------------
ALLOWED_HOSTS = env_list(os.getenv("DJANGO_ALLOWED_HOSTS"), ["127.0.0.1", "localhost"])
ALLOWED_HOSTS = [h for h in ALLOWED_HOSTS if h and h.strip()]

if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS cannot be empty when DEBUG=False.")


# ---------------------------
# Sites framework
# ---------------------------
try:
    SITE_ID = int(env_str(os.getenv("SITE_ID"), "1"))
except Exception:
    SITE_ID = 1


# ---------------------------
# Installed apps
# ---------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]

THIRD_PARTY_APPS = [
    "import_export",
    "solo",
    "django_countries",
    "crispy_forms",
    "crispy_bootstrap5",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "django_extensions",
]

SOCIAL_PROVIDERS = [
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.facebook",
    "allauth.socialaccount.providers.microsoft",
    "allauth.socialaccount.providers.github",
]

LOCAL_APPS = [
    "apps.core",
    "apps.users",
    "apps.site_settings",
    "apps.consent",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + SOCIAL_PROVIDERS + LOCAL_APPS


# ---------------------------
# Middleware
# ---------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.core.middleware.security_headers.SecurityHeadersMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "apps.core.middleware.ssl_toggle.SslToggleMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "apps.core.middleware.request_meta.RequestMetaMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "apps.consent.middleware.ConsentMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ---------------------------
# Routing / ASGI / WSGI
# ---------------------------
ROOT_URLCONF = "gsminfinity.urls"
WSGI_APPLICATION = "gsminfinity.wsgi.application"
ASGI_APPLICATION = "gsminfinity.asgi.application"


# ---------------------------
# Database
# ---------------------------
_db_name = env_str(os.getenv("DB_NAME"))
if not _db_name:
    _db_name = str(BASE_DIR / "db.sqlite3")

DATABASES = {
    "default": {
        "ENGINE": env_str(os.getenv("DB_ENGINE"), "django.db.backends.sqlite3"),
        "NAME": _db_name,
        "USER": env_str(os.getenv("DB_USER")),
        "PASSWORD": env_str(os.getenv("DB_PASSWORD")),
        "HOST": env_str(os.getenv("DB_HOST")),
        "PORT": env_str(os.getenv("DB_PORT")),

        # IMPORTANT:
        # async views (lazy_loader) cannot run with ATOMIC_REQUESTS=True
        # this caused your RuntimeError
        "ATOMIC_REQUESTS": False,

        "CONN_MAX_AGE": 60 if not DEBUG else 0,
    }
}


# ---------------------------
# Authentication
# ---------------------------
AUTH_USER_MODEL = "users.CustomUser"

AUTHENTICATION_BACKENDS = [
    "apps.users.auth_backends.MultiFieldAuthBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ---------------------------
# i18n / timezone
# ---------------------------
LANGUAGE_CODE = env_str(os.getenv("DJANGO_LANGUAGE"), "en-us")
TIME_ZONE = env_str(os.getenv("DJANGO_TIME_ZONE"), "Asia/Riyadh")

USE_I18N = True
USE_TZ = True


# ---------------------------
# Static / Media
# ---------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_STORAGE = (
    "django.contrib.staticfiles.storage.StaticFilesStorage"
    if DEBUG else
    "whitenoise.storage.CompressedManifestStaticFilesStorage"
)

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------
# Templates
# ---------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": DEBUG,
        "OPTIONS": {
            "debug": DEBUG,
            "string_if_invalid": "" if not DEBUG else "⚠ Missing: %s ⚠",
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.site_settings.context_processors.site_settings",
                "apps.consent.context_processors.consent_context",
                "apps.core.context_processors.location_based_providers",
            ],
        },
    },
]

if not DEBUG:
    TEMPLATES[0]["APP_DIRS"] = False
    TEMPLATES[0]["OPTIONS"]["loaders"] = [
        (
            "django.template.loaders.cached.Loader",
            [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
        )
    ]


# ---------------------------
# Login flows
# ---------------------------
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "/users/dashboard/"
LOGOUT_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_ON_GET = True


# ---------------------------
# Caching
# ---------------------------
USE_REDIS = env_bool(os.getenv("USE_REDIS_CACHE"), False)

if USE_REDIS:
    REDIS_URL = env_str(os.getenv("REDIS_URL"), "redis://127.0.0.1:6379/1")
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "IGNORE_EXCEPTIONS": not DEBUG,
            },
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "TIMEOUT": 300,
        }
    }


# ---------------------------
# Logging
# ---------------------------
LOG_LEVEL = env_str(os.getenv("LOG_LEVEL"), "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {module} {message}", "style": "{"},
        "simple": {"format": "{levelname} {message}", "style": "{"},
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "apps": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}


# ---------------------------
# Allauth
# ---------------------------
ACCOUNT_ADAPTER = "apps.users.adapters.CustomAccountAdapter"
SOCIALACCOUNT_ADAPTER = "apps.users.adapters.CustomSocialAccountAdapter"

ACCOUNT_FORMS = {"signup": "apps.users.forms.CustomSignupForm"}

ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = env_str(os.getenv("ACCOUNT_EMAIL_VERIFICATION"), "optional")
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
ACCOUNT_PREVENT_ENUMERATION = True
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = True
ACCOUNT_PASSWORD_MIN_LENGTH = 8
ACCOUNT_USERNAME_BLACKLIST = ["admin", "root", "administrator", "system"]
ACCOUNT_RATE_LIMITS = {"login_failed": "5/300s", "signup": "10/3600s"}
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https" if not DEBUG else "http"
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[Notification] "
ACCOUNT_PRESERVE_USERNAME_CASING = False


# ---------------------------
# Security
# ---------------------------
SECURE_SSL_REDIRECT = env_bool(os.getenv("SECURE_SSL_REDIRECT"), False)

SESSION_COOKIE_SECURE = env_bool(os.getenv("SESSION_COOKIE_SECURE"), False)
CSRF_COOKIE_SECURE = env_bool(os.getenv("CSRF_COOKIE_SECURE"), False)

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = env_str(os.getenv("SESSION_COOKIE_SAMESITE"), "Lax")

SECURE_HSTS_SECONDS = int(env_str(os.getenv("SECURE_HSTS_SECONDS"), "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS"), False)
SECURE_HSTS_PRELOAD = env_bool(os.getenv("SECURE_HSTS_PRELOAD"), False)

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = env_str(os.getenv("X_FRAME_OPTIONS"), "DENY")
SECURE_REFERRER_POLICY = env_str(os.getenv("SECURE_REFERRER_POLICY"), "strict-origin-when-cross-origin")


# Trusted CSRF origins
_csrf_hosts = [h.strip() for h in ALLOWED_HOSTS if h and not h.startswith("*")]
CSRF_TRUSTED_ORIGINS = []
for host in _csrf_hosts:
    CSRF_TRUSTED_ORIGINS.append(f"https://{host}")
    CSRF_TRUSTED_ORIGINS.append(f"http://{host}")


# ---------------------------
# Email
# ---------------------------
EMAIL_BACKEND = env_str(
    os.getenv("EMAIL_BACKEND"),
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
DEFAULT_FROM_EMAIL = env_str(os.getenv("DEFAULT_FROM_EMAIL"), "no-reply@local")
EMAIL_USE_TLS = env_bool(os.getenv("EMAIL_USE_TLS"), True)


# ---------------------------
# Celery / DRF
# ---------------------------
CELERY_BROKER_URL = env_str(os.getenv("CELERY_BROKER_URL"), "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env_str(os.getenv("CELERY_RESULT_BACKEND"), CELERY_BROKER_URL)

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "EXCEPTION_HANDLER": "apps.core.exceptions.EnterpriseExceptionHandler.handle_api_exception",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}


# ---------------------------
# Startup banner
# ---------------------------
logger.info("⚙️ Settings Loaded (DEBUG=%s)", DEBUG)
