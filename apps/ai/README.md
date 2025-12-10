# 🤖 AI App

AI-powered content generation and intelligent features for GSM Infinity. Provides OpenAI and Anthropic integrations for text generation, content enhancement, and AI-powered tools.

## ✨ Features

- **Content Generation**: Blog posts, article summaries, SEO content
- **Text Enhancement**: Grammar correction, style improvement, expansion
- **Multi-Provider Support**: OpenAI GPT-4, Anthropic Claude
- **Prompt Templates**: Pre-built prompts for common tasks
- **Token Management**: Track and optimize API usage
- **Streaming Support**: Real-time response streaming
- **Error Handling**: Robust fallback and retry logic
- **Cost Tracking**: Monitor AI API costs per operation

## 📦 Installation

### 1. Copy App to Your Project

```bash
cp -r apps/ai /your_project/apps/
```

### 2. Install Dependencies

```bash
pip install openai anthropic tiktoken
```

### 3. Add to INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    
    'apps.ai',
    
    # Required dependencies
    'apps.core',  # For AI clients
]
```

### 4. Configure URLs

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    path('ai/', include('apps.ai.urls')),
]
```

### 5. Run Migrations

```bash
python manage.py makemigrations ai
python manage.py migrate ai
```

## ⚙️ Configuration

### Environment Variables

```bash
# .env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
AI_DEFAULT_PROVIDER=openai  # or anthropic
AI_DEFAULT_MODEL=gpt-4  # or claude-3-5-sonnet-20241022
```

### Settings

```python
# settings.py

# AI Configuration
AI_CONFIG = {
    'default_provider': env('AI_DEFAULT_PROVIDER', default='openai'),
    'default_model': env('AI_DEFAULT_MODEL', default='gpt-4'),
    'max_tokens': 2000,
    'temperature': 0.7,
    'timeout': 30,
}

# OpenAI Settings
OPENAI_API_KEY = env('OPENAI_API_KEY')
OPENAI_MODELS = {
    'fast': 'gpt-3.5-turbo',
    'balanced': 'gpt-4',
    'creative': 'gpt-4-turbo-preview',
}

# Anthropic Settings
ANTHROPIC_API_KEY = env('ANTHROPIC_API_KEY')
ANTHROPIC_MODELS = {
    'fast': 'claude-3-haiku-20240307',
    'balanced': 'claude-3-5-sonnet-20241022',
    'powerful': 'claude-3-opus-20240229',
}
```

## 📚 Usage

### Content Generation

```python
from apps.ai.services import ContentGenerationService

service = ContentGenerationService()

# Generate blog post
post = service.generate_blog_post(
    topic="Django Best Practices",
    style="technical",
    length=500
)

# Generate summary
summary = service.summarize_text(
    text=long_article,
    max_length=100
)

# Enhance content
enhanced = service.enhance_content(
    text="Your draft text",
    improvements=['grammar', 'clarity', 'seo']
)
```

### Using AI Clients

```python
from apps.ai.clients import OpenAIClient, AnthropicClient

# OpenAI
openai = OpenAIClient()
response = openai.chat_completion(
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Explain Django ORM"}
    ],
    model="gpt-4"
)

# Anthropic
anthropic = AnthropicClient()
response = anthropic.create_message(
    messages=[
        {"role": "user", "content": "Explain Django ORM"}
    ],
    model="claude-3-5-sonnet-20241022",
    max_tokens=1000
)
```

### Streaming Responses

```python
from apps.ai.services import StreamingService

service = StreamingService()

for chunk in service.stream_completion("Write a story"):
    print(chunk, end='', flush=True)
```

### In Views

```python
from django.http import JsonResponse
from apps.ai.services import ContentGenerationService

def generate_content(request):
    topic = request.POST.get('topic')
    
    service = ContentGenerationService()
    content = service.generate_blog_post(topic=topic)
    
    return JsonResponse({
        'success': True,
        'content': content
    })
```

## 🔗 Integration with Other Apps

### With Blog App

```python
# Auto-generate blog content
from apps.blog.models import Post
from apps.ai.services import ContentGenerationService

def create_ai_post(topic):
    service = ContentGenerationService()
    
    # Generate content
    content = service.generate_blog_post(topic=topic)
    
    # Create post
    post = Post.objects.create(
        title=content['title'],
        body=content['body'],
        excerpt=content['summary'],
        ai_generated=True
    )
    return post
```

### With SEO App

```python
# Generate SEO metadata
from apps.ai.services import SEOService

seo_service = SEOService()
metadata = seo_service.generate_seo_metadata(
    title="Article Title",
    content="Article content..."
)

# Returns: {
#     'meta_description': '...',
#     'keywords': ['keyword1', 'keyword2'],
#     'og_description': '...'
# }
```

### With Comments App

```python
# AI moderation
from apps.ai.services import ModerationService

mod_service = ModerationService()
result = mod_service.analyze_comment("Comment text")

# Returns: {
#     'is_toxic': False,
#     'toxicity_score': 0.12,
#     'categories': []
# }
```

## 📊 Models

### AIRequest Model

```python
class AIRequest(models.Model):
    user = ForeignKey(User, null=True)
    provider = CharField(max_length=50)  # openai, anthropic
    model = CharField(max_length=100)
    prompt = TextField()
    response = TextField()
    tokens_used = IntegerField()
    cost = DecimalField(max_digits=10, decimal_places=6)
    duration_ms = IntegerField()
    status = CharField(max_length=20)  # success, error, timeout
    created_at = DateTimeField(auto_now_add=True)
```

### AIPromptTemplate Model

```python
class AIPromptTemplate(models.Model):
    name = CharField(max_length=100)
    description = TextField()
    template = TextField()  # Supports {{variable}} placeholders
    category = CharField(max_length=50)
    is_active = BooleanField(default=True)
```

## 🎯 Services

### ContentGenerationService

```python
from apps.ai.services import ContentGenerationService

service = ContentGenerationService(provider='openai', model='gpt-4')

# Generate blog post
post = service.generate_blog_post(
    topic="Python Tips",
    style="casual",
    length=500,
    include_outline=True
)

# Generate title suggestions
titles = service.generate_titles(
    topic="Django Tutorial",
    count=5
)

# Expand content
expanded = service.expand_content(
    text="Short paragraph",
    target_length=300
)
```

### SEOService

```python
from apps.ai.services import SEOService

service = SEOService()

# Generate meta description
meta = service.generate_meta_description(
    title="Article Title",
    content="Article content..."
)

# Extract keywords
keywords = service.extract_keywords(
    content="Long article text...",
    count=10
)

# Generate SEO-optimized content
optimized = service.optimize_for_seo(
    content="Original text",
    target_keywords=['django', 'python']
)
```

### ModerationService

```python
from apps.ai.services import ModerationService

service = ModerationService()

# Analyze text
result = service.analyze_content(
    text="User-generated content",
    categories=['toxicity', 'spam', 'profanity']
)

# Auto-moderate
action = service.auto_moderate(
    text="Comment text",
    threshold=0.7
)  # Returns: 'approve', 'reject', 'review'
```

## 🔒 Security Features

### Rate Limiting

```python
from django.core.cache import cache

def check_ai_rate_limit(user):
    key = f"ai_requests_{user.id}"
    count = cache.get(key, 0)
    
    if count >= 100:  # 100 requests per hour
        return False
    
    cache.set(key, count + 1, 3600)
    return True
```

### Cost Tracking

```python
from apps.ai.models import AIRequest

# Track costs per user
total_cost = AIRequest.objects.filter(
    user=user,
    created_at__gte=start_date
).aggregate(total=Sum('cost'))['total']
```

### Content Filtering

```python
from apps.ai.services import ContentFilter

filter = ContentFilter()
is_safe = filter.check_safety(user_prompt)
```

## 🧪 Testing

```python
from django.test import TestCase
from apps.ai.services import ContentGenerationService

class AITestCase(TestCase):
    def test_content_generation(self):
        service = ContentGenerationService()
        content = service.generate_blog_post(topic="Test")
        self.assertIsNotNone(content)
        self.assertIn('title', content)
        self.assertIn('body', content)
```

Run tests:

```bash
python manage.py test apps.ai
```

## 🚀 Performance

### Caching Responses

```python
from django.core.cache import cache

def cached_ai_generation(prompt):
    key = f"ai_{hash(prompt)}"
    cached = cache.get(key)
    
    if cached:
        return cached
    
    response = service.generate(prompt)
    cache.set(key, response, 3600)  # 1 hour
    return response
```

### Token Optimization

```python
import tiktoken

def count_tokens(text, model="gpt-4"):
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

# Truncate to fit token limits
def truncate_text(text, max_tokens=4000):
    tokens = count_tokens(text)
    if tokens <= max_tokens:
        return text
    
    # Calculate truncation ratio
    ratio = max_tokens / tokens
    return text[:int(len(text) * ratio)]
```

### Batch Processing

```python
from apps.ai.services import BatchService

service = BatchService()

# Process multiple items
results = service.batch_generate(
    prompts=['prompt1', 'prompt2', 'prompt3'],
    max_workers=3
)
```

## 📝 Required Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `openai` | ≥1.0.0 | OpenAI API |
| `anthropic` | ≥0.18.0 | Anthropic API |
| `tiktoken` | ≥0.5.0 | Token counting |
| `apps.core` | - | AI clients |

Install:

```bash
pip install openai anthropic tiktoken
```

## 🎯 API Endpoints

### POST /ai/generate/
Generate content

**Request:**
```json
{
    "prompt": "Write about Django",
    "model": "gpt-4",
    "max_tokens": 1000
}
```

**Response:**
```json
{
    "success": true,
    "content": "Generated text...",
    "tokens_used": 450,
    "cost": 0.0135
}
```

### POST /ai/summarize/
Summarize text

### POST /ai/enhance/
Enhance content

## 💡 Best Practices

1. **Always set token limits** to control costs
2. **Cache repeated prompts** to reduce API calls
3. **Use streaming** for better UX on long generations
4. **Track costs** per user/project
5. **Implement rate limiting** to prevent abuse
6. **Use prompt templates** for consistency
7. **Handle errors gracefully** with fallbacks
8. **Monitor API latency** and switch providers if needed

## 🛠️ Customization

### Custom Prompt Templates

```python
from apps.ai.models import AIPromptTemplate

template = AIPromptTemplate.objects.create(
    name="blog_intro",
    template="Write an introduction for a blog post about {{topic}} in a {{style}} style.",
    category="content_generation"
)

# Use template
prompt = template.template.replace("{{topic}}", "Django")
prompt = prompt.replace("{{style}}", "professional")
```

### Custom AI Provider

```python
from apps.ai.clients import BaseAIClient

class CustomAIClient(BaseAIClient):
    def __init__(self, api_key):
        self.api_key = api_key
    
    def generate(self, prompt, **kwargs):
        # Your implementation
        pass
```

## 📞 Support

- GitHub Issues: Tag with `[ai]`
- Documentation: Check docstrings
- Examples: See `tests.py`

## 📄 License

MIT License

## 🤝 Dependencies

**Required:**
- `apps.core` - For AI client infrastructure

**Optional:**
- `apps.blog` - For content generation
- `apps.seo` - For SEO optimization
- `apps.comments` - For moderation

## 📚 Related Apps

- `apps.ai_behavior` - Behavioral analysis (security focused)
- `apps.core` - AI client infrastructure
- `apps.blog` - Content management
- `apps.seo` - SEO tools
