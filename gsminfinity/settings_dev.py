"""
GSMInfinity Development Settings
================================
Overrides production `settings.py` for safe local development.

✅ DEBUG mode enabled
✅ HTTPS redirection fully disabled
✅ No HSTS / CSRF secure cookie enforcement
✅ Console email backend
✅ Local-only allowed hosts
✅ Fast logging and hashing
"""

from __future__ import annotations
from .settings import *  # import production defaults
from pathlib import Path

# ============================================================
# Environment / Debug
# ============================================================
DEBUG = True
ENV = "development"

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
SITE_ID = 1


# ============================================================
# Security Overrides (force HTTP)
# ============================================================
# Completely disable all HTTPS-related enforcement for dev
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False

SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False

# Ensure SslToggleMiddleware never forces HTTPS in dev
os.environ["FORCE_HTTPS_DEV_OVERRIDE"] = "0"


# ============================================================
# CSRF & Trusted Origins
# ============================================================
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]


# ============================================================
# Local SSL Certificate (optional)
# ============================================================
# Only used if you intentionally run dev server with TLS
CERT_DIR = Path("C:/certs")
SSL_CERT_FILE = CERT_DIR / "localhost.pem"
SSL_KEY_FILE = CERT_DIR / "localhost-key.pem"

if SSL_CERT_FILE.exists() and SSL_KEY_FILE.exists():
    print(f"🔒 Local HTTPS certs available: {SSL_CERT_FILE.name}")
else:
    print("⚠️  No local certs found — running HTTP-only")


# ============================================================
# Logging Configuration
# ============================================================
LOGGING["root"]["level"] = "DEBUG"
LOGGING["loggers"]["django"]["level"] = "DEBUG"

for logger_name in ("apps.users", "apps.core", "apps.consent", "apps.site_settings"):
    LOGGING["loggers"].setdefault(
        logger_name,
        {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    )


# ============================================================
# Email Backend (safe console)
# ============================================================
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "dev@gsm-infinity.local"


# ============================================================
# Caching (local memory)
# ============================================================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "TIMEOUT": 300,
    }
}


# ============================================================
# Password Hashers (fast)
# ============================================================
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]


# ============================================================
# Final notice
# ============================================================
print("⚙️  GSMInfinity Development Settings Loaded (HTTP-only, DEBUG=True)")
