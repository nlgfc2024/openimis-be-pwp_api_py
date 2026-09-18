from rest_framework import serializers

from .models import Subscription
from .services import SubscriptionService
from .validation import validate_subscription_data
from django.core.exceptions import ValidationError as DjangoValidationError, PermissionDenied
from rest_framework.exceptions import PermissionDenied as APIPermissionDenied


class ResourceSerializer(serializers.Serializer):
    """Subclasses declare response fields for OpenAPI and use the adapter converter."""

    def to_representation(self, instance):
        adapter = self.context["view"].adapter
        return adapter.converter_class(self.context["request"].user).to_representation(instance)

    def to_internal_value(self, data):
        adapter = self.context["view"].adapter
        return adapter.converter_class(self.context["request"].user).to_internal_value(data)


def require_service_success(result):
    if not result.get("success"):
        # Core result details may contain internals; do not expose them to API clients.
        raise serializers.ValidationError("Subscription operation rejected by the core service")
    return result.get("data")


class SubscriptionSerializer(serializers.ModelSerializer):
    active = serializers.BooleanField(source="enabled", required=False)
    created_at = serializers.DateTimeField(source="date_created", read_only=True)
    updated_at = serializers.DateTimeField(source="date_updated", read_only=True)

    class Meta:
        model = Subscription
        fields = ("id", "resource", "endpoint", "active", "expires_at", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        try:
            validate_subscription_data(self.context["request"].user, attrs, self.instance)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        except PermissionDenied as exc:
            raise APIPermissionDenied(str(exc)) from exc
        return attrs

    def create(self, validated_data):
        result = SubscriptionService(self.context["request"].user).create(validated_data)
        data = require_service_success(result)
        return Subscription.objects.get(pk=data["id"])

    def update(self, instance, validated_data):
        result = SubscriptionService(self.context["request"].user).update({**validated_data, "id": instance.pk})
        require_service_success(result)
        instance.refresh_from_db()
        return instance


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class LoginResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    exp = serializers.IntegerField()
