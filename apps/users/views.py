
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
from apps.devices.services import make_device_token, load_device_token, mark_device_trusted
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
from django.views.decorators.csrf import csrf_protect

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


@login_required
@csrf_protect
def devices_view(request: HttpRequest) -> HttpResponse:
    """
    List and manage the current user's devices (trust/untrust/delete).
    """
    devices = []
    message = ""
    error = ""
    pending_device = None
    try:
        from apps.devices.models import Device
    except Exception:
        Device = None

    if Device is None:
        error = "Device management is unavailable."
    else:
        if request.method == "POST":
            action = request.POST.get("action") or ""
            device_id = request.POST.get("device_id") or ""
            try:
                device = Device.objects.filter(user=request.user, id=device_id).first()
                if not device:
                    error = "Device not found."
                else:
                    if action == "trust":
                        device.is_trusted = True
                        device.save(update_fields=["is_trusted"])
                        message = "Device trusted."
                    elif action == "untrust":
                        device.is_trusted = False
                        device.save(update_fields=["is_trusted"])
                        message = "Device untrusted."
                    elif action == "delete":
                        device.delete()
                        message = "Device removed."
            except Exception as exc:
                error = f"Action failed: {exc}"

        try:
            devices = list(
                Device.objects.filter(user=request.user)
                .order_by("-last_seen_at")
                .values(
                    "id",
                    "machine_uuid",
                    "display_name",
                    "browser_family",
                    "os_family",
                    "is_trusted",
                    "is_blocked",
                    "risk_score",
                    "last_seen_at",
                    "first_seen_at",
                )
            )
        except Exception as exc:
            error = f"Could not load devices: {exc}"

        # Surface any pending device approval token so the user can complete registration/trust
        try:
            token = request.session.get("pending_device_token")
            reason = request.session.get("pending_device_reason", "")
            if token:
                pending_device = {
                    "token": token,
                    "reason": reason,
                    "approval_url": reverse("users:approve_device") + f"?t={token}",
                }
        except Exception:
            pending_device = None

    return render(
        request,
        "users/devices.html",
        {"devices": devices, "message": message, "error": error, "pending_device": pending_device},
    )


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
        enforcement_ctx = None

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
                    reason = (ctx or {}).get("reason") if isinstance(ctx, dict) else ""
                    device_obj = (ctx or {}).get("device")
                    approval_token = None
                    try:
                        if device_obj:
                            approval_token = make_device_token(self.request.user.id, device_obj.id, reason or "untrusted_new_device")
                            self.request.session["pending_device_token"] = approval_token
                            self.request.session["pending_device_reason"] = reason
                    except Exception:
                        approval_token = None
                    if reason == "blocked_device":
                        msg = "This device is blocked. Contact support to unblock."
                    elif reason == "untrusted_new_device":
                        msg = "New device detected and not trusted. Approve it from a trusted session to continue."
                    elif reason == "mfa_required":
                        msg = "New device requires MFA. Complete multi-factor authentication to continue."
                    elif reason == "mfa_required_risk":
                        msg = "This device was flagged as high risk. Complete MFA to continue or trust it from a known device."
                    elif reason == "monthly_device_quota":
                        msg = "Monthly device limit reached. Remove an old device or wait until next month."
                    elif reason == "yearly_device_quota":
                        msg = "Yearly device limit reached. Remove an old device or wait until next year."
                    elif reason == "user_window_quota":
                        msg = "Device enrollment window exceeded. Remove an old device or contact support."
                    elif reason == "device_quota_exceeded" or reason == "limit_reached":
                        msg = "Maximum devices reached. Remove an old device before signing in from a new one."
                    else:
                        msg = "This device is not allowed to sign in. Contact support."
                    if approval_token and reason in {"untrusted_new_device", "mfa_required", "mfa_required_risk"}:
                        messages.error(self.request, msg)
                        return redirect("users:device_approval_needed")
                    if reason in {"device_quota_exceeded", "limit_reached", "user_window_quota", "monthly_device_quota", "yearly_device_quota"}:
                        messages.error(self.request, msg)
                        return redirect("users:device_eviction")
                    form.add_error(None, msg)
                    return self.form_invalid(form)
                enforcement_ctx = ctx or {}
                setattr(self.request, "device", enforcement_ctx.get("device"))
            else:
                # Fallback: register device even if AppService is disabled
                try:
                    from apps.devices.services import resolve_or_create_device

                    device, is_new, ctx = resolve_or_create_device(self.request, self.request.user, service_name="login")
                    enforcement_ctx = ctx or {}
                    setattr(self.request, "device", device)
                    if is_new:
                        messages.info(
                            self.request,
                            "New device detected. Trust it from your account to avoid future prompts.",
                        )
                except Exception:
                    logger.debug("Device registration fallback skipped", exc_info=True)
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

        # --- Friendly prompt to trust new devices ---
        try:
            if enforcement_ctx:
                device = enforcement_ctx.get("device")
                is_new = bool(enforcement_ctx.get("is_new"))
                if device and (is_new or not getattr(device, "is_trusted", False)):
                    # Generate an approval token even when strict mode is off, so the user can trust immediately.
                    try:
                        approval_token = make_device_token(
                            self.request.user.id,
                            getattr(device, "id", None),
                            "new_device",
                        )
                        self.request.session["pending_device_token"] = approval_token
                        self.request.session["pending_device_reason"] = "new_device"
                    except Exception:
                        pass
                    messages.info(
                        self.request,
                        "New device detected. Trust it from your account to avoid future prompts.",
                    )
        except Exception:
            logger.debug("Trust reminder skipped", exc_info=True)

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
    # If already verified, skip the page and continue to dashboard
    if getattr(user, "email_verified_at", None):
        return redirect("users:dashboard")

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


@login_required
@require_http_methods(["GET"])
def verify_email_status(request: HttpRequest) -> JsonResponse:
    """
    Lightweight status endpoint so the client can auto-redirect once
    verification is completed elsewhere (e.g., staff/admin update).
    """
    verified = bool(getattr(request.user, "email_verified_at", None))
    return JsonResponse(
        {
            "verified": verified,
            "redirect": reverse("users:dashboard") if verified else None,
        }
    )


# ============================================================
# Device approval / eviction helpers
# ============================================================
def _get_pending_device_token(request) -> Optional[str]:
    return request.session.get("pending_device_token")


def device_approval_needed(request: HttpRequest) -> HttpResponse:
    token = _get_pending_device_token(request)
    reason = request.session.get("pending_device_reason", "")
    approval_url = reverse("users:approve_device")
    if token:
        approval_url = f"{approval_url}?t={token}"
    return render(
        request,
        "users/device_approval_needed.html",
        {"token": token, "reason": reason, "approval_url": approval_url},
    )


@login_required
def approve_device(request: HttpRequest) -> HttpResponse:
    token = request.GET.get("t") or _get_pending_device_token(request)
    if not token:
        messages.error(request, "No approval token found.")
        return redirect("users:dashboard")
    data = load_device_token(token)
    if not data:
        messages.error(request, "Approval link is invalid or expired.")
        return redirect("users:dashboard")
    if str(request.user.id) != str(data.get("u")):
        messages.error(request, "This approval link belongs to another account.")
        return redirect("users:dashboard")
    device_id = data.get("d")
    try:
        ok = mark_device_trusted(device_id, request.user.id)
        if not ok:
            messages.error(request, "Device not found.")
            return redirect("users:dashboard")
        messages.success(request, "Device approved and trusted. You can sign in from it now.")
        request.session.pop("pending_device_token", None)
        request.session.pop("pending_device_reason", None)
    except Exception:
        messages.error(request, "Could not approve device. Try again.")
    return redirect("users:devices")


@login_required
@require_http_methods(["GET", "POST"])
def device_eviction(request: HttpRequest) -> HttpResponse:
    """
    Allow users to evict old devices when quota is hit.
    """
    message = ""
    error = ""
    devices = []
    try:
        from apps.devices.models import Device

        if request.method == "POST":
            device_id = request.POST.get("device_id")
            if device_id:
                removed = Device.objects.filter(user=request.user, id=device_id).delete()[0]
                if removed:
                    message = "Device removed. You can now retry from your new device."
                else:
                    error = "Device not found."
        devices = list(
            Device.objects.filter(user=request.user)
            .order_by("last_seen_at")
            .values("id", "display_name", "machine_uuid", "last_seen_at", "is_trusted", "is_blocked")
        )
    except Exception as exc:
        error = f"Could not load devices: {exc}"

    return render(
        request,
        "users/device_eviction.html",
        {"devices": devices, "message": message, "error": error},
    )


@login_required
@require_http_methods(["GET", "POST"])
def device_mfa_challenge(request: HttpRequest) -> HttpResponse:
    """
    Placeholder MFA challenge: accept any non-empty code for demo;
    replace with real MFA verification as needed.
    """
    token = request.GET.get("t") or _get_pending_device_token(request)
    if not token:
        messages.error(request, "No MFA challenge pending.")
        return redirect("users:dashboard")
    data = load_device_token(token)
    if not data or str(request.user.id) != str(data.get("u")):
        messages.error(request, "This challenge link is invalid or expired.")
        return redirect("users:dashboard")
    if request.method == "POST":
        code = (request.POST.get("code") or "").strip()
        if not code:
            messages.error(request, "Enter the code to continue.")
        else:
            # TODO: integrate real MFA validation
            if mark_device_trusted(data.get("d"), request.user.id):
                messages.success(request, "MFA passed. Device trusted.")
                request.session.pop("pending_device_token", None)
                request.session.pop("pending_device_reason", None)
                return redirect("users:dashboard")
            messages.error(request, "Could not trust device. Try again.")
    return render(
        request,
        "users/device_mfa_challenge.html",
    )


# ============================================================
# Dashboard view
# ============================================================
@login_required(login_url="account_login")
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

    # Resolve current device (best effort) for trust reminder
    current_device = None
    try:
        from apps.devices.services import resolve_identity
        from apps.devices.models import Device

        ident = resolve_identity(request, user=request.user, service_name="login")
        candidate_id = ident.get("machine_uuid") or ident.get("server_fallback_fp")
        if candidate_id:
            current_device = (
                Device.objects.filter(user=request.user, machine_uuid=candidate_id)
                .values("id", "is_trusted", "is_blocked", "display_name", "last_seen_at")
                .first()
            )
    except Exception:
        current_device = None

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
        "current_device": current_device,
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
