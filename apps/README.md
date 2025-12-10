# 📦 GSM Infinity Apps - Pluggable Django Applications

This directory contains **self-contained, pluggable Django apps** that can be integrated into any Django project. Each app is designed to work independently while offering optional integration with other apps for enhanced functionality.

## 🎯 Core Philosophy

- **Self-Contained**: Each app has its own models, views, templates, and static files
- **Pluggable**: Install individually or combine multiple apps
- **Optional Dependencies**: Apps work standalone; integrations are opt-in
- **Django Standard**: Follows Django best practices and conventions

## 📚 Available Apps

### Core Infrastructure
- **`core`** - Shared utilities, base models, AI client, and app service layer
- **`site_settings`** - Global site configuration with singleton pattern
- **`app_registry`** - Feature flags and app enable/disable control

### Security & Identity
- **`users`** - Custom user model with allauth, MFA, notifications, and device management
- **`devices`** - Device fingerprinting and trusted device tracking
- **`crawler_guard`** - Bot detection and rate limiting
- **`ai_behavior`** - AI-powered behavioral analysis and anomaly detection
- **`security_events`** - Security audit logging
- **`consent`** - GDPR/CCPA consent management

### Content & Publishing
- **`blog`** - Full-featured blog with AI assistance, translations, and SEO
- **`comments`** - Comment system with AI moderation
- **`tags`** - Tag management with AI suggestions and keyword providers
- **`pages`** - Static pages management
- **`distribution`** - Content syndication

### Optimization & Analytics
- **`seo`** - SEO automation, metadata, redirects, and link suggestions
- **`ads`** - Advertisement management and networks integration

### Internationalization
- **`i18n`** - Translation management, locale configuration, and theme system
- **`i18n_themes`** - Theme variants and assignments

### Administration
- **`admin_suite`** - Enhanced admin dashboards

## 🚀 Quick Start

### 1. Install Individual App

```bash
# Copy the app directory to your project
cp -r /path/to/gsminfinity/apps/blog /your_project/apps/

# Or use as a submodule
git submodule add <repo_url> your_project/apps
```

### 2. Add to INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    # ... other Django apps
    
    'apps.blog',  # Add the app
]
```

### 3. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Include URLs (if applicable)

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    path('blog/', include('apps.blog.urls')),
]
```

## 📖 Integration Guides

Each app has its own `README.md` with:
- **Features**: What the app does
- **Dependencies**: Required packages and optional integrations
- **Installation**: Step-by-step setup instructions
- **Configuration**: Settings and environment variables
- **Usage**: How to use the app
- **Integration**: How to connect with other apps
- **API**: Available endpoints and services

## 🔗 App Dependencies

### Dependency Matrix

| App | Core Deps | Optional Deps |
|-----|-----------|---------------|
| **blog** | `core`, `tags` | `seo`, `comments`, `i18n` |
| **comments** | `core` | `consent`, `ai_behavior` |
| **tags** | `core` | `blog`, `seo` |
| **seo** | `core` | `blog`, `tags` |
| **users** | `core` | `devices`, `site_settings` |
| **consent** | `core` | - |
| **devices** | `core` | `users` |
| **ai_behavior** | `core` | `users`, `devices` |

## 🛠️ Customization

### Override Templates

```python
# In your project
TEMPLATES = [{
    'DIRS': [
        BASE_DIR / 'templates',  # Your custom templates first
    ],
}]
```

### Extend Models

```python
# your_app/models.py
from apps.blog.models import Post

class CustomPost(Post):
    extra_field = models.CharField(max_length=100)
    
    class Meta:
        proxy = True  # Or concrete inheritance
```

### Custom Settings

Most apps respect Django settings:

```python
# settings.py
BLOG_ENABLE_COMMENTS = True
BLOG_POSTS_PER_PAGE = 10
SEO_AUTO_META = True
```

## 📦 Distribution

### Create Standalone Package

```bash
# Package individual app
cd apps/blog
python setup.py sdist bdist_wheel

# Install from package
pip install dist/gsminfinity-blog-1.0.0.tar.gz
```

### Setup.py Template

```python
from setuptools import setup, find_packages

setup(
    name='gsminfinity-blog',
    version='1.0.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Django>=4.2',
        # ... app-specific requirements
    ],
)
```

## 🧪 Testing

Each app includes tests:

```bash
# Test individual app
python manage.py test apps.blog

# With pytest
pytest apps/blog/tests.py
```

## 📝 License

Each app is independently licensed. Check individual `LICENSE` files.

## 🤝 Contributing

See individual app README files for contribution guidelines.

## 📞 Support

- Documentation: Check each app's README.md
- Issues: Report app-specific issues with [APP_NAME] prefix
- Integration Help: See INTEGRATION.md in each app directory

## 🔄 Version Compatibility

| Django Version | Python Version | Status |
|----------------|----------------|--------|
| 4.2+ | 3.10+ | ✅ Supported |
| 5.0+ | 3.11+ | ✅ Supported |
| 5.2+ | 3.12+ | ✅ Supported |

## 📚 Additional Resources

- [Django Apps Documentation](https://docs.djangoproject.com/en/stable/ref/applications/)
- [Reusable Apps Guide](https://docs.djangoproject.com/en/stable/intro/reusable-apps/)
- [App Registry API](https://docs.djangoproject.com/en/stable/ref/applications/)
