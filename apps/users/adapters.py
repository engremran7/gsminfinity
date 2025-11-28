"""
Enterprise-grade Account & Social Adapters for GSMInfinity.
Integrates OAuth onboarding, trusted social email verification, and safe redirects.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialLogin
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.urls import NoReverseMatch, reverse
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


def _safe_reverse(name: str, default: str = "/") -> str:
    """Best-effort reverse that never raises; used for login/onboarding redirects."""
    try:
        return reverse(name)
    except NoReverseMatch:
        logger.warning("reverse(%s) failed - fallback=%s", name, default)
        return default
    except Exception as exc:
        logger.exception("reverse(%s) unexpected error: %s", name, exc)
        return default


class CustomAccountAdapter(DefaultAccountAdapter):
    """Account adapter with hardened password rules and trusted social email."""

    def is_open_for_signup(self, request: Optional[HttpRequest]) -> bool:
        try:
            from apps.site_settings.models import SiteSettings  # type: ignore

            settings_obj = SiteSettings.get_solo()
            return bool(getattr(settings_obj, "enable_signup", True))
        except Exception as exc:
            logger.warning("Signup availability check failed: %s", exc)
            return True

    def clean_password(self, password: str, user: Optional[Any] = None) -> str:
        if not isinstance(password, str):
            raise ValidationError(_("Invalid password format."))
        if len(password) < 8:
            raise ValidationError(_("Password must be at least 8 characters long."))
        if password.isdigit():
            raise ValidationError(_("Password cannot be entirely numeric."))
        return super().clean_password(password, user)

    def is_email_verified(self, user):
        try:
            social = getattr(user, "socialaccount_set", None)
            if social and social.first():
                return True
        except Exception:
            pass
        return super().is_email_verified(user)

    def get_login_redirect_url(self, request: HttpRequest) -> str:
        try:
            user = getattr(request, "user", None)
            if user and getattr(user, "email_verified_at", None) is None:
                verification_required = False
                if getattr(user, "manual_signup", False):
                    verification_required = True
                elif (
                    getattr(settings, "ACCOUNT_EMAIL_VERIFICATION", "optional")
                    == "mandatory"
                ):
                    verification_required = True

                if verification_required:
                    try:
                        messages.info(request, _("Please verify your email to continue."))
                    except Exception:
                        pass
                    return _safe_reverse("users:verify_email", default="/")
        except Exception as exc:
            logger.exception("Login redirect evaluation failed: %s", exc)
        return _safe_reverse("users:dashboard", default="/")

    def get_signup_redirect_url(self, request: HttpRequest) -> str:
        return _safe_reverse("users:tell_us_about_you", default="/users/profile/")


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Social adapter that trusts provider email and defers completion to onboarding."""

    def get_connect_redirect_url(self, request: HttpRequest, socialaccount) -> str:
        logger.debug(
            "Social connect redirect (provider=%s)",
            getattr(socialaccount, "provider", None),
        )
        return _safe_reverse("users:tell_us_about_you", default="/users/profile/")

    def get_signup_redirect_url(self, request: HttpRequest) -> str:
        logger.debug("Social signup redirect -> users:tell_us_about_you")
        return _safe_reverse("users:tell_us_about_you", default="/users/profile/")

    def pre_social_login(self, request: HttpRequest, sociallogin: SocialLogin) -> None:
        """
        Keep minimal: if the user is already fully onboarded, do nothing.
        Otherwise, let EnforceProfileCompletionMiddleware drive them to the
        tell-us-about-you flow.
        """
        try:
            user = getattr(sociallogin, "user", None)
            if user and getattr(user, "id", None) and getattr(
                user, "profile_completed", False
            ):
                return
            logger.debug("pre_social_login: social login requires onboarding.")
        except Exception as exc:
            logger.exception("pre_social_login fatal error: %s", exc)
            return
