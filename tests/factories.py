from core.models import InteractiveUser, Language, Role, RoleRight, User, UserRole


DEFAULT_RIGHTS = (158001, 158002, 158003, 158004, 900001)


def create_user(username, rights=DEFAULT_RIGHTS):
    language, _ = Language.objects.get_or_create(code="en", defaults={"name": "English"})
    interactive = InteractiveUser.objects.create(
        login_name=username, language=language, last_name=username, other_names="Test",
    )
    user = User.objects.create(username=username, i_user=interactive)
    role = Role.objects.create(name=username, is_system=0, is_blocked=False)
    UserRole.objects.create(user=interactive, role=role)
    for right in rights:
        RoleRight.objects.create(role=role, right_id=right)
    return user


def revoke_right(user, right):
    RoleRight.objects.filter(role__user_roles__user=user.i_user, right_id=right).delete()


def grant_right(user, right):
    role = Role.objects.get(user_roles__user=user.i_user)
    RoleRight.objects.create(role=role, right_id=right)
