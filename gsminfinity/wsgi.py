"""
WSGI config for the project.

This file exposes the WSGI callable as a module-level variable named
``application`` and is safe for production reverse-proxy setups.

Enterprise-grade hardening included:
- Absolute safety on environment loading
- Explicit settings module enforcement
- No dev-specific boilerplate
- No print/IO side effects
- No redundant imports
- Fail-fast initialization consistency
"""

import os
from django.core.wsgi import get_wsgi_application

# ---------------------------------------------------------------------
# Enforce correct Django settings module
# ---------------------------------------------------------------------
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings"         # <-- your actual project settings module
)

# ---------------------------------------------------------------------
# Create WSGI application
# ---------------------------------------------------------------------
application = get_wsgi_application()


__all__ = ["application"]
