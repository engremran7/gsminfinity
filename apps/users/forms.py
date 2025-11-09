"""
GSMInfinity - Custom Allauth Signup Form
----------------------------------------
✅ Compatible with django-allauth ≥ 0.65.13 and Django 5.x
✅ Prevents circular imports during startup
✅ Implements the required `signup(self, request, user)` method
✅ Adds enterprise-grade validation, password policy, and secure defaults
"""

import logging
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)
User = get_user_model()


class CustomSignupForm(forms.Form):
    """
    Lightweight, enterprise-ready wrapper around django-allauth’s signup system.
    Does not import allauth internals at import-time to prevent circular imports.
    """

    # ------------------------------------------------------------------
    #  Fields
    # ------------------------------------------------------------------
    email = forms.EmailField(
        max_length=255,
        label=_("Email address"),
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": _("Email")}),
    )
    username = forms.CharField(
        max_length=150,
        label=_("Username"),
        widget=forms.TextInput(attrs={"autocomplete": "username", "placeholder": _("Username")}),
    )
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "placeholder": _("Password")}),
        strip=False,
    )
    password2 = forms.CharField(
        label=_("Confirm password"),
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "placeholder": _("Confirm password")}),
        strip=False,
    )

    # ------------------------------------------------------------------
    #  Lazy property: safely load the real SignupForm only when used
    # ------------------------------------------------------------------
    @property
    def base_form_class(self):
        """Load django-allauth’s internal SignupForm lazily."""
        return import_string("allauth.account.forms.SignupForm")

    # ------------------------------------------------------------------
    #  Validation
    # ------------------------------------------------------------------
    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email or "@" not in email:
            raise ValidationError(_("Enter a valid email address."))
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_("A user with this email already exists."))
        return email

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if len(username) < 3:
            raise ValidationError(_("Username must be at least 3 characters long."))
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError(_("This username is already taken."))
        return username

    def clean_password1(self):
        password = self.cleaned_data.get("password1") or ""
        if len(password) < 8:
            raise ValidationError(_("Password must be at least 8 characters long."))
        if password.isdigit():
            raise ValidationError(_("Password cannot be entirely numeric."))
        return password

    def clean(self):
        cleaned = super().clean()
        pwd1, pwd2 = cleaned.get("password1"), cleaned.get("password2")
        if pwd1 and pwd2 and pwd1 != pwd2:
            raise ValidationError(_("Passwords do not match."))
        return cleaned

    # ------------------------------------------------------------------
    #  Required by django-allauth ≥ 0.65
    # ------------------------------------------------------------------
    def signup(self, request, user):
        """
        Called automatically by allauth after successful form validation.
        Populates and saves the user instance with enterprise logic.
        """
        user.username = self.cleaned_data.get("username")
        user.email = self.cleaned_data.get("email")

        # Optional enterprise logic: verification code, referral tracking, etc.
        if hasattr(user, "generate_verification_code"):
            user.verification_code = user.generate_verification_code()
            logger.debug("Generated verification code for %s", user.email)

        user.set_password(self.cleaned_data.get("password1"))
        user.save()
        logger.info("New user created via signup: %s", user.email)
        return user

    # ------------------------------------------------------------------
    #  Compatibility helper (legacy save signature)
    # ------------------------------------------------------------------
    def save(self, request):
        """
        Mirrors allauth’s `save()` signature for backwards compatibility.
        Simply delegates to `signup()`.
        """
        user = User()
        return self.signup(request, user)
