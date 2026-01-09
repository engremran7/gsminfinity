from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.smtp import EmailBackend as SmtpEmailBackend
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


def _get_fallback_backend_class():
    backend_path = getattr(
        settings,
        "DEFAULT_EMAIL_BACKEND",
        "django.core.mail.backends.console.EmailBackend",
    )
    try:
        return import_string(backend_path)
    except Exception as exc:
        logger.warning(
            "Failed to import fallback email backend %s: %s", backend_path, exc
        )
        return SmtpEmailBackend


def _gmail_config() -> dict[str, Any]:
    try:
        from apps.site_settings.models import SiteSettings  # type: ignore

        s = SiteSettings.get_solo()
        if not getattr(s, "gmail_enabled", False):
            return {}
        username = (getattr(s, "gmail_username", "") or "").strip()
        app_password = (getattr(s, "gmail_app_password", "") or "").strip()
        from_email = (getattr(s, "gmail_from_email", "") or username).strip()
        if username and app_password:
            return {
                "host": "smtp.gmail.com",
                "port": 587,
                "username": username,
                "password": app_password,
                "use_tls": True,
                "fail_silently": False,
                "from_email": from_email,
            }
    except Exception as exc:
        logger.warning("Gmail config unavailable: %s", exc)
    return {}


class GmailBackend(BaseEmailBackend):
    """
    Dynamic Gmail backend that reads credentials from SiteSettings.
    Falls back to DEFAULT_EMAIL_BACKEND when Gmail is disabled or misconfigured.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cfg = _gmail_config()
        if cfg:
            self._backend = SmtpEmailBackend(
                host=cfg["host"],
                port=cfg["port"],
                username=cfg["username"],
                password=cfg["password"],
                use_tls=cfg["use_tls"],
                fail_silently=cfg.get("fail_silently", False),
            )
            self._from_email = cfg.get("from_email")
        else:
            backend_cls = _get_fallback_backend_class()
            self._backend = backend_cls(
                fail_silently=kwargs.get("fail_silently", False)
            )
            self._from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)

    def open(self):
        return self._backend.open()

    def close(self):
        return self._backend.close()

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        if self._from_email:
            for m in email_messages:
                if not m.from_email:
                    m.from_email = self._from_email
        return self._backend.send_messages(email_messages)
