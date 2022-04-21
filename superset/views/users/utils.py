from superset import security_manager


def get_or_create_user(request_payload):
    user = security_manager.find_user(email=request_payload.get("email"))
    if user:
        return user

    return security_manager.add_user(
        **request_payload
    )
