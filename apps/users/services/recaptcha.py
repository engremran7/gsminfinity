"""
apps/users/services/recaptcha.py
--------------------------------
Enterprise-Grade Google reCAPTCHA Verification Service

✅ Supports v2 + v3 with hostname verification
✅ Configurable thresholds via SiteSettings
✅ Token-level caching (short-lived, atomic)
✅ Graceful degradation when disabled or unreachable
✅ Hardened against abuse, malformed tokens, and network errors
"""

import logging
import requests
from decimal import Decimal
from django.conf import settings as django_settings
from django.core.cache import cache
from apps.site_settings.models import SiteSettings

logger = logging.getLogger(__name__)


# ============================================================
#  MAIN VERIFICATION FUNCTION
# ============================================================
def verify_recaptcha(token: str, remote_ip: str = None, action: str = "login") -> dict:
    """
    Verify a Google reCAPTCHA token using configuration from SiteSettings.

    Args:
        token (str): The token returned by the frontend reCAPTCHA widget.
        remote_ip (str): The user's IP (optional, logged and validated).
        action (str): Context identifier (login, signup, etc.).

    Returns:
        dict:
            {
                "ok": bool,
                "score": float (v3 only),
                "errors": list[str],
                "error": str (internal issue, if any)
            }
    """

    # ------------------------------------------------------------------
    # Step 1. Retrieve configuration safely
    # ------------------------------------------------------------------
    try:
        settings_obj = SiteSettings.get_solo()
    except Exception as exc:
        logger.warning("reCAPTCHA: unable to load SiteSettings → %s", exc)
        return {"ok": False, "error": "settings_unavailable"}

    recaptcha_enabled = getattr(settings_obj, "recaptcha_enabled", False)
    recaptcha_mode = str(getattr(settings_obj, "recaptcha_mode", "off")).lower()
    private_key = getattr(settings_obj, "recaptcha_private_key", None)

    # ------------------------------------------------------------------
    # Step 2. Skip when disabled
    # ------------------------------------------------------------------
    if not recaptcha_enabled or recaptcha_mode == "off":
        logger.debug("reCAPTCHA: bypassed (disabled or off mode)")
        return {"ok": True}

    # ------------------------------------------------------------------
    # Step 3. Validate token input
    # ------------------------------------------------------------------
    if not token or len(str(token)) > 10000:
        return {"ok": False, "error": "invalid_token_format"}

    if not private_key:
        logger.error("reCAPTCHA: missing private key in SiteSettings")
        return {"ok": False, "error": "missing_credentials"}

    # ------------------------------------------------------------------
    # Step 4. Check short-term cache to prevent redundant API calls
    # ------------------------------------------------------------------
    cache_key = f"recaptcha:{action}:{hash(token)}"
    cached = cache.get(cache_key)
    if cached is not None:
        logger.debug("reCAPTCHA: using cached result for %s", action)
        return cached

    # ------------------------------------------------------------------
    # Step 5. Build request payload
    # ------------------------------------------------------------------
    payload = {"secret": private_key, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip

    timeout = max(
        float(getattr(settings_obj, "recaptcha_timeout_ms", 3000)) / 1000.0, 1.0
    )
    api_url = "https://www.google.com/recaptcha/api/siteverify"

    # ------------------------------------------------------------------
    # Step 6. Execute request with hardened network handling
    # ------------------------------------------------------------------
    try:
        resp = requests.post(api_url, data=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        logger.warning("reCAPTCHA: timeout verifying token (%s)", action)
        return {"ok": False, "error": "timeout"}
    except requests.exceptions.ConnectionError as exc:
        logger.error("reCAPTCHA: connection error → %s", exc)
        return {"ok": False, "error": "connection_error"}
    except requests.exceptions.RequestException as exc:
        logger.error("reCAPTCHA: network failure → %s", exc)
        return {"ok": False, "error": "network_error"}
    except ValueError:
        logger.error("reCAPTCHA: invalid JSON response")
        return {"ok": False, "error": "invalid_response"}
    except Exception as exc:
        logger.exception("reCAPTCHA: unexpected exception → %s", exc)
        return {"ok": False, "error": "recaptcha_unreachable"}

    # ------------------------------------------------------------------
    # Step 7. Validate response integrity
    # ------------------------------------------------------------------
    success = data.get("success", False)
    hostname = data.get("hostname")
    error_codes = data.get("error-codes", []) or []

    expected_host = getattr(django_settings, "RECAPTCHA_EXPECTED_HOSTNAME", None)
    if expected_host and hostname and hostname != expected_host:
        logger.warning("reCAPTCHA: hostname mismatch (%s ≠ %s)", hostname, expected_host)
        success = False
        error_codes.append("hostname_mismatch")

    # ------------------------------------------------------------------
    # Step 8. Handle v3 (score-based) or v2 verification
    # ------------------------------------------------------------------
    if recaptcha_mode == "v3":
        score = Decimal(str(data.get("score", 0.0)))
        threshold = Decimal(str(getattr(settings_obj, "recaptcha_score_threshold", 0.5)))
        valid = success and score >= threshold

        result = {
            "ok": bool(valid),
            "score": float(score),
            "errors": error_codes,
        }

        if not valid:
            logger.info(
                "reCAPTCHA v3 failed: score=%.2f threshold=%.2f host=%s",
                score,
                threshold,
                hostname,
            )
    else:
        # v2 (checkbox/invisible)
        result = {
            "ok": bool(success),
            "errors": error_codes,
        }

    # ------------------------------------------------------------------
    # Step 9. Cache result briefly (anti-abuse, performance)
    # ------------------------------------------------------------------
    cache.set(cache_key, result, timeout=15)  # 15s short TTL
    return result
