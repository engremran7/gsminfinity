from django.conf import settings

DEFAULTS = {
    "ENABLED": True,
}


def get(key: str, default=None):
    return getattr(settings, "SECURITY_RISK_CONFIG", {}).get(key, DEFAULTS.get(key, default))
