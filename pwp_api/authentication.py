def issue_token(request, username, password):
    """Reuse the host's authentication, password policies and JWT signing."""
    from core.jwt import jwt_encode_user_key
    from core.services import user_authentication
    from graphql_jwt.utils import jwt_payload
    from rest_framework.exceptions import AuthenticationFailed

    user = user_authentication(request, username, password)
    if not user or not user.is_active:
        raise AuthenticationFailed()
    request.user = user
    payload = jwt_payload(user=user)
    token = jwt_encode_user_key(payload=payload, context=request)
    if not token:
        raise AuthenticationFailed()
    return {"token": token, "exp": payload["exp"]}
