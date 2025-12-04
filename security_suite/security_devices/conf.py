from django.conf import settings

DEFAULTS = {
    "PERSISTENCE_ENABLED": True,
    "ATTACH_ON_LOGIN": True,
    "CONSENT_CATEGORY": "security",
}


def get(key: str, default=None):
    return getattr(settings, "SECURITY_DEVICES_CONFIG", {}).get(key, DEFAULTS.get(key, default))
