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
from typing import Any

from allauth.account.forms import ChangePasswordForm
from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)
User = get_user_model()


class CustomSignupForm(forms.Form):
    """
    Enterprise-grade wrapper around django-allauth's signup system.
    Lazy-loads allauth internals only when required to avoid circular imports.
    """

    # Compatibility with newer allauth flows that check this flag
    by_passkey: bool = False

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

    country = forms.CharField(
        max_length=2,
        required=False,
        label=_("Country"),
        widget=forms.Select(
            attrs={
                "class": "auth-input country-input",
            }
        ),
    )

    phone_country_code = forms.CharField(
        max_length=5,
        required=False,
        label=_("Country Code"),
        widget=forms.Select(
            attrs={
                "class": "phone-code-select",
            }
        ),
    )

    phone = forms.CharField(
        max_length=20,
        required=False,
        label=_("Phone Number"),
        widget=forms.TextInput(
            attrs={
                "autocomplete": "tel-national",
                "placeholder": _("Phone number (optional)"),
                "class": "auth-input phone-number-input",
                "type": "tel",
                "inputmode": "numeric",
                "pattern": "[0-9]{6,15}",
            }
        ),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

    @property
    def base_form_class(self) -> type:
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

    def clean_country(self) -> str:
        """Validate country code - must be 2 uppercase letters."""
        country = (self.cleaned_data.get("country") or "").strip().upper()
        if country and (len(country) != 2 or not country.isalpha()):
            raise ValidationError(_("Invalid country code."))
        return country

    def clean_phone(self) -> str:
        """Validate phone number - digits only, 6-15 characters."""
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            return ""

        # Remove any non-digit characters
        phone_digits = "".join(c for c in phone if c.isdigit())

        if len(phone_digits) < 6:
            raise ValidationError(_("Phone number must be at least 6 digits."))
        if len(phone_digits) > 15:
            raise ValidationError(_("Phone number cannot exceed 15 digits."))

        # Check for uniqueness
        if User.objects.filter(phone=phone_digits).exists():
            raise ValidationError(_("This phone number is already registered."))

        return phone_digits

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean()
        pwd1, pwd2 = cleaned.get("password1"), cleaned.get("password2")
        if pwd1 and pwd2 and pwd1 != pwd2:
            raise ValidationError(_("Passwords do not match."))
        return cleaned

    def signup(self, request: HttpRequest, user: Any) -> Any:
        """
        Called automatically by allauth after successful form validation.
        Populates and saves the user instance using GSMInfinity logic.
        """
        user.username = self.cleaned_data.get("username")
        user.email = self.cleaned_data.get("email")

        # Country and phone fields
        country = self.cleaned_data.get("country")
        phone = self.cleaned_data.get("phone")
        phone_country_code = self.cleaned_data.get("phone_country_code")

        if country and hasattr(user, "country"):
            user.country = country
        if phone and hasattr(user, "phone"):
            user.phone = phone
        if phone_country_code and hasattr(user, "phone_country_code"):
            user.phone_country_code = phone_country_code

        if hasattr(user, "generate_verification_code"):
            try:
                user.verification_code = user.generate_verification_code()
                logger.debug("Generated verification code for %s", user.email)
            except Exception as exc:
                logger.warning(
                    "Verification code generation failed for %s: %s", user.email, exc
                )

        password = self.cleaned_data.get("password1")
        user.set_password(password)

        if hasattr(user, "is_active") and user.is_active is False:
            user.is_active = True

        if hasattr(user, "manual_signup"):
            user.manual_signup = True
        if hasattr(user, "signup_method"):
            user.signup_method = "manual"

        user.save()
        logger.info("New user created via signup: %s", user.email)
        return user

    def save(self, request: HttpRequest) -> tuple[Any, None]:
        user = User()
        # Some allauth flows unpack save() (user, extra); return a tuple for compatibility.
        created = self.signup(request, user)
        return created, None

    def try_save(self, request: HttpRequest) -> tuple[Any, None]:
        return self.save(request)


class TellUsAboutYouForm(forms.Form):
    """
    Shared onboarding form for both social and manual signups.
    Requires username + full name.
    Requires password only if the user does not yet have one (typical for social signups).
    Includes country and phone with auto-detection support.
    """

    username = forms.CharField(
        max_length=150,
        label=_("Username"),
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "placeholder": _("Choose a username"),
                "class": "auth-input",
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
                "class": "auth-input",
            }
        ),
    )

    country = forms.CharField(
        max_length=2,
        required=False,
        label=_("Country"),
        widget=forms.Select(
            attrs={
                "class": "auth-input",
            }
        ),
    )

    phone_country_code = forms.CharField(
        max_length=5,
        required=False,
        label=_("Country Code"),
        widget=forms.Select(
            attrs={
                "class": "phone-code-select",
            }
        ),
    )

    phone = forms.CharField(
        max_length=20,
        required=False,
        label=_("Phone Number"),
        widget=forms.TextInput(
            attrs={
                "autocomplete": "tel-national",
                "placeholder": _("Phone number (optional)"),
                "class": "auth-input phone-number-input",
                "type": "tel",
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
                "class": "auth-input",
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
                "class": "auth-input",
            }
        ),
    )

    def __init__(
        self,
        *args: Any,
        user: Any | None = None,
        request: HttpRequest | None = None,
        **kwargs: Any,
    ) -> None:
        self.user = user
        self.request = request
        super().__init__(*args, **kwargs)

        # Require password only if user has no usable password (typical for social)
        self.require_password = bool(user and not user.has_usable_password())
        if self.require_password:
            self.fields["password1"].required = True
            self.fields["password2"].required = True

    def clean_username(self) -> str:
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

    def clean_phone(self) -> str:
        """Validate phone number - digits only, 6-15 characters."""
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            return ""

        # Remove any non-digit characters
        phone_digits = "".join(c for c in phone if c.isdigit())

        if len(phone_digits) < 6:
            raise ValidationError(_("Phone number must be at least 6 digits."))
        if len(phone_digits) > 15:
            raise ValidationError(_("Phone number cannot exceed 15 digits."))

        # Check for uniqueness
        UserModel = get_user_model()
        qs = UserModel.objects.filter(phone=phone_digits)
        if self.user and self.user.pk:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise ValidationError(_("This phone number is already registered."))

        return phone_digits

    def clean_country(self) -> str:
        """Validate country code - must be 2 uppercase letters."""
        country = (self.cleaned_data.get("country") or "").strip().upper()
        if country and (len(country) != 2 or not country.isalpha()):
            raise ValidationError(_("Invalid country code."))
        return country

    def clean(self) -> dict[str, Any]:
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


# ----------------------------------------------------------------------
# Legacy Social onboarding form (kept for compatibility)
# ----------------------------------------------------------------------


class CustomChangePasswordForm(ChangePasswordForm):
    """
    Require current password when changing it.
    If the account has no usable password, force user to go through password reset.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if "oldpassword" in self.fields:
            self.fields["oldpassword"].required = True

    def clean_oldpassword(self) -> str:
        if not self.user:
            raise ValidationError(_("User is required."))
        if not self.user.has_usable_password():
            raise ValidationError(
                _("No existing password found. Use 'Forgot password' to set one.")
            )
        oldpassword = (self.cleaned_data.get("oldpassword") or "").strip()
        if not oldpassword:
            raise ValidationError(_("Enter your current password."))
        if not self.user.check_password(oldpassword):
            raise ValidationError(_("The current password you entered is incorrect."))
        return oldpassword

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean()
        # Double-check old password in case upstream validation is bypassed.
        if self.user and self.user.has_usable_password():
            oldpassword = (self.cleaned_data.get("oldpassword") or "").strip()
            if not oldpassword or not self.user.check_password(oldpassword):
                raise ValidationError(
                    _("The current password you entered is incorrect.")
                )
        return cleaned
