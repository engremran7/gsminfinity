from __future__ import annotations

from .views_shared import *
from .views_shared import _make_breadcrumb, _render_admin


# Extracted views_users views from legacy views.py
@staff_member_required
def admin_suite_users(request: HttpRequest) -> HttpResponse:
    """Users overview for the admin suite (read-only metrics + paginated list)."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    stats = {
        "total_users": 0,
        "staff_users": 0,
        "active_users": 0,
        "local_users": 0,
        "social_users": 0,
    }
    users_page: list[Dict[str, Any]] = []
    page = 1
    page_size = 25
    query = (request.GET.get("q") or "").strip()
    provider_filter = (request.GET.get("provider") or "all").lower()
    if provider_filter not in {"all", "local", "social"}:
        provider_filter = "all"
    message = ""
    try:
        page = max(1, int(request.GET.get("page", "1")))
        page_size = max(1, min(100, int(request.GET.get("page_size", "25"))))
    except Exception:
        page = 1
        page_size = 25

    if request.method == "POST" and request.POST.get("action") == "create_user":
        email = (request.POST.get("email") or "").strip().lower()
        password = request.POST.get("password") or ""
        make_staff = bool(request.POST.get("is_staff"))
        if not email or len(password) < 10:
            message = "Email and password (min 10 chars) required."
        else:
            try:
                from apps.users.models import CustomUser

                user = CustomUser.objects.create_user(email=email, password=password)
                if make_staff and getattr(request.user, "is_superuser", False):
                    user.is_staff = True
                    user.save(update_fields=["is_staff"])
                elif make_staff:
                    message = "Staff flag requires superuser."
                message = "User created."
            except Exception as exc:
                message = f"Create failed: {exc}"

    try:
        from django.db.models import BooleanField, Exists, OuterRef, Q, Value

        from apps.users.models import CustomUser

        stats["total_users"] = CustomUser.objects.count()
        stats["staff_users"] = CustomUser.objects.filter(is_staff=True).count()
        stats["active_users"] = CustomUser.objects.filter(is_active=True).count()

        offset = (page - 1) * page_size
        qs = CustomUser.objects.only(
            "id", "email", "last_login", "date_joined", "is_staff", "is_active"
        ).order_by("-date_joined")

        try:
            from allauth.socialaccount.models import SocialAccount

            qs = qs.annotate(
                has_social=Exists(SocialAccount.objects.filter(user_id=OuterRef("id")))
            )
        except Exception:
            SocialAccount = None  # type: ignore
            qs = qs.annotate(has_social=Value(False, output_field=BooleanField()))

        if provider_filter == "local":
            qs = qs.filter(has_social=False)
        elif provider_filter == "social":
            qs = qs.filter(has_social=True)

        if query:
            qs = qs.filter(Q(email__icontains=query) | Q(id__icontains=query))

        # CSV export (lightweight, capped to 5000 rows)
        if request.GET.get("export") == "csv":
            try:
                throttle_key = f"admin_users_export_{getattr(request.user, 'id', 'anon')}_{request.META.get('REMOTE_ADDR', '')}"
                if cache.get(throttle_key):
                    return HttpResponse("rate_limited", status=429)
                cache.set(throttle_key, True, timeout=10)
            except Exception:
                pass
            export_qs = qs[:5000]
            rows = list(
                export_qs.values(
                    "id",
                    "email",
                    "last_login",
                    "date_joined",
                    "is_staff",
                    "is_active",
                    "has_social",
                )
            )
            providers_map: Dict[int, list[str]] = {}
            if rows and "SocialAccount" in locals() and SocialAccount:
                user_ids = [u["id"] for u in rows]
                for row in SocialAccount.objects.filter(user_id__in=user_ids).values(
                    "user_id", "provider"
                ):
                    providers_map.setdefault(row["user_id"], []).append(row["provider"])

            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="users.csv"'
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(
                [
                    "id",
                    "email",
                    "providers",
                    "is_staff",
                    "is_active",
                    "date_joined",
                    "last_login",
                ]
            )
            for u in rows:
                providers = providers_map.get(u["id"], []) if providers_map else []
                writer.writerow(
                    [
                        u["id"],
                        u["email"],
                        ",".join(providers)
                        if providers
                        else ("social" if u["has_social"] else "local"),
                        u["is_staff"],
                        u["is_active"],
                        u["date_joined"],
                        u["last_login"],
                    ]
                )
            response.write(buf.getvalue())
            return response

        raw_users = list(
            qs[offset : offset + page_size].values(
                "id",
                "email",
                "last_login",
                "date_joined",
                "is_staff",
                "is_active",
                "has_social",
            )
        )

        providers_map: Dict[int, list[str]] = {}
        if raw_users and "SocialAccount" in locals() and SocialAccount:
            user_ids = [u["id"] for u in raw_users]
            for row in SocialAccount.objects.filter(user_id__in=user_ids).values(
                "user_id", "provider"
            ):
                providers_map.setdefault(row["user_id"], []).append(row["provider"])

        # high-level counts for current filtered population (approx on page slice)
        stats["local_users"] = len([u for u in raw_users if not u.get("has_social")])
        stats["social_users"] = len([u for u in raw_users if u.get("has_social")])

        for u in raw_users:
            u["providers"] = providers_map.get(u["id"], []) if providers_map else []
            users_page.append(u)
    except Exception as exc:
        logger.warning("Admin suite users snapshot failed: %s", exc)

    return _render_admin(
        request,
        "admin_suite/users.html",
        {
            "stats": stats,
            "users_page": users_page,
            "page": page,
            "page_size": page_size,
            "q": query,
            "provider_filter": provider_filter,
            "message": message,
        },
        nav_active="users",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"), ("Users", None)
        ),
        subtitle="Staff and user activity overview",
    )


@staff_member_required
def admin_suite_user_detail(request: HttpRequest, user_id: str) -> HttpResponse:
    """User detail view with devices and risk insights."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    from apps.users.services.admin_profile import get_user_profile

    profile = get_user_profile(user_id)
    user_obj = profile.get("user")
    if not user_obj:
        raise Http404("User not found")

    message = ""

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action in {"toggle_staff", "toggle_active"}:
                field = "is_staff" if action == "toggle_staff" else "is_active"
                current = bool(getattr(user_obj, field))
                setattr(user_obj, field, not current)
                user_obj.save(update_fields=[field])
                message = f"{field} set to {not current}"
                logger.info(
                    "admin_suite_user_toggle",
                    extra={
                        "user_id": str(user_obj.id),
                        "field": field,
                        "staff_user": getattr(request.user, "email", None),
                    },
                )
            elif action == "force_verify_email":
                if not getattr(request.user, "is_superuser", False):
                    message = "Superuser required for this action."
                    raise Exception("superuser_required")
                target_email = request.POST.get("email") or user_obj.email
                from django.utils import timezone

                try:
                    from allauth.account.models import EmailAddress

                    EmailAddress.objects.update_or_create(
                        user=user_obj,
                        email=target_email,
                        defaults={"verified": True, "primary": True},
                    )
                except Exception:
                    pass
                if hasattr(user_obj, "email_verified_at"):
                    user_obj.email_verified_at = timezone.now()
                    user_obj.save(update_fields=["email_verified_at"])
                message = "Email marked as verified."
                logger.info(
                    "admin_suite_user_force_verify",
                    extra={
                        "user_id": str(user_obj.id),
                        "email": target_email,
                        "staff_user": getattr(request.user, "email", None),
                    },
                )
            elif action == "invalidate_sessions":
                try:
                    from django.contrib.sessions.models import Session
                    from django.utils import timezone

                    active_sessions = Session.objects.filter(
                        expire_date__gt=timezone.now()
                    )
                    for sess in active_sessions:
                        try:
                            data = sess.get_decoded()
                        except Exception:
                            continue
                        if str(data.get("_auth_user_id")) == str(
                            getattr(user_obj, "id", None)
                        ):
                            sess.delete()
                except Exception:
                    pass
                message = "User sessions invalidated."
                logger.info(
                    "admin_suite_user_invalidate_sessions",
                    extra={
                        "user_id": str(user_obj.id),
                        "staff_user": getattr(request.user, "email", None),
                    },
                )
            elif action == "send_password_reset":
                if not getattr(request.user, "is_superuser", False):
                    message = "Superuser required for this action."
                    raise Exception("superuser_required")
                try:
                    from allauth.account.forms import ResetPasswordForm

                    form = ResetPasswordForm(data={"email": user_obj.email})
                    if form.is_valid():
                        form.save(request)
                        message = "Password reset email sent."
                    else:
                        message = "Password reset could not be sent."
                except Exception:
                    message = "Password reset could not be sent."
                logger.info(
                    "admin_suite_user_password_reset",
                    extra={
                        "user_id": str(user_obj.id),
                        "staff_user": getattr(request.user, "email", None),
                    },
                )
            elif action in {
                "block_device",
                "unblock_device",
                "trust_device",
                "untrust_device",
            }:
                device_id = request.POST.get("device_id")
                if device_id:
                    from apps.devices.models import Device

                    device = Device.objects.filter(pk=device_id, user=user_obj).first()
                    if device:
                        if action == "block_device":
                            device.is_blocked = True
                        elif action == "unblock_device":
                            device.is_blocked = False
                        elif action == "trust_device":
                            device.is_trusted = True
                        elif action == "untrust_device":
                            device.is_trusted = False
                        device.save(update_fields=["is_blocked", "is_trusted"])
                        message = "Device updated."
                        logger.info(
                            "admin_suite_user_device_action",
                            extra={
                                "user_id": str(user_obj.id),
                                "device_id": str(device_id),
                                "action": action,
                                "staff_user": getattr(request.user, "email", None),
                            },
                        )
            elif action == "reset_device_quota":
                try:
                    from apps.devices.models_quota import UserDeviceQuota

                    quota, _ = UserDeviceQuota.objects.get_or_create(
                        user_id=user_obj.id
                    )
                    quota.last_reset_at = timezone.now()
                    quota.save(update_fields=["last_reset_at"])
                    message = "Device quota reset."
                    logger.info(
                        "admin_suite_user_quota_reset",
                        extra={
                            "user_id": str(user_obj.id),
                            "staff_user": getattr(request.user, "email", None),
                        },
                    )
                except Exception:
                    message = "Quota reset failed."
            elif action == "ban_user":
                if not getattr(request.user, "is_superuser", False):
                    message = "Superuser required for this action."
                    raise Exception("superuser_required")
                user_obj.is_active = False
                user_obj.save(update_fields=["is_active"])
                message = "User banned (set inactive)."
                logger.info(
                    "admin_suite_user_ban",
                    extra={
                        "user_id": str(user_obj.id),
                        "staff_user": getattr(request.user, "email", None),
                    },
                )
            elif action == "delete_user":
                if not getattr(request.user, "is_superuser", False):
                    message = "Superuser required for this action."
                    raise Exception("superuser_required")
                # Soft-delete: deactivate and anonymize identifiers to avoid collisions.
                user_obj.is_active = False
                if hasattr(user_obj, "email") and user_obj.email:
                    ts = timezone.now().strftime("%Y%m%d%H%M%S")
                    user_obj.email = f"deleted+{user_obj.id}+{ts}@example.invalid"
                if hasattr(user_obj, "username"):
                    user_obj.username = (
                        f"deleted_{user_obj.id}_{int(timezone.now().timestamp())}"
                    )
                user_obj.save()
                message = "User deactivated and anonymized."
                logger.info(
                    "admin_suite_user_delete_soft",
                    extra={
                        "user_id": str(user_obj.id),
                        "staff_user": getattr(request.user, "email", None),
                    },
                )
            elif action == "hard_delete_user":
                if not getattr(request.user, "is_superuser", False):
                    message = "Superuser required for this action."
                    raise Exception("superuser_required")
                uid = str(user_obj.id)
                user_obj.delete()
                logger.info(
                    "admin_suite_user_delete_hard",
                    extra={
                        "user_id": uid,
                        "staff_user": getattr(request.user, "email", None),
                    },
                )
                return HttpResponseRedirect(reverse("admin_suite:admin_suite_users"))
        except Exception as exc:
            logger.warning("Admin suite user action failed: %s", exc)
            message = "Action failed."

    return _render_admin(
        request,
        "admin_suite/user_detail.html",
        {
            "user_obj": user_obj,
            "devices": profile.get("devices", []),
            "device_events": profile.get("device_events", []),
            "risk_insights": profile.get("risk_insights", []),
            "email_addresses": profile.get("email_addresses", []),
            "social_accounts": profile.get("social_accounts", []),
            "message": message,
        },
        nav_active="users",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Users", "admin_suite:users"),
            (getattr(user_obj, "email", "User"), None),
        ),
    )


@staff_member_required
def admin_suite_user_sessions(request: HttpRequest) -> HttpResponse:
    """View active user sessions across the platform."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    sessions = []
    try:
        from django.contrib.sessions.models import Session
        from django.utils import timezone

        active_sessions = Session.objects.filter(
            expire_date__gt=timezone.now()
        ).order_by("-expire_date")[:100]
        for sess in active_sessions:
            try:
                data = sess.get_decoded()
                user_id = data.get("_auth_user_id")
                if user_id:
                    try:
                        user = CustomUser.objects.get(pk=user_id)
                        sessions.append(
                            {
                                "session_key": sess.session_key[:8] + "...",
                                "user": user,
                                "expire_date": sess.expire_date,
                            }
                        )
                    except CustomUser.DoesNotExist:
                        pass
            except Exception:
                pass
    except Exception as exc:
        logger.warning("Failed to load sessions: %s", exc)

    return _render_admin(
        request,
        "admin_suite/user_sessions.html",
        {"sessions": sessions},
        nav_active="users",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Users", "admin_suite:users"),
            ("Sessions", None),
        ),
        subtitle="Active user sessions",
    )


@staff_member_required
def admin_suite_staff_users(request: HttpRequest) -> HttpResponse:
    """View and manage staff users."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    staff_users = CustomUser.objects.filter(is_staff=True).order_by("-date_joined")

    return _render_admin(
        request,
        "admin_suite/staff_users.html",
        {"staff_users": staff_users},
        nav_active="users",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Users", "admin_suite:users"),
            ("Staff", None),
        ),
        subtitle="Staff user management",
    )


# ==============================================================================
# Social Authentication Provider Management
# ==============================================================================


@staff_member_required
def admin_suite_social_providers(request: HttpRequest) -> HttpResponse:
    """
    Social authentication provider configuration management.

    Allows administrators to:
    - Configure OAuth credentials for Google, Facebook, Microsoft, GitHub, etc.
    - View provider status and user counts
    - Test provider connections
    - Sync configurations to django-allauth
    """
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    from apps.users.models_social import SocialProviderConfig

    message = ""

    # Handle POST actions
    if request.method == "POST":
        action = request.POST.get("action")
        provider_id = request.POST.get("provider_id")

        try:
            if action == "create_provider":
                provider = request.POST.get("provider")
                client_id = request.POST.get("client_id", "").strip()
                client_secret = request.POST.get("client_secret", "").strip()

                if not provider:
                    message = "Provider type is required."
                elif not client_id or not client_secret:
                    message = "Client ID and Client Secret are required."
                else:
                    # Create or update
                    config, created = SocialProviderConfig.objects.get_or_create(
                        provider=provider,
                        defaults={
                            "display_name": dict(
                                SocialProviderConfig.PROVIDER_CHOICES
                            ).get(provider, provider),
                            "status": "unconfigured",
                            "scopes": SocialProviderConfig.get_default_scopes(provider),
                            "created_by": request.user,
                        },
                    )
                    config.set_client_id(client_id)
                    config.set_client_secret(client_secret)

                    # Handle provider-specific fields
                    if provider == "microsoft":
                        tenant_id = request.POST.get("tenant_id", "").strip()
                        config.tenant_id = tenant_id or "common"
                    elif provider == "apple":
                        config.team_id = request.POST.get("team_id", "").strip()
                        config.key_id = request.POST.get("key_id", "").strip()

                    config.status = "active"
                    config.save()

                    # Sync to allauth
                    if config.sync_to_allauth():
                        message = f"{'Created' if created else 'Updated'} {config.get_provider_display()} and synced to auth system."
                    else:
                        message = f"{'Created' if created else 'Updated'} {config.get_provider_display()} but sync failed. Check error."

            elif action == "test_connection" and provider_id:
                config = SocialProviderConfig.objects.filter(id=provider_id).first()
                if config:
                    success, msg = config.test_connection()
                    message = f"{config.get_provider_display()}: {msg}"

            elif action == "toggle_provider" and provider_id:
                config = SocialProviderConfig.objects.filter(id=provider_id).first()
                if config:
                    config.is_enabled = not config.is_enabled
                    config.status = "active" if config.is_enabled else "disabled"
                    config.save(update_fields=["is_enabled", "status", "updated_at"])
                    message = f"{config.get_provider_display()} {'enabled' if config.is_enabled else 'disabled'}."

            elif action == "sync_allauth" and provider_id:
                config = SocialProviderConfig.objects.filter(id=provider_id).first()
                if config and config.sync_to_allauth():
                    message = f"Synced {config.get_provider_display()} to authentication system."
                else:
                    message = "Sync failed. Check provider error."

            elif action == "delete_provider" and provider_id:
                if not getattr(request.user, "is_superuser", False):
                    message = "Superuser required to delete providers."
                else:
                    config = SocialProviderConfig.objects.filter(id=provider_id).first()
                    if config:
                        name = config.get_provider_display()
                        config.delete()
                        message = f"Deleted {name} configuration."

        except Exception as exc:
            logger.warning("Social provider action failed: %s", exc)
            message = f"Action failed: {exc}"

    # Get all configured providers
    providers = list(SocialProviderConfig.objects.all())

    # Update user counts
    for p in providers:
        p.update_user_count()

    # Get existing allauth social apps for comparison
    existing_allauth = set()
    try:
        from allauth.socialaccount.models import SocialApp

        existing_allauth = set(SocialApp.objects.values_list("provider", flat=True))
    except Exception:
        pass

    # Available provider choices (excluding already configured)
    configured_providers = {p.provider for p in providers}
    available_choices = [
        (k, v)
        for k, v in SocialProviderConfig.PROVIDER_CHOICES
        if k not in configured_providers
    ]

    return _render_admin(
        request,
        "admin_suite/social_providers.html",
        {
            "providers": providers,
            "provider_choices": available_choices,
            "existing_allauth": existing_allauth,
            "message": message,
        },
        nav_active="users",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Users", "admin_suite:users"),
            ("Social Providers", None),
        ),
        subtitle="Configure OAuth social authentication providers",
    )


@staff_member_required
def admin_suite_social_provider_detail(
    request: HttpRequest, provider_id: str
) -> HttpResponse:
    """
    Detailed view for a single social authentication provider.

    Shows:
    - Full configuration
    - Credential management
    - OAuth flow initiation for browser-based auth
    - Usage statistics
    """
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    from apps.users.models_social import SocialProviderConfig

    try:
        config = SocialProviderConfig.objects.get(id=provider_id)
    except SocialProviderConfig.DoesNotExist:
        raise Http404("Provider not found")

    message = ""

    if request.method == "POST":
        action = request.POST.get("action")

        try:
            if action == "update_credentials":
                client_id = request.POST.get("client_id", "").strip()
                client_secret = request.POST.get("client_secret", "").strip()

                if client_id:
                    config.set_client_id(client_id)
                if client_secret:
                    config.set_client_secret(client_secret)

                # Update provider-specific fields
                if config.provider == "microsoft":
                    config.tenant_id = (
                        request.POST.get("tenant_id", "").strip() or config.tenant_id
                    )
                elif config.provider == "apple":
                    config.team_id = (
                        request.POST.get("team_id", "").strip() or config.team_id
                    )
                    config.key_id = (
                        request.POST.get("key_id", "").strip() or config.key_id
                    )

                # Update scopes if provided
                scopes = request.POST.get("scopes", "").strip()
                if scopes:
                    config.scopes = [s.strip() for s in scopes.split(",") if s.strip()]

                config.display_name = (
                    request.POST.get("display_name", "").strip() or config.display_name
                )
                config.save()

                # Sync to allauth
                config.sync_to_allauth()
                message = "Credentials updated and synced."

            elif action == "update_settings":
                settings_json = request.POST.get("settings_json", "{}").strip()
                try:
                    import json

                    config.settings_json = (
                        json.loads(settings_json) if settings_json else {}
                    )
                    config.save(update_fields=["settings_json", "updated_at"])
                    config.sync_to_allauth()
                    message = "Settings updated."
                except json.JSONDecodeError:
                    message = "Invalid JSON format."

            elif action == "test_connection":
                success, msg = config.test_connection()
                message = msg

            elif action == "sync_allauth":
                if config.sync_to_allauth():
                    message = "Successfully synced to authentication system."
                else:
                    message = f"Sync failed: {config.last_error}"

        except Exception as exc:
            logger.warning("Provider detail action failed: %s", exc)
            message = f"Action failed: {exc}"

    # Get linked users count
    linked_users = []
    try:
        from allauth.socialaccount.models import SocialAccount

        linked_users = list(
            SocialAccount.objects.filter(provider=config.provider)
            .select_related("user")
            .order_by("-date_joined")[:10]
        )
        config.users_count = SocialAccount.objects.filter(
            provider=config.provider
        ).count()
    except Exception:
        pass

    # Mask sensitive data for display
    client_id = config.get_client_id()
    client_id_masked = (
        f"{client_id[:8]}...{client_id[-4:]}" if len(client_id) > 12 else "Not set"
    )

    return _render_admin(
        request,
        "admin_suite/social_provider_detail.html",
        {
            "config": config,
            "client_id_masked": client_id_masked,
            "linked_users": linked_users,
            "message": message,
        },
        nav_active="users",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Users", "admin_suite:users"),
            ("Social Providers", "admin_suite:social_providers"),
            (config.get_provider_display(), None),
        ),
        subtitle=f"Configure {config.get_provider_display()}",
    )


__all__ = [
    "admin_suite_users",
    "admin_suite_user_detail",
    "admin_suite_user_sessions",
    "admin_suite_staff_users",
    "admin_suite_social_providers",
    "admin_suite_social_provider_detail",
]
