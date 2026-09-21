from django.contrib.auth import get_user_model
import graphene

from pwp_api.converters import ResourceConverter
from pwp_api.registry import ResourceAdapter
from pwp_api.services import ResourceService


class ExampleService(ResourceService):
    def get_queryset(self):
        return get_user_model().objects.filter(pk=self.user.pk).order_by("pk")


class ExampleConverter(ResourceConverter):
    def to_representation(self, instance):
        return {"id": str(instance.pk), "name": instance.username}


class ExampleType(graphene.ObjectType):
    id = graphene.ID(required=True)
    name = graphene.String(required=True)


example = ResourceAdapter(
    name="Example", service_class=ExampleService, converter_class=ExampleConverter,
    graphql_type=ExampleType, read_permissions=("900001",),
    subscriptions_enabled=True,
)
