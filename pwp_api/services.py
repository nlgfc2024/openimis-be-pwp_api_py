from abc import ABC, abstractmethod

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone


class ResourceService(ABC):
    """Adapter services must apply source-module and consumer row restrictions."""

    def __init__(self, user):
        self.user = user

    @abstractmethod
    def get_queryset(self):
        """Return an authorized, deterministically ordered queryset."""


class SubscriptionService:
    def __init__(self, user):
        self.user = user

    def get_queryset(self):
        from .models import Subscription

        return Subscription.objects.filter(owner=self.user).order_by("created_at", "id")

    @transaction.atomic
    def create(self, data):
        from .models import Subscription

        return Subscription.objects.create(owner=self.user, **data)

    @transaction.atomic
    def update(self, instance, data):
        self._check_owner(instance)
        for name, value in data.items():
            setattr(instance, name, value)
        instance.updated_at = timezone.now()
        instance.save()
        return instance

    @transaction.atomic
    def delete(self, instance):
        self._check_owner(instance)
        instance.delete()

    def _check_owner(self, instance):
        if instance.owner_id != self.user.pk:
            raise PermissionDenied("Subscription belongs to another user")
