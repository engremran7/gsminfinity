# 📝 App Registry

Dynamic app discovery, registration, and status management for all Django apps in the project.

## ✨ Features

- **Automatic App Discovery**: Finds all installed apps
- **App Metadata**: Store app descriptions, versions, dependencies
- **Status Tracking**: Active/inactive app toggling
- **Dependency Management**: Track inter-app dependencies
- **Health Checks**: Monitor app health and availability
- **Admin Interface**: Manage apps via Django admin
- **API Endpoints**: RESTful API for app management
- **Plugin System**: Support for pluggable architecture

## 📦 Installation

### 1. Copy App to Your Project

```bash
cp -r apps/app_registry /your_project/apps/
```

### 2. Add to INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    
    'apps.app_registry',  # Add early for app discovery
    
    # Other apps
    'apps.blog',
    'apps.users',
    # ...
]
```

### 3. Configure URLs

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    path('api/app-registry/', include('apps.app_registry.urls')),
]
```

### 4. Run Migrations

```bash
python manage.py makemigrations app_registry
python manage.py migrate app_registry
```

### 5. Discover Apps

```bash
python manage.py discover_apps
```

## ⚙️ Configuration

### Settings

```python
# settings.py

# App Registry Configuration
APP_REGISTRY_CONFIG = {
    'auto_discover': True,  # Automatically discover apps on startup
    'track_health': True,   # Monitor app health
    'enable_api': True,     # Enable REST API
}

# Apps to exclude from registry
APP_REGISTRY_EXCLUDE = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
```

## 📚 Usage

### Register Apps Programmatically

```python
from apps.app_registry.models import AppRegistry

# Register an app
app = AppRegistry.objects.create(
    name='blog',
    display_name='Blog System',
    description='Content management for blog posts',
    version='1.0.0',
    is_active=True,
    dependencies=['core', 'users']
)
```

### Check App Status

```python
from apps.app_registry.services import is_app_active

if is_app_active('blog'):
    # Blog app is active
    pass
```

### Get App Info

```python
from apps.app_registry.services import get_app_info

info = get_app_info('blog')
# Returns: {
#     'name': 'blog',
#     'display_name': 'Blog System',
#     'is_active': True,
#     'dependencies': ['core', 'users'],
#     'version': '1.0.0'
# }
```

### List All Apps

```python
from apps.app_registry.services import list_all_apps

apps = list_all_apps()
for app in apps:
    print(f"{app.display_name}: {app.is_active}")
```

## 📊 Models

### AppRegistry

```python
class AppRegistry(models.Model):
    name = CharField(max_length=100, unique=True)
    display_name = CharField(max_length=200)
    description = TextField(blank=True)
    version = CharField(max_length=50, blank=True)
    is_active = BooleanField(default=True)
    dependencies = JSONField(default=list)  # List of app names
    health_status = CharField(max_length=20, default='healthy')
    last_check = DateTimeField(null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

## 🎯 API Endpoints

### GET /api/app-registry/
List all registered apps

**Response:**
```json
{
    "apps": [
        {
            "name": "blog",
            "display_name": "Blog System",
            "is_active": true,
            "version": "1.0.0"
        }
    ]
}
```

### GET /api/app-registry/{name}/
Get app details

### POST /api/app-registry/{name}/activate/
Activate an app

### POST /api/app-registry/{name}/deactivate/
Deactivate an app

## 🔗 Integration

### With Core App

```python
# Check app dependencies before operations
from apps.app_registry.services import check_dependencies

if not check_dependencies('blog'):
    raise Exception("Required dependencies not met")
```

## 🧪 Testing

```python
from django.test import TestCase
from apps.app_registry.models import AppRegistry

class AppRegistryTestCase(TestCase):
    def test_app_registration(self):
        app = AppRegistry.objects.create(
            name='test_app',
            display_name='Test App'
        )
        self.assertTrue(app.is_active)
```

## 📝 Management Commands

```bash
# Discover all apps
python manage.py discover_apps

# Check app health
python manage.py check_app_health

# List registered apps
python manage.py list_apps
```

## 📄 License

MIT License
