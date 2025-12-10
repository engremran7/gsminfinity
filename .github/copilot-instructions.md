# GSM Infinity - AI Coding Agent Instructions

## Architecture Overview

This is a Django 4.2+ monolithic application with a modular app structure. The project uses:
- **App-based architecture**: Each feature is a Django app in `apps/` (e.g., `blog`, `ads`, `ai`, `comments`)
- **Central configuration**: `gsminfinity/settings.py` with environment-based config via `.env`
- **Shared utilities**: `apps/core/` contains cross-cutting concerns (middleware, utils, base models)
- **Security suite**: Multi-layered security via `apps/crawler_guard/`, `apps/ai_behavior/`, and `apps/devices/`

## Key Patterns & Conventions

### App Structure
Each app follows this pattern (see `apps/blog/` or `apps/ads/`):
```
app_name/
  models.py          # Database models
  views.py           # View logic
  urls.py            # URL routing
  api.py             # API endpoints (if applicable)
  services.py        # Business logic layer
  templates/app_name/ # App-specific templates
  management/commands/ # Custom Django commands
```

### AI Integration
- **AI Services** (`apps/ai/`): Content generation, AI-powered features, OpenAI/Anthropic integration
- **AI Behavior Engine** (`apps/ai_behavior/`): Security-focused behavioral analysis and threat detection
- Use environment variables for API keys (configured in `.env`)

### Security Architecture

**Three-Layer Security Model:**

1. **Crawler Guard** (`apps/crawler_guard/`): Bot detection, rate limiting, and malicious crawler blocking
2. **AI Behavior Engine** (`apps/ai_behavior/`): Behavioral analysis and anomaly detection using AI
3. **Device Management** (`apps/devices/`): Device fingerprinting and trusted device tracking

### Authentication & Authorization
- **All authentication logic** resides in `apps/users/` (user auth) and admin authentication
- Use Django's built-in authentication system extended by `apps/users/`
- Admin suite in `apps/admin_suite/` provides enhanced admin dashboards
- Security events tracked in `apps/security_events/`

### Database & Models
- Uses SQLite (`db.sqlite3`) with Django ORM
- Models use `apps.core.models.TimestampedModel` as base class for created/modified timestamps
- Key models: `apps/blog/models.py` (Post, Category), `apps/ads/models.py` (Advertisement)

### Template System
- Base template: `templates/base.html`
- App templates: `apps/{app_name}/templates/{app_name}/`
- Static files: Collected via `python manage.py collectstatic` to `staticfiles/`

## Developer Workflows

### Setup
```bash
python -m venv .vnv
.vnv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.sample .env  # Configure environment variables
python manage.py migrate
python manage.py runserver
```

### Testing
```bash
pytest  # Uses conftest.py configuration
python manage.py test  # Django test runner alternative
```

### Common Commands
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic
python manage.py createsuperuser
```

### Audit Dumps
PowerShell script `generate_audit_dump.ps1` creates database snapshots

## Integration Points

- **Admin Suite**: `apps/admin_suite/` - Enhanced Django admin with custom dashboards
- **Comments System**: `apps/comments/` - Reusable comment functionality across apps
- **Consent Management**: `apps/consent/` - GDPR/privacy consent handling
- **SEO Management**: `apps/seo/` - SEO optimization features
- **App Registry**: `apps/app_registry/` - Dynamic app discovery and management
- **Distribution**: `apps/distribution/` - Content distribution functionality

## Important Files

- `gsminfinity/settings.py` - Central configuration
- `gsminfinity/urls.py` - Root URL configuration
- `apps/core/middleware.py` - Custom middleware
- `conftest.py` - Pytest configuration
- `README.md` - Project overview
- `OPS.md` - Operational procedures

## Security Development Guidelines

When adding new features:
1. **Always authenticate via `apps/users/`** - Don't implement auth elsewhere
2. **Apply security layers**: Use crawler_guard decorators for rate limiting
3. **Track behavior**: Integrate with `apps/ai_behavior/` for anomaly detection
4. **Device awareness**: Consider device tracking via `apps/devices/` for sensitive operations
5. **Log security events**: Use `apps/security_events/` for audit trails

## Code Style Notes

- Follow Django conventions for model/view/template organization
- Use class-based views where appropriate
- Environment variables for all secrets and configuration
- Modular design: keep features within their respective apps
- Use `apps.core` for shared functionality, not individual apps
- Business logic goes in `services.py`, keep views thin
