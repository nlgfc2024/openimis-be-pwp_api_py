# Skeleton scope and migration boundary

Source branch: `mw/develop`. PR base: `release/26.04`. Keep the PR in draft.

| Current task | Issue | Deliverable |
|---|---|---|
| Identity and registration | #1 | Distribution, app, configuration and v1 routes |
| API infrastructure | #2 | Registry, views, serializers, converters, permissions and services |
| Subscriptions | #3 | Independent persistence, ownership and post-commit notification extension |
| Validation and docs | #4 | Isolated tests, CI, package and schema checks |

No live Patient/Group data source, business service binding, or host manifest edit
is included. Insurance-specific implementations, fixtures, mappings and dependencies
are removed. Contracts are plain JSON; no FHIR conformance is claimed.

## Independent app

The old api_fhir_r4 app can remain installed from its upstream distribution.
Keep its migration history and database records under its original identity.
PWP creates pwp_api_subscription and pwp_api_notification_result with a swappable
owner relation to the host's user model. It does not reuse inherited permission IDs.

Do not rewrite django_migrations, fake migrations, rename FHIR tables or remove the
upstream FHIR app when installing this skeleton. No old subscription data migration
is included; new contracts and permissions require intentional future onboarding.
The new distribution begins at 0.1.0, independent of FHIR 1.10.0 and release/26.04.

## Deferred issues belong to their own PRs

- #5: Patient from individual.Individual, explicit fields, identifiers, permissions,
  source-specific tests and deliberate change bindings.
- #6: Group from individual.Group and GroupIndividual, household/membership semantics,
  scoped queries, contracts and source-specific tests.
- #7: consumer credentials/policies, transactional outbox/workers, signed delivery,
  retries/replay, deletion/revocation feeds and offline synchronization.

This PR must not close those deferred issues. Later PRs reference and close only
the work they implement.

## Validation boundary

The isolated suite uses Django auth, SQLite and a test-only adapter. It checks
routes, permissions, service/converter flow, ownership, schema, notifications and
transaction callbacks. Login is mocked at the host boundary. These tests do not
certify core JWT authentication, real Mlatho queries, PostgreSQL performance or
live partner delivery. Validate those in the assembled host before deployment.
