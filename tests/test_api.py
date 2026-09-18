from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.test import TestCase, override_settings
from django.urls import resolve, reverse
from django.utils import timezone
from rest_framework.test import APIClient

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
        self.client = APIClient()
        self.client.force_authenticate(self.owner)
        self.url = "/pwp_api/v1/subscriptions/"
        self.data = {"resource": "Example", "active": True, "endpoint": "https://partner.example/events",
                     "expires_at": (timezone.now() + timedelta(days=1)).isoformat()}

    def subscription(self, owner=None):
        result = SubscriptionService(owner or self.owner).create({
            "resource": "Example", "endpoint": self.data["endpoint"], "enabled": True,
            "expires_at": timezone.now() + timedelta(days=1),
        })
        self.assertTrue(result["success"], result)
        return Subscription.objects.get(pk=result["data"]["id"])

    def test_identity_and_versioned_routes(self):
        self.assertEqual(apps.get_app_config("pwp_api").__class__.__name__, "PwpApiConfig")
        self.assertEqual(reverse("pwp_api:subscription-list"), self.url)
        self.assertEqual(resolve(self.url).namespace, "pwp_api")
        for path in ("/api_fhir_r4/Patient/", "/pwp_api/Patient/", "/pwp_api/v1/Patient/",
                     "/pwp_api/v1/Group/", "/pwp_api/v1/Claim/"):
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_anonymous_requests_denied(self):
        self.client = APIClient()
        for path in (self.url, "/pwp_api/v1/Example/", "/pwp_api/v1/docs/"):
            self.assertEqual(self.client.get(path).status_code, 401)

    def test_resource_service_and_converter_scope(self):
        response = self.client.get("/pwp_api/v1/Example/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"], [{"id": str(self.owner.pk), "name": "owner"}])
        self.assertEqual(self.client.get(f"/pwp_api/v1/Example/{self.other.pk}/").status_code, 404)
        self.assertEqual(self.client.post("/pwp_api/v1/Example/", {}).status_code, 405)

    def test_missing_resource_permission_denied(self):
        user = create_user("no_rights", rights=(158002,))
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get("/pwp_api/v1/Example/").status_code, 403)
        self.assertEqual(self.client.post(self.url, self.data).status_code, 403)

    def test_subscription_create_update_delete_uses_service(self):
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 201, response.data)
        subscription = Subscription.objects.get(pk=response.data["id"])
        self.assertEqual(subscription.owner, self.owner)
        detail = f"{self.url}{subscription.pk}/"
        self.assertEqual(self.client.patch(detail, {"active": False}).status_code, 200)
        subscription.refresh_from_db()
        self.assertFalse(subscription.enabled)
        self.assertFalse(subscription.is_deleted)
        self.assertEqual(self.client.delete(detail).status_code, 204)

    def test_subscription_owner_isolation(self):
        own = self.subscription()
        foreign = self.subscription(self.other)
        self.assertEqual([r["id"] for r in self.client.get(self.url).data["results"]], [str(own.pk)])
        detail = f"{self.url}{foreign.pk}/"
        self.assertEqual(self.client.get(detail).status_code, 404)
        self.assertEqual(self.client.patch(detail, {"active": False}).status_code, 404)
        self.assertEqual(self.client.delete(detail).status_code, 404)

    def test_unregistered_resource_and_unapproved_endpoint_rejected(self):
        for change in ({"resource": "Patient"}, {"resource": "Group"},
                       {"endpoint": "https://unapproved.example/events"},
                       {"endpoint": "http://partner.example/events"},
                       {"expires_at": (timezone.now() - timedelta(days=1)).isoformat()}):
            self.assertEqual(self.client.post(self.url, {**self.data, **change}).status_code, 400)

    def test_schema_is_module_scoped_and_pwp_branded(self):
        response = self.client.get("/pwp_api/v1/docs/", HTTP_ACCEPT="application/vnd.oai.openapi+json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["info"]["title"], "openIMIS PWP API")
        self.assertIn(self.url, response.data["paths"])
        self.assertTrue(all(p.startswith("/pwp_api/v1/") for p in response.data["paths"]))
        self.assertNotIn("Patient", str(response.data["paths"]))

    def test_registry_requires_explicit_contract_and_rejects_duplicates(self):
        registry = ResourceRegistry()
        registry.register(example)
        with self.assertRaises(ImproperlyConfigured):
            registry.register(example)

    @patch("pwp_api.views.issue_token", return_value={"token": "test-token", "exp": 123})
    def test_login_delegates_to_host_authentication(self, issue_token):
        response = self.client.post("/pwp_api/v1/login/", {"username": "owner", "password": "secret"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"token": "test-token", "exp": 123})
        self.assertEqual(issue_token.call_args.kwargs, {"username": "owner", "password": "secret"})
        self.assertEqual(self.client.post("/pwp_api/v1/login/", {}).status_code, 400)

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
