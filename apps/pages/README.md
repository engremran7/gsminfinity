# 📄 Pages App

Static and dynamic page management system for custom content pages beyond blog posts.

## ✨ Features

- **Static Pages**: Create custom pages (About, Contact, FAQ)
- **Dynamic Content**: Page templates with dynamic data
- **Page Builder**: Visual page composition
- **SEO Integration**: Meta tags, Open Graph support
- **Versioning**: Track page revisions
- **Access Control**: Public/private pages
- **Custom Templates**: Override default templates per page
- **Slug Management**: Clean URLs for pages

## 📦 Installation

### 1. Copy App to Your Project

```bash
cp -r apps/pages /your_project/apps/
```

### 2. Add to INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    
    'apps.pages',
    
    # Optional integrations
    'apps.seo',  # For SEO metadata
    'apps.core',  # For base models
]
```

### 3. Configure URLs

```python
# urls.py - Add at the end to catch custom pages
from django.urls import path, include

urlpatterns = [
    # Other URL patterns
    path('', include('apps.pages.urls')),  # Catch-all for pages
]
```

### 4. Run Migrations

```bash
python manage.py makemigrations pages
python manage.py migrate pages
```

## ⚙️ Configuration

### Settings

```python
# settings.py

# Pages Configuration
PAGES_CONFIG = {
    'allow_html': True,  # Allow HTML in page content
    'enable_versioning': True,
    'default_template': 'pages/page_detail.html',
}
```

## 📚 Usage

### Create a Page

```python
from apps.pages.models import Page

page = Page.objects.create(
    title="About Us",
    slug="about",
    content="<h1>About Our Company</h1><p>We are...</p>",
    is_published=True
)
```

### In Templates

```django
<!-- List pages -->
{% for page in pages %}
    <a href="{% url 'pages:detail' slug=page.slug %}">
        {{ page.title }}
    </a>
{% endfor %}

<!-- Display page -->
<div class="page-content">
    {{ page.content|safe }}
</div>
```

## 📊 Models

### Page

```python
class Page(models.Model):
    title = CharField(max_length=200)
    slug = SlugField(unique=True)
    content = TextField()
    template = CharField(max_length=100, blank=True)
    is_published = BooleanField(default=False)
    published_at = DateTimeField(null=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

## 🎯 Views

```python
from django.views.generic import DetailView
from apps.pages.models import Page

class PageDetailView(DetailView):
    model = Page
    template_name = 'pages/page_detail.html'
    slug_field = 'slug'
    
    def get_queryset(self):
        return Page.objects.filter(is_published=True)
```

## 📄 License

MIT License

## 🤝 Dependencies

**Optional:**
- `apps.seo` - SEO metadata
- `apps.core` - Base models
