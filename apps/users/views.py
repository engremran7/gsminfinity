"""
apps.users.views
================
Enterprise-grade user management and authentication views for GSMInfinity.

✅ Highlights
-------------
• Tenant-aware SiteSettings resolver (uses site_settings.views._get_settings when available)
• Integrated rate limiting + reCAPTCHA verification
• Device fingerprint capture and per-user limit enforcement
• MFA / Email verification enforcement
• Optimized dashboard queries (deferred, select_related)
• Atomic safety and hardened UX
• Fully compatible with Django 5.x and allauth ≥ 0.65
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from allauth.account.forms import LoginForm, SignupForm
from allauth.account.views import LoginView, SignupView
from apps.users.forms import TellUsAboutYouForm
from apps.users.models import Announcement, DeviceFingerprint, Notification
from apps.users.services.rate_limit import allow_action
from apps.users.services.recaptcha import verify_recaptcha
from apps.users.utils.device import enforce_device_limit, record_device_fingerprint
from apps.users.utils.utils import get_device_fingerprint
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST, require_http_methods

logger = logging.getLogger(__name__)


@login_required
def profile(request: HttpRequest) -> HttpResponse:
    """
    Display the authenticated user's profile.
    """
    context: dict[str, Any] = {
        "user": request.user,
        "notifications": Notification.objects.filter(user=request.user).order_by(
            "-created_at"
        )[:10],
        "announcements": Announcement.objects.filter(is_active=True).order_by(
            "-created_at"
        )[:5],
        "referral_link": "",
    }
    try:
        if getattr(request.user, "referral_code", None):
            base_signup = request.build_absolute_uri(reverse("account_signup"))
            context["referral_link"] = f"{base_signup}?ref={request.user.referral_code}"
    except Exception:
        context["referral_link"] = ""
    return render(request, "users/profile.html", context)


def login_view(request: HttpRequest) -> HttpResponse:
    """
    Render the login page. Delegates authentication to django-allauth.
    """
    if request.user.is_authenticated:
        return redirect("core:home")

    context: dict[str, Any] = {
        "form": LoginForm(),
        "site": get_current_site(request),
    }
    return render(request, "login.html", context)


# ============================================================
# Settings resolver (lazy import to avoid circular deps)
# ============================================================
def _get_settings(request=None) -> Dict[str, object]:
    """
    Return primitive settings snapshot (dict). Try to use the canonical resolver
    from apps.site_settings.views (which already returns dict snapshots). If
    unavailable, fall back to safe defaults.
    """
    try:
        # Lazy import to avoid circular imports
        from apps.site_settings.views import (
            _get_settings as _ss_get_settings,
        )  # type: ignore

        result = _ss_get_settings(request)
        # Ensure it's a dict (backwards tolerant)
        if isinstance(result, dict):
            return result
        # If old-style model instance returned, convert to dict
        return {
            "site_name": getattr(result, "site_name", "GSMInfinity"),
            "enable_signup": getattr(result, "enable_signup", True),
            "max_login_attempts": int(getattr(result, "max_login_attempts", 5) or 5),
            "rate_limit_window_seconds": int(
                getattr(result, "rate_limit_window_seconds", 300) or 300
            ),
            "recaptcha_enabled": bool(getattr(result, "recaptcha_enabled", False)),
            "enforce_unique_device": bool(
                getattr(result, "enforce_unique_device", False)
            ),
            "max_devices_per_user": int(
                getattr(result, "max_devices_per_user", 3) or 3
            ),
            "require_mfa": bool(getattr(result, "require_mfa", False)),
            "enable_payments": bool(getattr(result, "enable_payments", True)),
        }
    except Exception:
        # Fallback defaults (primitive types only)
        logger.debug(
            "site settings resolver lazy import failed; using fallback defaults",
            exc_info=True,
        )
        return {
            "site_name": "GSMInfinity",
            "enable_signup": True,
            "max_login_attempts": 5,
            "rate_limit_window_seconds": 300,
            "recaptcha_enabled": False,
            "enforce_unique_device": False,
            "max_devices_per_user": 3,
            "require_mfa": False,
            "enable_payments": True,
            "site_header": "GSM Admin",
            "site_description": "Default configuration",
            "meta_tags": [],
            "verification_files": [],
            # Branding fallbacks used by base.html
            "primary_color": "#0d6efd",
            "secondary_color": "#6c757d",
            "logo": None,
            "dark_logo": None,
            "favicon": None,
        }


# ============================================================
# Enterprise Login View
# ============================================================
class EnterpriseLoginView(LoginView):
    """
    Enterprise login with:
    - IP-based rate limiting
    - reCAPTCHA verification
    - Device fingerprint & limit enforcement
    - Optional MFA redirect
    """

    form_class = LoginForm
    template_name = "account/login.html"

    def form_valid(self, form):
        settings_obj = _get_settings(self.request)
        ip = (
            (
                self.request.META.get("HTTP_X_FORWARDED_FOR")
                or self.request.META.get("REMOTE_ADDR")
                or "unknown"
            )
            .split(",")[0]
            .strip()
        )

        # --- Rate Limiting ---
        try:
            if not allow_action(
                f"login:{ip}",
                int(settings_obj.get("max_login_attempts", 5)),
                int(settings_obj.get("rate_limit_window_seconds", 300)),
            ):
                form.add_error(None, "Too many login attempts. Please try again later.")
                logger.warning("Rate limit exceeded for IP=%s", ip)
                return self.form_invalid(form)
        except Exception:
            # Fail-open: allow login if rate limiter has issues, but log
            logger.exception("Rate limiter failure (fail-open)")

        # --- reCAPTCHA ---
        token = self.request.POST.get("g-recaptcha-response") or self.request.POST.get(
            "recaptcha_token"
        )
        if settings_obj.get("recaptcha_enabled", False) and token:
            try:
                rc_result = verify_recaptcha(token, ip, action="login")
                if not rc_result.get("ok"):
                    form.add_error(
                        None, "reCAPTCHA verification failed. Please try again."
                    )
                    logger.info("reCAPTCHA failed for %s → %s", ip, rc_result)
                    return self.form_invalid(form)
            except Exception:
                logger.exception("reCAPTCHA error (fail-open): %s", exc_info=True)
                form.add_error(None, "reCAPTCHA service error. Try again later.")
                return self.form_invalid(form)

        # Authenticate & create session
        response = super().form_valid(form)

        # --- Session fixation protection ---
        try:
            if hasattr(self.request, "session"):
                # Rotate session key on login
                self.request.session.cycle_key()
                # Set a sane default expiry (2 weeks). Rely on remember-me elsewhere if present.
                self.request.session.set_expiry(1209600)
        except Exception:
            logger.exception("Failed to rotate session after login")

        user = self.request.user

        # --- Device limit enforcement (admin bypass inside helper) ---
        try:
            if settings_obj.get("enforce_unique_device", False):
                allowed = enforce_device_limit(user)
                if not allowed:
                    form.add_error(None, "Device limit exceeded. Contact support.")
                    logger.warning(
                        "Device limit exceeded for user=%s",
                        getattr(user, "email", user.pk),
                    )
                    return self.form_invalid(form)
        except Exception:
            logger.exception("Device enforcement error (fail-open)")

        # --- Fingerprint Recording (best-effort) ---
        try:
            fp = get_device_fingerprint(self.request)
            if fp:
                try:
                    record_device_fingerprint(
                        self.request, user, {"fingerprint_hash": fp}
                    )
                except PermissionError:
                    # Device rejected under strict mode
                    form.add_error(
                        None, "This device cannot be registered. Contact support."
                    )
                    logger.warning(
                        "Device blocked for user=%s", getattr(user, "email", user.pk)
                    )
                    return self.form_invalid(form)
                except Exception:
                    logger.exception("Failed to record device fingerprint")
        except Exception:
            logger.debug("Fingerprint capture failed (non-fatal)")

        # --- MFA / Email verification enforcement (config-aware) ---
        try:
            require_mfa = settings_obj.get("require_mfa", False)
            email_verification_mode = getattr(
                settings, "ACCOUNT_EMAIL_VERIFICATION", "optional"
            )
            if (
                require_mfa
                and email_verification_mode == "mandatory"
                and not getattr(user, "email_verified_at", None)
            ):
                logger.info(
                    "Redirecting %s to email verification (MFA required)",
                    getattr(user, "email", user.pk),
                )
                return redirect("users:verify_email")
        except Exception:
            logger.exception("MFA check failed (non-fatal)")

        return response


# ============================================================
# Enterprise Signup View
# ============================================================
class EnterpriseSignupView(SignupView):
    """Tenant-aware signup with optional reCAPTCHA verification."""

    form_class = SignupForm
    template_name = "account/signup.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pass request to form so it can prefill referral from ?ref=
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        s = _get_settings(self.request)

        if not s.get("enable_signup", True):
            form.add_error(None, "Signup is currently disabled.")
            logger.info("Signup attempt blocked by settings.")
            return self.form_invalid(form)

        token = self.request.POST.get("g-recaptcha-response") or self.request.POST.get(
            "recaptcha_token"
        )
        if s.get("recaptcha_enabled", False) and token:
            try:
                client_ip = (
                    (
                        self.request.META.get("HTTP_X_FORWARDED_FOR")
                        or self.request.META.get("REMOTE_ADDR")
                        or "unknown"
                    )
                    .split(",")[0]
                    .strip()
                )
                rc = verify_recaptcha(token, client_ip, action="signup")
                if not rc.get("ok"):
                    form.add_error(None, "reCAPTCHA failed. Please retry.")
                    logger.info("reCAPTCHA failed during signup → %s", rc)
                    return self.form_invalid(form)
            except Exception:
                logger.exception("reCAPTCHA error during signup")
                form.add_error(None, "reCAPTCHA error. Please try again.")
                return self.form_invalid(form)

        return super().form_valid(form)


# ============================================================
# Manual email verification (MFA / email)
# ============================================================
@login_required
def verify_email_view(request):
    """Manual verification for MFA / email confirmation."""
    user = request.user
    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        if not code:
            messages.error(request, "Verification code required.")
            return render(request, "users/verify_email.html")

        if code == getattr(user, "verification_code", ""):
            user.email_verified_at = timezone.now()
            user.verification_code = ""
            user.save(update_fields=["email_verified_at", "verification_code"])
            messages.success(request, "Email verified successfully.")
            return redirect("users:dashboard")

        messages.error(request, "Invalid verification code.")
        logger.warning("Invalid verification attempt for user=%s", user.pk)

    return render(request, "users/verify_email.html")


# ============================================================
# Dashboard view
# ============================================================
@login_required
def dashboard_view(request):
    """Render user dashboard with recent announcements and notifications."""
    s = _get_settings(request)
    # Gate unverified manual users if required
    try:
        if getattr(request.user, "manual_signup", False) and not getattr(
            request.user, "email_verified_at", None
        ):
            return redirect("users:verify_email")
    except Exception:
        pass
    now = timezone.now()

    # Announcements: use 'message' (model uses message field)
    announcements = (
        Announcement.objects.filter(start_at__lte=now)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .only("title", "message", "start_at", "expires_at")
        .order_by("-start_at")
    )

    notifications = (
        Notification.objects.filter(recipient=request.user)
        .select_related("recipient")
        # Include recipient to avoid deferred+select_related conflict with .only()
        .only("title", "message", "created_at", "recipient")
        .order_by("-created_at")[:5]
    )

    # Device usage snapshot (defensive)
    device_limit = int(s.get("max_devices_per_user", 3) or 3)
    try:
        device_used = (
            DeviceFingerprint.objects.filter(user=request.user, is_active=True).count()
        )
    except Exception:
        logger.debug("device count failed", exc_info=True)
        device_used = 0
    device_remaining = max(device_limit - device_used, 0)

    context = {
        "site_settings": s,
        "announcements": announcements,
        "notifications": notifications,
        "credits": getattr(request.user, "credits", 0),
        "can_watch_ad": bool(s.get("recaptcha_enabled", False)),
        "can_pay": bool(s.get("enable_payments", True)),
        "device_limit": device_limit,
        "device_used": device_used,
        "device_remaining": device_remaining,
    }
    return render(request, "users/dashboard.html", context)


# ============================================================
# Profile view
# ============================================================
@login_required
def profile_view(request):
    """Render the user profile overview page."""
    s = _get_settings(request)
    return render(
        request,
        "users/profile.html",
        {
            "user": request.user,
            "credits": getattr(request.user, "credits", 0),
            "site_settings": s,
        },
    )


# ============================================================
# Devices view / reset
# ============================================================
@login_required
def device_list_view(request):
    """List active devices for the current user."""
    devices = (
        DeviceFingerprint.objects.filter(user=request.user)
        .order_by("-last_used_at")
        .only("id", "fingerprint_hash", "os_info", "browser_info", "last_used_at")
    )
    return render(
        request,
        "users/devices.html",
        {"devices": devices, "site_settings": _get_settings(request)},
    )


@login_required
def device_reset_view(request, pk: int):
    """
    Deactivate a device fingerprint.
    Only staff/superusers may reset devices directly.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(
            request,
            "Self-service resets are not available. Please use paid or ad-based reset options.",
        )
        return redirect("users:devices")

    try:
        device = DeviceFingerprint.objects.get(pk=pk, user=request.user)
        device.is_active = False
        device.save(update_fields=["is_active", "last_used_at"])
        messages.success(request, "Device has been reset/deactivated.")
    except DeviceFingerprint.DoesNotExist:
        messages.error(request, "Device not found.")
    except Exception as exc:
        logger.exception("device_reset_view failed: %s", exc)
        messages.error(request, "Unable to reset device right now.")
    return redirect("users:devices")


# ============================================================
# Auth hub
# ============================================================
def auth_hub_view(request):
    """Landing page for login/signup/social auth selection."""
    return render(request, "account/hub.html")


# ============================================================
# Tell Us About You – OAuth / profile onboarding
# ============================================================
@login_required
@require_http_methods(["GET", "POST"])
def tell_us_about_you(request: HttpRequest):
    """
    Onboarding view that runs after social signup (and optionally manual signup)
    to ensure the user has:
      • a unique username
      • a full name
      • a usable password (required for social accounts)
    """
    user = request.user

    if getattr(user, "profile_completed", False):
        return redirect("users:dashboard")

    if request.method == "POST":
        form = TellUsAboutYouForm(request.POST, user=user, request=request)
        if form.is_valid():
            cleaned = form.cleaned_data
            update_fields: list[str] = []

            if user.username != cleaned["username"]:
                user.username = cleaned["username"]
                update_fields.append("username")

            full_name = cleaned.get("full_name") or ""
            if getattr(user, "full_name", "") != full_name:
                user.full_name = full_name
                update_fields.append("full_name")

            password = cleaned.get("password1") or ""
            if password:
                user.set_password(password)
                update_fields.append("password")

            if hasattr(user, "signup_method") and not user.signup_method:
                user.signup_method = "social"
                update_fields.append("signup_method")

            if hasattr(user, "profile_completed") and not user.profile_completed:
                user.profile_completed = True
                update_fields.append("profile_completed")

            # Optional referral capture if not already set
            if hasattr(user, "referred_by") and not user.referred_by:
                ref_code = (cleaned.get("referral_code") or "").strip().upper()
                if ref_code:
                    try:
                        from apps.users.models import CustomUser  # local import

                        referrer = CustomUser.objects.filter(
                            referral_code__iexact=ref_code
                        ).first()
                        if referrer and referrer != user:
                            user.referred_by = referrer
                            update_fields.append("referred_by")
                    except Exception:
                        logger.debug("Failed to attach referral during onboarding", exc_info=True)

            if update_fields:
                user.save(update_fields=update_fields)

            if password:
                try:
                    update_session_auth_hash(request, user)
                except Exception:
                    pass

            try:
                messages.success(request, _("Your profile has been completed."))
            except Exception:
                pass

            return redirect("users:dashboard")
    else:
        initial: Dict[str, Any] = {
            "username": user.username or "",
            "full_name": getattr(user, "full_name", "") or "",
            "referral_code": (request.GET.get("ref") or "").strip().upper(),
        }
        form = TellUsAboutYouForm(user=user, request=request, initial=initial)

    return render(request, "users/tell_us_about_you.html", {"form": form})


# ============================================================
# Resend email verification
# ============================================================
@login_required
@require_POST
def resend_verification(request: HttpRequest) -> JsonResponse:
    from allauth.account.models import EmailAddress
    from allauth.account.utils import send_email_confirmation

    email = request.user.email
    try:
        email_obj = EmailAddress.objects.get(user=request.user, email=email)
        if email_obj.verified:
            return JsonResponse({"ok": False, "error": "already_verified"})
        send_email_confirmation(request, request.user, email=email)
        return JsonResponse({"ok": True})
    except EmailAddress.DoesNotExist:
        return JsonResponse({"ok": False, "error": "email_not_found"})
    except Exception as exc:
        logger.exception("resend_verification failed: %s", exc)
        return JsonResponse({"ok": False, "error": "server_error"}, status=500)


# ============================================================
# Change username
# ============================================================
USERNAME_RE = re.compile(r"^[a-zA-Z0-9._-]{3,32}$")


@login_required
@require_POST
def change_username(request: HttpRequest) -> JsonResponse:
    new_username = (request.POST.get("username") or "").strip()
    if not USERNAME_RE.match(new_username):
        return JsonResponse({"ok": False, "error": "invalid_username"}, status=400)

    User = get_user_model()
    if User.objects.filter(username__iexact=new_username).exists():
        return JsonResponse({"ok": False, "error": "taken"}, status=409)

    try:
        request.user.username = new_username
        request.user.save(update_fields=["username"])
        return JsonResponse({"ok": True})
    except Exception as exc:
        logger.exception("change_username failed: %s", exc)
        return JsonResponse({"ok": False, "error": "server_error"}, status=500)
