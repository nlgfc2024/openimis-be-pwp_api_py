from rest_framework.permissions import BasePermission


class ResourcePermission(BasePermission):
    def has_permission(self, request, view):
        return view.adapter.can_read(request.user)

    def has_object_permission(self, request, view, obj):
        return view.get_queryset().filter(pk=obj.pk).exists()
