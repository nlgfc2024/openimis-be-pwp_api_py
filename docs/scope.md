# Skeleton scope and migration boundary

Branch hierarchy: `release/26.04` -> `mw/develop` -> `feature/pwp-api-skeleton`.
PR source: `feature/pwp-api-skeleton`. PR base: `mw/develop`. Keep the PR in draft.

| Current task | Issue | Deliverable |
|---|---|---|
| Identity and registration | #1 | Distribution, app, configuration and v1 routes |
| API infrastructure | #2 | Registry, views, serializers, converters, permissions and services |
| Subscriptions | #3 | Independent persistence, ownership and post-commit notification extension |
| Validation and docs | #4 | Core-backed tests, CI, package and schema checks |
| Retain generic core infrastructure | #9 | Numeric operation rights, history/audit, core services and validation |

No live Individual/Group data source, business service binding, or host manifest edit
is included. Insurance-specific implementations, fixtures, mappings and dependencies
are removed. Contracts are plain JSON; no FHIR conformance is claimed.

## Independent app

The old api_fhir_r4 app can remain installed from its upstream distribution.
Keep its migration history and database records under its original identity.
PWP creates pwp_api_subscription, pwp_api_historicalsubscription and
pwp_api_notification_result. Subscription inherits core HistoryBusinessModel,
including core user audit relations with distinct reverse names for coexistence.
It reuses subscription rights 158001–158004 as configurable operation defaults;
existing assignments also authorize the equivalent PWP operation. Ownership and
resource rights are additional constraints. No migration grants or revokes shared
role rights. See README for configuration.

Do not rewrite django_migrations, fake migrations, rename FHIR tables or remove the
upstream FHIR app when installing this skeleton. No old subscription data migration
is included; new contracts and permissions require intentional future onboarding.
The new distribution begins at 0.1.0, independent of FHIR 1.10.0 and release/26.04.
Subtask #9 revises this unpublished draft's initial PWP migration to include core
history fields. This is a fresh-install definition, not an upgrade migration for
a database that applied the earlier draft. No live database has been migrated by
this PR; do not fake this revised initial migration onto an earlier PWP schema.

## Deferred issues belong to their own PRs

- #5: Individual from individual.Individual, explicit fields, identifiers, permissions,
  source-specific tests and deliberate change bindings.
- #6: Group from individual.Group and GroupIndividual, household/membership semantics,
  scoped queries, contracts and source-specific tests.
- #7: consumer credentials/policies, transactional outbox/workers, signed delivery,
  retries/replay, deletion/revocation feeds and offline synchronization.

This PR must not close those deferred issues. Later PRs reference and close only
the work they implement.

## Validation boundary

The suite uses the actual pinned Mlatho core models, role-right evaluation,
BaseService, BaseModelValidation and HistoryBusinessModel, with SQLite and a
test-only resource adapter. Only unused core location foreign-key targets are
stubbed. Core schema is synchronized without running its legacy migrations;
PWP's initial migration and generated history model are tested normally.
Tests cover numeric rights, ownership, direct service validation, audit actors,
versioning, soft deletion, rollback, schema, notifications and transaction callbacks.
Login remains mocked at the host boundary. Core JWT authentication, full-host
PostgreSQL migrations, actual Mlatho queries and live delivery remain outside this
suite's scope.
