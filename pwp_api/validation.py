from urllib.parse import urlsplit

from core.validation import BaseModelValidation
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from .configuration import get_configuration
from .models import Subscription
from .permissions import has_subscription_permission


def endpoint_allowed(endpoint):
    parsed = urlsplit(endpoint)
    return (
        parsed.scheme == "https" and bool(parsed.hostname)
        and not parsed.username and not parsed.password and not parsed.fragment
        and endpoint in get_configuration()["notification_endpoints"]
    )


def validate_subscription_data(user, data, instance=None):
    from .registry import registry

    resource = data.get("resource", getattr(instance, "resource", None))
    adapter = registry.get(resource)
    if not adapter or not adapter.subscriptions_enabled:
        raise ValidationError({"resource": "Resource is not subscribable"})
    if not adapter.can_read(user):
        raise PermissionDenied("Resource access denied")
    endpoint = data.get("endpoint", getattr(instance, "endpoint", ""))
    if not endpoint_allowed(endpoint):
        raise ValidationError({"endpoint": "Endpoint is not an approved HTTPS destination"})
    expires_at = data.get("expires_at", getattr(instance, "expires_at", None))
    if expires_at is None or expires_at <= timezone.now():
        raise ValidationError({"expires_at": "Expiry must be in the future"})


class SubscriptionValidation(BaseModelValidation):
    OBJECT_TYPE = Subscription
    writable_fields = {"resource", "endpoint", "enabled", "expires_at"}

    @classmethod
    def _check_permission(cls, user, operation):
        if not has_subscription_permission(user, operation):
            raise PermissionDenied(f"Subscription {operation} permission required")

    @classmethod
    def _check_fields(cls, data, extra=()):
        if set(data) - cls.writable_fields - set(extra):
            raise ValidationError("Subscription ownership and audit fields cannot be supplied")

    @classmethod
    def _owned_instance(cls, user, data):
        instance = Subscription.objects.select_for_update().filter(
            pk=data.get("id"), owner=user, is_deleted=False,
        ).first()
        if instance is None:
            raise PermissionDenied("Subscription not found or not owned by this user")
        return instance

    @classmethod
    def validate_create(cls, user, **data):
        super().validate_create(user, **data)
        cls._check_permission(user, "create")
        cls._check_fields(data, extra=("owner",))
        if data.get("owner") != user:
            raise PermissionDenied("Subscription owner must be the acting user")
        validate_subscription_data(user, data)

    @classmethod
    def validate_update(cls, user, **data):
        super().validate_update(user, **data)
        cls._check_permission(user, "update")
        cls._check_fields(data, extra=("id",))
        validate_subscription_data(user, data, cls._owned_instance(user, data))

    @classmethod
    def validate_delete(cls, user, **data):
        super().validate_delete(user, **data)
        cls._check_permission(user, "delete")
        if set(data) != {"id"}:
            raise ValidationError("Delete requires only the subscription ID")
        cls._owned_instance(user, data)
