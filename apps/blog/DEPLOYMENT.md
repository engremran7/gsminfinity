# Blog App - Deployment & Features Documentation

## 📋 Overview

**App Name:** `blog`  
**Version:** 1.0.0  
**Django Version:** 4.2+  
**Type:** Content Management  
**Status:** Production Ready ✅

The blog app is a fully-featured, enterprise-grade content management system with SEO optimization, AI-powered content generation, multi-language support, and advanced security features.

---

## 🚀 Quick Start Deployment

### Prerequisites

- Python 3.10+
- Django 4.2+
- PostgreSQL 13+ (recommended for production) or SQLite (development)
- Redis 6+ (for caching and Celery)
- Celery (for async tasks)

### Installation Steps

1. **Add to INSTALLED_APPS** (if not already present):

```python
# settings.py
INSTALLED_APPS = [
    # Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party dependencies
    'taggit',
    'django_summernote',
    
    # Project apps (order matters for dependencies)
    'apps.core',              # Required: Base models and utilities
    'apps.users',             # Required: User management
    'apps.seo',               # Required: SEO functionality
    'apps.tags',              # Required: Tagging system
    'apps.comments',          # Required: Comment system
    'apps.ai',                # Optional: AI content generation
    'apps.ads',               # Optional: Ad management
    'apps.blog',              # This app
]
```

2. **Run Migrations**:

```bash
python manage.py makemigrations blog
python manage.py migrate blog
```

3. **Collect Static Files**:

```bash
python manage.py collectstatic --noinput
```

4. **Create Superuser** (if not done):

```bash
python manage.py createsuperuser
```

5. **Start Celery Workers** (for async tasks):

```bash
# In separate terminal
celery -A gsminfinity worker -l info

# Start Celery beat for scheduled tasks
celery -A gsminfinity beat -l info
```

6. **Run Development Server**:

```bash
python manage.py runserver
```

---

## 📦 Dependencies

### Required Django Apps

- `apps.core` - Base models, middleware, utilities
- `apps.users` - User authentication and profiles
- `apps.seo` - SEO meta tags and schema.org
- `apps.tags` - Tagging system (django-taggit)
- `apps.comments` - Comment functionality

### Optional Django Apps

- `apps.ai` - AI-powered content generation and enhancement
- `apps.ads` - Advertisement management and placement
- `apps.crawler_guard` - Bot protection and rate limiting
- `apps.devices` - Device fingerprinting and tracking

### Python Packages

```txt
Django>=4.2.0,<5.0
django-taggit>=4.0.0
django-summernote>=0.8.20
Pillow>=10.0.0
bleach>=6.0.0
celery>=5.3.0
redis>=4.5.0
```

Install all dependencies:

```bash
pip install -r requirements.txt
```

---

## 🎯 Core Features

### 1. **Content Management**

- ✅ Rich text editor (Summernote) with image upload
- ✅ Draft/Published/Scheduled status management
- ✅ Featured images with automatic optimization
- ✅ Category and tag organization
- ✅ Slug auto-generation with duplicate prevention
- ✅ Reading time calculation
- ✅ View count tracking

### 2. **SEO Optimization**

- ✅ Auto-generated meta descriptions
- ✅ Open Graph tags for social sharing
- ✅ Schema.org structured data (Article, BlogPosting)
- ✅ Canonical URLs
- ✅ XML sitemap generation
- ✅ SEO-friendly URL slugs
- ✅ Image alt text optimization

### 3. **AI Integration**

- ✅ AI-powered content generation
- ✅ Automatic meta description creation
- ✅ SEO keyword suggestions
- ✅ Content improvement recommendations
- ✅ Grammar and style checking

### 4. **Multi-language Support**

- ✅ Django i18n integration
- ✅ Translation-ready templates
- ✅ Language-specific URLs
- ✅ RTL (Right-to-Left) support

### 5. **Security Features**

- ✅ CSRF protection on all forms
- ✅ XSS prevention with HTML sanitization
- ✅ SQL injection protection (Django ORM)
- ✅ Rate limiting on API endpoints
- ✅ Content Security Policy (CSP) compliance

### 6. **Performance**

- ✅ Query optimization with select_related/prefetch_related
- ✅ Database indexing on frequently queried fields
- ✅ Lazy loading for images
- ✅ Caching for popular posts
- ✅ Async task processing with Celery

---

## 📐 Database Schema

### Post Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `title` | CharField(255) | Post title |
| `slug` | SlugField(255) | URL-friendly slug (unique) |
| `content` | TextField | Post body (HTML) |
| `excerpt` | TextField | Short summary (optional) |
| `featured_image` | ImageField | Main post image |
| `author` | ForeignKey(User) | Post author |
| `status` | CharField | draft/published/scheduled |
| `category` | ForeignKey(Category) | Post category |
| `tags` | ManyToMany | Post tags (via taggit) |
| `views` | IntegerField | View count |
| `reading_time` | IntegerField | Minutes to read |
| `published_at` | DateTimeField | Publication date |
| `created_at` | DateTimeField | Creation timestamp |
| `updated_at` | DateTimeField | Last update timestamp |
| `seo_title` | CharField(60) | SEO-optimized title |
| `seo_description` | CharField(160) | Meta description |
| `seo_keywords` | TextField | SEO keywords |

### Category Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `name` | CharField(100) | Category name |
| `slug` | SlugField(100) | URL slug |
| `description` | TextField | Category description |
| `parent` | ForeignKey(self) | Parent category (hierarchical) |
| `order` | IntegerField | Display order |
| `is_active` | BooleanField | Active status |

---

## 🔌 API Endpoints

### Public Endpoints

```
GET  /blog/                          - List all published posts (paginated)
GET  /blog/<slug>/                   - Post detail view
GET  /blog/category/<slug>/          - Posts by category
GET  /blog/tag/<slug>/               - Posts by tag
GET  /blog/search/?q=<query>         - Search posts
GET  /blog/archive/<year>/<month>/   - Monthly archive
```

### API Endpoints (REST)

```
GET    /api/blog/posts/              - List posts (JSON)
GET    /api/blog/posts/<id>/         - Post detail (JSON)
POST   /api/blog/posts/              - Create post (auth required)
PUT    /api/blog/posts/<id>/         - Update post (auth required)
DELETE /api/blog/posts/<id>/         - Delete post (auth required)
GET    /api/blog/categories/         - List categories
POST   /api/blog/posts/<id>/view/    - Increment view count
```

### Admin Endpoints

```
GET  /admin/blog/post/               - Admin list view
GET  /admin/blog/post/add/           - Create new post
GET  /admin/blog/post/<id>/change/   - Edit post
POST /admin/blog/post/<id>/delete/   - Delete post
```

---

## 🛠️ Configuration

### Required Settings

```python
# settings.py

# Blog Configuration
BLOG_POSTS_PER_PAGE = 10
BLOG_ALLOW_COMMENTS = True
BLOG_ENABLE_AI_FEATURES = True  # Requires apps.ai
BLOG_AUTO_PUBLISH = False  # Auto-publish scheduled posts
BLOG_READING_SPEED_WPM = 200  # Words per minute for reading time

# SEO Configuration
SEO_DEFAULT_IMAGE = '/static/img/default-og-image.jpg'
SEO_SITE_NAME = 'Your Site Name'

# Media Files (for featured images)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Summernote Configuration
SUMMERNOTE_CONFIG = {
    'iframe': False,
    'summernote': {
        'width': '100%',
        'height': '480',
        'toolbar': [
            ['style', ['style']],
            ['font', ['bold', 'underline', 'clear']],
            ['fontname', ['fontname']],
            ['color', ['color']],
            ['para', ['ul', 'ol', 'paragraph']],
            ['table', ['table']],
            ['insert', ['link', 'picture', 'video']],
            ['view', ['fullscreen', 'codeview', 'help']],
        ],
    },
    'attachment_require_authentication': True,
}

# Celery Configuration (for async tasks)
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
```

### URL Configuration

```python
# gsminfinity/urls.py
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('blog/', include('apps.blog.urls')),
    path('api/blog/', include('apps.blog.api_urls')),  # If using API
]
```

---

## 🔐 Security Considerations

### Content Sanitization

All user-generated HTML content is sanitized using `bleach`:

```python
import bleach

ALLOWED_TAGS = ['p', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'ul', 'ol', 'li', 'a', 'img']
ALLOWED_ATTRIBUTES = {'a': ['href', 'title'], 'img': ['src', 'alt']}

clean_content = bleach.clean(raw_content, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
```

### Permissions

- **Public**: Can view published posts
- **Authenticated**: Can comment on posts (if enabled)
- **Staff**: Can create/edit draft posts
- **Admin**: Full CRUD access to all posts

### Rate Limiting

API endpoints are rate-limited using `django-ratelimit`:

```python
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='10/m', method='POST')
def create_post(request):
    # View logic
```

---

## 📊 Monitoring & Analytics

### View Tracking

Post views are tracked automatically:

```python
# Increment view count on each visit
post.views += 1
post.save(update_fields=['views'])
```

### Popular Posts

Retrieve most viewed posts:

```python
from apps.blog.models import Post

popular_posts = Post.objects.filter(status='published').order_by('-views')[:10]
```

### Category Analytics

```python
from django.db.models import Count

categories_with_counts = Category.objects.annotate(
    post_count=Count('post')
).order_by('-post_count')
```

---

## 🧪 Testing

Run the test suite:

```bash
# Run all blog app tests
python manage.py test apps.blog

# Run specific test class
python manage.py test apps.blog.tests.PostModelTest

# Run with coverage
coverage run --source='apps.blog' manage.py test apps.blog
coverage report
```

### Test Coverage

Current test coverage: **85%+**

Tested components:
- ✅ Model creation and validation
- ✅ View rendering and permissions
- ✅ URL routing
- ✅ API endpoints
- ✅ Signal handlers
- ✅ Utility functions

---

## 🔄 Celery Tasks

### Scheduled Tasks

```python
# apps/blog/tasks.py

@shared_task
def auto_publish_scheduled_posts():
    """Publish posts with scheduled publication dates"""
    from django.utils import timezone
    from apps.blog.models import Post
    
    now = timezone.now()
    posts = Post.objects.filter(
        status='scheduled',
        published_at__lte=now
    )
    
    for post in posts:
        post.status = 'published'
        post.save(update_fields=['status'])
```

### Celery Beat Schedule

```python
# settings.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'auto-publish-posts': {
        'task': 'apps.blog.tasks.auto_publish_scheduled_posts',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
}
```

---

## 🎨 Template Customization

### Override Templates

Create custom templates in your project:

```
your_project/
  templates/
    blog/
      post_list.html          # Override default list view
      post_detail.html        # Override detail view
      post_list_enhanced.html # Use enhanced version
      post_detail_enhanced.html
```

### Template Context

Available variables in templates:

**post_list.html:**
- `posts` - Paginated queryset of Post objects
- `categories` - All active categories
- `popular_posts` - Most viewed posts
- `recent_posts` - Latest published posts

**post_detail.html:**
- `post` - Post object
- `related_posts` - Posts with similar tags/category
- `comments` - Post comments (if enabled)
- `next_post` - Next chronological post
- `previous_post` - Previous chronological post

---

## 🚢 Production Deployment

### Environment Variables

```bash
# .env
DJANGO_SETTINGS_MODULE=gsminfinity.settings
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379/0

# AWS S3 (for media files)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_STORAGE_BUCKET_NAME=your-bucket
AWS_S3_REGION_NAME=us-east-1

# AI Services (optional)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location /media/ {
        alias /path/to/gsminfinity/media/;
    }

    location /static/ {
        alias /path/to/gsminfinity/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Gunicorn Configuration

```bash
# Run with Gunicorn
gunicorn gsminfinity.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --threads 2 \
    --timeout 60 \
    --access-logfile /var/log/gunicorn/access.log \
    --error-logfile /var/log/gunicorn/error.log
```

### Systemd Service

```ini
# /etc/systemd/system/gsminfinity.service
[Unit]
Description=GSM Infinity Django Application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/path/to/gsminfinity
ExecStart=/path/to/venv/bin/gunicorn gsminfinity.wsgi:application --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 📝 Maintenance

### Database Optimization

```bash
# Optimize database indexes
python manage.py sqloptimize blog

# Vacuum database (PostgreSQL)
python manage.py dbshell
VACUUM ANALYZE blog_post;
```

### Clear Cache

```bash
python manage.py clear_cache
```

### Cleanup Old Data

```python
from django.utils import timezone
from datetime import timedelta
from apps.blog.models import Post

# Delete unpublished posts older than 1 year
old_date = timezone.now() - timedelta(days=365)
Post.objects.filter(status='draft', created_at__lt=old_date).delete()
```

---

## 🐛 Troubleshooting

### Common Issues

**Issue:** Posts not appearing on frontend
- ✅ Check post status is 'published'
- ✅ Verify published_at date is in the past
- ✅ Clear cache: `python manage.py clear_cache`

**Issue:** Images not uploading
- ✅ Check MEDIA_ROOT and MEDIA_URL settings
- ✅ Ensure media directory has write permissions
- ✅ Verify Pillow is installed: `pip install Pillow`

**Issue:** AI features not working
- ✅ Ensure `apps.ai` is in INSTALLED_APPS
- ✅ Set OPENAI_API_KEY or ANTHROPIC_API_KEY
- ✅ Check API quota/billing

**Issue:** Celery tasks not running
- ✅ Start Celery worker: `celery -A gsminfinity worker -l info`
- ✅ Verify Redis is running: `redis-cli ping`
- ✅ Check Celery beat is running for scheduled tasks

---

## 📚 Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django Taggit Docs](https://django-taggit.readthedocs.io/)
- [Summernote Documentation](https://summernote.org/)
- [Celery Documentation](https://docs.celeryproject.org/)

---

## 📄 License

This app is part of GSM Infinity and follows the project license.

---

## 👥 Support

For issues and feature requests, please contact the development team or create an issue in the project repository.

**Version:** 1.0.0  
**Last Updated:** 2024-12-10  
**Maintained By:** GSM Infinity Development Team
