from django.apps import AppConfig


class SecurityRiskConfig(AppConfig):
    name = "security_suite.security_risk"
    label = "security_risk"
    verbose_name = "Security Risk / AI Behavior"

    def ready(self):
        return
