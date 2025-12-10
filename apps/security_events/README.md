# 🚨 Security Events App

Comprehensive security event logging, monitoring, and alerting system.

## ✨ Features

- **Event Logging**: Log all security-related events
- **Event Classification**: Categorize events by type and severity
- **Real-time Monitoring**: Track events as they occur
- **Alert System**: Notify admins of critical events
- **Event Search**: Advanced filtering and search
- **Analytics Dashboard**: Security metrics and trends
- **Integration Ready**: Works with all security apps
- **Audit Trail**: Complete security audit logging

## 📦 Installation

### 1. Copy App to Your Project

```bash
cp -r apps/security_events /your_project/apps/
```

### 2. Add to INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    
    'apps.security_events',
    
    # Integrates with
    'apps.users',
    'apps.devices',
    'apps.crawler_guard',
    'apps.ai_behavior',
]
```

### 3. Run Migrations

```bash
python manage.py makemigrations security_events
python manage.py migrate security_events
```

## ⚙️ Configuration

### Settings

```python
# settings.py

# Security Events Configuration
SECURITY_EVENTS_CONFIG = {
    'enabled': True,
    'log_level': 'INFO',  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    'retention_days': 90,  # Keep logs for 90 days
    'alert_on_critical': True,
    'alert_email': 'admin@example.com',
}

# Event Types to Track
SECURITY_EVENT_TYPES = [
    'login_success',
    'login_failed',
    'logout',
    'password_change',
    'permission_denied',
    'suspicious_activity',
    'bot_detected',
    'rate_limit_exceeded',
    'device_verified',
    'device_blocked',
]

# Severity Levels
SECURITY_SEVERITY_LEVELS = [
    'low',
    'medium',
    'high',
    'critical',
]
```

## 📚 Usage

### Log Security Event

```python
from apps.security_events.models import SecurityEvent
from apps.security_events.services import log_event

# Simple logging
log_event(
    event_type='login_success',
    user=request.user,
    ip_address=get_client_ip(request),
    severity='low'
)

# Detailed logging
SecurityEvent.objects.create(
    event_type='suspicious_activity',
    user=request.user,
    ip_address='1.2.3.4',
    user_agent=request.META.get('HTTP_USER_AGENT'),
    severity='high',
    description='Multiple failed login attempts',
    metadata={
        'attempts': 5,
        'timeframe': '5 minutes',
        'target_account': 'admin'
    }
)
```

### Query Events

```python
from apps.security_events.models import SecurityEvent
from django.utils import timezone
from datetime import timedelta

# Get recent events
recent_events = SecurityEvent.objects.filter(
    timestamp__gte=timezone.now() - timedelta(hours=24)
).order_by('-timestamp')

# Get critical events
critical_events = SecurityEvent.objects.filter(
    severity='critical',
    resolved=False
)

# Get user activity
user_events = SecurityEvent.objects.filter(
    user=user
).order_by('-timestamp')[:50]
```

### Event Analytics

```python
from apps.security_events.services import SecurityAnalytics

analytics = SecurityAnalytics()

# Get event summary
summary = analytics.get_summary(days=7)
# Returns: {
#     'total_events': 1234,
#     'critical_events': 5,
#     'by_type': {...},
#     'by_severity': {...},
#     'top_ips': [...]
# }

# Detect patterns
patterns = analytics.detect_patterns(user=request.user)
# Returns suspicious patterns in user activity
```

### In Views

```python
from apps.security_events.decorators import log_security_event

@log_security_event(event_type='api_access', severity='low')
def sensitive_api_view(request):
    # Automatically logs access
    return JsonResponse({'data': 'sensitive'})
```

## 🔗 Integration with Other Apps

### With Users App

```python
# Log authentication events
from django.contrib.auth.signals import user_logged_in

def log_user_login(sender, request, user, **kwargs):
    log_event(
        event_type='login_success',
        user=user,
        ip_address=get_client_ip(request),
        severity='low'
    )

user_logged_in.connect(log_user_login)
```

### With Devices App

```python
# Log device events
from apps.devices.models import Device

def log_device_verification(device):
    log_event(
        event_type='device_verified',
        user=device.user,
        severity='medium',
        metadata={'device_id': device.id}
    )
```

### With Crawler Guard

```python
# Log bot detections
from apps.crawler_guard.services import is_bot

if is_bot(request):
    log_event(
        event_type='bot_detected',
        ip_address=get_client_ip(request),
        severity='medium',
        metadata={'bot_name': get_bot_info(request)['bot_name']}
    )
```

### With AI Behavior

```python
# Log anomalies
from apps.ai_behavior.services import track_behavior

risk_score = track_behavior(request, 'page_view')
if risk_score > 0.7:
    log_event(
        event_type='suspicious_activity',
        user=request.user,
        severity='high',
        metadata={'risk_score': risk_score}
    )
```

## 📊 Models

### SecurityEvent

```python
class SecurityEvent(models.Model):
    event_type = CharField(max_length=50)
    user = ForeignKey(User, null=True, blank=True)
    ip_address = GenericIPAddressField(null=True)
    user_agent = TextField(blank=True)
    severity = CharField(max_length=20, choices=SEVERITY_CHOICES)
    description = TextField(blank=True)
    metadata = JSONField(default=dict)
    resolved = BooleanField(default=False)
    resolved_by = ForeignKey(User, null=True, related_name='resolved_events')
    resolved_at = DateTimeField(null=True)
    timestamp = DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['severity', 'resolved']),
        ]
```

### EventAlert

```python
class EventAlert(models.Model):
    event = ForeignKey(SecurityEvent)
    alert_type = CharField(max_length=50)  # email, sms, webhook
    sent_to = CharField(max_length=200)
    sent_at = DateTimeField(auto_now_add=True)
    status = CharField(max_length=20)  # sent, failed, pending
```

## 🔒 Security Features

### Automatic Alerts

```python
from apps.security_events.services import send_alert

def log_critical_event(event_type, **kwargs):
    event = log_event(event_type=event_type, severity='critical', **kwargs)
    send_alert(event, method='email')
```

### Event Correlation

```python
from apps.security_events.services import correlate_events

# Find related events
related_events = correlate_events(
    ip_address='1.2.3.4',
    timeframe_minutes=60
)

if len(related_events) > 10:
    # Possible attack
    log_event(event_type='potential_attack', severity='critical')
```

### Threat Intelligence

```python
from apps.security_events.services import check_threat_intel

is_threat = check_threat_intel(ip_address='1.2.3.4')
if is_threat:
    log_event(event_type='known_threat', severity='critical')
```

## 🧪 Testing

```python
from django.test import TestCase
from apps.security_events.models import SecurityEvent

class SecurityEventsTestCase(TestCase):
    def test_event_logging(self):
        event = SecurityEvent.objects.create(
            event_type='test_event',
            severity='low'
        )
        self.assertEqual(event.event_type, 'test_event')
    
    def test_event_query(self):
        events = SecurityEvent.objects.filter(severity='critical')
        self.assertIsNotNone(events)
```

Run tests:

```bash
python manage.py test apps.security_events
```

## 🚀 Performance

### Batch Logging

```python
from apps.security_events.services import batch_log_events

events = [
    {'event_type': 'page_view', 'user': user1},
    {'event_type': 'page_view', 'user': user2},
    {'event_type': 'page_view', 'user': user3},
]

batch_log_events(events)
```

### Archiving Old Events

```python
# Management command to archive old events
python manage.py archive_security_events --days=90
```

### Database Indexing

```python
# Models have indexes on frequently queried fields
class Meta:
    indexes = [
        models.Index(fields=['event_type', 'timestamp']),
        models.Index(fields=['user', 'timestamp']),
        models.Index(fields=['severity', 'resolved']),
    ]
```

## 📝 Required Dependencies

| Package | Purpose | Required |
|---------|---------|----------|
| None | Core Django only | - |

**Optional:**
- `apps.users` - User tracking
- `apps.devices` - Device events
- `apps.crawler_guard` - Bot events
- `apps.ai_behavior` - Anomaly events

## 🎯 Management Commands

```bash
# Archive old events
python manage.py archive_security_events --days=90

# Generate security report
python manage.py security_report --days=7

# Export events
python manage.py export_security_events --format=json --output=events.json

# Clean up old events
python manage.py cleanup_security_events --days=180
```

## 💡 Best Practices

1. **Log all security events** consistently
2. **Set appropriate severity** levels
3. **Include context** in metadata field
4. **Monitor critical events** in real-time
5. **Archive old events** regularly
6. **Review patterns** for threat detection
7. **Alert on critical events**
8. **Use correlation** to detect attacks

## 🛠️ Customization

### Custom Event Types

```python
# Register custom event types
CUSTOM_EVENT_TYPES = [
    'custom_action',
    'special_access',
    'data_export',
]

SECURITY_EVENT_TYPES.extend(CUSTOM_EVENT_TYPES)
```

### Custom Alert Methods

```python
from apps.security_events.services import register_alert_method

@register_alert_method('slack')
def send_slack_alert(event):
    # Send to Slack
    pass
```

## 📞 Support

- GitHub Issues: Tag with `[security-events]`
- Documentation: Inline docstrings
- Examples: `tests.py`

## 📄 License

MIT License

## 🤝 Dependencies

**Optional:**
- `apps.users` - User tracking
- `apps.devices` - Device events
- `apps.crawler_guard` - Bot detection events
- `apps.ai_behavior` - Behavioral anomaly events

## 📚 Related Apps

- `apps.crawler_guard` - Bot protection
- `apps.ai_behavior` - Behavioral analysis
- `apps.devices` - Device management
- `apps.users` - User authentication
