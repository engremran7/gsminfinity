"""Admin Suite view aggregator.

Auto-loads view modules named views_*.py (except views_shared) so new admin sections can be added without touching this file.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

from . import views_shared as _shared

# Export core helpers for backward compatibility
__all__ = []
_shared_exports = ("logger", "_ADMIN_DISABLED", "_ADMIN_LOGIN_URL", "STAFF_ONLY", "_make_breadcrumb", "_render_admin")
for name in _shared_exports:
    globals()[name] = getattr(_shared, name)
    __all__.append(name)

def _auto_import_view_modules() -> None:
    base_pkg = __package__ or "apps.admin_suite"
    base_path = Path(__file__).resolve().parent
    for module_info in pkgutil.iter_modules([str(base_path)]):
        name = module_info.name
        if not name.startswith("views_") or name in {"views_shared", "views"}:
            continue
        module = importlib.import_module(f"{base_pkg}.{name}")
        exported = getattr(module, "__all__", None)
        if exported is None:
            exported = [n for n in dir(module) if not n.startswith("_")]
        for attr in exported:
            globals()[attr] = getattr(module, attr)
        __all__.extend(exported)

_auto_import_view_modules()

# Explicitly re-export new views if auto-import misses them (e.g. due to caching)

__all__.extend([
    "admin_suite_blog_categories",
    "admin_suite_pending_approval",
    "admin_suite_user_sessions",
    "admin_suite_staff_users",
    "admin_suite_security_events",
])

