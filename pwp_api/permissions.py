def has_subscription_permission(user, operation):
    from .configuration import get_configuration

    rights = get_configuration().get(f"subscription_{operation}_perms")
    return bool(user and user.is_authenticated and user.is_active and rights and user.has_perms(rights))
