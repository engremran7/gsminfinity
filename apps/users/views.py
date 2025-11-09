"""
apps/users/views.py
-------------------
Enterprise-grade user management and authentication views for GSMInfinity.

✅ Features:
- Tenant-aware site settings resolver
- Integrated rate limiting & reCAPTCHA
- Device fingerprint enforcement via signals
- MFA / email verification guard
- Optimized dashboard queries
- Robust logging, atomic safety, and consistent UX
"""

import logging
from typing import Optional
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Q

from allauth.account.views import LoginView, SignupView
from allauth.account.forms import LoginForm, SignupForm

from apps.site_settings.models import SiteSettings, TenantSiteSettings
from apps.users.models import Notification, Announcement
from apps.users.utils.utils import get_device_fingerprint
from apps.users.utils.device import record_device_fingerprint, enforce_device_limit
from apps.users.services.recaptcha import verify_recaptcha
from apps.users.services.rate_limit import allow_action

logger = logging.getLogger(__name__)


# ============================================================
#  SAFE SITE SETTINGS RESOLVER
# ============================================================
def _get_settings(request=None):
    """
    Fetch tenant-specific or global SiteSettings safely.

    Order of precedence:
        1. TenantSiteSettings for current site
        2. Global SiteSettings singleton
        3. Dummy fallback (safe defaults)
    """
    try:
        if request:
            current_site = get_current_site(request)
            return TenantSiteSettings.objects.select_related("site").get(site=current_site)
        return SiteSettings.get_solo()
    except TenantSiteSettings.DoesNotExist:
        return SiteSettings.get_solo()
    except Exception as exc:
        logger.warning("Falling back to Dummy site settings → %s", exc)

        class Dummy:
            site_name = "GSMInfinity"
            enable_signup = True
            max_login_attempts = 5
            rate_limit_window_seconds = 300
            recaptcha_enabled = False
            enforce_unique_device = False
            max_devices_per_user = 3
            require_mfa = False
            enable_payments = True
            site_header = "GSM Admin"
            site_description = "Default site configuration"
            meta_tags = []
            verification_files = []

        return Dummy()


# ============================================================
#  LOGIN VIEW
# ============================================================
class EnterpriseLoginView(LoginView):
    """Enterprise login with rate limiting, reCAPTCHA, and MFA enforcement."""
    form_class = LoginForm
    template_name = "account/login.html"

    def form_valid(self, form):
        s = _get_settings(self.request)
        ip = (
            self.request.META.get("HTTP_X_FORWARDED_FOR")
            or self.request.META.get("REMOTE_ADDR")
            or "unknown"
        ).split(",")[0].strip()

        # ------------------- Rate Limiting -------------------
        rl_key = f"login:{ip}"
        try:
            if not allow_action(
                rl_key,
                int(getattr(s, "max_login_attempts", 5)),
                int(getattr(s, "rate_limit_window_seconds", 300)),
            ):
                form.add_error(None, "Too many login attempts. Please try again later.")
                logger.warning("Rate limit exceeded for IP=%s", ip)
                return self.form_invalid(form)
        except Exception as exc:
            logger.exception("Rate limiter failure (fail-open) → %s", exc)

        # ------------------- reCAPTCHA -------------------
        token = self.request.POST.get("g-recaptcha-response") or self.request.POST.get("recaptcha_token")
        if getattr(s, "recaptcha_enabled", False) and token:
            try:
                rc = verify_recaptcha(token, ip, action="login")
                if not rc.get("ok"):
                    form.add_error(None, "reCAPTCHA verification failed. Please try again.")
                    logger.info("reCAPTCHA failed for %s → %s", ip, rc)
                    return self.form_invalid(form)
            except Exception as exc:
                logger.exception("reCAPTCHA error → %s", exc)
                form.add_error(None, "reCAPTCHA service error. Try again later.")
                return self.form_invalid(form)

        # Proceed with default login flow
        response = super().form_valid(form)
        user = self.request.user

        # ------------------- Device Limit -------------------
        try:
            if getattr(s, "enforce_unique_device", False):
                if not enforce_device_limit(user):
                    form.add_error(None, "Device limit exceeded. Contact support.")
                    logger.warning("Device limit exceeded for user=%s", getattr(user, "email", user.pk))
                    return self.form_invalid(form)
        except Exception as exc:
            logger.exception("Device enforcement error → %s", exc)

        # ------------------- Fingerprint Recording -------------------
        try:
            fp = get_device_fingerprint(self.request)
            if fp:
                try:
                    record_device_fingerprint(self.request, user, {"fingerprint_hash": fp})
                except PermissionError:
                    form.add_error(None, "This device cannot be registered. Contact support.")
                    logger.warning("Device blocked for user=%s", getattr(user, "email", user.pk))
                    return self.form_invalid(form)
                except Exception as exc:
                    logger.debug("Fingerprint record failure for %s → %s", user, exc)
        except Exception as exc:
            logger.debug("Fingerprint extraction failed → %s", exc)

        # ------------------- MFA Enforcement -------------------
        try:
            if getattr(s, "require_mfa", False) and not getattr(user, "email_verified_at", None):
                logger.info("Redirecting %s to MFA verification", getattr(user, "email", user.pk))
                return redirect("users:verify_email")
        except Exception as exc:
            logger.exception("MFA check failed → %s", exc)

        return response


# ============================================================
#  SIGNUP VIEW
# ============================================================
class EnterpriseSignupView(SignupView):
    """Tenant-aware signup view with optional reCAPTCHA verification."""
    form_class = SignupForm
    template_name = "account/signup.html"

    def form_valid(self, form):
        s = _get_settings(self.request)

        if not getattr(s, "enable_signup", True):
            form.add_error(None, "Signup is currently disabled.")
            logger.info("Signup attempt blocked by settings.")
            return self.form_invalid(form)

        token = self.request.POST.get("g-recaptcha-response") or self.request.POST.get("recaptcha_token")
        if getattr(s, "recaptcha_enabled", False) and token:
            try:
                rc = verify_recaptcha(token, self.request.META.get("REMOTE_ADDR"), action="signup")
                if not rc.get("ok"):
                    form.add_error(None, "reCAPTCHA failed. Please retry.")
                    logger.info("reCAPTCHA failed during signup → %s", rc)
                    return self.form_invalid(form)
            except Exception as exc:
                logger.exception("reCAPTCHA error → %s", exc)
                form.add_error(None, "reCAPTCHA error. Please try again.")
                return self.form_invalid(form)

        return super().form_valid(form)


# ============================================================
#  EMAIL VERIFICATION
# ============================================================
@login_required
def verify_email_view(request):
    """Manual verification for MFA / email confirmation."""
    rl_key = f"verify_email:{request.user.pk}"
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
#  DASHBOARD VIEW
# ============================================================
@login_required
def dashboard_view(request):
    """Render user dashboard with recent announcements and notifications."""
    s = _get_settings(request)
    now = timezone.now()

    announcements = (
        Announcement.objects.filter(start_at__lte=now)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .only("title", "content", "start_at", "expires_at")
        .order_by("-start_at")
    )

    notifications = (
        Notification.objects.filter(recipient=request.user)
        .select_related("recipient")
        .only("title", "message", "created_at")
        .order_by("-created_at")[:5]
    )

    context = {
        "site_settings": s,
        "announcements": announcements,
        "notifications": notifications,
        "credits": getattr(request.user, "credits", 0),
        "can_watch_ad": getattr(s, "recaptcha_enabled", False),
        "can_pay": getattr(s, "enable_payments", True),
    }
    return render(request, "users/dashboard.html", context)


# ============================================================
#  PROFILE VIEW
# ============================================================
@login_required
def profile_view(request):
    """Render user profile overview page."""
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
#  AUTH HUB
# ============================================================
def auth_hub_view(request):
    """Landing page for login/signup/social auth selection."""
    return render(request, "account/hub.html")
