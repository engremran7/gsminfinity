
# app/settings.py
"""
Core Django Settings
Django 5.2+ • Python 3.12+
Airtight • Modern • CSP-Safe • Zero Silent Failures • Hardened Imports
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

from django.core.exceptions import ImproperlyConfigured

# Optional .env loader (non-fatal)
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass

logger = logging.getLogger("app")


# ---------------------------
# Helper utilities
# ---------------------------
def _configure_io_encoding() -> None:
    """Ensure stdout/stderr can emit UTF-8 (avoid Windows console encode errors)."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


_configure_io_encoding()


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

_DEFAULT_DEV_SECRET = "django-insecure-development-secret"

SECRET_KEY = env_str(os.getenv("DJANGO_SECRET_KEY"), _DEFAULT_DEV_SECRET)

# MFA encryption key - separate from SECRET_KEY for safe key rotation
# If not set, falls back to SECRET_KEY (with warning in production)
MFA_ENCRYPTION_KEY = env_str(os.getenv("MFA_ENCRYPTION_KEY"), "")

_settings_module = os.getenv("DJANGO_SETTINGS_MODULE", "")
_default_debug = _settings_module.endswith("settings_dev")
DEBUG = env_bool(os.getenv("DJANGO_DEBUG", None), _default_debug)
ENV = "development" if DEBUG else "production"

# Proxy awareness (used by IP resolution helpers)
TRUSTED_PROXY_COUNT = int(os.getenv("TRUSTED_PROXY_COUNT", "0"))
# Admin suite: enabled by default; override with ADMIN_SUITE_ENABLED=false to disable explicitly
ADMIN_SUITE_ENABLED = env_bool(os.getenv("ADMIN_SUITE_ENABLED"), True)
IS_PRODUCTION = not DEBUG

if IS_PRODUCTION and (not SECRET_KEY or SECRET_KEY == _DEFAULT_DEV_SECRET):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be set in the environment for production; refusing to start with the development secret."
    )


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
    "django.contrib.humanize",
    "django.contrib.syndication",
    "django.contrib.sitemaps",
]

THIRD_PARTY_APPS = [
    "import_export",
    "solo",
    "django_countries",
    "django_summernote",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
]

SOCIAL_PROVIDERS = [
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.facebook",
    "allauth.socialaccount.providers.microsoft",
    "allauth.socialaccount.providers.github",
]

LOCAL_APPS = [
    "apps.core",
    "apps.admin_suite",
    "apps.users",
    "apps.devices",
    "apps.crawler_guard",
    "apps.ai_behavior",
    "apps.ai",
    "apps.app_registry",
    "apps.i18n",
    "apps.site_settings",
    "apps.consent",
    "apps.blog",
    "apps.tags",
    "apps.comments",
    "apps.seo",
    "apps.ads",
    "apps.analytics",  # Analytics app for tracking and metrics
    "apps.distribution",
    "apps.security_suite",
    "apps.security_events",
    "apps.pages",
    "apps.storage",
    "apps.firmwares",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + SOCIAL_PROVIDERS + LOCAL_APPS


# ---------------------------
# Middleware
# ---------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "app.middleware.csp_nonce.CSPNonceMiddleware",  # Add CSP nonce generation EARLY
    "apps.core.middleware.security_headers.SecurityHeadersMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "apps.core.middleware.ssl_toggle.SslToggleMiddleware",
    "apps.users.middleware.reset_throttle.PasswordResetThrottleMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "apps.devices.middleware.DevicePayloadMiddleware",
    "apps.core.middleware.correlation.CorrelationIdMiddleware",
    "apps.core.middleware.request_meta.RequestMetaMiddleware",
    "apps.core.middleware.rate_limit_bridge.RateLimitBridgeMiddleware",
    "apps.crawler_guard.middleware.CrawlerGuardMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "apps.devices.middleware.DeviceEnforcementMiddleware",
    "apps.consent.middleware.ConsentMiddleware",
    "apps.users.middleware.profile_completion.EnforceProfileCompletionMiddleware",
    "apps.users.middleware.mfa_enforce.EnforceMfaMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ---------------------------
# Routing / ASGI / WSGI
# ---------------------------
ROOT_URLCONF = "app.urls"
WSGI_APPLICATION = "app.wsgi.application"
ASGI_APPLICATION = "app.asgi.application"


# ---------------------------
# Database
# ---------------------------
_db_name = env_str(os.getenv("DB_NAME"), "appdb")
_db_engine = env_str(os.getenv("DB_ENGINE"), "django.db.backends.postgresql")
if _db_engine not in ("django.db.backends.postgresql",):
    raise ImproperlyConfigured("Only PostgreSQL is supported. SQLite has been removed.")
_db_user = env_str(os.getenv("DB_USER"), "")
_db_password = env_str(os.getenv("DB_PASSWORD"), "")
_db_host = env_str(os.getenv("DB_HOST"), "localhost")
_db_port = env_str(os.getenv("DB_PORT"), "5433")
if _db_engine == "django.db.backends.postgresql" and (not _db_user or not _db_password):
    raise ImproperlyConfigured("PostgreSQL credentials must be set via DB_USER and DB_PASSWORD.")

DATABASES = {
    "default": {
        "ENGINE": _db_engine,
        "NAME": _db_name,
        "USER": _db_user,
        "PASSWORD": _db_password,
        "HOST": _db_host,
        "PORT": _db_port,
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
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
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
    if DEBUG
    else "whitenoise.storage.CompressedManifestStaticFilesStorage"
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
                "django.template.context_processors.csrf",
                "apps.site_settings.context_processors.site_settings",
                "apps.consent.context_processors.consent_context",
                "apps.core.context_processors.location_based_providers",
                "apps.users.context_processors.auth_status",
                "apps.pages.context_processors.navigation_pages",
            ],
            "libraries": {
                "form_tags": "apps.core.templatetags.form_tags",
            },
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
ADMIN_LOGIN_URL = "admin_suite:admin_suite_login"
ADMIN_REDIRECT_URL = "admin_suite:admin_suite"
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "users:dashboard"
LOGOUT_REDIRECT_URL = "home"
ACCOUNT_LOGOUT_REDIRECT_URL = LOGOUT_REDIRECT_URL
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
LOG_DIR = BASE_DIR / "logs"
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _LOG_DIR_READY = True
except Exception:
    _LOG_DIR_READY = False

# Disable file logging on Windows in development to avoid file locking issues during server autoreload
_USE_FILE_LOGGING = _LOG_DIR_READY and (os.name != "nt" or not DEBUG)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{asctime} {levelname} {name} {message}", "style": "{"},
        "simple": {"format": "{levelname} {message}", "style": "{"},
    },
    "handlers": {
        # Console stays at INFO+ to keep runserver output readable.
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "INFO",
        },
        # File captures full DEBUG for troubleshooting with rotation (max 10MB per file, keep 5 backups).
        **(
            {
                "debug_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": LOG_DIR / "debug.log",
                    "formatter": "verbose",
                    "level": "DEBUG",
                    "encoding": "utf-8",
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5,  # Keep 5 old files (max 60MB total)
                }
            }
            if _USE_FILE_LOGGING
            else {}
        ),
    },
    "root": {"handlers": ["console"] + (["debug_file"] if _USE_FILE_LOGGING else []), "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console"] + (["debug_file"] if _USE_FILE_LOGGING else []), "level": LOG_LEVEL, "propagate": False},
        "apps": {"handlers": ["console"] + (["debug_file"] if _USE_FILE_LOGGING else []), "level": LOG_LEVEL, "propagate": False},
    },
}


# ---------------------------
# Allauth
# ---------------------------
ACCOUNT_ADAPTER = "apps.users.adapters.CustomAccountAdapter"
SOCIALACCOUNT_ADAPTER = "apps.users.adapters.CustomSocialAccountAdapter"

ACCOUNT_FORMS = {
    "signup": "apps.users.forms.CustomSignupForm",
    "change_password": "apps.users.forms.CustomChangePasswordForm",
}
ACCOUNT_OLD_PASSWORD_FIELD_ENABLED = True

ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = env_str(
    os.getenv("ACCOUNT_EMAIL_VERIFICATION"), "optional"
)
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
ACCOUNT_AUTHENTICATED_LOGIN_REDIRECTS = False


# ---------------------------
# Security
# ---------------------------
# We rely on SslToggleMiddleware + SiteSettings.force_https for dynamic control.
# Default secure in production, relaxed in dev unless overridden.
SECURE_SSL_REDIRECT = env_bool(os.getenv("SECURE_SSL_REDIRECT"), not DEBUG)

SESSION_COOKIE_SECURE = env_bool(os.getenv("SESSION_COOKIE_SECURE"), IS_PRODUCTION)
CSRF_COOKIE_SECURE = env_bool(os.getenv("CSRF_COOKIE_SECURE"), IS_PRODUCTION)
CSRF_COOKIE_DOMAIN = env_str(os.getenv("CSRF_COOKIE_DOMAIN"), None)

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = env_str(os.getenv("SESSION_COOKIE_SAMESITE"), "Lax")
CSRF_COOKIE_SAMESITE = env_str(os.getenv("CSRF_COOKIE_SAMESITE"), "Lax")
SESSION_COOKIE_AGE = int(env_str(os.getenv("SESSION_COOKIE_AGE"), "1209600"))  # 14 days default
SESSION_SAVE_EVERY_REQUEST = env_bool(os.getenv("SESSION_SAVE_EVERY_REQUEST"), False)

# Admin suite: optional shorter session age (falls back to default)
ADMIN_SESSION_AGE = int(env_str(os.getenv("ADMIN_SESSION_AGE"), "3600"))

# Password reset token lifetime (short-lived, single-use links)
PASSWORD_RESET_TIMEOUT = int(env_str(os.getenv("PASSWORD_RESET_TIMEOUT"), "900"))  # 15 minutes

# If behind a reverse proxy setting X-Forwarded-Proto, honor it for is_secure()
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https") if env_bool(os.getenv("USE_XFORWARDED_PROTO"), False) else None
)

SECURE_HSTS_SECONDS = int(
    env_str(os.getenv("SECURE_HSTS_SECONDS"), "31536000" if IS_PRODUCTION else "0")
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS"), IS_PRODUCTION
)
SECURE_HSTS_PRELOAD = env_bool(os.getenv("SECURE_HSTS_PRELOAD"), IS_PRODUCTION)

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True  # Prevents MIME type sniffing

# X-Frame-Options: Use DENY for maximum security
# Override to SAMEORIGIN only if Summernote iframe mode is needed
X_FRAME_OPTIONS = env_str(os.getenv("X_FRAME_OPTIONS"), "DENY")
SECURE_REFERRER_POLICY = env_str(
    os.getenv("SECURE_REFERRER_POLICY"), "strict-origin-when-cross-origin"
)

SECURITY_HSTS_VALUE = env_str(
    os.getenv("SECURITY_HSTS_VALUE"),
    "max-age=63072000; includeSubDomains; preload",
)
SECURITY_COEP_VALUE = env_str(os.getenv("SECURITY_COEP_VALUE"), "require-corp")
SECURITY_CORP_VALUE = env_str(os.getenv("SECURITY_CORP_VALUE"), "same-origin")


# Trusted CSRF origins
_csrf_hosts = [h.strip() for h in ALLOWED_HOSTS if h and not h.startswith("*")]
ALLOW_INSECURE_CSRF_ORIGINS = env_bool(os.getenv("ALLOW_INSECURE_CSRF_ORIGINS"), False)

CSRF_TRUSTED_ORIGINS: list[str] = []
for host in _csrf_hosts:
    CSRF_TRUSTED_ORIGINS.append(f"https://{host}")
    if ALLOW_INSECURE_CSRF_ORIGINS and host in {"127.0.0.1", "localhost", "0.0.0.0"}:
        CSRF_TRUSTED_ORIGINS.append(f"http://{host}")

# Ensure local dev hosts are trusted for CSRF in DEBUG even if env vars are absent.
if DEBUG:
    for host in ("127.0.0.1", "localhost"):
        if f"http://{host}" not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(f"http://{host}")
        if f"https://{host}" not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(f"https://{host}")


# ---------------------------
# Email
# ---------------------------
DEFAULT_EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_BACKEND = env_str(os.getenv("EMAIL_BACKEND"), "apps.core.email_backends.gmail.GmailBackend")
DEFAULT_FROM_EMAIL = env_str(os.getenv("DEFAULT_FROM_EMAIL"), "no-reply@local")
EMAIL_USE_TLS = env_bool(os.getenv("EMAIL_USE_TLS"), True)


# ---------------------------
# Celery / DRF
# ---------------------------
_celery_broker_url = env_str(os.getenv("CELERY_BROKER_URL"), "")
# Allow an explicit broker only; fall back to local Redis in DEBUG for dev convenience.
if not _celery_broker_url and DEBUG:
    _celery_broker_url = "redis://localhost:6379/0"
if not DEBUG and not _celery_broker_url:
    raise ImproperlyConfigured("CELERY_BROKER_URL must be set in production and should use TLS + auth.")

CELERY_BROKER_URL = _celery_broker_url
CELERY_RESULT_BACKEND = env_str(os.getenv("CELERY_RESULT_BACKEND"), "")
if not CELERY_RESULT_BACKEND:
    # Disable results unless explicitly configured (avoids leaking data to an unsecured backend).
    CELERY_RESULT_BACKEND = None
CELERY_TASK_ALWAYS_EAGER = env_bool(os.getenv("CELERY_TASK_ALWAYS_EAGER"), False)

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "distribution_pump_due": {
        "task": "distribution.pump_due_jobs",
        "schedule": 60.0,
    },
    "distribution_retry_failed": {
        "task": "distribution.retry_failed_jobs",
        "schedule": 300.0,
    },
}

# Distribution defaults
DISTRIBUTION_CHANNELS = [
    "twitter",
    "linkedin",
    "facebook",
    "instagram",
    "pinterest",
    "reddit",
    "telegram",
    "discord",
    "slack",
    "mailchimp",
    "sendgrid",
    "devto",
    "hashnode",
    "medium",
    "google_indexing",
    "bing_indexing",
    "rss",
    "atom",
    "json",
    "websub",
]

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        # Enable these only if the app is installed/configured:
        # "rest_framework.authentication.TokenAuthentication",
        # "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "EXCEPTION_HANDLER": "apps.core.exceptions.EnterpriseExceptionHandler.handle_api_exception",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}


# ---------------------------
# Security Headers & HTTPS Enforcement
# ---------------------------
# HSTS - HTTP Strict Transport Security (tell browsers to always use HTTPS)
if IS_PRODUCTION:
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
else:
    SECURE_HSTS_SECONDS = 0  # Disabled in development
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    SECURE_SSL_REDIRECT = False

# Prevent clickjacking (changed to SAMEORIGIN for Summernote iframe support)
X_FRAME_OPTIONS = "SAMEORIGIN"

# XSS Protection
SECURE_BROWSER_XSS_FILTER = True
X_CONTENT_TYPE_OPTIONS = "nosniff"

# Content Security Policy - Handled by SecurityHeadersMiddleware
# Nonces are generated per-request by apps.core.middleware.security_headers
# Only style-src-attr uses 'unsafe-inline' (jQuery limitation - no nonce support for style attributes)
# All other directives use nonces or 'self'
# SECURE_CONTENT_SECURITY_POLICY is NOT used (SecurityHeadersMiddleware handles CSP)

# Referrer policy
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Feature policy / Permissions policy
PERMISSIONS_POLICY = {
    "accelerometer": [],
    "ambient-light-sensor": [],
    "autoplay": [],
    "camera": [],
    "encrypted-media": [],
    "fullscreen": ["self"],
    "geolocation": [],
    "gyroscope": [],
    "magnetometer": [],
    "microphone": [],
    "midi": [],
    "payment": [],
    "picture-in-picture": [],
    "usb": [],
}


# ---------------------------
# Django Summernote Configuration
# ---------------------------
# X-Frame-Options: DENY for security, but SAMEORIGIN needed for Summernote
# In production, consider using CSP frame-ancestors instead
X_FRAME_OPTIONS = 'DENY' if not env_bool(os.getenv("SUMMERNOTE_ENABLED"), True) else 'SAMEORIGIN'

SUMMERNOTE_CONFIG = {
    # Using Summernote built-in theme
    'summernote': {
        # Toolbar customization - Full featured
        'width': '100%',
        'height': '480',
        'toolbar': [
            ['style', ['style']],
            ['font', ['bold', 'italic', 'underline', 'strikethrough', 'superscript', 'subscript', 'clear']],
            ['fontname', ['fontname']],
            ['fontsize', ['fontsize']],
            ['color', ['color']],
            ['para', ['ul', 'ol', 'paragraph']],
            ['height', ['height']],
            ['table', ['table']],
            ['insert', ['link', 'picture', 'video', 'hr']],
            ['view', ['fullscreen', 'codeview', 'help']],
        ],
        'popover': {
            'image': [
                ['image', ['resizeFull', 'resizeHalf', 'resizeQuarter', 'resizeNone']],
                ['float', ['floatLeft', 'floatRight', 'floatNone']],
                ['remove', ['removeMedia']],
            ],
            'link': [
                ['link', ['linkDialogShow', 'unlink']],
            ],
            'table': [
                ['add', ['addRowDown', 'addRowUp', 'addColLeft', 'addColRight']],
                ['delete', ['deleteRow', 'deleteCol', 'deleteTable']],
            ],
        },
        'codemirror': {
            'mode': 'htmlmixed',
            'lineNumbers': 'true',
            'theme': 'monokai',
        },
    },
    # Change editor size
    'width': '100%',
    'height': '480',
    
    # Set iframe mode for better isolation - DISABLED to fix CSP issues
    'iframe': False,
    
    # Disable file upload (or configure as needed)
    'disable_upload': False,
    
    # Set upload path (relative to MEDIA_ROOT)
    'upload_to': 'uploads/summernote/%Y-%m-%d/',
    
    # Storage class
    'attachment_storage_class': 'django.core.files.storage.FileSystemStorage',
    
    # Set attachment size limit (5MB)
    'attachment_filesize_limit': 5 * 1024 * 1024,
    
    # Allowed image file extensions - remove the model line
    # 'attachment_model': 'django_summernote.Attachment',
    
    # Require authentication for uploads
    'attachment_require_authentication': True,
    
    # Lazy loading
    'lazy': True,
    
    # Use native CSRF
    'disable_attachment': False,
    
    # Air mode - removes toolbar, shows inline
    'airMode': False,
    
    # Test mode
    'summernote_test_mode': False,
    
    # IMPORTANT: Don't load from CDN, use local files only
    'js': (),
    'css': (),
    'js_for_inplace': (),
    'css_for_inplace': (),
}


# ---------------------------
# Startup banner
# ---------------------------
logger.info("⚙️ Settings Loaded (DEBUG=%s)", DEBUG)


