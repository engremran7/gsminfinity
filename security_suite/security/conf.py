from django.conf import settings

DEFAULTS = {
    "DEVICES_ENABLED": True,
    "BOTS_ENABLED": True,
    "RISK_ENABLED": True,
    "DEFAULT_LOGIN_RISK_POLICY": "mfa_if_high",  # none | info | mfa_if_high | block_if_high
}


def get(key: str, default=None):
    return getattr(settings, "SECURITY_CONFIG", {}).get(key, DEFAULTS.get(key, default))
