from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from core.models import HistoryBusinessModel, MutationLog
from core.services import BaseService
from core.validation import BaseModelValidation
from django.test import TestCase, override_settings
from django.utils import timezone
from tests.graphql_helpers import execute, mutate

from pwp_api.models import NotificationResult, Subscription
from pwp_api.notifications import notify_subscribers
from pwp_api.services import SubscriptionService
from pwp_api.validation import SubscriptionValidation
from tests.factories import create_user, grant_right, revoke_right


class CoreInfrastructureTests(TestCase):
    def setUp(self):
        self.user = create_user("actor")
        self.other = create_user("other_actor")
        self.service = SubscriptionService(self.user)
        self.payload = {
            "resource": "Example", "endpoint": "https://partner.example/events", "enabled": True,
            "expires_at": timezone.now() + timedelta(days=1),
        }

    def create_subscription(self):
        result = self.service.create(self.payload.copy())
        self.assertTrue(result["success"], result)
        return Subscription.objects.get(pk=result["data"]["id"])

    def test_real_core_classes_are_used(self):
        self.assertTrue(issubclass(Subscription, HistoryBusinessModel))
        self.assertTrue(issubclass(SubscriptionService, BaseService))
        self.assertTrue(issubclass(SubscriptionValidation, BaseModelValidation))

    def test_history_records_actor_versions_and_soft_delete(self):
        sub = self.create_subscription()
        self.assertEqual(sub.user_created_id, self.user.pk)
        self.assertEqual(sub.user_updated_id, self.user.pk)
        self.assertEqual(sub.version, 1)
        self.assertEqual(sub.history.count(), 1)
        self.assertEqual(sub.history.first().history_user_id, self.user.pk)
        self.assertTrue(self.service.update({"id": sub.pk, "enabled": False})["success"])
        sub.refresh_from_db()
        self.assertEqual(sub.version, 2)
        self.assertFalse(sub.enabled)
        self.assertFalse(sub.is_deleted)
        self.assertTrue(sub.active)  # Inherited lifecycle property, not delivery status.
        self.assertEqual(sub.history.count(), 2)
        self.assertTrue(self.service.delete({"id": sub.pk})["success"])
        sub.refresh_from_db()
        self.assertTrue(sub.is_deleted)
        self.assertEqual(sub.version, 3)
        self.assertEqual(sub.history.count(), 3)
        self.assertEqual(sub.history.first().user_updated_id, self.user.pk)
        self.assertEqual(sub.history.first().history_user_id, self.user.pk)
        self.assertFalse(self.service.get_queryset().exists())
        self.assertEqual(execute(self.user, "{ pwpSubscriptions { id } }").data["pwpSubscriptions"], [])

    def test_graphql_enforces_each_numeric_operation_right(self):
        sub = self.create_subscription()
        revoke_right(self.user, 158001)
        self.assertTrue(execute(self.user, "{ pwpSubscriptions { id } }").errors)
        grant_right(self.user, 158001)
        payload = {"resource": "Example", "endpoint": self.payload["endpoint"],
                   "expiresAt": self.payload["expires_at"].isoformat()}
        for right, operation, data in ((158002, "create", payload),
                                       (158003, "update", {"id": str(sub.pk), "enabled": False}),
                                       (158004, "delete", {"id": str(sub.pk)})):
            revoke_right(self.user, right)
            self.assertEqual(mutate(self.user, operation, data).status, MutationLog.ERROR)
            grant_right(self.user, right)

    def test_direct_service_cannot_bypass_operation_rights(self):
        sub = self.create_subscription()
        for right, operation, data in ((158002, "create", self.payload),
                                       (158003, "update", {"id": sub.pk, "enabled": False}),
                                       (158004, "delete", {"id": sub.pk})):
            revoke_right(self.user, right)
            result = getattr(self.service, operation)(data.copy())
            self.assertFalse(result["success"], result)
            grant_right(self.user, right)
        sub.refresh_from_db()
        self.assertEqual(sub.version, 1)
        self.assertFalse(sub.is_deleted)

    def test_direct_service_cannot_modify_another_owners_record(self):
        sub = self.create_subscription()
        other_service = SubscriptionService(self.other)
        self.assertFalse(other_service.update({"id": sub.pk, "enabled": False})["success"])
        self.assertFalse(other_service.delete({"id": sub.pk})["success"])
        sub.refresh_from_db()
        self.assertEqual(sub.version, 1)

    def test_direct_service_cannot_forge_ownership_or_audit_fields(self):
        for field, value in (("owner", self.other), ("user_created", self.other),
                             ("user_updated", self.other), ("is_deleted", True), ("version", 99)):
            self.assertFalse(self.service.create({**self.payload, field: value})["success"])
        self.assertFalse(Subscription.objects.exists())
        sub = self.create_subscription()
        for field, value in (("owner", self.other), ("user_created", self.other),
                             ("user_updated", self.other), ("is_deleted", True), ("version", 99)):
            self.assertFalse(self.service.update({"id": sub.pk, field: value})["success"])
        sub.refresh_from_db()
        self.assertEqual(sub.version, 1)

    def test_direct_service_runs_resource_and_destination_validation(self):
        for change in ({"resource": "Individual"}, {"endpoint": "https://unknown.example/events"},
                       {"expires_at": timezone.now() - timedelta(seconds=1)}):
            self.assertFalse(self.service.create({**self.payload, **change})["success"])
        revoke_right(self.user, 900001)
        self.assertFalse(self.service.create(self.payload.copy())["success"])
        self.assertFalse(Subscription.objects.exists())

    @override_settings(PWP_API={"subscription_create_perms": ["900002"],
                                "notification_endpoints": ["https://partner.example/events"]})
    def test_operation_rights_are_configurable(self):
        self.assertFalse(self.service.create(self.payload.copy())["success"])
        grant_right(self.user, 900002)
        self.assertTrue(self.service.create(self.payload.copy())["success"])

    @override_settings(PWP_API={"subscription_search_perms": []})
    def test_empty_permission_configuration_denies_access(self):
        self.assertTrue(execute(self.user, "{ pwpSubscriptions { id } }").errors)

    @override_settings(PWP_API={"notifications_enabled": True,
                                "notification_endpoints": ["https://partner.example/events"]})
    def test_soft_deleted_subscription_never_delivers_and_keeps_results(self):
        sub = self.create_subscription()
        recorded = NotificationResult.objects.create(subscription=sub, successful=True, status_code=204)
        self.assertTrue(self.service.delete({"id": sub.pk})["success"])
        self.assertTrue(NotificationResult.objects.filter(pk=recorded.pk).exists())
        client = MagicMock(send=AsyncMock(return_value=204))
        notify_subscribers("Example", self.user.pk, client)
        client.send.assert_not_called()
        self.assertFalse(self.service.update({"id": sub.pk, "enabled": True})["success"])
        self.assertFalse(self.service.delete({"id": sub.pk})["success"])

    def test_disabled_delivery_does_not_prevent_soft_delete(self):
        sub = self.create_subscription()
        self.assertTrue(self.service.update({"id": sub.pk, "enabled": False})["success"])
        self.assertTrue(self.service.delete({"id": sub.pk})["success"])
        sub.refresh_from_db()
        self.assertTrue(sub.is_deleted)

    def test_core_failure_rolls_back_and_is_not_returned_as_api_success(self):
        def save_then_fail(service, instance):
            instance.save(user=service.user)
            raise RuntimeError("internal secret diagnostic")

        with patch.object(BaseService, "save_instance", save_then_fail):
            response = mutate(self.user, "create", {
                "resource": "Example", "endpoint": self.payload["endpoint"], "enabled": True,
                "expiresAt": self.payload["expires_at"].isoformat(),
            })
        self.assertEqual(response.status, MutationLog.ERROR)
        self.assertNotIn("internal secret", str(response.error))
        self.assertFalse(Subscription.objects.exists())
        self.assertFalse(Subscription.history.exists())

    def test_subscription_permissions_are_discoverable_by_core(self):
        from core.utils import collect_all_gql_permissions

        collect_all_gql_permissions.cache_clear()
        permissions = collect_all_gql_permissions()["pwp_api"]
        self.assertEqual(permissions["subscription_search_perms"], ["158001"])
        self.assertEqual(permissions["subscription_create_perms"], ["158002"])
        self.assertEqual(permissions["subscription_update_perms"], ["158003"])
        self.assertEqual(permissions["subscription_delete_perms"], ["158004"])

    def test_direct_search_requires_search_right(self):
        from django.core.exceptions import PermissionDenied

        revoke_right(self.user, 158001)
        with self.assertRaises(PermissionDenied):
            self.service.get_queryset()

    def test_update_and_delete_rights_do_not_require_search_right(self):
        sub = self.create_subscription()
        revoke_right(self.user, 158001)
        self.assertTrue(execute(self.user, "{ pwpSubscriptions { id } }").errors)
        self.assertEqual(mutate(self.user, "update", {"id": str(sub.pk), "enabled": False}).status, MutationLog.SUCCESS)
        self.assertEqual(mutate(self.user, "delete", {"id": str(sub.pk)}).status, MutationLog.SUCCESS)
