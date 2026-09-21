# Skeleton scope and migration boundary

Branch hierarchy: `release/26.04` -> `mw/develop` -> `feature/pwp-api-skeleton`.
PR source: `feature/pwp-api-skeleton`. PR base: `mw/develop`. Keep the PR in draft.

| Current task | Issue | Deliverable |
|---|---|---|
| Identity and registration | #1 | Distribution, app and configuration identity |
| API infrastructure | #2 | Registry, typed GraphQL projections, converters, permissions and services |
| Subscriptions | #3 | Independent persistence, ownership and post-commit notification extension |
| Validation and docs | #4 | Core-backed tests, CI, package and schema checks |
| Retain generic core infrastructure | #9 | Numeric operation rights, history/audit, core services and validation |
| Native GraphQL interface | #10 | Host Query/Mutation composition, typed variables, core mutation logging and schema docs |

No live Individual/Group data source, business service binding, or host manifest edit
is included. Insurance-specific implementations, fixtures, mappings and dependencies
are removed. The shared host GraphQL endpoint replaces the draft REST/OpenAPI interface;
GraphQL inputs/outputs and webhook JSON have no FHIR conformance claim.

## Gap and relationship to existing GraphQL

Existing openIMIS GraphQL already supports authorized reads with host credentials,
including a suitably provisioned service account. Basic PWP data access alone does
not justify another API module. This PR contributes to that same endpoint; it
adds no separate server, login flow or live Individual/Group read capability.

The planned addition is a deliberately limited integration contract: approved
Individual/Group fields and consumer-specific dataset restrictions (#5/#6), then
committed-change delivery and resumable mobile read synchronization (#7). Those
guarantees do not follow merely from having GraphQL credentials. They remain
follow-up work, not capabilities delivered by this skeleton. If a consumer only
needs reads already covered by the existing schema and permissions, use those
queries and polling; a PWP adapter or webhook is not a prerequisite.

## Consumers and why subscriptions are retained

Issues #5, #6, #7 and their parent #11 describe approved external partner systems
and mobile applications as the intended consumer categories. They do not establish
a named first consumer, an agreed Jobs Portal contract, a reporting-pipeline
requirement, or a delivery latency/volume target. Those decisions remain open;
this skeleton must not be presented as an approved integration for such a system.

The subscription extension from #3 is retained for a future partner requirement
to receive committed record changes without repeated polling. It is an outbound
HTTP webhook mechanism, not GraphQL subscriptions or WebSockets. Mobile clients
would pull snapshots and changes under #7 rather than host webhook endpoints.
Read-only requirements can use polling. A named consumer, agreed fields/scope,
freshness requirements and an explicit polling-versus-push decision are required
before enabling a production integration. No business signals or adapters are
bound here, and notifications remain disabled by default.

Current delivery loops over recipients synchronously after commit; each HTTP
request has a default 10-second timeout, so multiple subscribers can occupy the
calling worker for many timeout periods. Before a real consumer depends on push,
#7 must provide a transactional outbox, background workers (for example Celery),
retries, deduplication, signing and operational recovery. Merely dispatching the
HTTP call to Celery does not close the commit-to-enqueue loss window. Adapter
development and notification enablement are separate milestones.

## Target MIS and deployment gate

The intended host is Malawi's Mlatho backend, `nlgfc2024/openimis-be_py`, on the
`mw/develop` integration line based on `release/26.04`. Its `openimis.json` on
21 September 2026 has no `pwp_api` entry and retains upstream `api_fhir_r4`.
That is a source-manifest observation, not evidence about a running deployment.
This draft PR is preparatory and does not install or enable the module in a MIS.

A separate host integration PR should select an immutable tested revision or
release artifact after the first consumer contract, required adapters, consumer
policy and assembled-host authentication/schema/migration checks are accepted.
Production push or offline synchronization additionally requires #7's acceptance
evidence. No deployment date or pin is committed by this PR, and merging the
skeleton must not automatically enable notifications.

## Independent app

This repository stops distributing the inherited FHIR implementation. PWP's
planned contract is non-FHIR; there is no planned FHIR restoration within #5–#7.
It does not replace or retire upstream FHIR integrations. Any later FHIR mapping
would require an explicit separate scope and compatibility decision.

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
test-only resource adapter. The real pinned location module satisfies core
GraphQL imports; only its unused medical-pricelist foreign-key targets are stubbed. Core schema is synchronized without running its legacy migrations;
PWP's initial migration and generated history model are tested normally.
Tests cover numeric rights, ownership, direct service validation, audit actors,
versioning, soft deletion, rollback, schema, notifications and transaction callbacks.
Tests compose module Query/Mutation using host-style inheritance and exercise
real core mutation logging and worker execution. Authentication is supplied as
a request context; host JWT middleware, full-host
PostgreSQL migrations, actual Mlatho queries and live delivery remain outside this
suite's scope.
