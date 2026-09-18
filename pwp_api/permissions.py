from rest_framework.permissions import BasePermission


class ResourcePermission(BasePermission):
    def has_permission(self, request, view):
        return view.adapter.can_read(request.user)

    def has_object_permission(self, request, view, obj):
        return view.get_queryset().filter(pk=obj.pk).exists()


def has_subscription_permission(user, operation):
    from .configuration import get_configuration

    rights = get_configuration().get(f"subscription_{operation}_perms")
    return bool(user and user.is_authenticated and user.is_active and rights and user.has_perms(rights))


class SubscriptionPermission(BasePermission):
    operations = {"GET": "search", "HEAD": "search", "OPTIONS": "search", "POST": "create",
                  "PUT": "update", "PATCH": "update", "DELETE": "delete"}

    def has_permission(self, request, view):
        return has_subscription_permission(request.user, self.operations.get(request.method, "unsupported"))
