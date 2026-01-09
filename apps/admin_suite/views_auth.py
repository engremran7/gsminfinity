from __future__ import annotations

import secrets

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.core.mail import send_mail
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from apps.users import models as user_models
from apps.users.models import SecurityQuestion

from .views_shared import STAFF_ONLY, _make_breadcrumb, _render_admin

# Extracted views_auth views from legacy views.py


class AdminSuiteLoginView(LoginView):
    """
    Custom login view for Admin Suite with staff enforcement, throttling,
    and graceful redirect for non-staff users.
    """

    template_name = "admin_suite/login.html"
    redirect_authenticated_user = True
    success_url = reverse_lazy("admin_suite:admin_suite")
    throttle_limit = 10
    throttle_window = 120  # seconds

    def _attempt_key(self) -> str:
        ip = self.request.META.get("REMOTE_ADDR", "")
        username = (self.request.POST.get("username") or "").strip().lower()
        return f"admin_login_attempts_{ip}_{username}"

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        # If already authenticated but not staff, log out and force fresh login instead of redirecting to user dashboard.
        if request.user.is_authenticated and not getattr(
            request.user, "is_staff", False
        ):
            messages.warning(
                request,
                "Admin access requires a staff account. Please sign in with a staff user.",
                extra_tags="admin_only",
            )
            try:
                logout(request)
            except Exception:
                pass
        # Simple throttle per IP/user
        cache_key = self._attempt_key()
        attempts = cache.get(cache_key, 0)
        if attempts >= self.throttle_limit:
            messages.error(
                request, "Too many login attempts. Please wait and try again."
            )
            return self.form_invalid(self.get_form())
        resp = super().dispatch(request, *args, **kwargs)
        return resp

    def form_valid(self, form):
        user = self.request.user
        if not getattr(user, "is_staff", False):
            messages.warning(
                self.request,
                "You are signed in, but admin access requires staff privileges.",
                extra_tags="admin_only",
            )
        cache_key = self._attempt_key()
        cache.delete(cache_key)
        return super().form_valid(form)

    def form_invalid(self, form):
        cache_key = self._attempt_key()
        attempts = cache.get(cache_key, 0) + 1
        cache.set(cache_key, attempts, self.throttle_window)
        return super().form_invalid(form)

    def get_success_url(self):
        user = getattr(self.request, "user", None)
        if user and getattr(user, "is_staff", False):
            # Optionally shorten session for admin area
            try:
                self.request.session.set_expiry(
                    getattr(settings, "ADMIN_SESSION_AGE", 3600)
                )
            except Exception:
                pass
            # Force security question setup on first staff login
            try:
                if not hasattr(user, "security_question"):
                    return reverse("admin_suite:admin_suite_security_question_setup")
            except Exception:
                pass
            return reverse("admin_suite:admin_suite")
        # Fallback: always stay on admin login for non-staff
        return reverse("admin_suite:admin_suite_login")


@ensure_csrf_cookie
@csrf_protect
def admin_suite_security_question(request: HttpRequest) -> HttpResponse:
    """
    Security-question-based recovery for admin accounts with fallback to email code.
    """
    # Always treat this flow as unauthenticated recovery to avoid redirect loops
    if request.user.is_authenticated:
        try:
            # Drop the session first to rotate the session key and clear auth
            if hasattr(request, "session"):
                request.session.flush()
            logout(request)
            # Ensure the request.user is now anonymous for the remainder of this request
            from django.contrib.auth.models import AnonymousUser

            request.user = AnonymousUser()
        except Exception:
            pass

    identifier = (
        request.POST.get("identifier") or request.GET.get("identifier") or ""
    ).strip()
    user_obj = None
    sq = None
    User = get_user_model()
    if identifier:
        try:
            user_obj = User.objects.filter(
                models.Q(email__iexact=identifier)
                | models.Q(username__iexact=identifier)
            ).first()
            if user_obj:
                sq = getattr(user_obj, "security_question", None)
                if sq and not sq.is_active:
                    sq = None
        except Exception:
            user_obj = None
            sq = None

    message = ""
    success = False
    max_attempts = 3
    attempts = 0
    fallback_ready = False

    def _attempt_key(uid):
        return f"admin_pw_attempts_{uid or identifier}"

    def _code_key(uid):
        return f"admin_pw_code_{uid or identifier}"

    # Handle actions
    action = request.POST.get("action", "lookup" if request.method == "POST" else "")
    # Baseline attempts and fallback readiness based on state
    if user_obj:
        attempts = cache.get(_attempt_key(user_obj.id), 0)
        if attempts >= max_attempts:
            fallback_ready = True
        # If no security question configured, allow email fallback immediately
        if not sq:
            fallback_ready = True

    if request.method == "POST" and action == "answer":
        if fallback_ready:
            message = "Security question locked. Use the email verification code."
        else:
            answer = (request.POST.get("answer") or "").strip()
            if not user_obj or not sq:
                message = "No security question is configured. Use email reset."
            else:
                if attempts >= max_attempts:
                    fallback_ready = True
                    message = "Too many attempts. Use the email code fallback."
                else:
                    if sq.check_answer(answer):
                        request.session["admin_pw_reset_user"] = str(user_obj.id)
                        return redirect("admin_suite:admin_suite_password_reset")
                    attempts += 1
                    cache.set(_attempt_key(user_obj.id), attempts, 600)
                    if attempts >= max_attempts:
                        fallback_ready = True
                        message = "Too many attempts. Use the email code fallback."
                    else:
                        message = "Incorrect answer. Please try again."

    elif request.method == "POST" and action == "send_code":
        if not user_obj:
            message = "Enter a valid email or username first."
        elif not fallback_ready:
            message = "Please answer your security question first."
        else:
            code = secrets.token_hex(3)
            cache.set(_code_key(user_obj.id), code, 600)
            try:
                send_mail(
                    subject="Admin password recovery code",
                    message=f"Use this code to reset your admin password: {code}",
                    from_email=None,
                    recipient_list=[user_obj.email],
                    fail_silently=True,
                )
                message = "Verification code sent to your email."
            except Exception:
                message = "Could not send email. Try again later."
            fallback_ready = True

    elif request.method == "POST" and action == "verify_code":
        code = (request.POST.get("code") or "").strip()
        if not user_obj:
            message = "Enter a valid email or username first."
        elif not fallback_ready:
            message = "Please answer your security question first."
        else:
            cached = cache.get(_code_key(user_obj.id))
            if cached and cached == code:
                request.session["admin_pw_reset_user"] = str(user_obj.id)
                cache.delete(_code_key(user_obj.id))
                return redirect("admin_suite:admin_suite_password_reset")
            else:
                message = "Invalid or expired code."
        fallback_ready = True

    # If user submitted lookup with a valid identifier and no SQ, unlock fallback
    if request.method == "POST" and action == "lookup" and user_obj and not sq:
        fallback_ready = True

    return render(
        request,
        "admin_suite/security_question.html",
        {
            "identifier": identifier,
            "user_obj": user_obj,
            "sq": sq,
            "message": message,
            "success": success,
            "fallback_ready": fallback_ready,
            "max_attempts": max_attempts,
        },
    )


@STAFF_ONLY
@csrf_protect
def admin_suite_security_question_setup(request: HttpRequest) -> HttpResponse:
    """
    Staff-only setup of security question/answer (enforced on first admin login).
    """
    user = request.user
    existing = getattr(user, "security_question", None)
    message = ""

    class SQForm(forms.Form):
        question_key = forms.ChoiceField(
            choices=SecurityQuestion.QUESTION_CHOICES,
            initial="first_pet",
        )
        custom_question = forms.CharField(required=False, max_length=255)
        answer = forms.CharField(widget=forms.PasswordInput, max_length=255)
        confirm = forms.CharField(widget=forms.PasswordInput, max_length=255)

        def clean(self):
            data = super().clean()
            if data.get("answer") != data.get("confirm"):
                raise forms.ValidationError("Answers do not match.")
            if data.get("question_key") == "custom" and not data.get("custom_question"):
                raise forms.ValidationError("Custom question text is required.")
            return data

    if request.method == "POST":
        form = SQForm(request.POST)
        if form.is_valid():
            qkey = form.cleaned_data["question_key"]
            ctext = form.cleaned_data["custom_question"] if qkey == "custom" else ""
            ans = form.cleaned_data["answer"]
            sq = existing or SecurityQuestion(user=user)
            sq.question_key = qkey
            sq.custom_question = ctext
            sq.set_answer(ans)
            sq.is_active = True
            sq.save()
            message = "Security question saved."
            return redirect("admin_suite:admin_suite")
    else:
        initial = {}
        if existing:
            initial = {
                "question_key": existing.question_key,
                "custom_question": existing.custom_question,
            }
        form = SQForm(initial=initial)

    return _render_admin(
        request,
        "admin_suite/security_question_setup.html",
        {"form": form, "message": message, "existing": existing},
        nav_active="settings",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"), ("Security Question", None)
        ),
        subtitle="Set a recovery question for admin password reset",
    )


@csrf_protect
def admin_suite_password_reset(request: HttpRequest) -> HttpResponse:
    """
    Final step: after security question or email code verification, allow password reset.
    """
    uid = request.session.get("admin_pw_reset_user")
    if not uid:
        return redirect("admin_suite:admin_suite_security_question")

    User = get_user_model()
    try:
        user = User.objects.get(pk=uid)
    except User.DoesNotExist:
        user = None

    if not user:
        request.session.pop("admin_pw_reset_user", None)
        return redirect("admin_suite:admin_suite_security_question")

    if request.method == "POST":
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            request.session.pop("admin_pw_reset_user", None)
            return redirect("admin_suite:admin_suite_login")
    else:
        form = SetPasswordForm(user)

    return render(
        request,
        "admin_suite/password_reset_inline.html",
        {"form": form},
    )


__all__ = [
    "AdminSuiteLoginView",
    "admin_suite_security_question",
    "admin_suite_security_question_setup",
    "admin_suite_password_reset",
]
