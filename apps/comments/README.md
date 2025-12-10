# 💬 Comments App

A pluggable Django app for managing comments with AI-powered moderation, spam detection, and consent-aware tracking.

## ✨ Features

- **Comment Management**: Create, edit, moderate, and soft-delete comments
- **AI Moderation**: Automatic toxicity detection and content classification
- **Spam Detection**: AI-powered spam flagging
- **Consent Aware**: Respects GDPR/CCPA consent preferences
- **Rate Limiting**: Built-in rate limiting per user
- **Moderation Dashboard**: Admin and staff moderation interfaces
- **Status Workflow**: Approved, Pending, Rejected, Spam statuses
- **Soft Deletion**: Comments are soft-deleted, not permanently removed

## 📦 Installation

### 1. Copy App to Your Project

```bash
cp -r apps/comments /your_project/apps/
```

### 2. Install Dependencies

```bash
pip install django-solo  # Optional, for settings model
```

### 3. Add to INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    # Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    
    # Your apps
    'apps.comments',
    
    # Optional integrations
    'apps.consent',      # For consent-aware features
    'apps.core',         # For AI client and utilities
    'apps.ai_behavior',  # For behavior analysis
]
```

### 4. Configure URLs

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    path('comments/', include('apps.comments.urls')),
]
```

### 5. Run Migrations

```bash
python manage.py makemigrations comments
python manage.py migrate comments
```

## ⚙️ Configuration

### Required Settings

```python
# settings.py

# Optional: Comment settings (if using solo)
COMMENTS_ENABLE_AI_MODERATION = True
COMMENTS_ALLOW_ANONYMOUS = False
```

### Environment Variables

```bash
# .env
OPENAI_API_KEY=your_openai_key  # For AI moderation
ANTHROPIC_API_KEY=your_anthropic_key  # Alternative AI provider
```

## 📚 Usage

### Basic Usage

```python
from apps.comments.models import Comment
from apps.blog.models import Post

# Create a comment
post = Post.objects.get(slug='my-post')
comment = Comment.objects.create(
    post=post,
    user=request.user,
    body="Great article!",
    status=Comment.Status.APPROVED
)

# Moderate comment
comment.status = Comment.Status.REJECTED
comment.save()

# Soft delete
comment.is_deleted = True
comment.save()
```

### In Templates

```django
{% load static %}

<form method="post" action="{% url 'comments:add' slug=post.slug %}">
    {% csrf_token %}
    <textarea name="body" rows="4" required></textarea>
    <button type="submit" class="btn-primary">Post Comment</button>
</form>

<!-- Display comments -->
{% for comment in comments %}
    <div class="comment">
        <p>{{ comment.body }}</p>
        <small>By {{ comment.user }} on {{ comment.created_at }}</small>
    </div>
{% endfor %}
```

### Views

```python
from apps.comments.views import add_comment, list_comments, moderation_view

# Add to your URLs
urlpatterns = [
    path('comments/add/<slug:slug>/', add_comment, name='add_comment'),
    path('comments/list/<slug:slug>/', list_comments, name='list_comments'),
    path('comments/moderation/', moderation_view, name='moderation'),
]
```

## 🔗 Integration with Other Apps

### With Blog App

```python
# apps/blog/models.py
from django.db import models

class Post(models.Model):
    allow_comments = models.BooleanField(default=True)
    
    def get_approved_comments(self):
        return self.comments.filter(
            status='approved',
            is_deleted=False
        ).order_by('-created_at')
```

### With Consent App

The app automatically checks consent if `apps.consent` is installed:

```python
from apps.consent.decorators import consent_required

@consent_required(["functional", "comments"])
def add_comment(request, slug):
    # Only allows users who consented to functional & comments cookies
    pass
```

### With AI Behavior App

Comments are analyzed for anomalies when `apps.ai_behavior` is present:

```python
from apps.ai_behavior.services import track_behavior

# Automatically tracks comment posting patterns
```

## 🤖 AI Moderation

### Enable AI Moderation

```python
# apps/comments/models.py
class CommentSettings(SingletonModel):
    enable_ai_moderation = models.BooleanField(default=True)
```

### Moderation Service

```python
from apps.comments.services.moderation import classify_comment

result = classify_comment(comment_text)
# Returns: {
#     'label': 'safe' | 'spam' | 'toxic',
#     'toxicity_score': 0.0 to 1.0,
#     'reason': 'explanation'
# }
```

## 🎨 Admin Customization

### Custom Admin Template

The app includes a custom admin change_list template at:
```
apps/comments/templates/admin/comments/comment/change_list.html
```

### Admin Actions

- Mark as Approved
- Mark as Rejected
- Mark as Spam
- Soft Delete

### Filters

- Status (Approved, Pending, Rejected, Spam)
- Created Date
- User
- Post

## 📊 Models

### Comment Model

```python
class Comment(models.Model):
    post = ForeignKey  # Can be any model with comments
    user = ForeignKey('auth.User')
    body = TextField
    status = CharField  # approved, pending, rejected, spam
    is_approved = BooleanField
    is_deleted = BooleanField
    toxicity_score = FloatField
    moderation_flags = JSONField
    created_at = DateTimeField
    updated_at = DateTimeField
```

### CommentSettings Model

```python
class CommentSettings(SingletonModel):
    enable_comments = BooleanField
    allow_anonymous = BooleanField
    enable_ai_moderation = BooleanField
```

## 🔒 Security Features

### Rate Limiting

```python
from apps.comments.views import _check_comment_rate_limit

# Limits: 5 comments per 5 minutes per user
if not _check_comment_rate_limit(request):
    return HttpResponseBadRequest("Too many comments")
```

### Honeypot Protection

```html
<input type="text" name="hp" class="hidden" tabindex="-1">
```

### CSRF Protection

All comment forms require CSRF tokens.

### Content Sanitization

Comment bodies are automatically sanitized to prevent XSS.

## 🧪 Testing

```python
# tests.py
from django.test import TestCase
from apps.comments.models import Comment

class CommentTestCase(TestCase):
    def test_comment_creation(self):
        comment = Comment.objects.create(
            body="Test comment",
            status=Comment.Status.APPROVED
        )
        self.assertTrue(comment.is_approved)
```

Run tests:

```bash
python manage.py test apps.comments
```

## 🎯 API Endpoints

### POST /comments/add/<slug>/
Create a new comment

**Request:**
```json
{
    "body": "Comment text",
    "hp": ""  // Honeypot field
}
```

### GET /comments/list/<slug>/
List comments for a post (JSON)

**Response:**
```json
{
    "comments": [
        {
            "id": 1,
            "body": "Comment text",
            "user": "username",
            "created_at": "2025-12-10T10:00:00Z"
        }
    ]
}
```

### POST /comments/moderation-action/
Moderate a comment (staff only)

## 🚀 Performance

### Optimization Tips

1. **Use select_related for users**:
```python
comments = Comment.objects.select_related('user').filter(post=post)
```

2. **Cache comment counts**:
```python
from django.core.cache import cache
count = cache.get(f'post_{post.id}_comments')
```

3. **Paginate comments**:
```python
from django.core.paginator import Paginator
paginator = Paginator(comments, 20)
```

## 📝 Optional Dependencies

| Package | Purpose | Required |
|---------|---------|----------|
| `django-solo` | Settings model | Optional |
| `apps.consent` | GDPR compliance | Optional |
| `apps.core` | AI client | Optional |
| `apps.ai_behavior` | Behavior tracking | Optional |

## 🔄 Migration from Other Comment Systems

### From Django Comments Framework

```python
from django_comments.models import Comment as OldComment
from apps.comments.models import Comment as NewComment

for old in OldComment.objects.all():
    NewComment.objects.create(
        body=old.comment,
        user=old.user,
        created_at=old.submit_date,
        is_approved=not old.is_removed
    )
```

## 🛠️ Customization

### Custom Comment Model

```python
from apps.comments.models import Comment

class BlogComment(Comment):
    rating = models.IntegerField(default=0)
    
    class Meta:
        proxy = True
```

### Custom Moderation Logic

```python
from apps.comments.services import moderation

def custom_classify(text):
    # Your custom logic
    return {'label': 'safe', 'toxicity_score': 0.0}

# Override in services/moderation.py
```

## 📞 Support

- GitHub Issues: Tag with `[comments]`
- Documentation: See inline code comments
- Examples: Check `tests.py`

## 📄 License

MIT License - See LICENSE file

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Add tests
5. Submit pull request

## 📚 Related Apps

- `apps.blog` - Blog posts with comments
- `apps.consent` - GDPR consent management
- `apps.ai_behavior` - Behavioral analysis
- `apps.core` - Shared utilities
