"""
GSMInfinity Development Settings
--------------------------------
Overrides production settings for local development.

✅ Always HTTP — never enforces HTTPS
✅ DEBUG = True
✅ Console email backend
✅ Safe cache, session & CSRF defaults
✅ Supports local runserver (no SSL certs required)
"""

import os
from pathlib import Path

from .settings import *  # import all production defaults

# -------------------------
# Core environment
# -------------------------
DEBUG = True
ENV = "development"

# Disable any accidental HTTPS enforcement (middleware or admin toggle)
FORCE_HTTPS_DEV_OVERRIDE = 0

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "0.0.0.0"]

# -------------------------
# Security overrides (safe HTTP)
# -------------------------
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_HTTPONLY = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False
SESSION_COOKIE_SAMESITE = "Lax"

CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://0.0.0.0:8000",
]

# -------------------------
# Local SSL certificate paths (optional, not used by default)
# -------------------------
CERT_DIR = Path(BASE_DIR) / "certs"
SSL_CERT_FILE = CERT_DIR / "localhost.pem"
SSL_KEY_FILE = CERT_DIR / "localhost-key.pem"

# Optional developer feedback — nothing enforces SSL
if SSL_CERT_FILE.exists():
    print(f"🔒 Optional local certificate found: {SSL_CERT_FILE}")
else:
    print("🌐 Development mode running strictly over HTTP (no HTTPS enforced).")

# -------------------------
# Logging (verbose for development)
# -------------------------
LOGGING["root"]["level"] = "DEBUG"
for logger_name in ("apps.users", "apps.core", "apps.consent", "apps.site_settings"):
    LOGGING.setdefault("loggers", {}).setdefault(
        logger_name,
        {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    )

# -------------------------
# Email (console backend)
# -------------------------
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# -------------------------
# Cache (local memory)
# -------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "TIMEOUT": 300,
    }
}

# -------------------------
# Faster password hashing for quick test logins
# -------------------------
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# -------------------------
# Optional development-only toolbar or extensions (future toggle)
# -------------------------
if DEBUG and "django_extensions" not in INSTALLED_APPS:
    INSTALLED_APPS += ["django_extensions"]

# -------------------------
# Runtime banner
# -------------------------
print("⚙️  GSMInfinity Development Settings Loaded (HTTP only, DEBUG=True)")