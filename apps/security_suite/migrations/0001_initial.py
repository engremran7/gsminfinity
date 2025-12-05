from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="SecurityConfig",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("devices_enabled", models.BooleanField(default=True)),
                ("crawler_guard_enabled", models.BooleanField(default=False)),
                ("mfa_enabled", models.BooleanField(default=True)),
                ("login_risk_enabled", models.BooleanField(default=False)),
                ("device_quota_enforcement_enabled", models.BooleanField(default=False)),
                (
                    "default_device_window",
                    models.CharField(
                        choices=[("3m", "3 Months"), ("6m", "6 Months"), ("12m", "12 Months")],
                        default="12m",
                        max_length=4,
                    ),
                ),
                ("default_device_limit", models.PositiveIntegerField(default=5)),
                (
                    "security_tier",
                    models.CharField(
                        choices=[("basic", "Basic"), ("standard", "Standard"), ("strict", "Strict")],
                        default="basic",
                        max_length=16,
                    ),
                ),
                (
                    "crawler_default_action",
                    models.CharField(
                        choices=[("allow", "Allow"), ("throttle", "Throttle"), ("block", "Block"), ("challenge", "Challenge")],
                        default="allow",
                        max_length=12,
                    ),
                ),
                (
                    "mfa_policy",
                    models.CharField(
                        choices=[("optional", "Optional"), ("mfa_if_high", "MFA if High Risk"), ("required", "Required")],
                        default="optional",
                        max_length=20,
                    ),
                ),
                (
                    "login_risk_policy",
                    models.CharField(
                        choices=[
                            ("none", "None"),
                            ("info", "Info Only"),
                            ("mfa_if_high", "MFA if High Risk"),
                            ("block_if_high", "Block if High Risk"),
                        ],
                        default="mfa_if_high",
                        max_length=20,
                    ),
                ),
            ],
            options={
                "verbose_name": "Security Config",
            },
        ),
    ]
