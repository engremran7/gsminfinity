"""
GSMInfinity – Custom Allauth Signup Form
----------------------------------------
✅ Compatible with django-allauth ≥ 0.65.13 and Django 5.2 LTS
✅ Prevents circular imports during startup
✅ Implements required `signup(self, request, user)` API
✅ Enforces enterprise-grade validation and password policy
"""

from __future__ import annotations

import logging
from typing import Any
from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)
User = get_user_model()


class CustomSignupForm(forms.Form):
    """
    Enterprise-grade wrapper around django-allauth’s signup system.
    Lazy-loads allauth internals only when required to avoid circular imports.
    """

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------
    email = forms.EmailField(
        max_length=255,
        label=_("Email address"),
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "placeholder": _("Email"),
                "class": "form-control",
            }
        ),
    )

    username = forms.CharField(
        max_length=150,
        label=_("Username"),
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "placeholder": _("Username"),
                "class": "form-control",
            }
        ),
    )

    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": _("Password"),
                "class": "form-control",
            }
        ),
    )

    password2 = forms.CharField(
        label=_("Confirm password"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": _("Confirm password"),
                "class": "form-control",
            }
        ),
    )

    # ------------------------------------------------------------------
    # Lazy import of base allauth SignupForm
    # ------------------------------------------------------------------
    @property
    def base_form_class(self):
        """Load django-allauth’s internal SignupForm lazily."""
        return import_string("allauth.account.forms.SignupForm")

    # ------------------------------------------------------------------
    # Field-level validation
    # ------------------------------------------------------------------
    def clean_email(self) -> str:
        email = (self.cleaned_data.get("email") or "").strip().casefold()
        if not email or "@" not in email:
            raise ValidationError(_("Enter a valid email address."))
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_("A user with this email already exists."))
        return email

    def clean_username(self) -> str:
        username = (self.cleaned_data.get("username") or "").strip()
        if len(username) < 3:
            raise ValidationError(_("Username must be at least 3 characters long."))
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError(_("This username is already taken."))
        return username

    def clean_password1(self) -> str:
        password = self.cleaned_data.get("password1") or ""
        if len(password) < 8:
            raise ValidationError(_("Password must be at least 8 characters long."))
        # Use Django’s configured password validators (settings.AUTH_PASSWORD_VALIDATORS)
        try:
            password_validation.validate_password(password)
        except ValidationError as e:
            raise ValidationError(e.messages)
        return password

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean()
        pwd1, pwd2 = cleaned.get("password1"), cleaned.get("password2")
        if pwd1 and pwd2 and pwd1 != pwd2:
            raise ValidationError(_("Passwords do not match."))
        return cleaned

    # ------------------------------------------------------------------
    # Required by django-allauth ≥ 0.65
    # ------------------------------------------------------------------
    def signup(self, request, user):
        """
        Called automatically by allauth after successful form validation.
        Populates and saves the user instance using GSMInfinity logic.
        """
        user.username = self.cleaned_data.get("username")
        user.email = self.cleaned_data.get("email")

        # Generate a verification code if supported
        if hasattr(user, "generate_verification_code"):
            try:
                user.verification_code = user.generate_verification_code()
                logger.debug("Generated verification code for %s", user.email)
            except Exception as exc:
                logger.warning("Verification code generation failed for %s: %s", user.email, exc)

        # Set password (hashing handled by Django)
        password = self.cleaned_data.get("password1")
        user.set_password(password)

        # Initial defaults
        if hasattr(user, "is_active") and user.is_active is False:
            user.is_active = True

        user.save()
        logger.info("New user created via signup: %s", user.email)
        return user

    # ------------------------------------------------------------------
    # Backward-compatible helper for legacy allauth versions
    # ------------------------------------------------------------------
    def save(self, request):
        """
        Mirrors allauth’s legacy `save()` signature for backward compatibility.
        Simply delegates to `signup()`.
        """
        user = User()
        return self.signup(request, user)
