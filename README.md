# 🚀 GSM Infinity - Enterprise Django Platform

<div align="center">

![Django](https://img.shields.io/badge/django-5.2.8-green?style=for-the-badge&logo=django)
![Python](https://img.shields.io/badge/python-3.11%2B-blue?style=for-the-badge&logo=python)
![License](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)
![Coverage](https://codecov.io/gh/engremran7/gsminfinity/branch/main/graph/badge.svg)

**A modern, feature-rich Django platform with enterprise-grade architecture, AI integration, and comprehensive security**

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#️-architecture) • [API](#-api-documentation) • [Contributing](#-contributing)

</div>

---

## 🌟 Features

### **Core Features**
- 📝 **Blog System**: Full-featured blog with categories, tags, comments, and rich content management
- 💬 **Advanced Comments**: 8 reaction types, voting, threading, moderation, awards, bookmarks, analytics
- 🏷️ **Smart Tags**: AI-powered suggestions, trending analysis, relationships, subscriptions, collections
- 📢 **Advertising System**: Ad management with placement targeting, performance tracking
- 🔐 **Security Suite**: Multi-layer defense with crawler guard, AI behavior analysis, device management
- 🤖 **AI Integration**: Content generation, moderation, tag suggestions, OpenAI/Anthropic support
- 🌍 **Internationalization**: Multi-language support with theme customization
- 📜 **Consent Management**: GDPR-compliant cookie and privacy consent
- 🔍 **SEO Optimization**: Meta management, sitemaps, structured data

### **Enterprise Features**
- 🎯 **Event-Driven Architecture**: EventBus for decoupled component communication
- 📊 **Metrics & Analytics**: Real-time tracking with MetricsCollector
- 🔄 **Queue System**: Background task processing (Celery/Django-Q/Sync modes)
- 📧 **Email Service**: Multi-backend email with templating and queuing
- 💾 **Storage Service**: Pluggable storage (Local/S3/GCS/Azure)
- 🪝 **Webhooks**: Outbound webhook management with retry logic
- 🎨 **Admin Suite**: Modern, CSP-compliant admin interface with dashboards
- 📦 **App Registry**: Dynamic app discovery and feature management

### **Comment System Features** (NEW)
- ✨ **8 Reaction Types**: like, love, insightful, funny, celebrate, support, curious, disagree
- 👍 **Voting System**: Upvote/downvote with karma tracking
- 🌳 **Threading**: Unlimited depth with materialized thread metadata
- 🤖 **AI Moderation**: Toxicity scoring and auto-actions
- 🏆 **Gamification**: 8 award types (gold, silver, bronze, helpful, etc.)
- 📊 **Analytics**: 12 metrics including engagement and quality scores
- 🔖 **Bookmarks**: Save comments with personal notes
- 📝 **Edit History**: Complete audit trail with edit reasons
- 🚩 **Flagging**: User-generated moderation with 7 reason types
- 💬 **@Mentions**: Auto-detection with notifications

### **Tag System Features** (NEW)
- �� **Trending Analysis**: 4 time periods (hourly, daily, weekly, monthly)
- 🤖 **AI Suggestions**: Confidence-scored tag recommendations
- 🔗 **Relationships**: 6 types (synonym, related, broader, narrower, etc.)
- 📧 **Subscriptions**: 4 notification frequencies (instant, daily, weekly, never)
- 🎨 **Categories**: Organized tag groups with colors and icons
- 📚 **Collections**: User-curated tag playlists
- ♻️ **Merge System**: Tag consolidation with automatic redirects
- 🚫 **Blacklist**: Prevent inappropriate tags with regex support
- 📈 **Analytics**: Usage tracking, growth rates, quality scoring
- 🔎 **Aliases**: Alternative names with automatic suggestions

---

## 🏗️ Architecture

### **Project Structure**
```
gsminfinity/
├── apps/                      # Modular Django apps
│   ├── core/                  # Shared infrastructure
│   │   ├── infrastructure/    # Queue, Storage, Email services
│   │   ├── events/            # EventBus system
│   │   ├── metrics/           # Analytics collector
│   │   ├── webhooks/          # Webhook management
│   │   └── utils/             # Text, Date, Security utilities
│   ├── blog/                  # Blog system
│   │   ├── models.py          # Post, Category models
│   │   ├── services/          # PostService, AIEditor
│   │   └── api.py             # REST endpoints
│   ├── comments/              # Comment system
│   │   ├── models.py          # Comment model
│   │   ├── models_enhanced.py # 10 new models
│   │   ├── services/          # CommentService
│   │   ├── api_enhanced.py    # 9 REST endpoints
│   │   └── tasks.py           # Background processing
│   ├── tags/                  # Tag system
│   │   ├── models.py          # Tag model
│   │   ├── models_enhanced.py # 11 new models
│   │   ├── services/          # TagService
│   │   ├── api_enhanced.py    # 14 REST endpoints
│   │   └── tasks.py           # Trending tasks
│   └── ...                    # 20+ other apps
└── manage.py                  # Django CLI
```

### **Three-Layer Security Model**
1. **Crawler Guard**: Bot detection, rate limiting
2. **AI Behavior Engine**: Behavioral anomaly detection
3. **Device Management**: Device fingerprinting and trust

---

## 🚀 Installation

### **Quick Start**

1. **Clone & Setup**
```bash
git clone https://github.com/engremran7/gsminfinity.git
cd gsminfinity
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

2. **Configure**
```bash
cp .env.sample .env
# Edit .env with your settings
```

3. **Database**
```bash
python manage.py migrate
python manage.py createsuperuser
```

4. **Run**
```bash
python manage.py collectstatic --noinput
python manage.py runserver
```

5. **Visit**
- Frontend: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/
- Admin Suite: http://127.0.0.1:8000/admin-suite/

---

## 📡 API Documentation

### **Comment API Endpoints (9 Total)**

#### **List Comments**
```http
GET /api/comments/?content_type=1&object_id=123&sort=score&page=1

Query Parameters:
- content_type: ContentType ID
- object_id: Object ID
- sort: score, created, updated (default: created)
- page: Page number for pagination
```

#### **Create Comment**
```http
POST /api/comments/create/
Content-Type: application/json

{
  "content_type": 1,
  "object_id": 123,
  "body": "Great post!",
  "parent": null  # Optional: parent comment ID for threading
}
```

#### **React to Comment**
```http
POST /api/comments/{id}/react/
Content-Type: application/json

{
  "reaction_type": "insightful"  # like, love, insightful, funny, celebrate, support, curious, disagree
}
```

#### **Vote on Comment**
```http
POST /api/comments/{id}/vote/
Content-Type: application/json

{
  "vote": 1  # 1 for upvote, -1 for downvote
}
```

#### **Flag Comment**
```http
POST /api/comments/{id}/flag/
Content-Type: application/json

{
  "reason": "spam",  # spam, harassment, hate_speech, off_topic, misinformation, nsfw, other
  "details": "This is spam content"
}
```

#### **Bookmark Comment**
```http
POST /api/comments/{id}/bookmark/
Content-Type: application/json

{
  "notes": "Great insight to remember"  # Optional personal notes
}
```

#### **Moderate Comment** (Staff Only)
```http
POST /api/comments/{id}/moderate/
Content-Type: application/json

{
  "action": "approve",  # approve, reject, delete, spam, lock, unlock, pin, unpin, hide, unhide
  "reason": "Quality content"
}
```

#### **Get Comment Thread**
```http
GET /api/comments/{id}/thread/?max_depth=10&sort=score

Query Parameters:
- max_depth: Maximum thread depth (default: 10)
- sort: score, created (default: score)
```

#### **Get Top Comments**
```http
GET /api/comments/top/?content_type=1&object_id=123&period=week&limit=10

Query Parameters:
- content_type: ContentType ID
- object_id: Object ID
- period: hour, day, week, month, all (default: all)
- limit: Number of results (default: 10)
```

---

### **Tag API Endpoints (14 Total)**

#### **Search Tags**
```http
GET /api/tags/search/?q=python&limit=20&curated_only=true

Query Parameters:
- q: Search query (required)
- limit: Max results (default: 20)
- curated_only: Only curated tags (default: false)
```

#### **List Tags**
```http
GET /api/tags/?page=1&per_page=50&sort=usage&category=1

Query Parameters:
- page: Page number
- per_page: Results per page (default: 50)
- sort: usage, name, created (default: usage)
- category: Filter by category ID
```

#### **Get Tag Details**
```http
GET /api/tags/{slug}/

Returns tag details with statistics:
- Total usage count
- Trending data
- Related tags
- Subscriptions
- Analytics
```

#### **Get Trending Tags**
```http
GET /api/tags/trending/?period=daily&limit=10

Query Parameters:
- period: hourly, daily, weekly, monthly (default: daily)
- limit: Number of results (default: 10)
```

#### **Get Related Tags**
```http
GET /api/tags/{slug}/related/?type=synonym&limit=10

Query Parameters:
- type: synonym, related, broader, narrower, replaces, equivalent
- limit: Number of results (default: 10)
```

#### **AI Tag Suggestions**
```http
POST /api/tags/suggest/content/
Content-Type: application/json

{
  "content": "Article about Django and Python...",
  "title": "Django Best Practices",
  "existing_tags": ["python"],
  "max_suggestions": 5
}

Returns:
[
  {
    "name": "django-orm",
    "confidence": 0.92,
    "rationale": "Content discusses database queries..."
  },
  ...
]
```

#### **Create Tag Suggestion**
```http
POST /api/tags/suggest/create/
Content-Type: application/json

{
  "name": "django-orm",
  "description": "Django ORM techniques",
  "category": 1  # Optional category ID
}
```

#### **Subscribe to Tag**
```http
POST /api/tags/{slug}/subscribe/
Content-Type: application/json

{
  "frequency": "daily"  # instant, daily, weekly, never
}
```

#### **Unsubscribe from Tag**
```http
POST /api/tags/{slug}/unsubscribe/
```

#### **Approve Suggestion** (Staff Only)
```http
POST /api/tags/suggest/{id}/approve/
Content-Type: application/json

{
  "approved_name": "django-orm",  # Optional: override suggested name
  "category": 1  # Optional: assign category
}
```

#### **Merge Tags** (Staff Only)
```http
POST /api/tags/merge/
Content-Type: application/json

{
  "source_slug": "js",
  "target_slug": "javascript",
  "reason": "Common alias"
}
```

#### **Get Tag Categories**
```http
GET /api/tags/categories/

Returns list of all tag categories with usage counts
```

#### **Get User Subscriptions**
```http
GET /api/tags/collections/my-subscriptions/

Returns authenticated user's tag subscriptions
```

#### **Create Tag Collection**
```http
POST /api/tags/collections/create/
Content-Type: application/json

{
  "name": "My Favorite Topics",
  "description": "Tags I follow",
  "tag_slugs": ["python", "django", "postgresql"],
  "is_public": true
}
```

---

## 🛠️ Code Usage Examples

### **Using Comment Service**

```python
from apps.comments.services import CommentService
from apps.blog.models import Post
from django.contrib.auth import get_user_model

User = get_user_model()
service = CommentService()

# Create comment
post = Post.objects.get(slug='my-post')
user = User.objects.get(username='john')

comment = service.create_comment(
    content_object=post,
    user=user,
    body="Great article! Very helpful.",
    auto_approve=False  # Queue for moderation
)

# React to comment
reaction = service.add_reaction(
    comment=comment,
    user=user,
    reaction_type="insightful"
)

# Vote on comment (upvote)
vote = service.vote_comment(
    comment=comment,
    user=user,
    vote=1  # 1 for upvote, -1 for downvote
)

# Get top comments by engagement
top_comments = service.get_top_comments(
    content_object=post,
    limit=10,
    period="week"  # hour, day, week, month, all
)

# Get full comment thread
thread = service.get_comment_thread(
    root_comment=comment,
    max_depth=10,
    sort_by="score"  # score, created
)

# Give award to comment (staff only)
award = service.give_award(
    comment=comment,
    user=staff_user,
    award_type="gold",
    reason="Exceptional contribution"
)
```

### **Using Tag Service**

```python
from apps.tags.services import TagService
from apps.blog.models import Post

service = TagService()

# Create tag
tag = service.create_tag(
    name="Django",
    description="Django web framework",
    is_curated=True,
    category_name="Backend Frameworks"
)

# Get AI tag suggestions
post = Post.objects.get(slug='django-tips')
suggestions = service.suggest_tags_for_content(
    content=post.body,
    title=post.title,
    existing_tags=["python"],
    max_suggestions=5
)
# Returns: [
#   {"name": "django-orm", "confidence": 0.92, "rationale": "..."},
#   {"name": "database", "confidence": 0.85, "rationale": "..."},
#   ...
# ]

# Get trending tags
trending = service.get_trending_tags(
    period="daily",  # hourly, daily, weekly, monthly
    limit=10
)

# Get related tags
related = service.get_related_tags(
    tag=tag,
    relationship_type="related",  # synonym, related, broader, narrower
    min_strength=0.7,
    limit=10
)

# Subscribe user to tag
subscription = service.subscribe_to_tag(
    tag=tag,
    user=user,
    notification_frequency="daily"  # instant, daily, weekly, never
)

# Get tag statistics
stats = service.get_tag_stats(tag)
# Returns: {
#   "total_usage": 1250,
#   "usage_24h": 45,
#   "usage_7d": 312,
#   "usage_30d": 1089,
#   "growth_rate_7d": 15.3,
#   "growth_rate_30d": 22.7,
#   "avg_engagement": 8.5,
#   "quality_score": 0.87,
#   "total_subscribers": 89,
#   "trending_score": 12.4
# }

# Auto-tag content with AI
tags = service.auto_tag_content(
    content_object=post,
    content=post.body,
    title=post.title,
    min_confidence=0.7,
    max_tags=5
)
```

### **Using Infrastructure Services**

```python
from apps.core.infrastructure import QueueService, EmailService, StorageService
from apps.core.events import event_bus, EventTypes
from apps.core.metrics import metrics

# Queue Service - Background Tasks
queue = QueueService()

# Enqueue immediate task
task_id = queue.enqueue('apps.blog.tasks.publish_post', post_id=123)

# Enqueue delayed task (3600 seconds = 1 hour)
task_id = queue.enqueue_in('apps.blog.tasks.send_reminder', 3600, user_id=456)

# Email Service
email = EmailService()

# Send templated email
email.send_templated_email(
    recipient='user@example.com',
    template='welcome_email',
    context={'username': 'John', 'verification_link': 'https://...'},
    subject='Welcome to GSM Infinity!'
)

# Send bulk emails
email.send_bulk_email(
    recipients=['user1@example.com', 'user2@example.com'],
    template='newsletter',
    context={'month': 'January', 'posts': [...]}
)

# Storage Service
storage = StorageService()

# Save file
with open('image.jpg', 'rb') as f:
    file_content = f.read()
url = storage.save_file('uploads/image.jpg', file_content)

# Get file
file_content = storage.get_file('uploads/image.jpg')

# Delete file
storage.delete_file('uploads/image.jpg')

# Event Bus - Pub/Sub
@event_bus.subscribe(EventTypes.BLOG_POST_PUBLISHED)
def on_post_published(data):
    print(f"Post {data['post_id']} was published!")
    # Send notifications, update cache, etc.

# Publish event
event_bus.publish(EventTypes.BLOG_POST_PUBLISHED, {
    'post_id': 123,
    'title': 'My New Post',
    'author_id': 1
})

# Metrics - Analytics
metrics.increment('blog.post.created')
metrics.increment('blog.post.viewed', amount=5)
metrics.gauge('blog.posts.total', Post.objects.count())
metrics.histogram('blog.post.word_count', 1250)

# Time operations
with metrics.timer('blog.post.render'):
    # Code to measure execution time
    rendered_html = render_post(post)
```

---

## 📊 Statistics

- **Total LOC**: ~20,000 lines of production code
- **Database Models**: 47 models (21 new enterprise features)
- **API Endpoints**: ~100 total (23 new REST APIs)
- **Apps**: 25+ Django apps
- **Service Layers**: 2,000+ LOC (CommentService + TagService)
- **Background Tasks**: 15+ Celery tasks
- **Admin Interfaces**: 21 enhanced model admins

### **New Enterprise Features (2024)**
- **Comment System**: 10 new models, 9 REST endpoints, 600+ LOC service layer
- **Tag System**: 11 new models, 14 REST endpoints, 700+ LOC service layer
- **Infrastructure**: Queue, Storage, Email, Event Bus, Metrics, Webhooks
- **CI/CD**: GitHub Actions with test matrix, coverage, security checks

---

## 🔒 Security

### **Features**
- CSRF Protection on all POST requests
- SQL Injection prevention via Django ORM
- XSS Protection with template escaping
- Content Security Policy headers
- Rate limiting per-user and per-IP
- Bot detection with Crawler Guard
- AI moderation with toxicity detection
- Device fingerprinting and trust scoring

---

## 🧪 Testing

### **Run Tests**

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test apps.comments apps.tags

# Run with pytest
pytest

# Run with coverage
coverage run --source='apps' manage.py test
coverage report
coverage html  # Generates htmlcov/index.html
```

### **Run Linters**

```bash
# Black (code formatting)
black apps/ --line-length=120

# isort (import sorting)
isort apps/ --profile=black

# flake8 (style guide)
flake8 apps/ --max-line-length=120 --exclude=migrations

# Run all checks
black apps/ && isort apps/ && flake8 apps/
```

### **Security Checks**

```bash
# Check for security issues
bandit -r apps/ -ll

# Check dependencies for vulnerabilities
safety check
```

---

## 🚢 Deployment

### **Production Checklist**

- [ ] Set `DEBUG=False` in production settings
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Set strong `SECRET_KEY` (use `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`)
- [ ] Configure PostgreSQL database with `DATABASE_URL`
- [ ] Set up Redis for Celery background tasks
- [ ] Configure email backend (SMTP/SendGrid/etc.)
- [ ] Set up static file serving (CDN or WhiteNoise)
- [ ] Configure file storage (S3/GCS/Azure)
- [ ] Set up SSL certificates (Let's Encrypt)
- [ ] Configure security headers (CSP, HSTS, etc.)
- [ ] Set up monitoring (Sentry for errors)
- [ ] Configure backups (database + media files)
- [ ] Run migrations: `python manage.py migrate`
- [ ] Collect static files: `python manage.py collectstatic --noinput`
- [ ] Create superuser: `python manage.py createsuperuser`

### **Environment Variables**

```env
# Django Settings
DJANGO_SECRET_KEY=your-very-long-random-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=example.com,www.example.com

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/gsminfinity

# Redis (for Celery)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# AI Services (Optional)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Storage (Optional - AWS S3)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-east-1

# Monitoring (Optional)
SENTRY_DSN=https://...@sentry.io/...
```

### **Docker Deployment**

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy project
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Run migrations
RUN python manage.py migrate --noinput

# Create superuser from env vars (optional)
# RUN python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD') if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists() else None"

EXPOSE 8000

# Run gunicorn
CMD ["gunicorn", "gsminfinity.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  web:
    build: .
    command: gunicorn gsminfinity.wsgi:application --bind 0.0.0.0:8000 --workers 4
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/gsminfinity
      - REDIS_URL=redis://redis:6379/0
      - DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
      - DJANGO_DEBUG=False
    depends_on:
      - db
      - redis
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=gsminfinity
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  celery:
    build: .
    command: celery -A gsminfinity worker -l info --concurrency=4
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/gsminfinity
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  celery-beat:
    build: .
    command: celery -A gsminfinity beat -l info
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/gsminfinity
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
  static_volume:
  media_volume:
```

### **Run with Docker**

```bash
# Build and run
docker-compose up -d --build

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# View logs
docker-compose logs -f web

# Stop services
docker-compose down
```

---

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

### **Development Setup**

```bash
# Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/gsminfinity.git
cd gsminfinity

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements.txt
pip install black isort flake8 pytest pytest-django coverage

# Set up pre-commit hooks (optional)
pip install pre-commit
pre-commit install

# Create feature branch
git checkout -b feature/your-feature-name
```

### **Contribution Workflow**

1. **Find or Create Issue**: Check existing issues or create new one
2. **Fork Repository**: Create your own fork
3. **Create Branch**: `git checkout -b feature/amazing-feature`
4. **Write Code**: Follow Django and project conventions
5. **Write Tests**: Add tests for new features
6. **Run Tests**: `python manage.py test`
7. **Check Style**: `black apps/ && isort apps/ && flake8 apps/`
8. **Commit Changes**: `git commit -m 'Add amazing feature'`
9. **Push Branch**: `git push origin feature/amazing-feature`
10. **Open Pull Request**: Submit PR with clear description

### **Code Style Guidelines**

- Follow PEP 8 and Django coding standards
- Use Black for code formatting (line length 120)
- Use isort for import sorting
- Write docstrings for public methods/classes
- Keep functions focused and small
- Use type hints where appropriate
- Write descriptive commit messages

### **Testing Guidelines**

- Write tests for all new features
- Maintain or improve code coverage
- Test edge cases and error conditions
- Use Django's TestCase or pytest fixtures
- Mock external services (AI APIs, email, etc.)

### **Pull Request Requirements**

- [ ] Tests pass (`python manage.py test`)
- [ ] Code style checks pass (`black`, `isort`, `flake8`)
- [ ] No security vulnerabilities (`bandit`, `safety`)
- [ ] Documentation updated (if needed)
- [ ] Migration files included (if models changed)
- [ ] Clear description of changes
- [ ] Linked to related issue(s)

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2024 GSM Infinity

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🙏 Acknowledgments

- **Django Software Foundation** - For the amazing framework
- **OpenAI & Anthropic** - For AI integration capabilities
- **PostgreSQL Community** - For robust database
- **Python Community** - For ecosystem and libraries
- **All Contributors** - Thank you for your contributions!

---

## 📞 Support & Community

- **Documentation**: [Full Documentation](https://gsminfinity.readthedocs.io) (Coming Soon)
- **Issues**: [GitHub Issues](https://github.com/engremran7/gsminfinity/issues)
- **Discussions**: [GitHub Discussions](https://github.com/engremran7/gsminfinity/discussions)
- **Security**: Report security issues to security@gsminfinity.com

---

## 🗺️ Roadmap

### **Completed ✅**
- [x] Enterprise comment system with 10 models
- [x] Smart tag system with 11 models
- [x] AI integration (OpenAI, Anthropic)
- [x] Three-layer security suite
- [x] Infrastructure services (Queue, Storage, Email)
- [x] Event-driven architecture
- [x] CI/CD pipeline with GitHub Actions
- [x] Code coverage reporting

### **In Progress 🚧**
- [ ] GraphQL API
- [ ] Real-time notifications (WebSocket)
- [ ] Mobile app (React Native)
- [ ] Content recommendation engine
- [ ] Advanced analytics dashboard

### **Planned 📋**
- [ ] Multi-tenancy support
- [ ] Plugin marketplace
- [ ] Theme customization UI
- [ ] Advanced SEO tools
- [ ] Content versioning and drafts
- [ ] Collaborative editing

---

## 👥 Authors & Contributors

- **Lead Developer**: Emran ([@engremran7](https://github.com/engremran7))
- **Enterprise Architecture**: AI-Assisted Development
- **Contributors**: [View all contributors](https://github.com/engremran7/gsminfinity/graphs/contributors)

---

<div align="center">

**Made with ❤️ using Django, Python, and AI**

[![GitHub stars](https://img.shields.io/github/stars/engremran7/gsminfinity?style=social)](https://github.com/engremran7/gsminfinity)
[![GitHub forks](https://img.shields.io/github/forks/engremran7/gsminfinity?style=social)](https://github.com/engremran7/gsminfinity)
[![GitHub issues](https://img.shields.io/github/issues/engremran7/gsminfinity)](https://github.com/engremran7/gsminfinity/issues)

[⬆ Back to Top](#-gsm-infinity---enterprise-django-platform)

</div>
