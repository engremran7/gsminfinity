from django.conf import settings

DEFAULTS = {
    "ENABLED": True,
    "DEFAULT_ACTION": "allow",  # allow | throttle | block
}


def get(key: str, default=None):
    return getattr(settings, "SECURITY_BOTS_CONFIG", {}).get(key, DEFAULTS.get(key, default))
