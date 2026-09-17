import uuid

from django.conf import settings
from django.db import models


class Subscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name="pwp_api_subscriptions")
    resource = models.CharField(max_length=80)
    endpoint = models.URLField(max_length=500)
    active = models.BooleanField(default=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
