from django.contrib import admin

from .models import SecurityConfig


@admin.register(SecurityConfig)
class SecurityConfigAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Toggles",
            {
                "fields": (
                    "devices_enabled",
                    "crawler_guard_enabled",
                    "mfa_enabled",
                    "login_risk_enabled",
                )
            },
        ),
        (
            "Device Quota",
            {
                "fields": (
                    "device_quota_enforcement_enabled",
                    "default_device_limit",
                    "default_device_window",
                )
            },
        ),
        (
            "Policies",
            {
                "fields": (
                    "security_tier",
                    "crawler_default_action",
                    "mfa_policy",
                    "login_risk_policy",
                )
            },
        ),
    )
    list_display = (
        "devices_enabled",
        "crawler_guard_enabled",
        "mfa_enabled",
        "login_risk_enabled",
    )
