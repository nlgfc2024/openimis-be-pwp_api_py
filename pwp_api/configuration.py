from copy import deepcopy

from django.conf import settings

MODULE_NAME = "pwp_api"
DEFAULTS = {
    "notifications_enabled": False,
    "notification_endpoints": [],
    "notification_timeout": 10,
}
_configuration = deepcopy(DEFAULTS)


def configure(apps):
    global _configuration
    _configuration = deepcopy(DEFAULTS)
    if apps.is_installed("core"):
        from core.models import ModuleConfiguration

        _configuration.update(ModuleConfiguration.get_or_default(MODULE_NAME, DEFAULTS))


def get_configuration():
    # Settings override the database configuration, including in standalone tests.
    return {**deepcopy(_configuration), **getattr(settings, "PWP_API", {})}
