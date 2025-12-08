# Core App

Shared infrastructure: feature flags, cache helpers, middleware (rate limits/security headers), logging/sanitize utilities, AI client/job helpers, base views, and context processors.

## Capabilities
- Feature flags and app service registry.
- Rate-limit bridge, security headers middleware.
- Logging/sanitize utilities, IP helpers.
- AI client/job helper wrappers; app_service discovery.
- Context processors for site/app flags.

## Key Files
- `app_service.py` — App registry/service resolution.
- `middleware/` — rate_limit_bridge, security_headers.
- `utils/` — feature_flags, ip, sanitize, logging.
- `ai.py/ai_client.py/ai_job.py` — AI execution helpers.
- `context_processors.py` — Injects site/app flags into templates.
