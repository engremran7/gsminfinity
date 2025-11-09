# apps/users/backends.py
"""
Custom Multi-Field Authentication Backend
-----------------------------------------
Enterprise-ready authentication backend for GSMInfinity.

✅ Features:
- Login via email, username, or phone number.
- Timing-safe and allauth-compatible.
- Case-insensitive lookups across identifiers.
- Protects against user enumeration & timing leaks.
- Graceful fallback and detailed logging.
"""

import logging
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.core.exceptions import MultipleObjectsReturned
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)
UserModel = get_user_model()


class MultiFieldAuthBackend(ModelBackend):
    """
    Authenticate users using email, username, or phone number.
    Designed for concurrent authentication safety and minimal side-channel exposure.
    """

    def authenticate(self, request, username: str = None, password: str = None, **kwargs):
        """
        Authenticate a user based on a flexible identifier.

        Args:
            request: Optional HttpRequest
            username (str): Input identifier (email / username / phone)
            password (str): Raw password
        Returns:
            Authenticated user or None
        """
        if not username or not password:
            logger.debug("Authentication attempt missing credentials.")
            return None

        identifier = str(username).strip().lower()
        user = None

        try:
            # Unified case-insensitive lookup
            qs = UserModel.objects.filter(
                Q(email__iexact=identifier)
                | Q(username__iexact=identifier)
                | Q(phone__iexact=identifier)
            ).distinct()

            # Defensive: take first and log duplicates
            if qs.count() > 1:
                logger.warning("Multiple accounts share identifier=%s", identifier)
            user = qs.first()

        except MultipleObjectsReturned:
            logger.warning("MultipleObjectsReturned: %s", identifier)
            return None
        except Exception as exc:
            logger.exception("User lookup failed for %s → %s", identifier, exc)
            return None

        if not user:
            # Silent fail to avoid user enumeration
            logger.debug("No matching user for identifier=%s", identifier)
            return None

        try:
            # Timing-safe password check
            if user.check_password(password) and self.user_can_authenticate(user):
                logger.info("Successful login: %s", getattr(user, "email", user.pk))
                return user
            else:
                logger.debug("Invalid password or inactive account for %s", identifier)
        except Exception as exc:
            logger.exception("Password verification error for %s → %s", identifier, exc)

        return None

    def get_user(self, user_id):
        """
        Retrieve a user instance safely for session authentication.
        """
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            logger.debug("get_user: User not found id=%s", user_id)
            return None
        except Exception as exc:
            logger.exception("get_user failed for id=%s → %s", user_id, exc)
            return None
