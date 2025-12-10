# 🤖 Crawler Guard

Bot detection, rate limiting, and malicious crawler blocking. Primary security pattern for protecting against automated threats.

## ✨ Features

- **Bot Detection**: Identify automated traffic
- **Rate Limiting**: Per-user and per-IP rate limiting
- **CAPTCHA Integration**: Challenge suspicious requests
- **User-Agent Analysis**: Detect bot signatures
- **Behavior Fingerprinting**: Identify bot patterns
- **Whitelist/Blacklist**: Manage allowed/blocked bots
- **Honeypot Protection**: Trap malicious bots
- **Request Throttling**: Prevent abuse and scraping
- **Analytics Dashboard**: Monitor bot traffic

## 📦 Installation

### 1. Copy App to Your Project

```bash
cp -r apps/crawler_guard /your_project/apps/
```

### 2. Install Dependencies

```bash
pip install django-ratelimit user-agents
```

### 3. Add to INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    
    'apps.crawler_guard',
    
    # Optional integrations
    'apps.ai_behavior',      # For behavioral analysis
    'apps.security_events',  # For event logging
]
```

### 4. Add Middleware

```python
# settings.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'apps.crawler_guard.middleware.BotDetectionMiddleware',  # Add this
    'apps.crawler_guard.middleware.RateLimitMiddleware',     # Add this
    'django.contrib.sessions.middleware.SessionMiddleware',
    # ... rest of middleware
]
```

### 5. Run Migrations

```bash
python manage.py makemigrations crawler_guard
python manage.py migrate crawler_guard
```

## ⚙️ Configuration

### Settings

```python
# settings.py

# Crawler Guard Configuration
CRAWLER_GUARD_CONFIG = {
    'enabled': True,
    'auto_block_bots': True,
    'allow_good_bots': True,  # Allow Googlebot, Bingbot, etc.
    'challenge_suspicious': True,  # Show CAPTCHA
    'log_blocked_requests': True,
}

# Rate Limiting
RATE_LIMIT_CONFIG = {
    'anonymous_requests_per_minute': 60,
    'authenticated_requests_per_minute': 120,
    'burst_limit': 10,  # Max requests in 1 second
    'block_duration': 300,  # Block for 5 minutes
}

# Bot Detection
BOT_DETECTION = {
    'check_user_agent': True,
    'check_headers': True,
    'check_javascript': True,  # JS challenge
    'check_honeypot': True,
}

# Good Bots (Whitelist)
ALLOWED_BOTS = [
    'Googlebot',
    'Bingbot',
    'Slackbot',
    'TwitterBot',
    'facebookexternalhit',
]

# Bad Bots (Blacklist)
BLOCKED_BOTS = [
    'scrapy',
    'selenium',
    'phantomjs',
    'curl',
    'wget',
]
```

### Environment Variables

```bash
# .env
CRAWLER_GUARD_ENABLED=True
RATE_LIMIT_ENABLED=True
CAPTCHA_SITE_KEY=your_recaptcha_site_key
CAPTCHA_SECRET_KEY=your_recaptcha_secret_key
```

## 📚 Usage

### Decorator-Based Protection

```python
from apps.crawler_guard.decorators import (
    rate_limit,
    block_bots,
    require_human,
)

# Rate limit view
@rate_limit(requests=10, period=60)  # 10 requests per minute
def my_view(request):
    return JsonResponse({'success': True})

# Block all bots
@block_bots()
def api_view(request):
    return JsonResponse({'data': 'sensitive'})

# Require human (CAPTCHA challenge)
@require_human()
def contact_form(request):
    return render(request, 'contact.html')
```

### Manual Bot Detection

```python
from apps.crawler_guard.services import is_bot, get_bot_info

# Check if request is from bot
if is_bot(request):
    return HttpResponseForbidden("Bots not allowed")

# Get bot details
bot_info = get_bot_info(request)
# Returns: {
#     'is_bot': True,
#     'bot_name': 'Googlebot',
#     'category': 'search_engine',
#     'allowed': True
# }
```

### Rate Limiting

```python
from apps.crawler_guard.services import check_rate_limit

# Check rate limit
allowed = check_rate_limit(
    identifier=request.user.id or get_client_ip(request),
    max_requests=100,
    period=3600  # 1 hour
)

if not allowed:
    return HttpResponseTooManyRequests("Rate limit exceeded")
```

### Honeypot Protection

```html
<!-- Add to forms to trap bots -->
<form method="post">
    {% csrf_token %}
    
    <!-- Honeypot field (hidden from humans) -->
    <input type="text" name="hp" class="hidden" tabindex="-1" autocomplete="off">
    
    <!-- Real fields -->
    <input type="text" name="name" required>
    <button type="submit">Submit</button>
</form>
```

```python
# In view
from apps.crawler_guard.services import check_honeypot

if check_honeypot(request):
    # Bot detected! Filled honeypot field
    return HttpResponseForbidden("Bot detected")
```

## 🔗 Integration with Other Apps

### With AI Behavior

```python
from apps.ai_behavior.services import track_behavior
from apps.crawler_guard.services import is_bot

if is_bot(request):
    risk_score = 1.0  # Bots = high risk
    track_behavior(request, 'bot_access', {'risk': risk_score})
else:
    risk_score = track_behavior(request, 'human_access')
```

### With Security Events

```python
from apps.security_events.models import SecurityEvent

# Log blocked bots
if is_bot(request) and not bot_allowed:
    SecurityEvent.objects.create(
        event_type='bot_blocked',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT'),
        metadata={'bot_name': bot_info['bot_name']}
    )
```

### With Users

```python
# Track bot attacks per user
from apps.users.models import CustomUser

user = CustomUser.objects.get(pk=user_id)
if is_bot(request) and user:
    user.bot_attack_count += 1
    user.save()
```

## 📊 Models

### BotRequest

```python
class BotRequest(models.Model):
    ip_address = GenericIPAddressField()
    user_agent = TextField()
    bot_name = CharField(max_length=100)
    is_allowed = BooleanField()
    path = CharField(max_length=500)
    method = CharField(max_length=10)
    timestamp = DateTimeField(auto_now_add=True)
```

### RateLimitEntry

```python
class RateLimitEntry(models.Model):
    identifier = CharField(max_length=100)  # User ID or IP
    resource = CharField(max_length=200)  # URL or action
    count = IntegerField()
    period_start = DateTimeField()
    period_end = DateTimeField()
    is_blocked = BooleanField(default=False)
```

### BotWhitelist

```python
class BotWhitelist(models.Model):
    name = CharField(max_length=100)
    user_agent_pattern = CharField(max_length=200)
    category = CharField(max_length=50)  # search_engine, social, monitoring
    is_active = BooleanField(default=True)
```

### BotBlacklist

```python
class BotBlacklist(models.Model):
    name = CharField(max_length=100)
    user_agent_pattern = CharField(max_length=200)
    ip_pattern = CharField(max_length=100)
    reason = TextField()
    is_active = BooleanField(default=True)
```

## 🔒 Security Features

### Multi-Layer Bot Detection

```python
def is_bot(request):
    # Check user agent
    if is_bot_user_agent(request.META.get('HTTP_USER_AGENT')):
        return True
    
    # Check missing headers
    if not request.META.get('HTTP_ACCEPT_LANGUAGE'):
        return True
    
    # Check automation tools
    if 'selenium' in request.META.get('HTTP_USER_AGENT', '').lower():
        return True
    
    return False
```

### IP-Based Blocking

```python
from apps.crawler_guard.services import block_ip, is_ip_blocked

# Block IP
block_ip('1.2.3.4', reason='Malicious activity', duration=3600)

# Check if blocked
if is_ip_blocked(request):
    return HttpResponseForbidden("Your IP is blocked")
```

### JavaScript Challenge

```html
<!-- Verify browser has JS enabled -->
<script>
    document.cookie = "js_enabled=1; path=/";
</script>
```

```python
# In view
def check_js_enabled(request):
    return request.COOKIES.get('js_enabled') == '1'
```

### CAPTCHA Integration

```python
from apps.crawler_guard.services import verify_captcha

if suspicious_request:
    # Show CAPTCHA
    if not verify_captcha(request.POST.get('g-recaptcha-response')):
        return HttpResponseForbidden("CAPTCHA verification failed")
```

## 🧪 Testing

```python
from django.test import TestCase, Client
from apps.crawler_guard.services import is_bot

class CrawlerGuardTestCase(TestCase):
    def test_bot_detection(self):
        client = Client(HTTP_USER_AGENT='Googlebot/2.1')
        response = client.get('/')
        # Test bot handling
    
    def test_rate_limiting(self):
        # Simulate rapid requests
        for i in range(100):
            response = self.client.get('/')
        
        # Should be rate limited
        response = self.client.get('/')
        self.assertEqual(response.status_code, 429)
```

Run tests:

```bash
python manage.py test apps.crawler_guard
```

## 🚀 Performance

### Caching Bot Checks

```python
from django.core.cache import cache

def is_bot_cached(user_agent):
    key = f"bot_check_{hash(user_agent)}"
    cached = cache.get(key)
    
    if cached is not None:
        return cached
    
    is_bot_result = is_bot_user_agent(user_agent)
    cache.set(key, is_bot_result, 3600)  # 1 hour
    return is_bot_result
```

### Batch IP Blocking

```python
from apps.crawler_guard.services import block_ips_batch

# Block multiple IPs at once
block_ips_batch([
    '1.2.3.4',
    '5.6.7.8',
    '9.10.11.12'
], reason='Botnet detected')
```

### Async Logging

```python
from celery import shared_task

@shared_task
def log_bot_request_async(data):
    BotRequest.objects.create(**data)
```

## 📝 Required Dependencies

| Package | Purpose | Required |
|---------|---------|----------|
| `django-ratelimit` | Rate limiting | Yes |
| `user-agents` | User agent parsing | Yes |
| `apps.security_events` | Event logging | Optional |
| `apps.ai_behavior` | Behavioral analysis | Optional |

Install:

```bash
pip install django-ratelimit user-agents
```

## 🎯 Management Commands

### Update Bot Lists

```bash
# Update good bot list from online database
python manage.py update_bot_whitelist

# Update bad bot list
python manage.py update_bot_blacklist

# Clear rate limit cache
python manage.py clear_rate_limits
```

## 💡 Best Practices

1. **Allow good bots** (search engines, social media)
2. **Use rate limiting** on all public endpoints
3. **Implement honeypots** in forms
4. **Log blocked requests** for analysis
5. **Update bot lists** regularly
6. **Use CAPTCHA** for sensitive actions
7. **Monitor bot traffic** via admin dashboard
8. **Combine with AI behavior** for better detection

## 🛠️ Customization

### Custom Bot Detection Rules

```python
from apps.crawler_guard.services import register_bot_detector

@register_bot_detector
def custom_detector(request):
    # Your custom logic
    if 'suspicious_pattern' in request.path:
        return True
    return False
```

### Custom Rate Limit Rules

```python
from apps.crawler_guard.decorators import rate_limit

@rate_limit(key=lambda request: request.user.id, requests=100, period=3600)
def my_view(request):
    # Custom rate limit key function
    pass
```

## 📞 Support

- GitHub Issues: Tag with `[crawler-guard]`
- Documentation: Inline docstrings
- Examples: `tests.py`

## 📄 License

MIT License

## 🤝 Dependencies

**Required:**
- `django-ratelimit` - Rate limiting
- `user-agents` - UA parsing

**Optional:**
- `apps.security_events` - Event logging
- `apps.ai_behavior` - Behavioral analysis
- `apps.devices` - Device tracking

## 📚 Related Apps

- `apps.ai_behavior` - Behavioral analysis (primary security)
- `apps.devices` - Device fingerprinting (primary security)
- `apps.security_events` - Security logging
- `apps.users` - User authentication

## 🎓 Advanced Features

### Adaptive Rate Limiting

```python
def get_rate_limit(user):
    if user.is_trusted:
        return 1000  # Trusted users get higher limits
    elif user.is_authenticated:
        return 100
    else:
        return 60
```

### Bot Behavior Learning

```python
from apps.crawler_guard.services import learn_bot_patterns

# Analyze traffic to identify new bots
new_bots = learn_bot_patterns(days=7)
```

### Distributed Rate Limiting

```python
# Use Redis for multi-server rate limiting
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```
