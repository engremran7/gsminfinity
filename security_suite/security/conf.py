from django.conf import settings

DEFAULTS = {
    "DEVICES_ENABLED": True,
    "BOTS_ENABLED": True,
    "RISK_ENABLED": True,
    "DEFAULT_LOGIN_RISK_POLICY": "mfa_if_high",  # none | info | mfa_if_high | block_if_high
    "CRAWLER_DEFAULT_ACTION": "allow",
    "MFA_POLICY": "optional",
}


def _db_snapshot():
    try:
        from apps.security_suite.api import security_settings_snapshot

        return security_settings_snapshot()
    except Exception:
        return {}


def get(key: str, default=None):
    db_cfg = _db_snapshot()
    if key in db_cfg:
        return db_cfg.get(key, DEFAULTS.get(key, default))
    return getattr(settings, "SECURITY_CONFIG", {}).get(key, DEFAULTS.get(key, default))
