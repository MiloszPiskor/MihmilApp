import json
import time
import requests
from flask import request, g, abort, current_app
from jose import jwt
from sqlalchemy import select
from domain import model

class AuthError(Exception):
    pass

class OktaAuth:
    def __init__(self, issuer: str, audience: str):
        self.issuer = issuer.rstrip("/")
        self.audience = audience
        self.jwks_uri = f"{self.issuer}/v1/keys"
        self._jwks = None
        self._jwks_ts = 0

    def _get_jwks(self):
        if self._jwks and time.time() - self._jwks_ts < 3600:
            return self._jwks
        resp = requests.get(self.jwks_uri, timeout=10)
        resp.raise_for_status()
        self._jwks = resp.json()
        self._jwks_ts = time.time()
        return self._jwks

    def decode_token(self, token: str):
        unverified_header = jwt.get_unverified_header(token)
        jwks = self._get_jwks()

        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
                break

        if not rsa_key:
            raise AuthError("Unable to find appropriate key")

        return jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=self.audience,
            issuer=self.issuer,
            options={"verify_at_hash": False},
        )

def get_bearer_token():
    auth_header = request.headers.get("Authorization", None)
    if not auth_header:
        raise AuthError("Authorization header is missing")

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthError("Authorization header must be Bearer token")

    return parts[1]

def load_current_user(session):
    token = get_bearer_token()
    claims = current_app.okta_auth.decode_token(token)

    sub = claims.get("sub")
    if not sub:
        raise AuthError("Token missing sub")

    stmt = select(model.User).where(model.User.sub == sub)
    user = session.execute(stmt).scalar_one_or_none()

    if user is None:
        user = model.User(
            sub=sub,
            email=claims.get("email", ""),
            name=claims.get("name", claims.get("preferred_username", sub)),
            role="rep",
            rep_reference=None,
            is_active=True,
            okta_groups=json.dumps(claims.get("groups", [])),
        )
        session.add(user)
        session.flush()

    user.email = claims.get("email", user.email)
    user.name = claims.get("name", claims.get("preferred_username", user.name))
    user.okta_groups = json.dumps(claims.get("groups", []))

    g.current_user = user
    g.okta_claims = claims
    return user

