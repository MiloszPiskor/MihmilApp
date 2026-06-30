from functools import wraps
from flask import g, abort
from infrastructure.auth import load_current_user, AuthError

def requires_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            uow = g.uow
            load_current_user(uow.session)
        except AuthError as e:
            abort(401, description=str(e))
        return fn(*args, **kwargs)
    return wrapper

def requires_role(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = getattr(g, "current_user", None)
            if user is None:
                abort(401)
            if user.role not in allowed_roles and user.role != "admin":
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def requires_rep_ownership(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = getattr(g, "current_user", None)
        if user is None:
            abort(401)

        if user.role in ("admin", "office"):
            return fn(*args, **kwargs)

        requested_rep = kwargs.get("rep_reference")
        if not requested_rep or user.rep_reference != requested_rep:
            abort(403)

        return fn(*args, **kwargs)
    return wrapper


