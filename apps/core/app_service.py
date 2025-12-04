
from __future__ import annotations

"""
apps.core.app_service
---------------------
Simple dynamic app registry + resolver for micro-module APIs.
"""

import importlib
import logging
from typing import Any, Dict, Optional

from apps.core.models import AppRegistry

logger = logging.getLogger(__name__)


class AppService:
    """
    Resolve per-app API modules dynamically, respecting AppRegistry.enable flags.
    """

    _cache: Dict[str, Any] = {}

    @classmethod
    def get(cls, app_label: str) -> Optional[Any]:
        key = app_label.strip().lower()
        if not key:
            return None

        # Disabled in registry? return None
        try:
            reg = AppRegistry.get_solo()
            enabled = getattr(reg, f"{key}_enabled", True)
            if enabled is False:
                return None
        except Exception:
            # Fail-open if registry missing
            pass

        if key in cls._cache:
            return cls._cache[key]

        candidates = [
            f"apps.{key}.api",
            f"{key}.api",
        ]
        for mod_path in candidates:
            try:
                module = importlib.import_module(mod_path)
                cls._cache[key] = module
                return module
            except ModuleNotFoundError:
                continue
            except Exception as exc:
                logger.exception("Failed loading app api %s: %s", mod_path, exc)
                return None
        return None


__all__ = ["AppService"]


