import re
from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from .converters import ResourceConverter
from .services import ResourceService


@dataclass(frozen=True)
class ResourceAdapter:
    name: str
    service_class: type
    converter_class: type
    serializer_class: type
    read_permissions: tuple
    subscriptions_enabled: bool = False

    def can_read(self, user):
        return bool(
            user and user.is_authenticated and user.is_active
            and self.read_permissions and user.has_perms(self.read_permissions)
        )


class ResourceRegistry:
    def __init__(self):
        self._adapters = {}

    def register(self, adapter):
        from .serializers import ResourceSerializer

        if not isinstance(adapter, ResourceAdapter):
            raise ImproperlyConfigured("PWP_API_ADAPTERS entries must be ResourceAdapter objects")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,79}", adapter.name):
            raise ImproperlyConfigured("Invalid PWP resource name")
        if adapter.name.lower() in {"login", "subscriptions", "docs"}:
            raise ImproperlyConfigured("Reserved PWP resource name")
        if any(name.lower() == adapter.name.lower() for name in self._adapters):
            raise ImproperlyConfigured("Duplicate PWP resource name")
        if not adapter.read_permissions:
            raise ImproperlyConfigured("PWP adapters require explicit read permissions")
        for implementation, base in (
            (adapter.service_class, ResourceService),
            (adapter.converter_class, ResourceConverter),
            (adapter.serializer_class, ResourceSerializer),
        ):
            if not issubclass(implementation, base):
                raise ImproperlyConfigured(f"PWP adapter must implement {base.__name__}")
        self._adapters[adapter.name] = adapter

    def load(self):
        self._adapters.clear()
        for path in getattr(settings, "PWP_API_ADAPTERS", ()):
            self.register(import_string(path))

    def get(self, name):
        return self._adapters.get(name)

    def all(self):
        return tuple(self._adapters.values())


registry = ResourceRegistry()
