# Crawler Guard App - Deployment & Features Documentation

## 📋 Overview

**App Name:** `crawler_guard`  
**Version:** 1.0.0  
**Django Version:** 4.2+  
**Type:** Security - Bot Detection & Rate Limiting  
**Status:** Production Ready ✅

Enterprise-grade bot detection, crawler management, and rate limiting system. Protects your application from malicious bots, scrapers, and DDoS attacks while allowing legitimate crawlers (Google, Bing, etc.).

---

## 🚀 Quick Start Deployment

### Prerequisites

- Python 3.10+
- Django 4.2+
- Redis 6+ (for rate limiting)
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
    
    # Security apps (order matters)
    'apps.core',              # Required: Base utilities
    'apps.security_events',   # Required: Event logging
    'apps.crawler_guard',     # This app
    'apps.ai_behavior',       # Optional: AI-powered threat detection
    'apps.devices',           # Optional: Device fingerprinting
]
```

2. **Install Dependencies**:

```bash
pip install django-ratelimit>=4.1.0
pip install redis>=4.5.0
pip install user-agents>=2.2.0
pip install geoip2>=4.7.0  # Optional: IP geolocation
```

3. **Configure Middleware**:

```python
# settings.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Crawler Guard middleware (add after auth middleware)
    'apps.crawler_guard.middleware.CrawlerDetectionMiddleware',
    'apps.crawler_guard.middleware.RateLimitMiddleware',
    'apps.crawler_guard.middleware.BotChallengeMiddleware',
]
```

4. **Run Migrations**:

```bash
python manage.py makemigrations crawler_guard
python manage.py migrate crawler_guard
```

5. **Configure Redis**:

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

6. **Load Crawler Rules** (Optional):

```bash
python manage.py loaddata crawler_rules.json
```

---

## 📦 Dependencies

### Required Python Packages

```txt
Django>=4.2.0,<5.0
django-ratelimit>=4.1.0
redis>=4.5.0
django-redis>=5.3.0
user-agents>=2.2.0
```

### Optional Packages

```txt
geoip2>=4.7.0  # IP geolocation
dnspython>=2.4.0  # Reverse DNS lookup
```

### Required Django Apps

- `apps.core` - Base models and utilities
- `apps.security_events` - Security event logging

### Optional Django Apps

- `apps.ai_behavior` - AI-powered behavioral analysis
- `apps.devices` - Device fingerprinting and tracking

---

## 🎯 Core Features

### 1. **Bot Detection**

- ✅ User-agent analysis (600+ known bots)
- ✅ Header pattern matching
- ✅ IP reputation checking
- ✅ Behavioral analysis (click patterns, timing)
- ✅ JavaScript challenge (headless browser detection)
- ✅ CAPTCHA integration
- ✅ Reverse DNS verification

### 2. **Crawler Management**

- ✅ Whitelist for legitimate crawlers (Google, Bing, etc.)
- ✅ Blacklist for malicious bots
- ✅ Crawler-specific rate limits
- ✅ robots.txt enforcement
- ✅ Custom crawler rules
- ✅ Crawler analytics and reporting

### 3. **Rate Limiting**

- ✅ Per-IP rate limiting
- ✅ Per-user rate limiting
- ✅ Per-endpoint rate limiting
- ✅ Sliding window algorithm
- ✅ Token bucket algorithm
- ✅ Graceful degradation
- ✅ Custom rate limit rules

### 4. **DDoS Protection**

- ✅ Request rate monitoring
- ✅ Connection limit enforcement
- ✅ Automatic IP blocking
- ✅ Geo-blocking (country-level)
- ✅ Challenge-response system
- ✅ Progressive delays

### 5. **Security Features**

- ✅ SQL injection detection in query strings
- ✅ XSS attempt detection
- ✅ Directory traversal protection
- ✅ Suspicious pattern detection
- ✅ Honeypot endpoints
- ✅ Security headers enforcement

### 6. **Analytics & Monitoring**

- ✅ Real-time bot traffic dashboard
- ✅ Traffic pattern analysis
- ✅ Threat level indicators
- ✅ Block/allow statistics
- ✅ Export reports (CSV, JSON)
- ✅ Email alerts for attacks

---

## 📐 Database Schema

### CrawlerRule Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `name` | CharField | Rule name |
| `pattern` | CharField | User-agent pattern (regex) |
| `rule_type` | CharField | whitelist/blacklist/ratelimit |
| `action` | CharField | allow/block/challenge |
| `rate_limit` | IntegerField | Requests per minute |
| `is_active` | BooleanField | Rule status |
| `priority` | IntegerField | Rule priority (lower = higher) |
| `created_at` | DateTimeField | Creation timestamp |

### BlockedIP Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `ip_address` | GenericIPAddressField | Blocked IP |
| `reason` | CharField | Block reason |
| `blocked_until` | DateTimeField | Temporary block expiry |
| `is_permanent` | BooleanField | Permanent block flag |
| `block_count` | IntegerField | Number of times blocked |
| `last_seen` | DateTimeField | Last request timestamp |
| `metadata` | JSONField | Additional data |

### CrawlerRequest Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `ip_address` | GenericIPAddressField | Request IP |
| `user_agent` | TextField | User-agent string |
| `path` | CharField | Request path |
| `method` | CharField | HTTP method |
| `is_bot` | BooleanField | Bot detection result |
| `bot_type` | CharField | Bot category |
| `action_taken` | CharField | allow/block/challenge |
| `threat_score` | IntegerField | 0-100 threat level |
| `created_at` | DateTimeField | Request timestamp |

---

## 🔌 API Endpoints

### Admin API

```bash
# Crawler Rules Management
GET    /api/crawler-guard/rules/
POST   /api/crawler-guard/rules/
PUT    /api/crawler-guard/rules/<id>/
DELETE /api/crawler-guard/rules/<id>/

# Blocked IPs
GET    /api/crawler-guard/blocked-ips/
POST   /api/crawler-guard/blocked-ips/
DELETE /api/crawler-guard/blocked-ips/<ip>/

# Analytics
GET    /api/crawler-guard/stats/
GET    /api/crawler-guard/traffic/
GET    /api/crawler-guard/threats/

# Actions
POST   /api/crawler-guard/block-ip/
POST   /api/crawler-guard/unblock-ip/
POST   /api/crawler-guard/test-rule/
```

### Public Endpoints

```bash
# Bot Challenge
GET  /crawler-guard/challenge/
POST /crawler-guard/verify-challenge/

# Status Check
GET  /crawler-guard/status/
```

---

## 🛠️ Configuration

### Required Settings

```python
# settings.py

# ===== CRAWLER GUARD CONFIGURATION =====

# Bot Detection
CRAWLER_GUARD_ENABLED = True
CRAWLER_GUARD_STRICT_MODE = False  # Block unknown bots
CRAWLER_GUARD_LOG_ALL_REQUESTS = False  # Log all or only suspicious

# Rate Limiting (requests per minute)
CRAWLER_GUARD_RATE_LIMITS = {
    'default': 60,          # Anonymous users
    'authenticated': 120,   # Logged-in users
    'bot_good': 30,        # Whitelisted bots
    'bot_suspicious': 5,   # Suspicious bots
}

# Whitelisted Crawlers (User-Agent patterns)
CRAWLER_GUARD_WHITELIST = [
    r'Googlebot',
    r'Bingbot',
    r'Slurp',  # Yahoo
    r'DuckDuckBot',
    r'Baiduspider',
    r'YandexBot',
    r'facebookexternalhit',
    r'LinkedInBot',
    r'Twitterbot',
]

# Blacklisted User-Agents
CRAWLER_GUARD_BLACKLIST = [
    r'scrapy',
    r'python-requests',
    r'curl',
    r'wget',
    r'SemrushBot',
    r'AhrefsBot',
    r'MJ12bot',
]

# IP Whitelist (Never block these IPs)
CRAWLER_GUARD_IP_WHITELIST = [
    '127.0.0.1',
    '::1',
    # Add your monitoring service IPs
]

# IP Blacklist (Always block)
CRAWLER_GUARD_IP_BLACKLIST = [
    # Add known malicious IPs
]

# Geo-Blocking (ISO country codes)
CRAWLER_GUARD_GEO_BLACKLIST = []  # e.g., ['CN', 'RU']
CRAWLER_GUARD_GEO_WHITELIST = []  # If set, only allow these countries

# Challenge Settings
CRAWLER_GUARD_ENABLE_JS_CHALLENGE = True
CRAWLER_GUARD_ENABLE_CAPTCHA = False  # Requires reCAPTCHA keys
CRAWLER_GUARD_CAPTCHA_SITE_KEY = ''
CRAWLER_GUARD_CAPTCHA_SECRET_KEY = ''

# Blocking Behavior
CRAWLER_GUARD_AUTO_BLOCK_THRESHOLD = 10  # Violations before auto-block
CRAWLER_GUARD_TEMP_BLOCK_DURATION = 3600  # Seconds (1 hour)
CRAWLER_GUARD_PERM_BLOCK_THRESHOLD = 5  # Temp blocks before permanent

# Suspicious Patterns (regex)
CRAWLER_GUARD_SUSPICIOUS_PATTERNS = [
    r'\.\./',  # Directory traversal
    r'<script',  # XSS attempt
    r'union.*select',  # SQL injection
    r'base64',
    r'eval\(',
]

# Honeypot Endpoints (trap bots)
CRAWLER_GUARD_HONEYPOTS = [
    '/admin.php',
    '/wp-admin/',
    '/.env',
    '/phpMyAdmin/',
]

# Response Templates
CRAWLER_GUARD_BLOCK_TEMPLATE = 'crawler_guard/blocked.html'
CRAWLER_GUARD_CHALLENGE_TEMPLATE = 'crawler_guard/challenge.html'

# Notification
CRAWLER_GUARD_ALERT_EMAIL = 'security@yourdomain.com'
CRAWLER_GUARD_ALERT_THRESHOLD = 100  # Requests/min to trigger alert
```

### Environment Variables

```bash
# .env
CRAWLER_GUARD_ENABLED=true
CRAWLER_GUARD_STRICT_MODE=false
CRAWLER_GUARD_ALERT_EMAIL=security@example.com
CAPTCHA_SITE_KEY=your-recaptcha-site-key
CAPTCHA_SECRET_KEY=your-recaptcha-secret
```

---

## 🔐 Security Features

### 1. **Multi-Layer Bot Detection**

```python
# apps/crawler_guard/detectors.py
from apps.crawler_guard.services import BotDetector

detector = BotDetector()

# Analyze request
result = detector.analyze_request(request)

if result['is_bot']:
    if result['is_malicious']:
        # Block the request
        return HttpResponse('Access Denied', status=403)
    elif result['requires_challenge']:
        # Present JS challenge
        return render(request, 'crawler_guard/challenge.html')
```

### 2. **Automatic IP Blocking**

```python
from apps.crawler_guard.models import BlockedIP

# Temporary block (1 hour)
BlockedIP.objects.create(
    ip_address='203.0.113.10',
    reason='Exceeded rate limit',
    blocked_until=timezone.now() + timedelta(hours=1)
)

# Permanent block
BlockedIP.objects.create(
    ip_address='198.51.100.50',
    reason='Malicious bot',
    is_permanent=True
)
```

### 3. **Rate Limiting Decorators**

```python
from apps.crawler_guard.decorators import rate_limit

# Apply rate limit to view
@rate_limit(key='ip', rate='10/m')
def api_endpoint(request):
    return JsonResponse({'data': 'value'})

# User-based rate limit
@rate_limit(key='user', rate='100/h')
def user_action(request):
    # View logic
    pass
```

### 4. **Challenge-Response**

```python
from apps.crawler_guard.challenges import JSChallenge

# Generate challenge
challenge = JSChallenge.generate()

# Verify response
is_valid = JSChallenge.verify(request.POST.get('response'), challenge_id)

if not is_valid:
    # Block bot
    BlockedIP.objects.create(...)
```

---

## 🧪 Testing

### Unit Tests

```bash
python manage.py test apps.crawler_guard
pytest apps/crawler_guard/tests/ --cov=apps.crawler_guard
```

### Test Examples

```python
# apps/crawler_guard/tests.py
from django.test import TestCase, Client
from apps.crawler_guard.services import BotDetector

class BotDetectionTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.detector = BotDetector()
    
    def test_googlebot_allowed(self):
        response = self.client.get(
            '/',
            HTTP_USER_AGENT='Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
        )
        self.assertEqual(response.status_code, 200)
    
    def test_scrapy_blocked(self):
        response = self.client.get(
            '/',
            HTTP_USER_AGENT='Scrapy/2.5.0'
        )
        self.assertEqual(response.status_code, 403)
    
    def test_rate_limit_enforced(self):
        # Make 61 requests (exceeds 60/min limit)
        for i in range(61):
            response = self.client.get('/')
        
        self.assertEqual(response.status_code, 429)
```

---

## 📊 Usage Examples

### Basic Bot Detection

```python
from apps.crawler_guard.services import BotDetector

detector = BotDetector()

# Check if request is from a bot
result = detector.is_bot(request)
print(f"Is bot: {result['is_bot']}")
print(f"Bot type: {result['bot_type']}")
print(f"Threat score: {result['threat_score']}")
```

### Rate Limiting in Views

```python
from django.views.decorators.cache import cache_page
from apps.crawler_guard.decorators import rate_limit

@rate_limit(key='ip', rate='30/m')
@cache_page(60)  # Cache for 1 minute
def public_api(request):
    data = {'message': 'Hello, World!'}
    return JsonResponse(data)
```

### Custom Crawler Rules

```python
from apps.crawler_guard.models import CrawlerRule

# Add custom rule
CrawlerRule.objects.create(
    name='Block BadBot',
    pattern=r'BadBot/\d+\.\d+',
    rule_type='blacklist',
    action='block',
    is_active=True,
    priority=10
)

# Rate limit specific crawler
CrawlerRule.objects.create(
    name='Limit SlowBot',
    pattern=r'SlowBot',
    rule_type='ratelimit',
    action='challenge',
    rate_limit=5,  # 5 requests/min
    is_active=True
)
```

---

## 🚢 Production Deployment

### Nginx Configuration

```nginx
# Rate limiting at nginx level (additional layer)
limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=api:10m rate=5r/s;

server {
    listen 80;
    server_name yourdomain.com;

    # General rate limit
    limit_req zone=general burst=20 nodelay;

    # API rate limit
    location /api/ {
        limit_req zone=api burst=10 nodelay;
        proxy_pass http://127.0.0.1:8000;
    }

    # Block known bad bots at nginx level
    if ($http_user_agent ~* (scrapy|curl|wget|python-requests)) {
        return 403;
    }
}
```

### Systemd Service for Monitoring

```ini
# /etc/systemd/system/crawler-guard-monitor.service
[Unit]
Description=Crawler Guard Monitoring Service
After=network.target redis.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/gsminfinity
ExecStart=/path/to/venv/bin/python manage.py monitor_crawlers
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 🐛 Troubleshooting

### Common Issues

**Issue:** Legitimate users getting blocked
```python
# Solution: Add IP to whitelist
CRAWLER_GUARD_IP_WHITELIST = [
    '203.0.113.100',  # Your office IP
]

# Or reduce rate limits
CRAWLER_GUARD_RATE_LIMITS = {
    'default': 120,  # Increase from 60
}
```

**Issue:** Google/Bing not crawling site
```python
# Solution: Verify crawler verification
from apps.crawler_guard.services import verify_google_crawler

if verify_google_crawler(ip_address):
    # Allow access
    pass
```

**Issue:** High memory usage with many blocked IPs
```python
# Solution: Clean up old temporary blocks
from django.core.management.base import BaseCommand
from apps.crawler_guard.models import BlockedIP
from django.utils import timezone

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Delete expired temporary blocks
        BlockedIP.objects.filter(
            is_permanent=False,
            blocked_until__lt=timezone.now()
        ).delete()
```

---

## 📈 Monitoring & Analytics

### Dashboard Metrics

```python
from apps.crawler_guard.models import CrawlerRequest
from django.db.models import Count, Q

# Bot traffic statistics
stats = CrawlerRequest.objects.aggregate(
    total_requests=Count('id'),
    bot_requests=Count('id', filter=Q(is_bot=True)),
    blocked_requests=Count('id', filter=Q(action_taken='block'))
)

print(f"Total: {stats['total_requests']}")
print(f"Bots: {stats['bot_requests']}")
print(f"Blocked: {stats['blocked_requests']}")
```

### Real-time Alerts

```python
from django.core.mail import send_mail
from apps.crawler_guard.services import ThreatMonitor

monitor = ThreatMonitor()

if monitor.detect_attack():
    send_mail(
        'Security Alert: Possible DDoS Attack',
        f'Detected {monitor.requests_per_minute} requests/min',
        'security@yourdomain.com',
        ['admin@yourdomain.com'],
        fail_silently=False,
    )
```

---

## 📚 Additional Resources

- [Django Rate Limiting](https://django-ratelimit.readthedocs.io/)
- [Bot Detection Best Practices](https://owasp.org/www-community/controls/Blocking_Brute_Force_Attacks)
- [Google Crawler Verification](https://developers.google.com/search/docs/advanced/crawling/verifying-googlebot)

---

## 📄 License

This app is part of GSM Infinity and follows the project license.

**Version:** 1.0.0  
**Last Updated:** 2024-12-10  
**Maintained By:** GSM Infinity Development Team
