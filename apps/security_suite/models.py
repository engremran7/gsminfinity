from __future__ import annotations

from django.db import models
from solo.models import SingletonModel


class SecurityConfig(SingletonModel):
    """
    Global, DB-backed security controls consumed by modular apps.
    """

    devices_enabled = models.BooleanField(default=True)
    crawler_guard_enabled = models.BooleanField(default=False)
    mfa_enabled = models.BooleanField(default=True)
    login_risk_enabled = models.BooleanField(default=False)

    device_quota_enforcement_enabled = models.BooleanField(default=False)
    default_device_window = models.CharField(
        max_length=4,
        choices=[("3m", "3 Months"), ("6m", "6 Months"), ("12m", "12 Months")],
        default="12m",
    )
    default_device_limit = models.PositiveIntegerField(default=5)

    security_tier = models.CharField(
        max_length=16,
        choices=[("basic", "Basic"), ("standard", "Standard"), ("strict", "Strict")],
        default="basic",
    )

    crawler_default_action = models.CharField(
        max_length=12,
        choices=[("allow", "Allow"), ("throttle", "Throttle"), ("block", "Block"), ("challenge", "Challenge")],
        default="allow",
    )

    mfa_policy = models.CharField(
        max_length=20,
        choices=[
            ("optional", "Optional"),
            ("mfa_if_high", "MFA if High Risk"),
            ("required", "Required"),
        ],
        default="optional",
    )
    login_risk_policy = models.CharField(
        max_length=20,
        choices=[
            ("none", "None"),
            ("info", "Info Only"),
            ("mfa_if_high", "MFA if High Risk"),
            ("block_if_high", "Block if High Risk"),
        ],
        default="mfa_if_high",
    )

    class Meta:
        verbose_name = "Security Config"

    def __str__(self) -> str:  # pragma: no cover - admin display only
        return "Security Config"
