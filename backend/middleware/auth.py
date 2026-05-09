import time

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, ExpiredSignatureError
from config import get_settings

security = HTTPBearer(auto_error=False)
_JWKS_CACHE_TTL_SECONDS = 600
_ASYMMETRIC_ALGORITHMS = ["ES256", "RS256"]
_jwks_cache: dict | None = None
_jwks_cache_expires_at = 0.0


def _jwks_url(supabase_url: str) -> str:
    return f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"


async def _get_jwks(supabase_url: str) -> dict:
    """Fetch and cache Supabase asymmetric signing keys."""
    global _jwks_cache, _jwks_cache_expires_at
    now = time.time()
    if _jwks_cache and now < _jwks_cache_expires_at:
        return _jwks_cache

    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(_jwks_url(supabase_url))
        response.raise_for_status()

    _jwks_cache = response.json()
    _jwks_cache_expires_at = now + _JWKS_CACHE_TTL_SECONDS
    return _jwks_cache


def _find_jwk(jwks: dict, kid: str | None) -> dict:
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    raise JWTError("Unable to find matching Supabase signing key")


async def _decode_supabase_jwt(token: str) -> dict:
    """Decode legacy HS256 or current Supabase JWKS-signed access tokens."""
    settings = get_settings()
    header = jwt.get_unverified_header(token)
    algorithm = header.get("alg")

    if algorithm == "HS256":
        key = settings.supabase_jwt_secret
    elif algorithm in _ASYMMETRIC_ALGORITHMS:
        jwks = await _get_jwks(settings.supabase_url)
        key = _find_jwk(jwks, header.get("kid"))
    else:
        raise JWTError(f"Unsupported token algorithm: {algorithm}")

    return jwt.decode(
        token,
        key,
        algorithms=[algorithm],
        audience="authenticated",
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    Verify Supabase JWT and return user_id.
    Raises 401 if token is missing, invalid, or expired.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    try:
        payload = await _decode_supabase_jwt(credentials.credentials)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
            )
        return user_id

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired. Please sign in again.",
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str | None:
    """Optional auth — returns None if no token instead of raising 401."""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
