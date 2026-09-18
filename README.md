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
| API prefix | `<SITE_ROOT>/pwp_api/v1/` |

## Installation

Add an entry to the host openimis.json, then use its normal module installation
and migration workflow:

```json
{
  "name": "pwp_api",
  "pip": "-e /absolute/path/to/openimis-be-pwp_api_py"
}
```

Use a pinned revision or built package for deployment. The host mounts this app
at `<SITE_ROOT>/pwp_api/`; the app adds `v1/`. In ordinary Django, use
`path("pwp_api/", include("pwp_api.urls"))`.

The host supplies openIMIS core authentication and REST framework authentication
settings plus `drf_spectacular.openapi.AutoSchema`. The module inherits those
authentication classes and does not bypass session CSRF checks. Login delegates
to the host's authentication and JWT functions.

This is a new application, not an in-place upgrade of api_fhir_r4. Keep upstream
FHIR installed separately when needed. PWP creates only its own tables and does
not adopt FHIR migration history or subscriptions. See [scope notes](docs/scope.md).

## Available routes

| Route under module prefix | Purpose |
|---|---|
| `v1/login/` | POST username/password; host returns token and expiry |
| `v1/subscriptions/` | Authenticated, owner-scoped subscription CRUD |
| `v1/docs/` | Authenticated, module-only OpenAPI schema |
| `v1/docs/swagger/` | Authenticated Swagger UI |
| `v1/docs/redoc/` | Authenticated ReDoc |

Business routes are absent. Subscription creation rejects all resources until an
explicit adapter is registered and opts into subscriptions. Contracts use plain
versioned JSON and DRF errors, not the inherited FHIR payload format.

## Extension interfaces

- `ResourceService`: return an authorized, deterministically ordered queryset
  using source-module access rules and additional consumer restrictions.
- `ResourceConverter`: map records to a stable external contract with explicit
  field allowlists. Implement inbound conversion only for an approved write flow.
- `ResourceSerializer`: declare concrete fields for OpenAPI; delegate conversion
  to the adapter converter.
- `ResourceAdapter`: combine service, converter, serializer, unique resource name,
  nonempty read-permission tuple, and explicit subscription opt-in.
- `PWP_API_ADAPTERS`: Django setting of dotted paths to trusted adapter objects;
  defaults to empty. Routes expose list/detail only. Writes need separate commands.
- `signals.bind_service_signals()`: host discovery hook, intentionally with no
  source bindings. Future adapters can bind approved service events and call
  `notifications.publish_resource(resource_name, primary_key)`.

The [test-only Example adapter](tests/adapters.py) demonstrates the interface with
real openIMIS user/role fixtures. It is not a Mlatho resource and is excluded from the wheel.
Do not expose arbitrary models, full json_ext fields, or unrestricted querysets.

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

Subscription input: `resource`, `endpoint`, `active`, `expires_at`. Ownership is
assigned from the authenticated user, never the payload. Lists, details and
mutations are owner-scoped and require the configured operation right.
Creation/update additionally requires resource rights and an approved HTTPS destination. No arbitrary ORM criteria or caller-supplied
credential headers are accepted. The API's `active` flag maps to `enabled` internally
and defaults to false; it controls delivery, not record deletion.

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
DELETE marks the subscription deleted and preserves its history and delivery results;
deleted records are excluded from API queries and notification delivery.

Delivery rechecks recipient rights and recipient-scoped visibility, expiry,
active status and destination approval. It does not follow redirects. All 2xx
responses, including empty 204, are accepted. Results store status and sanitized
errors, not response bodies or resource payloads. Destination configuration is an
administrator trust boundary: configure controlled endpoints and enforce network
egress restrictions when deploying delivery.

`publish_resource()` waits for commit, then delivers synchronously. This is not a
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
python -m django spectacular --settings=tests.empty_settings --urlconf=pwp_api.schema_urls --validate --fail-on-warn --file=/tmp/pwp-schema.yml
python -m build
```

CI installs a pinned Mlatho core revision and exercises its actual models,
role rights, services, validation and history against SQLite. Two minimal test-only
location models satisfy unused core foreign keys; they provide no location behavior.
Core/location legacy migrations are not run in this harness; PWP migrations are.
Full assembled-host authentication and PostgreSQL migration validation remain
required before deployment. Initial targets: Python 3.10–3.12 and Django 4.2.
Inherited FHIR publication automation is removed; no package is auto-published.

## Work tracking and provenance

Current PR tasks: [#1](https://github.com/nlgfc2024/openimis-be-pwp_api_py/issues/1),
[#2](https://github.com/nlgfc2024/openimis-be-pwp_api_py/issues/2),
[#3](https://github.com/nlgfc2024/openimis-be-pwp_api_py/issues/3),
[#4](https://github.com/nlgfc2024/openimis-be-pwp_api_py/issues/4),
[#9](https://github.com/nlgfc2024/openimis-be-pwp_api_py/issues/9) (retain core infrastructure).

Separate future PRs:
- [#5](https://github.com/nlgfc2024/openimis-be-pwp_api_py/issues/5): Individual from individual.Individual.
- [#6](https://github.com/nlgfc2024/openimis-be-pwp_api_py/issues/6): Group from individual.Group / GroupIndividual.
- [#7](https://github.com/nlgfc2024/openimis-be-pwp_api_py/issues/7): durable delivery and mobile synchronization.

Derived from the openIMIS FHIR R4 reference module at release/26.04, commit
514b1c70c6086cdc951b4cbbda66dec0cda64555. The insurance implementation remains in
Git history. This branch reshapes its integration patterns into a source-independent
skeleton. Original author attribution and license notices are retained.
License: GNU AGPL v3; see [LICENSE.md](LICENSE.md).
