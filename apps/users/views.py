
"""
apps.users.views
Enterprise-grade user management and authentication views for GSMInfinity.

✅ Highlights
-------------
• Tenant-aware SiteSettings resolver (uses site_settings.views._get_settings when available)
• Integrated rate limiting + reCAPTCHA verification
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
from apps.users.models import Announcement, Notification
from apps.users.services.rate_limit import allow_action
from apps.users.services.recaptcha import verify_recaptcha
from apps.core.app_service import AppService
from apps.core.utils.ip import get_client_ip
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.core.validators import RegexValidator
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
    }
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
        from apps.users.models import UsersSettings
        from apps.site_settings.models import SiteSettings

        us = UsersSettings.get_solo()
        ss = SiteSettings.get_solo()
        return {
            "site_name": "GSMInfinity",
            "enable_signup": bool(getattr(us, "enable_signup", True)),
            "max_login_attempts": int(getattr(us, "max_login_attempts", 5) or 5),
            "rate_limit_window_seconds": int(
                getattr(us, "rate_limit_window_seconds", 300) or 300
            ),
            # reCAPTCHA now comes from SiteSettings
            "recaptcha_enabled": bool(getattr(ss, "recaptcha_enabled", False)),
            "recaptcha_mode": getattr(ss, "recaptcha_mode", "v2"),
            "recaptcha_score_threshold": float(
                getattr(ss, "recaptcha_score_threshold", 0.5)
            ),
            "recaptcha_timeout_ms": int(getattr(ss, "recaptcha_timeout_ms", 3000)),
            "require_mfa": bool(getattr(us, "require_mfa", False)),
            "enable_payments": bool(getattr(us, "enable_payments", True)),
            "required_profile_fields": list(
                getattr(us, "required_profile_fields", []) or []
            ),
        }
    except Exception:
        logger.debug("UsersSettings fallback defaults in use", exc_info=True)
        return {
            "site_name": "GSMInfinity",
            "enable_signup": True,
            "max_login_attempts": 5,
            "rate_limit_window_seconds": 300,
            "recaptcha_enabled": False,
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
            "required_profile_fields": ["full_name", "username", "email"],
        }


# ============================================================
# Enterprise Login View
# ============================================================
class EnterpriseLoginView(LoginView):
    """
    Enterprise login with:
    - IP-based rate limiting
    - reCAPTCHA verification
    - Optional MFA redirect
    """

    form_class = LoginForm
    template_name = "account/login.html"

    def form_valid(self, form):
        settings_obj = _get_settings(self.request)
        ip = get_client_ip(self.request) or "unknown"

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
                    logger.info("reCAPTCHA failed for %s : %s", ip, rc_result)
                    return self.form_invalid(form)
            except Exception:
                logger.exception("reCAPTCHA error (fail-open)", exc_info=True)
                form.add_error(None, "reCAPTCHA service error. Try again later.")
                return self.form_invalid(form)

        response = super().form_valid(form)

        # --- Device policy enforcement (if devices app is enabled) ---
        try:
            devices_api = AppService.get("devices")
            if devices_api and hasattr(devices_api, "enforce_device_policy_for_login"):
                allowed, ctx = devices_api.enforce_device_policy_for_login(self.request, self.request.user)
                if not allowed:
                    form.add_error(None, "This device is not allowed to sign in. Contact support.")
                    return self.form_invalid(form)
                setattr(self.request, "device", (ctx or {}).get("device"))
        except Exception:
            logger.debug("Device policy enforcement skipped", exc_info=True)

        # --- Session fixation protection ---
        try:
            if hasattr(self.request, "session"):
                self.request.session.cycle_key()
                self.request.session.set_expiry(1209600)
        except Exception:
            logger.exception("Failed to rotate session after login")

        user = self.request.user

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
            # Notify user (best-effort)
            try:
                from apps.users.services.notifications import send_notification

                send_notification(
                    recipient=user,
                    title="Email verified",
                    message="Your email address has been verified successfully.",
                    level="info",
                )
            except Exception:
                logger.debug("verify_email notification skipped", exc_info=True)
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

    def _display_name(u):
        try:
            full = (getattr(u, "full_name", "") or "").strip()
            if full:
                return full
            username = (getattr(u, "username", "") or "").strip()
            if username:
                return username
            email = (getattr(u, "email", "") or "").strip()
            if email and "@" in email:
                return email.split("@", 1)[0]
        except Exception:
            pass
        return "user"

    def _missing_profile_fields(u):
        field_labels = {
            "full_name": "Full name",
            "username": "Username",
            "email": "Email",
            "country": "Country",
            "city": "City",
            "phone": "Phone number",
            "date_of_birth": "Date of birth",
        }
        required = s.get("required_profile_fields") or ["full_name", "username", "email"]
        missing: list[str] = []
        for field in required:
            label = field_labels.get(field, field.replace("_", " ").title())
            try:
                val = getattr(u, field, None)
                if not (val and str(val).strip()):
                    missing.append(label)
            except Exception:
                missing.append(label)
        return missing

    context = {
        "site_settings": s,
        "announcements": announcements,
        "notifications": notifications,
        "display_name": _display_name(request.user),
        "profile_missing_fields": _missing_profile_fields(request.user),
        "credits": getattr(request.user, "credits", 0),
        "can_watch_ad": bool(s.get("recaptcha_enabled", False)),
        "can_pay": bool(s.get("enable_payments", True)),
    }
    return render(request, "users/dashboard.html", context)


# ============================================================
# Profile view
# ============================================================
@login_required
def profile_view(request):
    """Render the user profile overview page with inline updates."""
    s = _get_settings(request)
    user = request.user

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "update_full_name":
            full_name = (request.POST.get("full_name") or "").strip()
            user.full_name = full_name
            user.save(update_fields=["full_name"])
            messages.success(request, _("Full name updated."))

    return render(
        request,
        "users/profile.html",
        {
            "user": user,
            "credits": getattr(user, "credits", 0),
            "site_settings": s,
        },
    )


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


USERNAME_RE = re.compile(r"^[a-zA-Z0-9._-]{3,32}$")


@login_required
@require_POST
def change_username(request: HttpRequest) -> JsonResponse:
    new_username = (request.POST.get("username") or "").strip()
    if not USERNAME_RE.match(new_username):
        return JsonResponse({"ok": False, "error": "invalid_username"}, status=400)

    User = get_user_model()
    # Allow current username
    if new_username.lower() != (request.user.username or "").lower() and User.objects.filter(username__iexact=new_username).exists():
        return JsonResponse({"ok": False, "error": "taken"}, status=409)

    # Enforce change limits: max 2 per calendar year
    now = timezone.now()
    user = request.user
    if user.username_last_changed_at and user.username_last_changed_at.year == now.year:
        if (user.username_changes_this_year or 0) >= 2:
            return JsonResponse({"ok": False, "error": "limit_reached"}, status=429)

    try:
        user.username = new_username
        # Reset counters if new year
        if not user.username_last_changed_at or user.username_last_changed_at.year != now.year:
            user.username_changes_this_year = 1
        else:
            user.username_changes_this_year = (user.username_changes_this_year or 0) + 1
        user.username_last_changed_at = now
        user.save(update_fields=["username", "username_changes_this_year", "username_last_changed_at"])
        return JsonResponse({"ok": True})
    except Exception as exc:
        logger.exception("change_username failed: %s", exc)
        return JsonResponse({"ok": False, "error": "server_error"}, status=500)


@login_required
@require_POST
def check_username(request: HttpRequest) -> JsonResponse:
    new_username = (request.POST.get("username") or "").strip()
    if not USERNAME_RE.match(new_username):
        return JsonResponse({"ok": False, "error": "invalid"}, status=400)
    User = get_user_model()
    # Allow current username
    if new_username.lower() == (request.user.username or "").lower():
        return JsonResponse({"ok": True, "same": True})
    if User.objects.filter(username__iexact=new_username).exists():
        return JsonResponse({"ok": False, "error": "taken"}, status=409)
    # Pre-calculate if limit reached
    now = timezone.now()
    user = request.user
    limit_reached = False
    if user.username_last_changed_at and user.username_last_changed_at.year == now.year:
        limit_reached = (user.username_changes_this_year or 0) >= 2
    return JsonResponse({"ok": True, "limit_reached": limit_reached})
