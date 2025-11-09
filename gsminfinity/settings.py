"""
gsminfinity/settings.py
=======================
GSMInfinity Enterprise Django Configuration
-------------------------------------------
✅ Production-ready for Django 5.x + django-allauth 0.65.13

Features:
- Strict environment isolation (.env driven)
- Flexible caching (Redis or LocMem)
- Hardened security defaults
- allauth modern configuration
- Multi-site, consent, and device enforcement ready
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ============================================================
#  CORE PATHS & ENVIRONMENT
# ============================================================
load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret")
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"
ENV = os.getenv("ENV", "development")

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

SITE_ID = int(os.getenv("SITE_ID", "1"))


# ============================================================
#  APPLICATION DEFINITION
# ============================================================
INSTALLED_APPS = [
    # Core Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # Third-party
    "import_export",
    "solo",
    "django_countries",
    "crispy_forms",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.facebook",

    # Project apps
    "apps.core",
    "apps.users",
    "apps.site_settings",
    "apps.consent",
]


# ============================================================
#  MIDDLEWARE
# ============================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "apps.consent.middleware.ConsentMiddleware",  # ✅ custom GDPR middleware
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
#  URLS / WSGI / ASGI
# ============================================================
ROOT_URLCONF = "gsminfinity.urls"
WSGI_APPLICATION = "gsminfinity.wsgi.application"


# ============================================================
#  TEMPLATES
# ============================================================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.site_settings.context_processors.site_settings",
            ],
        },
    },
]


# ============================================================
#  DATABASES
# ============================================================
DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.getenv("DB_NAME", BASE_DIR / "db.sqlite3"),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", ""),
        "PORT": os.getenv("DB_PORT", ""),
        "ATOMIC_REQUESTS": True,
    }
}


# ============================================================
#  AUTHENTICATION / USERS
# ============================================================
AUTH_USER_MODEL = "users.CustomUser"

AUTHENTICATION_BACKENDS = (
    "apps.users.auth_backends.MultiFieldAuthBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
    "django.contrib.auth.backends.ModelBackend",
)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ============================================================
#  INTERNATIONALIZATION
# ============================================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Riyadh"
USE_I18N = True
USE_TZ = True


# ============================================================
#  STATIC & MEDIA
# ============================================================
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ============================================================
#  AUTH FLOW (LOGIN / LOGOUT)
# ============================================================
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "/users/dashboard/"
LOGOUT_REDIRECT_URL = "/"


# ============================================================
#  CACHING (REDIS or LOCMEM)
# ============================================================
USE_REDIS = os.getenv("USE_REDIS_CACHE", "False").lower() == "true"
CACHES = {
    "default": {
        "BACKEND": (
            "django_redis.cache.RedisCache"
            if USE_REDIS
            else "django.core.cache.backends.locmem.LocMemCache"
        ),
        "LOCATION": (
            os.getenv("REDIS_URL", "redis://127.0.0.1:6379/1") if USE_REDIS else ""
        ),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"} if USE_REDIS else {},
        "TIMEOUT": None,
    }
}

CONSENT_POLICY_CACHE_TTL = int(os.getenv("CONSENT_POLICY_CACHE_TTL", "300"))
REDIS_SOCKET_TIMEOUT = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))


# ============================================================
#  LOGGING
# ============================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "apps.users": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "apps.consent": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "apps.site_settings": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "apps.core": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}


# ============================================================
#  DJANGO-ALLAUTH CONFIGURATION
# ============================================================
ACCOUNT_ADAPTER = "apps.users.adapters.CustomAccountAdapter"
SOCIALACCOUNT_ADAPTER = "apps.users.adapters.CustomSocialAccountAdapter"

ACCOUNT_FORMS = {"signup": "apps.users.forms.CustomSignupForm"}

ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = os.getenv("ACCOUNT_EMAIL_VERIFICATION", "optional")
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = int(
    os.getenv("ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS", "3")
)
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_PASSWORD_MIN_LENGTH = int(os.getenv("ACCOUNT_PASSWORD_MIN_LENGTH", "8"))
ACCOUNT_PRESERVE_USERNAME_CASING = False
ACCOUNT_USERNAME_BLACKLIST = ["admin", "root"]
ACCOUNT_RATE_LIMITS = {
    "login_failed": os.getenv("ACCOUNT_RATE_LOGIN_FAILED", "5/300s"),
}
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https" if not DEBUG else "http"

SOCIALACCOUNT_PROVIDERS = {
    "google": {"SCOPE": ["profile", "email"]},
    "facebook": {"METHOD": "oauth2", "SCOPE": ["email"]},
}


# ============================================================
#  FORMS / UI
# ============================================================
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"


# ============================================================
#  SECURITY HEADERS
# ============================================================
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False").lower() == "true"
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true"
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "False").lower() == "true"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]


# ============================================================
#  EMAIL
# ============================================================
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@gsm-infinity.local")


# ============================================================
#  CELERY
# ============================================================
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
