# 🛡️ AI Behavior Engine

AI-powered behavioral analysis and anomaly detection for security. Primary security pattern alongside `crawler_guard` and `devices`.

## ✨ Features

- **Behavioral Analysis**: AI-powered pattern recognition
- **Anomaly Detection**: Identify suspicious user behavior
- **Risk Scoring**: Real-time threat assessment
- **Pattern Learning**: Adaptive baseline building
- **Threat Classification**: Categorize security events
- **Automated Response**: Block/challenge suspicious activity
- **Session Analysis**: Track user journey patterns
- **Integration Ready**: Works with security_events, devices, crawler_guard

## 📦 Installation

### 1. Copy App to Your Project

```bash
cp -r apps/ai_behavior /your_project/apps/
```

### 2. Install Dependencies

```bash
pip install scikit-learn numpy anthropic openai
```

### 3. Add to INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    
    'apps.ai_behavior',
    
    # Required dependencies
    'apps.core',            # For AI clients
    'apps.security_events', # For event logging
    'apps.devices',         # For device tracking
]
```

### 4. Add Middleware (Optional)

```python
# settings.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'apps.ai_behavior.middleware.BehaviorAnalysisMiddleware',  # Add this
    'django.middleware.common.CommonMiddleware',
    # ... rest of middleware
]
```

### 5. Run Migrations

```bash
python manage.py makemigrations ai_behavior
python manage.py migrate ai_behavior
```

## ⚙️ Configuration

### Settings

```python
# settings.py

# AI Behavior Configuration
AI_BEHAVIOR_CONFIG = {
    'enabled': True,
    'analysis_mode': 'realtime',  # realtime, batch, hybrid
    'risk_threshold': 0.7,  # 0.0 to 1.0
    'learning_mode': True,  # Build baselines
    'auto_block': False,  # Auto-block high-risk requests
    'challenge_threshold': 0.5,  # Trigger MFA/CAPTCHA
}

# Anomaly Detection
ANOMALY_DETECTION = {
    'min_samples': 100,  # Min data points for baseline
    'contamination': 0.1,  # Expected outlier ratio
    'algorithms': ['isolation_forest', 'one_class_svm'],
}

# AI Provider for Analysis
AI_BEHAVIOR_PROVIDER = 'anthropic'  # or 'openai'
AI_BEHAVIOR_MODEL = 'claude-3-5-sonnet-20241022'
```

### Environment Variables

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
AI_BEHAVIOR_ENABLED=True
```

## 📚 Usage

### Track User Behavior

```python
from apps.ai_behavior.services import track_behavior

# Track action
track_behavior(
    request=request,
    action='login_attempt',
    metadata={'success': True}
)

# Returns risk score: 0.0 (safe) to 1.0 (high risk)
risk_score = track_behavior(
    request=request,
    action='comment_post',
    metadata={'comment_id': 123}
)
```

### Analyze Risk

```python
from apps.ai_behavior.services import BehaviorAnalysisService

service = BehaviorAnalysisService()

# Analyze user session
analysis = service.analyze_user_session(user=request.user)
# Returns: {
#     'risk_score': 0.45,
#     'anomalies': ['unusual_timing', 'new_device'],
#     'recommendation': 'challenge'  # allow, challenge, block
# }

# Check specific action
is_suspicious = service.is_suspicious_action(
    user=request.user,
    action='bulk_download',
    context={'file_count': 50}
)
```

### Pattern Detection

```python
from apps.ai_behavior.services import PatternDetectionService

service = PatternDetectionService()

# Detect patterns
patterns = service.detect_patterns(
    user=request.user,
    timeframe_hours=24
)

# Build baseline
service.build_user_baseline(user=request.user)
```

### In Views

```python
from django.http import HttpResponseForbidden
from apps.ai_behavior.decorators import require_low_risk

@require_low_risk(max_risk=0.7)
def sensitive_action(request):
    # This view requires low risk score
    return JsonResponse({'success': True})

# Manual check
from apps.ai_behavior.services import check_risk

def my_view(request):
    risk = check_risk(request)
    
    if risk > 0.7:
        return HttpResponseForbidden("Action blocked due to security concerns")
    
    # Proceed with action
    return JsonResponse({'success': True})
```

## 🔗 Integration with Other Apps

### With Security Events

```python
# Automatic event logging
from apps.security_events.models import SecurityEvent

# Behavior analysis triggers security events
track_behavior(request, 'suspicious_activity')
# Creates SecurityEvent automatically
```

### With Devices

```python
# Device-aware analysis
from apps.devices.models import Device

device = Device.get_or_create_device(request)
analysis = service.analyze_user_session(
    user=request.user,
    device=device
)

# New devices increase risk score
if not device.is_trusted:
    risk_score += 0.2
```

### With Crawler Guard

```python
# Combined bot + behavior detection
from apps.crawler_guard.services import is_bot

if is_bot(request):
    risk_score = 1.0  # Bots = high risk
else:
    risk_score = track_behavior(request, 'page_view')
```

### With Users

```python
# User-specific behavior profiles
from apps.users.models import CustomUser

user = CustomUser.objects.get(pk=user_id)
profile = service.get_behavior_profile(user)
# Returns: {
#     'typical_hours': [9, 10, 11, 14, 15, 16],
#     'typical_locations': ['US', 'CA'],
#     'typical_devices': [device1, device2],
#     'baseline_risk': 0.15
# }
```

## 📊 Models

### BehaviorEvent

```python
class BehaviorEvent(models.Model):
    user = ForeignKey(User, null=True)
    session_id = CharField(max_length=100)
    action = CharField(max_length=100)
    risk_score = FloatField()  # 0.0 to 1.0
    anomaly_flags = JSONField(default=list)
    metadata = JSONField(default=dict)
    ip_address = GenericIPAddressField()
    user_agent = TextField()
    timestamp = DateTimeField(auto_now_add=True)
```

### UserBehaviorProfile

```python
class UserBehaviorProfile(models.Model):
    user = OneToOneField(User)
    baseline_data = JSONField()  # Historical patterns
    risk_score = FloatField(default=0.0)
    last_analysis = DateTimeField()
    total_events = IntegerField(default=0)
    anomaly_count = IntegerField(default=0)
    is_flagged = BooleanField(default=False)
```

### AnomalyDetection

```python
class AnomalyDetection(models.Model):
    user = ForeignKey(User)
    anomaly_type = CharField(max_length=50)
    description = TextField()
    severity = CharField(max_length=20)  # low, medium, high, critical
    detected_at = DateTimeField(auto_now_add=True)
    resolved = BooleanField(default=False)
```

## 🤖 AI Analysis

### Behavioral Classification

```python
from apps.ai_behavior.services import classify_behavior

result = classify_behavior(
    actions=['login', 'view_page', 'view_page', 'logout'],
    timestamps=[...],
    metadata={...}
)

# Returns: {
#     'pattern': 'normal_browsing',
#     'confidence': 0.89,
#     'anomalies': [],
#     'risk_level': 'low'
# }
```

### Threat Detection

```python
from apps.ai_behavior.services import detect_threats

threats = detect_threats(
    user=request.user,
    session_events=events
)

# Returns list of detected threats:
# [
#     {'type': 'account_takeover', 'confidence': 0.75},
#     {'type': 'credential_stuffing', 'confidence': 0.82}
# ]
```

## 🔒 Security Features

### Automatic Blocking

```python
# In middleware
if analysis['risk_score'] > 0.9:
    return HttpResponseForbidden("Access denied for security reasons")
```

### Challenge High-Risk Users

```python
if analysis['risk_score'] > 0.5:
    # Require MFA
    return redirect('users:device_mfa_challenge')
```

### Rate Limiting

```python
from apps.ai_behavior.services import check_rate_limit

if not check_rate_limit(request.user, action='comment_post'):
    return HttpResponseTooManyRequests("Too many actions")
```

## 🧪 Testing

```python
from django.test import TestCase, RequestFactory
from apps.ai_behavior.services import track_behavior

class BehaviorTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_track_normal_behavior(self):
        request = self.factory.get('/')
        risk = track_behavior(request, 'page_view')
        self.assertLess(risk, 0.5)
    
    def test_detect_suspicious_pattern(self):
        # Simulate rapid actions
        for i in range(100):
            track_behavior(request, 'page_view')
        
        risk = track_behavior(request, 'page_view')
        self.assertGreater(risk, 0.7)
```

Run tests:

```bash
python manage.py test apps.ai_behavior
```

## 🚀 Performance

### Batch Analysis

```python
from apps.ai_behavior.services import batch_analyze

# Analyze multiple users
results = batch_analyze(
    user_ids=[1, 2, 3, 4, 5],
    timeframe_hours=24
)
```

### Caching

```python
from django.core.cache import cache

def get_behavior_profile(user):
    key = f"behavior_profile_{user.id}"
    cached = cache.get(key)
    
    if cached:
        return cached
    
    profile = service.analyze_user(user)
    cache.set(key, profile, 300)  # 5 minutes
    return profile
```

### Async Processing

```python
from celery import shared_task

@shared_task
def analyze_behavior_async(user_id):
    service = BehaviorAnalysisService()
    return service.analyze_user(user_id)
```

## 📝 Required Dependencies

| Package | Purpose | Required |
|---------|---------|----------|
| `scikit-learn` | ML algorithms | Yes |
| `numpy` | Numerical computing | Yes |
| `anthropic` | AI analysis | Yes (or openai) |
| `openai` | AI analysis | Yes (or anthropic) |
| `apps.core` | AI clients | Yes |
| `apps.security_events` | Event logging | Optional |
| `apps.devices` | Device tracking | Optional |

Install:

```bash
pip install scikit-learn numpy anthropic openai
```

## 🎯 API Endpoints

### POST /ai-behavior/analyze/
Analyze user behavior

**Request:**
```json
{
    "user_id": 123,
    "actions": ["login", "view_page", "logout"],
    "timeframe": "1h"
}
```

**Response:**
```json
{
    "risk_score": 0.35,
    "anomalies": [],
    "recommendation": "allow"
}
```

## 💡 Best Practices

1. **Start in learning mode** to build baselines
2. **Set appropriate thresholds** based on your security needs
3. **Combine with other security layers** (devices, crawler_guard)
4. **Monitor false positives** and adjust algorithms
5. **Log all high-risk events** for investigation
6. **Use async processing** for large-scale analysis
7. **Cache behavior profiles** to reduce DB load

## 🛠️ Customization

### Custom Anomaly Detectors

```python
from apps.ai_behavior.services import BaseAnomalyDetector

class CustomDetector(BaseAnomalyDetector):
    def detect(self, data):
        # Your algorithm
        return anomalies
```

### Custom Risk Scoring

```python
def calculate_custom_risk(user, actions):
    base_risk = 0.0
    
    # Your scoring logic
    if len(actions) > 100:
        base_risk += 0.3
    
    # Check patterns
    # ...
    
    return min(base_risk, 1.0)
```

## 📞 Support

- GitHub Issues: Tag with `[ai-behavior]`
- Documentation: Inline docstrings
- Examples: `tests.py`

## 📄 License

MIT License

## 🤝 Dependencies

**Required:**
- `apps.core` - AI client infrastructure
- `scikit-learn` - ML algorithms

**Optional:**
- `apps.security_events` - Event logging
- `apps.devices` - Device tracking
- `apps.crawler_guard` - Bot detection
- `apps.users` - User management

## 📚 Related Apps

- `apps.crawler_guard` - Bot protection (primary security)
- `apps.devices` - Device fingerprinting (primary security)
- `apps.security_events` - Security logging
- `apps.ai` - AI services (content, not security)
