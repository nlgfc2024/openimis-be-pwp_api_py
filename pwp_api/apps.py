from django.apps import AppConfig


class PwpApiConfig(AppConfig):
    name = "pwp_api"
    verbose_name = "openIMIS PWP API"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from .configuration import configure
        from .registry import registry

        configure(self.apps)
        registry.load()
