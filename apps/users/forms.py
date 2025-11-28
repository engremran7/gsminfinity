"""
GSMInfinity - Custom Allauth Signup & Onboarding Forms
------------------------------------------------------
✅ Compatible with django-allauth ≥ 0.65.13 and Django 5.2 LTS
✅ Prevents circular imports during startup
✅ Implements required `signup(self, request, user)` API
✅ Enforces enterprise-grade validation and password policy
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)
User = get_user_model()


class CustomSignupForm(forms.Form):
    """
    Enterprise-grade wrapper around django-allauth's signup system.
    Lazy-loads allauth internals only when required to avoid circular imports.
    """

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

    referral_code = forms.CharField(
        max_length=12,
        required=False,
        label=_("Referral code (optional)"),
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "placeholder": _("Referral code"),
                "class": "form-control",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        # Prefill referral from ?ref=CODE if present
        try:
            if self.request and self.request.GET.get("ref"):
                code = (self.request.GET.get("ref") or "").strip().upper()[:12]
                if code:
                    self.initial.setdefault("referral_code", code)
        except Exception:
            pass

    @property
    def base_form_class(self):
        """Load django-allauth's internal SignupForm lazily."""
        return import_string("allauth.account.forms.SignupForm")

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

    def clean_referral_code(self) -> str:
        code = (self.cleaned_data.get("referral_code") or "").strip().upper()
        if not code:
            return ""
        try:
            from apps.users.models import CustomUser  # local import

            exists = CustomUser.objects.filter(referral_code__iexact=code).exists()
            if not exists:
                raise ValidationError(_("Invalid referral code."))
        except ValidationError:
            raise
        except Exception as exc:
            logger.debug("Referral code lookup failed: %s", exc)
        return code

    def signup(self, request, user):
        """
        Called automatically by allauth after successful form validation.
        Populates and saves the user instance using GSMInfinity logic.
        """
        user.username = self.cleaned_data.get("username")
        user.email = self.cleaned_data.get("email")

        if hasattr(user, "generate_verification_code"):
            try:
                user.verification_code = user.generate_verification_code()
                logger.debug("Generated verification code for %s", user.email)
            except Exception as exc:
                logger.warning("Verification code generation failed for %s: %s", user.email, exc)

        password = self.cleaned_data.get("password1")
        user.set_password(password)

        if hasattr(user, "is_active") and user.is_active is False:
            user.is_active = True

        if hasattr(user, "manual_signup"):
            user.manual_signup = True
        if hasattr(user, "signup_method"):
            user.signup_method = "manual"

        # Attach referral if provided
        ref_code = (self.cleaned_data.get("referral_code") or "").strip().upper()
        if ref_code and hasattr(user, "referred_by"):
            from apps.users.models import CustomUser  # local import

            referrer = CustomUser.objects.filter(referral_code__iexact=ref_code).first()
            if referrer and referrer != user:
                user.referred_by = referrer

        user.save()
        logger.info("New user created via signup: %s", user.email)
        return user

    def save(self, request):
        user = User()
        return self.signup(request, user)

    def try_save(self, request):
        return self.save(request)


class TellUsAboutYouForm(forms.Form):
    """
    Shared onboarding form for both social and manual signups.
    Requires username + full name.
    Requires password only if the user does not yet have one (typical for social signups).
    """

    username = forms.CharField(
        max_length=150,
        label=_("Username"),
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "placeholder": _("Choose a username"),
                "class": "form-control",
            }
        ),
    )

    full_name = forms.CharField(
        max_length=150,
        label=_("Full name"),
        widget=forms.TextInput(
            attrs={
                "autocomplete": "name",
                "placeholder": _("Your full name"),
                "class": "form-control",
            }
        ),
    )

    password1 = forms.CharField(
        label=_("Password"),
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": _("Create a password"),
                "class": "form-control",
            }
        ),
    )

    password2 = forms.CharField(
        label=_("Confirm password"),
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": _("Confirm password"),
                "class": "form-control",
            }
        ),
    )

    referral_code = forms.CharField(
        max_length=12,
        required=False,
        label=_("Referral code (optional)"),
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "placeholder": _("Referral code"),
                "class": "form-control",
            }
        ),
    )

    def __init__(self, *args, user=None, request=None, **kwargs):
        self.user = user
        self.request = request
        super().__init__(*args, **kwargs)

        # Require password only if user has no usable password (typical for social)
        self.require_password = bool(user and not user.has_usable_password())
        if self.require_password:
            self.fields["password1"].required = True
            self.fields["password2"].required = True

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not username:
            raise ValidationError(_("Username is required."))

        UserModel = get_user_model()
        qs = UserModel.objects.filter(username__iexact=username)
        if self.user and self.user.pk:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise ValidationError(_("This username is already taken."))
        return username

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1") or ""
        p2 = cleaned.get("password2") or ""

        if self.require_password:
            if not p1 or not p2:
                raise ValidationError(_("Password is required."))
            if p1 != p2:
                raise ValidationError(_("Passwords do not match."))
            validate_password(p1, self.user)

        return cleaned

    def clean_referral_code(self):
        code = (self.cleaned_data.get("referral_code") or "").strip().upper()
        if not code:
            return ""
        try:
            from apps.users.models import CustomUser  # local import

            exists = CustomUser.objects.filter(referral_code__iexact=code).exists()
            if not exists:
                raise ValidationError(_("Invalid referral code."))
        except ValidationError:
            raise
        except Exception as exc:
            logger.debug("Referral lookup failed in onboarding: %s", exc)
        return code


# ----------------------------------------------------------------------
# Legacy Social onboarding form (kept for compatibility)
# ----------------------------------------------------------------------
