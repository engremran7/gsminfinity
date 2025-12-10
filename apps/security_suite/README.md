# 🔐 Security Suite

Parent security package containing modular security components that can be used independently or together.

## ✨ Overview

The Security Suite is a meta-package that bundles security-related apps:
- `security_bots/` - Bot detection utilities
- `security_devices/` - Device fingerprinting
- `security_risk/` - Risk assessment

This package is designed for distribution as a standalone security toolkit.

## 📦 Installation

### As Standalone Package

```bash
pip install gsminfinity-security-suite
```

### From Source

```bash
cp -r security_suite /your_project/
pip install -e security_suite/
```

## 📚 Components

### security_bots

Bot detection and management utilities.

```python
from security_suite.security_bots import detect_bot

is_bot = detect_bot(user_agent)
```

### security_devices

Device fingerprinting and tracking.

```python
from security_suite.security_devices import get_device_fingerprint

fingerprint = get_device_fingerprint(request)
```

### security_risk

Risk scoring and assessment.

```python
from security_suite.security_risk import calculate_risk

risk_score = calculate_risk(user, actions)
```

## ⚙️ Configuration

See `pyproject.toml` for package configuration.

## 🔗 Integration

These components are used by:
- `apps/crawler_guard` - Uses security_bots
- `apps/devices` - Uses security_devices
- `apps/ai_behavior` - Uses security_risk

## 📝 Development

```bash
# Install dev dependencies
pip install -e security_suite/[dev]

# Run tests
pytest security_suite/

# Build package
python -m build security_suite/
```

## 📄 License

MIT License

## 🤝 Dependencies

See `pyproject.toml` for package dependencies.
