import graphene
from django.test import RequestFactory
from core.models import MutationLog
from pwp_api.schema import Query, Mutation


# Match host composition, including inherited module fields.
class HostQuery(Query, graphene.ObjectType):
    host_marker = graphene.Boolean()


class HostMutation(Mutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=HostQuery, mutation=HostMutation)


def execute(user, document, variables=None):
    request = RequestFactory().post("/graphql", content_type="application/json")
    request.user = user
    return schema.execute(document, variable_values=variables, context_value=request)


def mutate(user, operation, payload):
    title = operation.title()
    field = operation + "PwpSubscription"
    result = execute(user, "mutation($input: " + title + "PwpSubscriptionMutationInput!) { " + field +
                     "(input: $input) { internalId clientMutationId } }", {"input": payload})
    if result.errors:
        raise AssertionError(result.errors)
    return MutationLog.objects.get(pk=result.data[field]["internalId"])
