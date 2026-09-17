import asyncio
import logging

import aiohttp
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone
import json

from .configuration import get_configuration
from .models import NotificationResult, Subscription
from .registry import registry
from .serializers import endpoint_allowed

logger = logging.getLogger(__name__)


class NotificationClient:
    async def send(self, endpoint, payload):
        timeout = aiohttp.ClientTimeout(total=get_configuration()["notification_timeout"])
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                endpoint, data=json.dumps(payload, cls=DjangoJSONEncoder),
                headers={"Content-Type": "application/json"}, allow_redirects=False,
            ) as response:
                # 204 and other non-JSON successful responses are valid acknowledgements.
                return response.status


def notify_subscribers(resource, pk, client=None):
    if not get_configuration()["notifications_enabled"]:
        return
    adapter = registry.get(resource)
    if not adapter or not adapter.subscriptions_enabled:
        return
    client = client or NotificationClient()
    subscriptions = Subscription.objects.filter(
        resource=resource, active=True, expires_at__gt=timezone.now(),
    ).select_related("owner")
    for subscription in subscriptions:
        if not adapter.can_read(subscription.owner) or not endpoint_allowed(subscription.endpoint):
            continue
        # Resolve again in the recipient's scope, never the event actor's scope.
        instance = adapter.service_class(subscription.owner).get_queryset().filter(pk=pk).first()
        if instance is None:
            continue
        status_code = None
        error = ""
        try:
            payload = {
                "resource": resource,
                "data": adapter.converter_class(subscription.owner).to_representation(instance),
            }
            status_code = asyncio.run(client.send(subscription.endpoint, payload))
            successful = 200 <= status_code < 300
            if not successful:
                error = "HTTP delivery rejected"
        except Exception as exc:
            successful = False
            error = type(exc).__name__  # Do not persist headers, payloads or remote response bodies.
        NotificationResult.objects.create(
            subscription=subscription, successful=successful,
            status_code=status_code, error=error,
        )


def publish_resource(resource, pk):
    """Future source adapters may call this after an approved service operation.

    Runs synchronously after commit. This is not a durable outbox or retry queue.
    Deletes and offline sync require a future event contract.
    """
    def deliver():
        try:
            notify_subscribers(resource, pk)
        except Exception:
            logger.exception("PWP notification failed after commit")

    transaction.on_commit(deliver)
