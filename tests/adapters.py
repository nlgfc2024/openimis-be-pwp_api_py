from django.contrib.auth import get_user_model
from rest_framework import serializers

from pwp_api.converters import ResourceConverter
from pwp_api.registry import ResourceAdapter
from pwp_api.serializers import ResourceSerializer
from pwp_api.services import ResourceService


class ExampleService(ResourceService):
    def get_queryset(self):
        return get_user_model().objects.filter(pk=self.user.pk).order_by("pk")


class ExampleConverter(ResourceConverter):
    def to_representation(self, instance):
        return {"id": str(instance.pk), "name": instance.username}


class ExampleSerializer(ResourceSerializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)


example = ResourceAdapter(
    name="Example", service_class=ExampleService, converter_class=ExampleConverter,
    serializer_class=ExampleSerializer, read_permissions=("900001",),
    subscriptions_enabled=True,
)
