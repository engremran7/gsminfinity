# AI App - Deployment & Features Documentation

## 📋 Overview

**App Name:** `ai`  
**Version:** 1.0.0  
**Django Version:** 4.2+  
**Type:** AI Integration & Content Generation  
**Status:** Production Ready ✅

Enterprise-grade AI integration app providing content generation, enhancement, and intelligent features powered by OpenAI GPT-4 and Anthropic Claude. Fully modular and self-contained with comprehensive API support.

---

## 🚀 Quick Start Deployment

### Prerequisites

- Python 3.10+
- Django 4.2+
- OpenAI API Key OR Anthropic API Key
- Redis 6+ (for rate limiting and caching)
- PostgreSQL 13+ (recommended for production)

### Installation Steps

1. **Add to INSTALLED_APPS**:

```python
# settings.py
INSTALLED_APPS = [
    # Django core apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'django_ratelimit',
    
    # Project apps
    'apps.core',              # Required: Base utilities
    'apps.users',             # Required: User authentication
    'apps.security_events',   # Required: Security logging
    'apps.ai',                # This app
]
```

2. **Install AI SDK Dependencies**:

```bash
pip install openai>=1.0.0
pip install anthropic>=0.18.0
pip install tiktoken>=0.5.0  # Token counting for GPT models
pip install django-ratelimit>=4.1.0
pip install redis>=4.5.0
```

3. **Configure API Keys**:

```bash
# .env
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-api03-...

# Optional: Choose default AI provider
AI_DEFAULT_PROVIDER=openai  # or 'anthropic'
AI_DEFAULT_MODEL=gpt-4-turbo-preview  # or 'claude-3-opus-20240229'
```

4. **Run Migrations**:

```bash
python manage.py makemigrations ai
python manage.py migrate ai
```

5. **Configure Redis** (for rate limiting):

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

6. **Add URL Configuration**:

```python
# gsminfinity/urls.py
urlpatterns = [
    path('ai/', include('apps.ai.urls')),
    path('api/ai/', include('apps.ai.api')),  # REST API
]
```

---

## 📦 Dependencies

### Required Python Packages

```txt
# AI SDKs
openai>=1.0.0
anthropic>=0.18.0
tiktoken>=0.5.0

# Django dependencies
Django>=4.2.0,<5.0
djangorestframework>=3.14.0
django-ratelimit>=4.1.0
redis>=4.5.0
celery>=5.3.0

# Utilities
python-dotenv>=1.0.0
pydantic>=2.0.0  # For data validation
```

### Required Django Apps

- `apps.core` - Base models and utilities
- `apps.users` - User authentication and permissions
- `apps.security_events` - Security logging and audit trails

### Optional Django Apps

- `apps.blog` - For blog content generation
- `apps.ads` - For AI-powered ad copy generation
- `apps.crawler_guard` - Rate limiting and bot protection

---

## 🎯 Core Features

### 1. **Multi-Provider AI Support**

- ✅ OpenAI GPT-4 Turbo, GPT-4o, GPT-3.5
- ✅ Anthropic Claude 3 Opus, Sonnet, Haiku
- ✅ Automatic failover between providers
- ✅ Model-specific configuration
- ✅ Token usage tracking and cost estimation

### 2. **Content Generation**

- ✅ Blog post generation from prompts
- ✅ Meta description generation
- ✅ SEO keyword extraction
- ✅ Article summarization
- ✅ Title generation with A/B variants
- ✅ Content expansion and elaboration
- ✅ Tone adjustment (formal, casual, technical)

### 3. **Content Enhancement**

- ✅ Grammar and spelling correction
- ✅ Style improvement suggestions
- ✅ Readability optimization
- ✅ SEO optimization recommendations
- ✅ Fact-checking assistance
- ✅ Plagiarism detection integration

### 4. **Smart Features**

- ✅ Context-aware responses
- ✅ Multi-turn conversations
- ✅ Chat history persistence
- ✅ Custom prompt templates
- ✅ Few-shot learning examples
- ✅ Structured output formatting (JSON)

### 5. **Security & Compliance**

- ✅ Rate limiting per user/IP
- ✅ Content filtering (profanity, NSFW)
- ✅ API key encryption
- ✅ Usage quota management
- ✅ Audit logging for all AI operations
- ✅ GDPR-compliant data handling

### 6. **Performance Optimization**

- ✅ Response caching for identical queries
- ✅ Streaming responses for long content
- ✅ Async processing with Celery
- ✅ Token optimization
- ✅ Automatic retry with exponential backoff

---

## 📐 Database Schema

### AIRequest Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `user` | ForeignKey(User) | Requesting user (nullable) |
| `provider` | CharField | openai/anthropic |
| `model` | CharField | Model used (e.g., gpt-4) |
| `prompt` | TextField | User prompt |
| `response` | TextField | AI-generated response |
| `tokens_used` | IntegerField | Total tokens consumed |
| `cost` | DecimalField | Estimated API cost |
| `status` | CharField | pending/success/failed |
| `error_message` | TextField | Error details (if failed) |
| `metadata` | JSONField | Additional context |
| `created_at` | DateTimeField | Request timestamp |
| `completed_at` | DateTimeField | Completion timestamp |

### AIUsageQuota Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `user` | OneToOneField(User) | User account |
| `monthly_limit` | IntegerField | Max tokens per month |
| `tokens_used_this_month` | IntegerField | Current usage |
| `reset_date` | DateField | Quota reset date |
| `is_unlimited` | BooleanField | Unlimited access flag |

### AIPromptTemplate Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `name` | CharField | Template name |
| `description` | TextField | Template description |
| `template` | TextField | Prompt template with {{variables}} |
| `category` | CharField | content/seo/marketing etc. |
| `is_active` | BooleanField | Active status |
| `created_by` | ForeignKey(User) | Creator |

---

## 🔌 API Endpoints

### REST API

```bash
# Content Generation
POST /api/ai/generate/
{
  "prompt": "Write a blog post about Python best practices",
  "provider": "openai",  # optional
  "model": "gpt-4-turbo-preview",  # optional
  "max_tokens": 1000,
  "temperature": 0.7
}

# Response
{
  "id": "uuid-here",
  "response": "Generated content...",
  "tokens_used": 850,
  "cost": 0.0255,
  "model": "gpt-4-turbo-preview"
}

# Meta Description Generation
POST /api/ai/generate-meta/
{
  "content": "Full article content here...",
  "max_length": 160
}

# SEO Keywords Extraction
POST /api/ai/extract-keywords/
{
  "content": "Article content...",
  "num_keywords": 10
}

# Content Enhancement
POST /api/ai/enhance/
{
  "content": "Original content...",
  "style": "professional",  # casual/professional/technical
  "improve_seo": true
}

# Chat Completion (Streaming)
POST /api/ai/chat/stream/
{
  "messages": [
    {"role": "user", "content": "Hello, can you help me?"}
  ],
  "stream": true
}

# Usage Statistics
GET /api/ai/usage/
# Returns user's token usage, quota, and costs
```

### Django Views

```bash
# AI Dashboard
GET /ai/dashboard/

# Generate Content (Form-based)
GET /ai/generate/
POST /ai/generate/

# Chat Interface
GET /ai/chat/
POST /ai/chat/send/

# Usage Analytics
GET /ai/analytics/
```

---

## 🛠️ Configuration

### Required Settings

```python
# settings.py

# ===== AI CONFIGURATION =====

# API Keys (set in .env)
OPENAI_API_KEY = env('OPENAI_API_KEY', default=None)
ANTHROPIC_API_KEY = env('ANTHROPIC_API_KEY', default=None)

# Default Provider
AI_DEFAULT_PROVIDER = env('AI_DEFAULT_PROVIDER', default='openai')
AI_DEFAULT_MODEL = env('AI_DEFAULT_MODEL', default='gpt-4-turbo-preview')

# Provider Configuration
AI_PROVIDERS = {
    'openai': {
        'api_key': OPENAI_API_KEY,
        'models': {
            'gpt-4-turbo-preview': {
                'max_tokens': 4096,
                'cost_per_1k_tokens': 0.03,
                'capabilities': ['chat', 'completion', 'vision']
            },
            'gpt-3.5-turbo': {
                'max_tokens': 4096,
                'cost_per_1k_tokens': 0.002,
                'capabilities': ['chat', 'completion']
            }
        }
    },
    'anthropic': {
        'api_key': ANTHROPIC_API_KEY,
        'models': {
            'claude-3-opus-20240229': {
                'max_tokens': 4096,
                'cost_per_1k_tokens': 0.015,
                'capabilities': ['chat', 'completion', 'vision']
            },
            'claude-3-sonnet-20240229': {
                'max_tokens': 4096,
                'cost_per_1k_tokens': 0.003,
                'capabilities': ['chat', 'completion']
            }
        }
    }
}

# Rate Limiting
AI_RATE_LIMIT_REQUESTS_PER_MINUTE = 10
AI_RATE_LIMIT_REQUESTS_PER_HOUR = 100

# Token Limits
AI_DEFAULT_MAX_TOKENS = 1000
AI_DEFAULT_TEMPERATURE = 0.7

# Caching
AI_CACHE_ENABLED = True
AI_CACHE_TTL_SECONDS = 3600  # 1 hour

# Content Filtering
AI_ENABLE_CONTENT_FILTER = True
AI_BLOCKED_KEYWORDS = ['inappropriate', 'offensive']

# Quota Management
AI_FREE_TIER_MONTHLY_TOKENS = 100000  # 100k tokens/month
AI_PRO_TIER_MONTHLY_TOKENS = 1000000  # 1M tokens/month

# Failover Configuration
AI_AUTO_FAILOVER = True
AI_FAILOVER_RETRY_COUNT = 3
AI_FAILOVER_RETRY_DELAY = 2  # seconds
```

### Environment Variables

```bash
# .env
OPENAI_API_KEY=sk-proj-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
AI_DEFAULT_PROVIDER=openai
AI_DEFAULT_MODEL=gpt-4-turbo-preview
AI_ENABLE_CONTENT_FILTER=true
AI_CACHE_ENABLED=true
```

---

## 🔐 Security Features

### 1. **API Key Protection**

```python
# Keys stored in environment variables, never in code
import os
from django.conf import settings

# Encrypted storage option
from cryptography.fernet import Fernet

class SecureAPIKeyManager:
    @staticmethod
    def encrypt_key(key: str) -> str:
        cipher = Fernet(settings.ENCRYPTION_KEY)
        return cipher.encrypt(key.encode()).decode()
    
    @staticmethod
    def decrypt_key(encrypted_key: str) -> str:
        cipher = Fernet(settings.ENCRYPTION_KEY)
        return cipher.decrypt(encrypted_key.encode()).decode()
```

### 2. **Rate Limiting**

```python
from django_ratelimit.decorators import ratelimit

@ratelimit(key='user', rate='10/m', method='POST')
@ratelimit(key='user', rate='100/h', method='POST')
def generate_content(request):
    # View logic
    pass
```

### 3. **Content Filtering**

```python
from apps.ai.services import ContentFilter

filter = ContentFilter()
if filter.contains_inappropriate_content(text):
    return JsonResponse({'error': 'Content violates policies'}, status=400)
```

### 4. **Audit Logging**

```python
from apps.security_events.models import SecurityEvent

SecurityEvent.objects.create(
    event_type='ai_request',
    user=request.user,
    severity='info',
    description=f'AI request: {model} - {tokens_used} tokens',
    metadata={'provider': provider, 'cost': cost}
)
```

---

## 🧪 Testing

### Unit Tests

```bash
# Run AI app tests
python manage.py test apps.ai

# Run with coverage
pytest apps/ai/tests/ --cov=apps.ai --cov-report=html
```

### Test Examples

```python
# apps/ai/tests.py
from django.test import TestCase
from apps.ai.services import AIService

class AIServiceTest(TestCase):
    def test_generate_content_openai(self):
        service = AIService(provider='openai')
        response = service.generate(
            prompt="Write a test",
            max_tokens=50
        )
        self.assertIsNotNone(response)
        self.assertIn('content', response)
    
    def test_rate_limiting(self):
        # Test rate limit enforcement
        for i in range(12):  # Exceeds 10/minute limit
            response = self.client.post('/api/ai/generate/', {...})
        
        self.assertEqual(response.status_code, 429)  # Too Many Requests
```

---

## 📊 Usage Examples

### Basic Content Generation

```python
from apps.ai.services import AIService

# Initialize service
ai_service = AIService(provider='openai', model='gpt-4-turbo-preview')

# Generate content
response = ai_service.generate(
    prompt="Write a blog post about Django best practices",
    max_tokens=1000,
    temperature=0.7
)

print(response['content'])
print(f"Tokens used: {response['tokens_used']}")
print(f"Cost: ${response['cost']:.4f}")
```

### Meta Description Generation

```python
from apps.ai.services import SEOService

seo_service = SEOService()

# Generate meta description from article
meta_description = seo_service.generate_meta_description(
    content="Full article content here...",
    max_length=160
)

print(meta_description)
```

### Chat Completion

```python
from apps.ai.clients import OpenAIClient

client = OpenAIClient()

messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is Django?"}
]

response = client.chat_completion(messages=messages)
print(response['choices'][0]['message']['content'])
```

### Streaming Responses

```python
from apps.ai.services import AIService

ai_service = AIService()

for chunk in ai_service.generate_stream(prompt="Tell me a story"):
    print(chunk, end='', flush=True)
```

---

## 🚢 Production Deployment

### Environment Setup

```bash
# Production .env
DJANGO_SETTINGS_MODULE=gsminfinity.settings
DEBUG=False
OPENAI_API_KEY=sk-proj-production-key
ANTHROPIC_API_KEY=sk-ant-production-key
AI_DEFAULT_PROVIDER=openai
AI_RATE_LIMIT_REQUESTS_PER_MINUTE=50
AI_CACHE_ENABLED=true
REDIS_URL=redis://redis:6379/1
```

### Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Install AI dependencies
RUN pip install openai anthropic tiktoken

CMD ["gunicorn", "gsminfinity.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### Celery Tasks

```python
# apps/ai/tasks.py
from celery import shared_task
from apps.ai.services import AIService

@shared_task
def generate_content_async(prompt, user_id, **kwargs):
    """Generate AI content asynchronously"""
    ai_service = AIService()
    response = ai_service.generate(prompt=prompt, **kwargs)
    
    # Save to database
    from apps.ai.models import AIRequest
    AIRequest.objects.create(
        user_id=user_id,
        prompt=prompt,
        response=response['content'],
        tokens_used=response['tokens_used']
    )
    
    return response

# Usage
from apps.ai.tasks import generate_content_async

task = generate_content_async.delay(
    prompt="Generate content",
    user_id=request.user.id
)
```

---

## 🐛 Troubleshooting

### Common Issues

**Issue:** "OpenAI API key not found"
```bash
# Solution: Set environment variable
export OPENAI_API_KEY=sk-proj-...
# Or add to .env file
```

**Issue:** Rate limit exceeded
```python
# Solution: Implement exponential backoff
import time
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def call_ai_api():
    return ai_service.generate(...)
```

**Issue:** High API costs
```python
# Solution: Implement caching and use cheaper models
from django.core.cache import cache

cache_key = f"ai_response_{hash(prompt)}"
cached_response = cache.get(cache_key)

if cached_response:
    return cached_response

# Use GPT-3.5 instead of GPT-4 for simple tasks
ai_service = AIService(model='gpt-3.5-turbo')
```

**Issue:** Slow responses
```python
# Solution: Use streaming or async processing
response_stream = ai_service.generate_stream(prompt)
for chunk in response_stream:
    yield chunk  # Stream to frontend
```

---

## 📈 Monitoring & Analytics

### Track Usage

```python
from apps.ai.models import AIRequest
from django.db.models import Sum, Count, Avg

# Total tokens used this month
total_tokens = AIRequest.objects.filter(
    created_at__month=datetime.now().month
).aggregate(Sum('tokens_used'))

# Most active users
top_users = AIRequest.objects.values('user__username').annotate(
    total_requests=Count('id'),
    total_tokens=Sum('tokens_used')
).order_by('-total_requests')[:10]
```

### Cost Tracking

```python
# Calculate monthly AI costs
monthly_cost = AIRequest.objects.filter(
    created_at__month=datetime.now().month
).aggregate(Sum('cost'))['cost__sum'] or 0

print(f"Monthly AI cost: ${monthly_cost:.2f}")
```

---

## 📚 Additional Resources

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Anthropic Claude Documentation](https://docs.anthropic.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Celery Documentation](https://docs.celeryproject.org/)

---

## 📄 License

This app is part of GSM Infinity and follows the project license.

**Version:** 1.0.0  
**Last Updated:** 2024-12-10  
**Maintained By:** GSM Infinity Development Team
