import uuid

from django.conf import settings
from django.db import models
from core.models import HistoryBusinessModel


class Subscription(HistoryBusinessModel):
    USE_CACHE = False

    # Distinct reverse names allow coexistence with api_fhir_r4.Subscription.
    user_created = models.ForeignKey(
        "core.User", on_delete=models.DO_NOTHING, db_column="UserCreatedUUID",
        related_name="pwp_api_subscriptions_created",
    )
    user_updated = models.ForeignKey(
        "core.User", on_delete=models.DO_NOTHING, db_column="UserUpdatedUUID",
        related_name="pwp_api_subscriptions_updated",
    )
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name="pwp_api_subscriptions")
    resource = models.CharField(max_length=80)
    endpoint = models.URLField(max_length=500)
    # HistoryModel.active controls deletion; delivery must use a separate field.
    enabled = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "pwp_api_subscription"


class NotificationResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE,
                                     related_name="notification_results")
    successful = models.BooleanField()
    status_code = models.PositiveSmallIntegerField(null=True)
    error = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pwp_api_notification_result"
