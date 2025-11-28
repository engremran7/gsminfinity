"""
GSMInfinity Development Settings
================================
Overrides production `settings.py` for safe local development.

- DEBUG mode enabled
- HTTPS redirection fully disabled
- No HSTS / CSRF secure cookie enforcement
- Console email backend
- Local-only allowed hosts
- Fast logging and hashing
"""

from __future__ import annotations

from pathlib import Path

from .settings import *  # import production defaults

# ============================================================
# Environment / Debug
# ============================================================
DEBUG = True
ENV = "development"

# Allow sync DB/session access in async dev server contexts (suppress SynchronousOnlyOperation)
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

ACCOUNT_AUTHENTICATED_LOGIN_REDIRECTS = False

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "0.0.0.0", "testserver"]
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
SESSION_COOKIE_AGE = 1209600  # 14 days
SESSION_SAVE_EVERY_REQUEST = False

CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"

# Dev: do not trust X-Forwarded-Proto by default
SECURE_PROXY_SSL_HEADER = None

# Ensure SslToggleMiddleware never forces HTTPS in dev
os.environ["FORCE_HTTPS_DEV_OVERRIDE"] = "0"
MIDDLEWARE = [
    mw for mw in MIDDLEWARE if mw != "apps.core.middleware.ssl_toggle.SslToggleMiddleware"
]


# ============================================================
# CSRF & Trusted Origins
# ============================================================
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

# When already authenticated, redirect away from login/signup to the dashboard
ACCOUNT_AUTHENTICATED_LOGIN_REDIRECTS = True


# ============================================================
# Local SSL Certificate (optional)
# ============================================================
# Only used if you intentionally run dev server with TLS
CERT_DIR = Path("C:/certs")
SSL_CERT_FILE = CERT_DIR / "localhost.pem"
SSL_KEY_FILE = CERT_DIR / "localhost-key.pem"

if SSL_CERT_FILE.exists() and SSL_KEY_FILE.exists():
    print(f"[DEV] Local HTTPS certs available: {SSL_CERT_FILE.name}")
else:
    print("[DEV] No local certs found - running HTTP-only")


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
print("[DEV] GSMInfinity Development Settings Loaded (HTTP-only, DEBUG=True)")
