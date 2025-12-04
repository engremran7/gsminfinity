from django.apps import AppConfig


class SecurityBotsConfig(AppConfig):
    name = "security_suite.security_bots"
    label = "security_bots"
    verbose_name = "Security Bots / Crawler Guard"

    def ready(self):
        return
