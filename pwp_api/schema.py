"""Contributions to the shared openIMIS GraphQL schema."""
import graphene
from core.schema import OpenIMISMutation
from django.core.exceptions import PermissionDenied
from graphene_django import DjangoObjectType
from graphql import GraphQLError

from .models import Subscription
from .permissions import has_subscription_permission
from .registry import registry
from .services import SubscriptionService


def bounded_page(queryset, limit, offset):
    if limit is None or offset is None or not 1 <= limit <= 100 or offset < 0:
        raise GraphQLError("Use a limit from 1 to 100 and a nonnegative offset")
    return queryset[offset:offset + limit]


class PwpSubscriptionType(DjangoObjectType):
    """Explicit public fields; ownership and audit metadata cannot be traversed."""

    class Meta:
        model = Subscription
        fields = ("id", "resource", "endpoint", "enabled", "expires_at", "date_created", "date_updated")


def resource_resolver(adapter):
    def resolve(root, info, limit=25, offset=0):
        user = info.context.user
        if not adapter.can_read(user):
            raise PermissionDenied("Resource access denied")
        queryset = adapter.service_class(user).get_queryset()
        converter = adapter.converter_class(user)
        return [converter.to_representation(row) for row in bounded_page(queryset, limit, offset)]
    return resolve


class SubscriptionQuery(graphene.ObjectType):
    pwp_subscriptions = graphene.List(
        PwpSubscriptionType, limit=graphene.Int(default_value=25), offset=graphene.Int(default_value=0),
        id=graphene.UUID(), description="Owned, undeleted webhook subscriptions (maximum 100 per page).",
    )

    def resolve_pwp_subscriptions(self, info, limit=25, offset=0, id=None):
        queryset = SubscriptionService(info.context.user).get_queryset()
        if id is not None:
            queryset = queryset.filter(pk=id)
        return bounded_page(queryset, limit, offset)


# Loaded once at schema assembly, from deployment-controlled adapters only.
# Prefix fields so they cannot collide with source modules in the host schema.
resource_fields = {}
for adapter in registry.all():
    field_name = "pwp_resource_" + adapter.name
    resource_fields[field_name] = graphene.Field(
        graphene.List(adapter.graphql_type), resolver=resource_resolver(adapter),
        limit=graphene.Int(default_value=25), offset=graphene.Int(default_value=0),
        description="Permission-scoped projection through the registered service and converter.",
    )


Query = type("Query", (SubscriptionQuery,), resource_fields)


class SubscriptionMutation(OpenIMISMutation):
    class Meta:
        abstract = True

    _mutation_module = "pwp_api"
    operation = None

    @classmethod
    def async_mutate(cls, user, **data):
        # Core executes this both synchronously and in its mutation worker.
        if not has_subscription_permission(user, cls.operation):
            return [{"message": "Subscription operation denied"}]
        for key in ("client_mutation_id", "client_mutation_label", "client_mutation_details",
                    "mutation_extensions"):
            data.pop(key, None)
        result = getattr(SubscriptionService(user), cls.operation)(data)
        if not result.get("success"):
            return [{"message": "Subscription operation rejected by the core service"}]
        return None


class CreatePwpSubscriptionMutation(SubscriptionMutation):
    operation = "create"

    class Input(OpenIMISMutation.Input):
        resource = graphene.String(required=True)
        endpoint = graphene.String(required=True)
        enabled = graphene.Boolean(default_value=False)
        expires_at = graphene.DateTime(required=True)


class UpdatePwpSubscriptionMutation(SubscriptionMutation):
    operation = "update"

    class Input(OpenIMISMutation.Input):
        id = graphene.UUID(required=True)
        resource = graphene.String()
        endpoint = graphene.String()
        enabled = graphene.Boolean()
        expires_at = graphene.DateTime()


class DeletePwpSubscriptionMutation(SubscriptionMutation):
    operation = "delete"

    class Input(OpenIMISMutation.Input):
        id = graphene.UUID(required=True)


class Mutation(graphene.ObjectType):
    create_pwp_subscription = CreatePwpSubscriptionMutation.Field()
    update_pwp_subscription = UpdatePwpSubscriptionMutation.Field()
    delete_pwp_subscription = DeletePwpSubscriptionMutation.Field()
