from urllib.parse import urlsplit

from django.utils import timezone
from rest_framework import serializers

from .configuration import get_configuration
from .models import Subscription
from .services import SubscriptionService


class ResourceSerializer(serializers.Serializer):
    """Subclasses declare response fields for OpenAPI and use the adapter converter."""

    def to_representation(self, instance):
        adapter = self.context["view"].adapter
        return adapter.converter_class(self.context["request"].user).to_representation(instance)

    def to_internal_value(self, data):
        adapter = self.context["view"].adapter
        return adapter.converter_class(self.context["request"].user).to_internal_value(data)


def endpoint_allowed(endpoint):
    parsed = urlsplit(endpoint)
    return (
        parsed.scheme == "https" and bool(parsed.hostname)
        and not parsed.username and not parsed.password and not parsed.fragment
        and endpoint in get_configuration()["notification_endpoints"]
    )


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ("id", "resource", "endpoint", "active", "expires_at", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        from .registry import registry

        resource = attrs.get("resource", getattr(self.instance, "resource", None))
        adapter = registry.get(resource)
        if not adapter or not adapter.subscriptions_enabled:
            raise serializers.ValidationError({"resource": "Resource is not subscribable"})
        if not adapter.can_read(self.context["request"].user):
            raise serializers.ValidationError({"resource": "Resource access denied"})
        endpoint = attrs.get("endpoint", getattr(self.instance, "endpoint", ""))
        if not endpoint_allowed(endpoint):
            raise serializers.ValidationError({"endpoint": "Endpoint is not an approved HTTPS destination"})
        expires_at = attrs.get("expires_at", getattr(self.instance, "expires_at", None))
        if expires_at is None or expires_at <= timezone.now():
            raise serializers.ValidationError({"expires_at": "Expiry must be in the future"})
        return attrs

    def create(self, validated_data):
        return SubscriptionService(self.context["request"].user).create(validated_data)

    def update(self, instance, validated_data):
        return SubscriptionService(self.context["request"].user).update(instance, validated_data)


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class LoginResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    exp = serializers.IntegerField()
