from core.models import MutationLog
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from tests.graphql_helpers import execute, mutate, schema

from pwp_api.models import NotificationResult, Subscription
from pwp_api.notifications import NotificationClient, notify_subscribers, publish_resource
from pwp_api.registry import ResourceRegistry
from tests.adapters import example
from tests.factories import create_user, grant_right, revoke_right
from pwp_api.services import SubscriptionService


class SkeletonTests(TestCase):
    def setUp(self):
        self.owner = create_user("owner")
        self.other = create_user("other")
        self.data = {"resource": "Example", "enabled": True, "endpoint": "https://partner.example/events",
                     "expiresAt": (timezone.now() + timedelta(days=1)).isoformat()}

    def subscription(self, owner=None):
        result = SubscriptionService(owner or self.owner).create({
            "resource": "Example", "endpoint": self.data["endpoint"], "enabled": True,
            "expires_at": timezone.now() + timedelta(days=1),
        })
        self.assertTrue(result["success"], result)
        return Subscription.objects.get(pk=result["data"]["id"])

    def test_anonymous_requests_denied(self):
        result = execute(AnonymousUser(), "{ pwpSubscriptions { id } pwpResourceExample { id } }")
        self.assertEqual(len(result.errors), 2)

    def test_resource_service_and_converter_scope(self):
        result = execute(self.owner, "{ pwpResourceExample(limit: 10) { id name } }")
        self.assertFalse(result.errors, result.errors)
        self.assertEqual(result.data["pwpResourceExample"], [{"id": str(self.owner.pk), "name": "owner"}])

    def test_missing_resource_permission_denied(self):
        revoke_right(self.owner, 900001)
        self.assertTrue(execute(self.owner, "{ pwpResourceExample { id } }").errors)
        self.assertEqual(mutate(self.owner, "create", self.data).status, MutationLog.ERROR)

    def test_subscription_create_update_delete_uses_core_mutation_log(self):
        log = mutate(self.owner, "create", {**self.data, "clientMutationId": "pwp-test-1"})
        self.assertEqual(log.status, MutationLog.SUCCESS, log.error)
        self.assertEqual(log.client_mutation_id, "pwp-test-1")
        sub = Subscription.objects.get()
        self.assertEqual(sub.owner, self.owner)
        self.assertEqual(mutate(self.owner, "update", {"id": str(sub.pk), "enabled": False}).status,
                         MutationLog.SUCCESS)
        sub.refresh_from_db()
        self.assertFalse(sub.enabled)
        self.assertEqual(mutate(self.owner, "delete", {"id": str(sub.pk)}).status, MutationLog.SUCCESS)
        sub.refresh_from_db()
        self.assertTrue(sub.is_deleted)
        self.assertEqual(sub.history.count(), 3)

    def test_subscription_owner_isolation(self):
        own = self.subscription()
        foreign = self.subscription(self.other)
        result = execute(self.owner, "{ pwpSubscriptions { id } }")
        self.assertFalse(result.errors, result.errors)
        self.assertEqual(result.data["pwpSubscriptions"], [{"id": str(own.pk)}])
        result = execute(self.owner, "query($id: UUID!) { pwpSubscriptions(id: $id) { id } }",
                         {"id": str(foreign.pk)})
        self.assertEqual(result.data["pwpSubscriptions"], [])
        self.assertEqual(mutate(self.owner, "update", {"id": str(foreign.pk), "enabled": False}).status,
                         MutationLog.ERROR)
        self.assertEqual(mutate(self.owner, "delete", {"id": str(foreign.pk)}).status, MutationLog.ERROR)

    def test_unregistered_resource_and_unapproved_endpoint_rejected(self):
        for change in ({"resource": "Individual"}, {"resource": "Group"},
                       {"endpoint": "https://unapproved.example/events"},
                       {"endpoint": "http://partner.example/events"},
                       {"expiresAt": (timezone.now() - timedelta(days=1)).isoformat()}):
            self.assertEqual(mutate(self.owner, "create", {**self.data, **change}).status, MutationLog.ERROR)
        self.assertFalse(Subscription.objects.exists())

    def test_schema_has_only_explicit_fields_and_no_domain_adapters(self):
        result = schema.introspect()
        types = {t["name"]: t for t in result["__schema"]["types"]}
        fields = {f["name"] for f in types["PwpSubscriptionType"]["fields"]}
        self.assertEqual(fields, {"id", "resource", "endpoint", "enabled", "expiresAt",
                                  "dateCreated", "dateUpdated"})
        self.assertNotIn("Patient", str(schema))
        self.assertNotIn("pwpResourceIndividual", str(schema))
        self.assertNotIn("pwpResourceGroup", str(schema))
        for path in ("/pwp_api/v1/subscriptions/", "/pwp_api/v1/login/", "/pwp_api/v1/docs/"):
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_registry_requires_explicit_contract_and_rejects_duplicates(self):
        registry = ResourceRegistry()
        registry.register(example)
        with self.assertRaises(ImproperlyConfigured):
            registry.register(example)

    def test_bounded_pagination_and_typed_arguments(self):
        for arguments in ("limit: 101", "limit: 0", "offset: -1", "limit: null", 'limit: "x"'):
            self.assertTrue(execute(self.owner, "{ pwpResourceExample(" + arguments + ") { id } }").errors)
        result = execute(self.owner, "{ pwpResourceExample(limit: 1, offset: 1) { id } }")
        self.assertEqual(result.data["pwpResourceExample"], [])
        for change in ({"owner": str(self.other.pk)}, {"expiresAt": "bad-date"}):
            result = execute(self.owner,
                             "mutation($input: CreatePwpSubscriptionMutationInput!) { "
                             "createPwpSubscription(input: $input) { internalId } }",
                             {"input": {**self.data, **change}})
            self.assertTrue(result.errors, change)
        self.assertFalse(Subscription.objects.exists())

    def test_delivery_disabled_by_default(self):
        self.subscription()
        client = MagicMock(send=AsyncMock(return_value=204))
        notify_subscribers("Example", self.owner.pk, client)
        client.send.assert_not_called()
        self.assertFalse(NotificationResult.objects.exists())

    @override_settings(PWP_API={"notifications_enabled": True,
                                "notification_endpoints": ["https://partner.example/events"]})
    def test_delivery_rechecks_recipient_scope_and_accepts_204(self):
        self.subscription()
        self.subscription(self.other)
        client = MagicMock(send=AsyncMock(return_value=204))
        notify_subscribers("Example", self.owner.pk, client)
        client.send.assert_awaited_once()
        self.assertEqual(client.send.call_args.args[1]["data"], {"id": str(self.owner.pk), "name": "owner"})
        self.assertTrue(NotificationResult.objects.get().successful)

    @override_settings(PWP_API={"notifications_enabled": True,
                                "notification_endpoints": ["https://partner.example/events"]})
    def test_revoked_rights_expiry_and_destination_disable_delivery(self):
        sub = self.subscription()
        client = MagicMock(send=AsyncMock(return_value=200))
        revoke_right(self.owner, 900001)
        notify_subscribers("Example", self.owner.pk, client)
        grant_right(self.owner, 900001)
        sub.expires_at = timezone.now() - timedelta(seconds=1)
        sub.save(user=self.owner)
        notify_subscribers("Example", self.owner.pk, client)
        sub.expires_at = timezone.now() + timedelta(days=1)
        sub.endpoint = "https://removed.example/events"
        sub.save(user=self.owner)
        notify_subscribers("Example", self.owner.pk, client)
        client.send.assert_not_called()

    @override_settings(PWP_API={"notifications_enabled": True,
                                "notification_endpoints": ["https://partner.example/events"]})
    def test_failed_delivery_records_sanitized_error(self):
        self.subscription()
        client = MagicMock(send=AsyncMock(side_effect=TimeoutError("sensitive destination details")))
        notify_subscribers("Example", self.owner.pk, client)
        result = NotificationResult.objects.get()
        self.assertFalse(result.successful)
        self.assertEqual(result.error, "TimeoutError")

    @patch("pwp_api.notifications.notify_subscribers")
    def test_publish_waits_for_commit_and_rollback_discards_callback(self, notify):
        with self.captureOnCommitCallbacks(execute=True):
            publish_resource("Example", self.owner.pk)
            notify.assert_not_called()
        notify.assert_called_once_with("Example", self.owner.pk)
        notify.reset_mock()
        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    publish_resource("Example", self.owner.pk)
                    raise ValueError("rollback")
            except ValueError:
                pass
        notify.assert_not_called()

    @patch("pwp_api.notifications.aiohttp.ClientSession")
    def test_http_client_does_not_parse_json_or_follow_redirects(self, session_class):
        import asyncio
        response = MagicMock(status=204)
        response.json = AsyncMock(side_effect=ValueError("empty body"))
        session = session_class.return_value.__aenter__.return_value
        session.post = MagicMock()
        session.post.return_value.__aenter__.return_value = response
        self.assertEqual(asyncio.run(NotificationClient().send(self.data["endpoint"], {"id": "a"})), 204)
        response.json.assert_not_called()
        self.assertFalse(session.post.call_args.kwargs["allow_redirects"])

    @patch("core.async_mutations", True)
    @patch("core.schema.openimis_mutation_async.delay")
    def test_native_worker_loads_schema_class_and_rechecks_permissions(self, delay):
        from core.tasks import openimis_mutation_async

        payload = {**self.data, 'mutationExtensions': '{"source": "test"}'}
        log = mutate(self.owner, "create", payload)
        self.assertEqual(log.status, MutationLog.RECEIVED)
        delay.assert_called_once_with(log.pk, "pwp_api", "CreatePwpSubscriptionMutation")
        self.assertFalse(Subscription.objects.exists())
        openimis_mutation_async.run(log.pk, "pwp_api", "CreatePwpSubscriptionMutation")
        log.refresh_from_db()
        self.assertEqual(log.status, MutationLog.SUCCESS, log.error)
        self.assertEqual(Subscription.objects.count(), 1)
        pending = mutate(self.owner, "create", self.data)
        revoke_right(self.owner, 158002)
        openimis_mutation_async.run(pending.pk, "pwp_api", "CreatePwpSubscriptionMutation")
        pending.refresh_from_db()
        self.assertEqual(pending.status, MutationLog.ERROR)
        self.assertEqual(Subscription.objects.count(), 1)
