"""
Production Settings for GsmInfinity
Django 5.2+ Production Configuration

This file should be used for production deployments.
Requires environment variables to be set (see docs/PRODUCTION_SETUP.md)
"""

from .settings import *

# Production-specific overrides
IS_PRODUCTION = True
DEBUG = False

# Validate required environment variables
if not os.getenv("DJANGO_SECRET_KEY"):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be set in production. "
        "Generate one with: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\""
    )

if SECRET_KEY == "django-insecure-development-secret":
    raise ImproperlyConfigured(
        "Production detected but SECRET_KEY is still the development default. "
        "Set DJANGO_SECRET_KEY environment variable."
    )

# ALLOWED_HOSTS must be explicitly set
ALLOWED_HOSTS = env_list(os.getenv("DJANGO_ALLOWED_HOSTS"))
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must be set in production. "
        "Example: export DJANGO_ALLOWED_HOSTS='yourdomain.com,www.yourdomain.com'"
    )

# Security settings (most auto-enabled via IS_PRODUCTION in base settings)
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'  # Override to SAMEORIGIN if Summernote iframe needed

# Database - Require PostgreSQL for production
if DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
    raise ImproperlyConfigured(
        "Production requires PostgreSQL. Set DB_ENGINE='django.db.backends.postgresql' "
        "and configure DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT"
    )

# Connection pooling for production
DATABASES['default']['CONN_MAX_AGE'] = 600
DATABASES['default']['OPTIONS'] = {
    'connect_timeout': 10,
}

# Static files - Use WhiteNoise with compression
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.getenv('DJANGO_LOG_FILE', '/var/log/django/error.log'),
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# Email configuration for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = env_bool(os.getenv('EMAIL_USE_TLS'), True)
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)
SERVER_EMAIL = os.getenv('SERVER_EMAIL', EMAIL_HOST_USER)

# Admin email for error notifications
ADMINS = [
    ('Admin', os.getenv('ADMIN_EMAIL', 'admin@example.com')),
]
MANAGERS = ADMINS

# Cache configuration (Redis recommended)
if os.getenv('REDIS_URL'):
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.getenv('REDIS_URL'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'SOCKET_CONNECT_TIMEOUT': 5,
                'SOCKET_TIMEOUT': 5,
                'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
                'CONNECTION_POOL_KWARGS': {
                    'max_connections': 50,
                    'retry_on_timeout': True,
                },
            },
            'KEY_PREFIX': 'gsminfinity',
            'TIMEOUT': 300,
        }
    }

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db' if os.getenv('REDIS_URL') else 'django.contrib.sessions.backends.db'

# Disable browsable API in production (if using DRF)
if 'rest_framework' in INSTALLED_APPS:
    REST_FRAMEWORK = REST_FRAMEWORK.copy() if 'REST_FRAMEWORK' in globals() else {}
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
        'rest_framework.renderers.JSONRenderer',
    ]

# Celery configuration for async tasks (if using Celery)
if os.getenv('CELERY_BROKER_URL'):
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', CELERY_BROKER_URL)
    CELERY_TASK_ALWAYS_EAGER = False
    CELERY_TASK_EAGER_PROPAGATES = False

# Startup banner
logger.info("🚀 Production Settings Loaded (DEBUG=%s, ALLOWED_HOSTS=%s)", DEBUG, ALLOWED_HOSTS)
