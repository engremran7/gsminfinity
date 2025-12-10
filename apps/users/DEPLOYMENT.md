# Users App - Deployment & Features Documentation

## 📋 Overview

**App Name:** `users`  
**Version:** 1.0.0  
**Django Version:** 4.2+  
**Type:** Authentication & User Management  
**Status:** Production Ready ✅

Enterprise-grade user authentication, profile management, social login, and account security system with device tracking and notification preferences.

---

## 🚀 Quick Start Deployment

### Prerequisites

- Python 3.10+
- Django 4.2+
- Django-allauth 0.54+
- Redis 6+ (for sessions)
- PostgreSQL 13+ (recommended)

### Installation Steps

1. **Add to INSTALLED_APPS**:

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    
    # Third-party auth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.github',
    
    # Project apps
    'apps.core',
    'apps.devices',           # Optional: Device tracking
    'apps.security_events',   # Optional: Security logging
    'apps.users',             # This app
]

SITE_ID = 1  # Required by django-allauth
```

2. **Install Dependencies**:

```bash
pip install django-allauth>=0.54.0
pip install Pillow>=10.0.0  # For avatar uploads
pip install django-crispy-forms>=2.0
pip install crispy-bootstrap5>=0.7
```

3. **Configure Authentication**:

```python
# settings.py
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

AUTH_USER_MODEL = 'auth.User'  # Or custom user model

# Allauth Configuration
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = True

LOGIN_URL = '/account/login/'
LOGIN_REDIRECT_URL = '/users/dashboard/'
LOGOUT_REDIRECT_URL = '/'
```

4. **Run Migrations**:

```bash
python manage.py migrate sites
python manage.py migrate allauth
python manage.py migrate users
```

5. **Configure Social Auth** (Optional):

```bash
# Create social app in admin
python manage.py shell
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

# Google OAuth
google_app = SocialApp.objects.create(
    provider='google',
    name='Google OAuth',
    client_id='YOUR_GOOGLE_CLIENT_ID',
    secret='YOUR_GOOGLE_CLIENT_SECRET'
)
google_app.sites.add(Site.objects.get_current())

# Facebook OAuth
facebook_app = SocialApp.objects.create(
    provider='facebook',
    name='Facebook Login',
    client_id='YOUR_FACEBOOK_APP_ID',
    secret='YOUR_FACEBOOK_APP_SECRET'
)
facebook_app.sites.add(Site.objects.get_current())
```

---

## 📦 Dependencies

### Required Packages

```txt
Django>=4.2.0,<5.0
django-allauth>=0.54.0
Pillow>=10.0.0
django-crispy-forms>=2.0
crispy-bootstrap5>=0.7
```

### Optional Packages

```txt
django-two-factor-auth>=1.15.0  # 2FA support
qrcode>=7.4.0  # For 2FA QR codes
django-password-validators>=1.7.0  # Enhanced password validation
```

### Required Django Apps

- `apps.core` - Base models and utilities
- `django.contrib.sites` - Required by allauth

### Optional Django Apps

- `apps.devices` - Device fingerprinting and trusted devices
- `apps.security_events` - Login/logout event logging
- `apps.ai_behavior` - Behavioral anomaly detection

---

## 🎯 Core Features

### 1. **Authentication**

- ✅ Email + Password login
- ✅ Username + Password login
- ✅ Social authentication (Google, Facebook, GitHub, Twitter)
- ✅ Email verification required
- ✅ "Remember Me" functionality
- ✅ Password reset via email
- ✅ Session management
- ✅ Two-factor authentication (2FA) optional

### 2. **User Registration**

- ✅ Email-based signup
- ✅ Username validation (3-32 chars, alphanumeric)
- ✅ Strong password requirements
- ✅ Email confirmation
- ✅ Anti-spam measures
- ✅ Terms of Service acceptance
- ✅ Welcome email

### 3. **Profile Management**

- ✅ Avatar upload with image optimization
- ✅ Bio and personal information
- ✅ Social media links
- ✅ Display name customization
- ✅ Timezone selection
- ✅ Language preference
- ✅ Privacy settings

### 4. **Account Security**

- ✅ Password change with old password verification
- ✅ Active session management (view/revoke)
- ✅ Login history tracking
- ✅ Suspicious activity detection
- ✅ Email alerts for security events
- ✅ Device recognition and management
- ✅ Account deletion with confirmation

### 5. **Notification Preferences**

- ✅ Email notification toggles
- ✅ Push notification settings
- ✅ Comment notifications
- ✅ Marketing email opt-in/out
- ✅ Weekly digest preferences
- ✅ Real-time notification center

### 6. **Dashboard**

- ✅ User activity overview
- ✅ Recent posts/comments
- ✅ Account statistics
- ✅ Quick actions
- ✅ Personalized recommendations
- ✅ Achievement badges (optional)

---

## 📐 Database Schema

### UserProfile Model (extends auth.User)

| Field | Type | Description |
|-------|------|-------------|
| `user` | OneToOneField(User) | Link to Django user |
| `avatar` | ImageField | Profile picture |
| `bio` | TextField | User biography (500 chars) |
| `website` | URLField | Personal website |
| `location` | CharField | City/country |
| `birth_date` | DateField | Date of birth (optional) |
| `timezone` | CharField | User timezone |
| `language` | CharField | Preferred language |
| `email_verified` | BooleanField | Email verification status |
| `is_public` | BooleanField | Public profile flag |
| `created_at` | DateTimeField | Account creation date |
| `updated_at` | DateTimeField | Last profile update |

### NotificationPreference Model

| Field | Type | Description |
|-------|------|-------------|
| `user` | OneToOneField(User) | User account |
| `email_comments` | BooleanField | Comment notifications |
| `email_replies` | BooleanField | Reply notifications |
| `email_mentions` | BooleanField | Mention notifications |
| `email_marketing` | BooleanField | Marketing emails |
| `email_digest` | BooleanField | Weekly digest |
| `push_enabled` | BooleanField | Push notifications |

### LoginHistory Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `user` | ForeignKey(User) | User account |
| `ip_address` | GenericIPAddressField | Login IP |
| `user_agent` | TextField | Browser/device info |
| `device_fingerprint` | CharField | Unique device ID |
| `location` | CharField | Geo-location |
| `success` | BooleanField | Login success/failure |
| `created_at` | DateTimeField | Login timestamp |

---

## 🔌 API Endpoints

### Authentication

```bash
# Registration
POST /api/users/register/
{
  "username": "johndoe",
  "email": "john@example.com",
  "password1": "SecurePass123!",
  "password2": "SecurePass123!"
}

# Login
POST /api/users/login/
{
  "email": "john@example.com",
  "password": "SecurePass123!"
}

# Logout
POST /api/users/logout/

# Password Reset
POST /api/users/password-reset/
{
  "email": "john@example.com"
}

# Password Reset Confirm
POST /api/users/password-reset-confirm/
{
  "token": "reset-token",
  "password1": "NewPass123!",
  "password2": "NewPass123!"
}
```

### Profile Management

```bash
# Get Profile
GET /api/users/profile/

# Update Profile
PUT /api/users/profile/
{
  "bio": "Software developer",
  "website": "https://example.com",
  "location": "San Francisco"
}

# Upload Avatar
POST /api/users/profile/avatar/
Content-Type: multipart/form-data

# Change Password
POST /api/users/change-password/
{
  "old_password": "OldPass123!",
  "new_password1": "NewPass456!",
  "new_password2": "NewPass456!"
}
```

### Social Authentication

```bash
# Google OAuth
GET /account/google/login/
GET /account/google/login/callback/

# Facebook OAuth
GET /account/facebook/login/
GET /account/facebook/login/callback/

# GitHub OAuth
GET /account/github/login/
GET /account/github/login/callback/
```

### Dashboard & Statistics

```bash
# User Dashboard
GET /api/users/dashboard/

# Activity Feed
GET /api/users/activity/

# Login History
GET /api/users/login-history/

# Active Sessions
GET /api/users/sessions/
DELETE /api/users/sessions/<session_id>/
```

---

## 🛠️ Configuration

### Required Settings

```python
# settings.py

# ===== USER APP CONFIGURATION =====

# Authentication
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

LOGIN_URL = '/account/login/'
LOGIN_REDIRECT_URL = '/users/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# Allauth Settings
ACCOUNT_AUTHENTICATION_METHOD = 'email'  # or 'username' or 'username_email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'  # or 'optional' or 'none'
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = True
ACCOUNT_USERNAME_MIN_LENGTH = 3
ACCOUNT_USERNAME_BLACKLIST = ['admin', 'root', 'support']

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'

# Password Validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Session Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_COOKIE_SECURE = True  # Production only
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Media Files (for avatars)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
AVATAR_MAX_SIZE = 5 * 1024 * 1024  # 5MB

# Social Auth (Google)
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'APP': {
            'client_id': env('GOOGLE_CLIENT_ID'),
            'secret': env('GOOGLE_CLIENT_SECRET'),
            'key': ''
        }
    },
    'facebook': {
        'METHOD': 'oauth2',
        'SCOPE': ['email', 'public_profile'],
        'FIELDS': ['id', 'email', 'name', 'first_name', 'last_name', 'picture'],
        'APP': {
            'client_id': env('FACEBOOK_APP_ID'),
            'secret': env('FACEBOOK_APP_SECRET'),
            'key': ''
        }
    }
}

# User Settings
USERS_ALLOW_REGISTRATION = True
USERS_REQUIRE_EMAIL_VERIFICATION = True
USERS_DEFAULT_AVATAR = '/static/img/default-avatar.svg'
USERS_ENABLE_2FA = False  # Requires django-two-factor-auth
```

### Environment Variables

```bash
# .env
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxx
FACEBOOK_APP_ID=1234567890
FACEBOOK_APP_SECRET=xxx
EMAIL_HOST_USER=noreply@yourdomain.com
EMAIL_HOST_PASSWORD=your-app-password
```

---

## 🔐 Security Features

### Password Security

```python
# Strong password requirements enforced
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    # Include uppercase, lowercase, numbers, symbols
]

# Password hashing (default: PBKDF2)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',  # Recommended
]
```

### Account Security

```python
from apps.users.services import SecurityService

# Check for suspicious login
security = SecurityService()
if security.is_suspicious_login(user, request):
    # Send verification email
    security.send_login_alert(user, request)
    
# Revoke all sessions (force logout everywhere)
security.revoke_all_sessions(user)

# Enable 2FA
security.enable_2fa(user)
```

---

## 🚢 Production Deployment

### Nginx Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Media files (avatars)
    location /media/ {
        alias /path/to/gsminfinity/media/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Rate limit auth endpoints
    location /account/ {
        limit_req zone=auth burst=5 nodelay;
        proxy_pass http://127.0.0.1:8000;
    }
}
```

### Celery Tasks

```python
# apps/users/tasks.py
from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_welcome_email(user_id):
    from django.contrib.auth.models import User
    user = User.objects.get(id=user_id)
    
    send_mail(
        'Welcome to GSM Infinity!',
        f'Hello {user.username}, welcome aboard!',
        'noreply@gsminf inity.com',
        [user.email],
        fail_silently=False,
    )

@shared_task
def cleanup_unverified_accounts():
    """Delete accounts not verified within 7 days"""
    from django.utils import timezone
    from datetime import timedelta
    from apps.users.models import UserProfile
    
    cutoff = timezone.now() - timedelta(days=7)
    unverified = UserProfile.objects.filter(
        email_verified=False,
        created_at__lt=cutoff
    )
    
    for profile in unverified:
        profile.user.delete()
```

---

## 📚 Additional Resources

- [Django Authentication Docs](https://docs.djangoproject.com/en/4.2/topics/auth/)
- [Django-allauth Documentation](https://django-allauth.readthedocs.io/)
- [OAuth 2.0 Guide](https://oauth.net/2/)

**Version:** 1.0.0  
**Last Updated:** 2024-12-10  
**Maintained By:** GSM Infinity Development Team
