# Security Suite (Optional)

Facade that delegates to in-project apps for devices, bots, and risk; can be packaged separately.

## Capabilities
- `security/security/services.py` calls into security_devices/security_bots/security_risk modules.
- Shims map to in-project apps (devices, crawler_guard, ai_behavior) by default.
- Toggleable via `SECURITY_CONFIG` / `ADMIN_SUITE_ENABLED` flags.

## Structure
- `security/` — entrypoint and services facade.
- `security_devices`, `security_bots`, `security_risk` — delegating shims.

## Notes
- Designed to remain pluggable/self-contained; integrate or replace with external services as needed.
