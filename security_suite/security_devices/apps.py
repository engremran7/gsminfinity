from django.apps import AppConfig


class SecurityDevicesConfig(AppConfig):
    name = "security_suite.security_devices"
    label = "security_devices"
    verbose_name = "Security Devices"

    def ready(self):
        return
