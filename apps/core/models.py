from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    """
    Minimal timestamp mixin for models that do not need soft-delete/audit.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """
    Soft-delete abstraction (opt-in per concrete model).
    """

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_deleted",
    )

    class Meta:
        abstract = True

    def soft_delete(self, user=None, commit: bool = True) -> None:
        self.is_deleted = True
        self.deleted_at = models.functions.Now()
        if user and not self.deleted_by:
            self.deleted_by = user
        if commit:
            self.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])


class AuditFieldsModel(models.Model):
    """
    Adds created_by / updated_by without forcing concrete relations to use them.
    """

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_updated",
    )

    class Meta:
        abstract = True
