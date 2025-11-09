"""
Custom Account & Social Adapters for GSMInfinity
-------------------------------------------------
Integrates django-allauth with GSMInfinity's enterprise-grade
custom user model, onboarding flow, and global site settings.

Ensures:
- Signup toggle from SiteSettings
- Strong password enforcement
- Verified user redirect logic
- Social signup → onboarding ("Tell us about you")
- Safe fallbacks if SiteSettings are missing
- Compatible with django-allauth ≥ 0.65.13
"""

import logging
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.contrib import messages
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from apps.site_settings.models import SiteSettings

logger = logging.getLogger(__name__)

# ============================================================
#  Custom Account Adapter
# ============================================================


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Overrides allauth’s account adapter to integrate with GSMInfinity settings
    and custom user verification flow.
    """

    def is_open_for_signup(self, request: HttpRequest) -> bool:
        """
        Respect the `enable_signup` flag in SiteSettings.
        Return True if signup is allowed; False otherwise.
        """
        try:
            site_settings = SiteSettings.get_solo()
            allowed = getattr(site_settings, "enable_signup", True)
            logger.debug("Signup permission from SiteSettings: %s", allowed)
            return allowed
        except Exception as exc:
            logger.warning("SiteSettings lookup failed: %s", exc)
            return True  # Fallback: allow signup if SiteSettings table not ready

    def clean_password(self, password: str, user=None) -> str:
        """
        Enforce strong password requirements.
        Delegates to DefaultAccountAdapter after enforcing custom rules.
        """
        if not password or len(password) < 8:
            raise ValidationError(_("Password must be at least 8 characters long."))
        if password.isdigit():
            raise ValidationError(_("Password cannot be entirely numeric."))
        return super().clean_password(password, user)

    def get_login_redirect_url(self, request: HttpRequest) -> str:
        """
        Determine redirect after successful login.
        - If email not verified → send to verification page
        - Otherwise → dashboard
        """
        user = getattr(request, "user", None)
        if user and hasattr(user, "email_verified_at") and not user.email_verified_at:
            messages.info(request, _("Please verify your email to continue."))
            logger.debug("Redirecting unverified user %s to verify_email", user.email)
            return reverse("users:verify_email")

        logger.debug("Redirecting verified user %s to dashboard", getattr(user, "email", None))
        return reverse("users:dashboard")

    def get_signup_redirect_url(self, request: HttpRequest) -> str:
        """
        After standard signup (email/password), direct user to onboarding/profile step.
        This supports the "Tell us about you" workflow.
        """
        logger.debug("Redirecting to profile onboarding after signup.")
        return reverse("users:profile")


# ============================================================
#  Custom Social Account Adapter
# ============================================================


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Integrates social-account events with GSMInfinity flow.
    Redirects new social signups to onboarding/profile page.
    """

    def get_connect_redirect_url(self, request: HttpRequest, socialaccount) -> str:
        """
        Redirect after connecting a new provider to an existing account.
        """
        logger.debug("Social connect redirect for account %s", socialaccount.provider)
        return reverse("users:profile")

    def get_signup_redirect_url(self, request: HttpRequest) -> str:
        """
        Redirect after a social signup (first-time social login).
        """
        logger.debug("Redirecting social signup to onboarding profile step.")
        return reverse("users:profile")

    def pre_social_login(self, request: HttpRequest, sociallogin) -> None:
        """
        Hook called just after a successful social login, before login is finalized.
        Auto-links social accounts to existing users by matching email addresses.

        Prevents duplicate user creation when the same email signs up via social login.
        """
        user_email = getattr(sociallogin.user, "email", None)
        if not user_email:
            logger.debug("Social login has no email; skipping auto-link.")
            return

        User = get_user_model()
        try:
            existing_user = User.objects.get(email__iexact=user_email)
        except User.DoesNotExist:
            logger.debug("No existing user found for social email: %s", user_email)
            return

        # If already linked, skip.
        if sociallogin.is_existing:
            logger.debug("Social account already linked for email: %s", user_email)
            return

        # Link existing user and skip creating a duplicate
        logger.info("Auto-linking social account for existing user: %s", user_email)
        sociallogin.connect(request, existing_user)
