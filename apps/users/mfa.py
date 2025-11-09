"""
Multi-Factor Authentication (MFA) Utilities for GSMInfinity
------------------------------------------------------------
Provides enterprise-grade Time-based One-Time Password (TOTP) management
and global MFA enforcement logic.

Features:
- RFC 6238–compliant TOTP codes (compatible with Google Authenticator)
- ± time drift tolerance for device clock variance
- Configurable issuer and enforcement policy via SiteSettings
- Secure HMAC comparison to prevent timing attacks
"""

import base64
import os
import time
import hmac
import hashlib
import logging
from apps.site_settings.models import SiteSettings


logger = logging.getLogger(__name__)


# ============================================================
#  TOTP SERVICE
# ============================================================
class TOTPService:
    """
    Provides TOTP (Time-based One-Time Password) generation and verification
    compatible with major authenticator apps (Google, Authy, Microsoft).
    """

    @staticmethod
    def generate_secret(length: int = 20) -> str:
        """
        Generate a random Base32-encoded secret key for TOTP.
        Default length: 20 bytes (~160 bits of entropy).
        """
        try:
            secret = base64.b32encode(os.urandom(length)).decode("utf-8").rstrip("=")
            return secret
        except Exception as exc:
            logger.error("Failed to generate TOTP secret: %s", exc)
            raise

    # ------------------------------------------------------------
    #  PRIVATE HELPERS
    # ------------------------------------------------------------
    @staticmethod
    def _normalize_secret(secret: str) -> bytes:
        """
        Normalize the Base32 secret by padding if required.
        Ensures compatibility with decoders regardless of input length.
        """
        pad = (8 - (len(secret) % 8)) % 8
        padded = secret.upper() + "=" * pad
        return base64.b32decode(padded)

    @staticmethod
    def _hotp(secret: str, counter: int, digits: int = 6) -> str:
        """
        Generate an HMAC-based OTP from a counter value.
        Internal utility for TOTP computation.
        """
        key = TOTPService._normalize_secret(secret)
        msg = counter.to_bytes(8, "big")
        hmac_hash = hmac.new(key, msg, hashlib.sha1).digest()
        offset = hmac_hash[-1] & 0x0F
        binary = int.from_bytes(hmac_hash[offset:offset + 4], "big") & 0x7FFFFFFF
        otp = str(binary % (10 ** digits)).zfill(digits)
        return otp

    # ------------------------------------------------------------
    #  PUBLIC INTERFACE
    # ------------------------------------------------------------
    @staticmethod
    def generate_current_code(secret: str, period: int = 30, digits: int = 6) -> str:
        """
        Compute the current TOTP code for the given secret.
        Args:
            secret: Base32 encoded secret
            period: Time step in seconds (default 30)
            digits: Number of output digits (default 6)
        """
        counter = int(time.time() / period)
        return TOTPService._hotp(secret, counter, digits)

    @staticmethod
    def verify(secret: str, code: str, tolerance: int = 1, period: int = 30, digits: int = 6) -> bool:
        """
        Verify a TOTP code against the current time window, allowing ±1 drift.

        Args:
            secret (str): Base32 secret
            code (str): User-supplied code
            tolerance (int): Number of time steps to allow for drift (default ±1)
            period (int): TOTP time step duration (seconds)
            digits (int): Expected length of code (default 6)

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            current_counter = int(time.time() / period)
            code = str(code).zfill(digits)

            for offset in range(-tolerance, tolerance + 1):
                expected = TOTPService._hotp(secret, current_counter + offset, digits)
                if hmac.compare_digest(expected, code):
                    return True
            return False

        except Exception as exc:
            logger.warning("TOTP verification failed: %s", exc)
            return False


# ============================================================
#  MFA ENFORCER
# ============================================================
class MFAEnforcer:
    """
    Utility for checking global MFA enforcement policies and issuer identity.
    Reads configuration from SiteSettings.
    """

    @staticmethod
    def required() -> bool:
        """
        Returns True if MFA is required globally (via site settings).
        """
        try:
            settings = SiteSettings.get_solo()
            return bool(getattr(settings, "require_mfa", False))
        except Exception as exc:
            logger.warning("MFAEnforcer.required() failed: %s", exc)
            return False

    @staticmethod
    def issuer() -> str:
        """
        Returns the MFA issuer name (used in authenticator apps).
        Defaults to the site name or 'GSMInfinity' as fallback.
        """
        try:
            settings = SiteSettings.get_solo()
            return getattr(settings, "mfa_totp_issuer", getattr(settings, "site_name", "GSMInfinity"))
        except Exception as exc:
            logger.warning("MFAEnforcer.issuer() failed: %s", exc)
            return "GSMInfinity"

    @staticmethod
    def qr_uri(secret: str, user_email: str) -> str:
        """
        Build an otpauth:// URI for QR code generation.
        Enables direct import into Authenticator apps.

        Returns:
            str: otpauth URI formatted for QR encoding.
        """
        issuer = MFAEnforcer.issuer()
        return f"otpauth://totp/{issuer}:{user_email}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"
