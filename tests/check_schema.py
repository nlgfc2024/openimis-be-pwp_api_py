"""Validate the empty-registry schema against its reviewed SDL contract."""
import os
from pathlib import Path

os.environ["DJANGO_SETTINGS_MODULE"] = "tests.empty_settings"

import django  # noqa: E402

django.setup()

import graphene  # noqa: E402
from pwp_api.schema import Query, Mutation  # noqa: E402

schema = graphene.Schema(query=Query, mutation=Mutation)
assert schema.introspect()["__schema"]["queryType"]["name"] == "Query"
expected = Path(__file__).resolve().parents[1] / "docs/schema.graphql"
assert str(schema) + "\n" == expected.read_text(), "Update docs/schema.graphql for deliberate schema changes"
print("Empty-registry GraphQL schema matches docs/schema.graphql")
