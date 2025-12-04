
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class ConsentPolicy(models.Model):
    version = models.CharField(max_length=50, unique=True)
    site_domain = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=False)
    banner_text = models.TextField(blank=True, default="")
    manage_text = models.TextField(blank=True, default="")
    cache_ttl_seconds = models.IntegerField(default=86400)
    text = models.TextField(blank=True, default="")
    categories_snapshot = models.JSONField(default=dict, blank=True)
    effective_from = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Policy {self.version} ({'active' if self.is_active else 'inactive'})"


class ConsentDecision(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    session_id = models.CharField(max_length=64, blank=True, default="")
    policy = models.ForeignKey(ConsentPolicy, null=True, blank=True, on_delete=models.SET_NULL)
    categories = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ip_hash = models.CharField(max_length=64, blank=True, default="")
    user_agent_hash = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def set_hashes(self, ip: str = "", ua: str = "") -> None:
        from apps.consent.utils import hash_ip, hash_ua

        self.ip_hash = hash_ip(ip)
        self.user_agent_hash = hash_ua(ua)


class ConsentEvent(models.Model):
    decision = models.ForeignKey(ConsentDecision, null=True, blank=True, on_delete=models.SET_NULL, related_name="events")
    policy = models.ForeignKey(ConsentPolicy, null=True, blank=True, on_delete=models.SET_NULL)
    categories = models.JSONField(default=dict, blank=True)
    event_type = models.CharField(max_length=32, default="accepted")
    created_at = models.DateTimeField(auto_now_add=True)
    ip_hash = models.CharField(max_length=64, blank=True, default="")
    user_agent_hash = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def set_hashes(self, ip: str = "", ua: str = "") -> None:
        from apps.consent.utils import hash_ip, hash_ua

        self.ip_hash = hash_ip(ip)
        self.user_agent_hash = hash_ua(ua)


class ConsentRecord(ConsentDecision):
    """
    Proxy to maintain admin/import compatibility with the legacy model name.
    """

    class Meta:
        proxy = True
        verbose_name = "Consent record"
        verbose_name_plural = "Consent records"


class ConsentLog(ConsentEvent):
    """
    Proxy to maintain admin/import compatibility with the legacy audit log name.
    """

    class Meta:
        proxy = True
        verbose_name = "Consent log"
        verbose_name_plural = "Consent logs"


class ConsentCategory(models.Model):
    """
    Legacy stub to keep historical tables in place without generating new
    destructive migrations. Managed=False so schema is not altered.
    """

    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    index = models.IntegerField(default=0)

    class Meta:
        managed = False
        db_table = "consent_consentcategory"
        ordering = ["index", "slug"]


