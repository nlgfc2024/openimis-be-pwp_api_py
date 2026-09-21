# openIMIS PWP API module skeleton

Reusable infrastructure for future Mlatho integrations. No Individual, Group,
insurance or other business-data source is implemented or registered yet.

| Identity | Value |
|---|---|
| Repository | `nlgfc2024/openimis-be-pwp_api_py` |
| Python distribution | `openimis-be-pwp_api` |
| Python package / Django app / configuration key | `pwp_api` |
| AppConfig | `pwp_api.apps.PwpApiConfig` |
| Independent package version | `0.1.0` |
| GraphQL endpoint | Host `<SITE_ROOT>/graphql` |

## Installation

Add an entry to the host openimis.json, then use its normal module installation
and migration workflow:

```json
{
  "name": "pwp_api",
  "pip": "-e /absolute/path/to/openimis-be-pwp_api_py"
}
```

Use a pinned revision or built package for deployment. The host discovers
`pwp_api.schema.Query` and `pwp_api.schema.Mutation` and composes them with other
modules at `<SITE_ROOT>/graphql`. The module's `urls.py` deliberately exports no
routes. Its identity remains `pwp_api`; there is no separate PWP GraphQL server.

Authentication, JWT middleware, CSRF policy and GraphQL tooling come from the
host. Use its existing login/token flow. GraphQL still uses HTTP: clients POST a
query/mutation document plus a JSON `variables` object, instead of resource URLs
and REST query parameters. Subtask #10 supersedes the earlier draft's
`/pwp_api/v1/` routes and OpenAPI/Swagger/ReDoc interface.

This is a new application, not an in-place upgrade of api_fhir_r4. Keep upstream
FHIR installed separately when needed. PWP creates only its own tables and does
not adopt FHIR migration history or subscriptions. See [scope notes](docs/scope.md).

## GraphQL contract

The reviewed empty-registry [schema](docs/schema.graphql) is checked by CI. Use
the host's schema introspection/GraphiQL facilities where enabled.

| GraphQL field | Purpose |
|---|---|
| `pwpSubscriptions(limit, offset, id)` | Owned, undeleted webhook registrations |
| `createPwpSubscription(input)` | Create through core validation/service |
| `updatePwpSubscription(input)` | Update an owned registration |
| `deletePwpSubscription(input)` | Soft-delete an owned registration |
| `pwpResource<Name>(limit, offset)` | Read-only projection for each explicitly registered adapter |

Lists default to 25 records, allow at most 100 and require a nonnegative offset.
There are no arbitrary ORM filters or unbounded nested model relationships.
No Individual or Group field exists yet. Subscription creation rejects unknown
resources, including all resources when the production registry is empty.

```graphql
query Registrations($limit: Int!, $offset: Int!) {
  pwpSubscriptions(limit: $limit, offset: $offset) {
    id resource enabled expiresAt
  }
}
```

Variables: `{"limit": 25, "offset": 0}`.

Once a future source adapter is registered, clients can create a registration:

```graphql
mutation Register($input: CreatePwpSubscriptionMutationInput!) {
  createPwpSubscription(input: $input) { internalId clientMutationId }
}
```

For the test-only Example adapter, variables take this shape (choose an approved
endpoint and a future expiry in the deployment):

```json
{
  "input": {
    "resource": "Example",
    "endpoint": "https://partner.example/events",
    "enabled": true,
    "expiresAt": "2099-01-01T00:00:00",
    "clientMutationId": "registration-1",
    "clientMutationLabel": "Register partner webhook"
  }
}
```

Mutations inherit `core.schema.OpenIMISMutation`: core records the request,
runs validation signals and executes synchronously or through its configured
worker. `internalId` identifies the **mutation log**, not the subscription.
Acceptance is not proof of success: use the host's mutation-status query with
`clientMutationId` and inspect errors before refreshing `pwpSubscriptions`.
Input coercion follows the host's Graphene 2 conventions. Worker execution
rechecks permission and ownership through the same service as synchronous calls.

## Extension interfaces

- `ResourceService`: return an authorized, deterministically ordered queryset
  using source-module access rules and additional consumer restrictions.
- `ResourceConverter`: map records to an explicit external field allowlist.
  The read resolver and notification delivery use the same converter. Inbound
  conversion remains an extension point for future approved source mutations.
- `ResourceAdapter`: combine service, converter, `graphql_type` (a concrete
  `graphene.ObjectType` projection), unique GraphQL-safe resource name,
  nonempty read-permission tuple and explicit subscription opt-in. GraphQL
  types replace DRF serializers for schema declaration and response serialization.
- `PWP_API_ADAPTERS`: trusted dotted adapter paths, empty by default. Schema
  assembly exposes typed, prefixed read fields; restart after registry changes.
  Source writes and source-specific filters require deliberate typed additions.
- `signals.bind_service_signals()`: intentionally empty host discovery hook.
  Future adapters can bind approved service events to
  `notifications.publish_resource(resource_name, primary_key)`.

The [test-only Example adapter](tests/adapters.py) demonstrates conversion and
scope with real openIMIS user/role fixtures; it is excluded from the wheel.
Do not expose arbitrary models, full `json_ext` fields or unrestricted querysets.
Do not add a Relay node lookup that bypasses service-level row permissions.

## Subscription configuration and limitations

Configuration is loaded from openIMIS ModuleConfiguration under `pwp_api`.
Django settings override database values:

```python
PWP_API = {
    "notifications_enabled": False,
    "notification_endpoints": [],  # exact trusted HTTPS URLs, no wildcards
    "notification_timeout": 10,
    "subscription_search_perms": ["158001"],
    "subscription_create_perms": ["158002"],
    "subscription_update_perms": ["158003"],
    "subscription_delete_perms": ["158004"],
}
PWP_API_ADAPTERS = []
```

Subscription input: `resource`, `endpoint`, `enabled`, `expiresAt`. Ownership is
assigned from the authenticated user, never the payload. Lists, details and
mutations are owner-scoped and require the configured operation right.
Creation/update additionally requires resource rights and an approved HTTPS destination. No arbitrary ORM criteria or caller-supplied
credential headers are accepted. `enabled` defaults to false and controls delivery.
The inherited model `active` property still reflects soft-deletion status.

Subscription search/create/update/delete deliberately reuse rights 158001–158004
by default. Existing holders of those FHIR subscription rights can perform the
corresponding PWP operation, subject to ownership and resource access. Deployments
that require separate PWP authorization can override these lists. Empty lists deny
access. Defaults are exported for core permission discovery. This module does not
regrant or revoke shared role rights in migrations; existing role assignments and
core's IMIS administrator behavior remain authoritative.

Subscriptions inherit `core.models.HistoryBusinessModel`: actor audit fields,
versioning, historical snapshots, business validity and soft deletion are retained.
Mutations call `core.services.BaseService` with `BaseModelValidation`-based checks,
including for direct service callers. History records include the acting user.
`deletePwpSubscription` marks the subscription deleted and preserves its history and delivery results;
deleted records are excluded from API queries and notification delivery.

Delivery rechecks recipient rights and recipient-scoped visibility, expiry,
enabled status and destination approval. It does not follow redirects. All 2xx
responses, including empty 204, are accepted. Results store status and sanitized
errors, not response bodies or resource payloads. Destination configuration is an
administrator trust boundary: configure controlled endpoints and enforce network
egress restrictions when deploying delivery.

These subscriptions register outbound HTTP webhooks; they are not GraphQL
`subscription` operations or WebSocket streams. `publish_resource()` waits for
commit, then delivers synchronously. This is not a
durable queue: crashes can lose notifications and slow receivers can delay the
caller. Retries, signing, replay, delete/revocation events, consumer credentials
and offline synchronization belong to follow-up #7. Keep notifications disabled
until a real adapter and partner delivery policy exist.

## Development

Isolated checks need no openIMIS database or insurance modules:

```bash
python -m pip install -r requirements-test.txt
python -m django test tests --settings=tests.settings
python -m django makemigrations --check --dry-run --settings=tests.empty_settings
python -m tests.check_schema
python -m build
```

CI installs pinned Mlatho core and location revisions and exercises actual core
models, role rights, mutation logs, worker execution, services and history against
SQLite. Two minimal test-only medical-pricelist models satisfy unused location
foreign keys; no medical behavior is provided. Core/location legacy migrations
are not run in this harness; PWP migrations are.
Full assembled-host authentication and PostgreSQL migration validation remain
required before deployment. Initial targets: Python 3.10–3.12 and Django 4.2.
Inherited FHIR publication automation is removed; no package is auto-published.

## Work tracking and provenance

Current PR tasks: [#1](https://github.com/nlgfc2024/openimis-be-pwp_api_py/issues/1),
[#2](https://github.com/nlgfc2024/openimis-be-pwp_api_py/issues/2),
[#3](https://github.com/nlgfc2024/openimis-be-pwp_api_py/issues/3),
[#4](https://github.com/nlgfc2024/openimis-be-pwp_api_py/issues/4),
[#9](https://github.com/nlgfc2024/openimis-be-pwp_api_py/issues/9) (retain core infrastructure),
[#10](https://github.com/nlgfc2024/openimis-be-pwp_api_py/issues/10) (native GraphQL interface).

Separate future PRs:
- [#5](https://github.com/nlgfc2024/openimis-be-pwp_api_py/issues/5): Individual from individual.Individual.
- [#6](https://github.com/nlgfc2024/openimis-be-pwp_api_py/issues/6): Group from individual.Group / GroupIndividual.
- [#7](https://github.com/nlgfc2024/openimis-be-pwp_api_py/issues/7): durable delivery and mobile synchronization.

Derived from the openIMIS FHIR R4 reference module at release/26.04, commit
514b1c70c6086cdc951b4cbbda66dec0cda64555. The insurance implementation remains in
Git history. This branch reshapes its integration patterns into a source-independent
skeleton. Original author attribution and license notices are retained.
License: GNU AGPL v3; see [LICENSE.md](LICENSE.md).
