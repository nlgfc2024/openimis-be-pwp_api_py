from django.apps import AppConfig

from .configuration import DEFAULTS as DEFAULT_CFG  # noqa: F401; core permission discovery


class PwpApiConfig(AppConfig):
    name = "pwp_api"
    verbose_name = "openIMIS PWP API"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from .configuration import configure
        from .registry import registry

        configure(self.apps)
        registry.load()
