from django.apps import AppConfig


class SecurityConfig(AppConfig):
    name = "security_suite.security"
    label = "security"
    verbose_name = "Security Facade"

    def ready(self):
        # Facade only; no side effects.
        return
