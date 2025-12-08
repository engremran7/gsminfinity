# Devices App

Device identity, quotas, risk/MFA thresholds, and approval flows.

## Capabilities
- Device model: machine UUID, fingerprint hash, risk score, trust/block flags.
- Quotas: global defaults + per-user override (`UserDeviceQuota`), monthly/yearly limits.
- Risk/MFA: `DeviceConfig.risk_mfa_threshold` to gate MFA on high-risk devices.
- Approval flow: tokens issued on untrusted/risky devices; approval/eviction views; admin/user actions.
- Events log (`DeviceEvent`) for auditing.

## Key Files
- `models.py` — Device, DeviceConfig, AppPolicy, DeviceEvent.
- `models_quota.py` — UserDeviceQuota.
- `services.py` — Resolve/create devices, enforce policy, logging, notifications.
- `views.py` — Device list for users.
- `admin.py` — Device admin with trust/block actions; singleton config.

## Frontend
- `static/js/device_identity.js` — consent-gated fingerprint submission (local).
- `templates/users/devices.html` — device list + pending approval banner.

## Integration
- Login flow hooks in `apps/users.views` call `enforce_device_policy_for_login`.
- Admin suite security pages expose device stats/actions.
