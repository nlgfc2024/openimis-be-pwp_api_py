from abc import ABC, abstractmethod

from core.services import BaseService

from .models import Subscription


class ResourceService(ABC):
    """Adapter services must apply source-module and consumer row restrictions."""

    def __init__(self, user):
        self.user = user

    @abstractmethod
    def get_queryset(self):
        """Return an authorized, deterministically ordered queryset."""


class SubscriptionService(BaseService):
    OBJECT_TYPE = Subscription

    def __init__(self, user, validation_class=None):
        from .validation import SubscriptionValidation

        super().__init__(user, validation_class or SubscriptionValidation)

    def get_queryset(self, operation="search"):
        from django.core.exceptions import PermissionDenied
        from .permissions import has_subscription_permission

        if not has_subscription_permission(self.user, operation):
            raise PermissionDenied(f"Subscription {operation} permission required")
        return Subscription.objects.filter(owner=self.user, is_deleted=False).order_by("date_created", "id")

    def _adjust_create_payload(self, data):
        from django.core.exceptions import PermissionDenied

        if "owner" in data and data["owner"] != self.user:
            raise PermissionDenied("Subscription owner must be the acting user")
        return {**super()._adjust_create_payload(data), "owner": self.user}

    def save_instance(self, instance):
        instance._history_user = self.user
        return super().save_instance(instance)

    def delete_instance(self, instance):
        instance._history_user = self.user
        return super().delete_instance(instance)
