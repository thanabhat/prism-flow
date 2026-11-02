from datetime import datetime, timedelta, timezone
import os
import secrets
from typing import Any

from fastapi import HTTPException, Request, Response, WebSocket, status
import httpx
import jwt
from pydantic import BaseModel

JWT_ALGORITHM = "HS256"
JWT_EXPIRES_MINUTES = int(os.getenv("JWT_EXPIRES_MINUTES", "480"))
COOKIE_NAME = "prismflow_access_token"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

JWT_SECRET = os.getenv("JWT_SECRET", "").strip()
if not JWT_SECRET:
    if COOKIE_SECURE or os.getenv("RENDER") == "true":
        raise RuntimeError("Set JWT_SECRET before starting an HTTPS or Render deployment.")
    # Local development only: never reuse a public signing key.
    JWT_SECRET = secrets.token_hex(32)
elif len(JWT_SECRET.encode("utf-8")) < 32:
    raise RuntimeError("JWT_SECRET must contain at least 32 bytes.")

# Optional URL of an external authentication microservice
EXTERNAL_AUTH_URL = os.getenv("EXTERNAL_AUTH_URL", "")

# Simulated users representing records in the external authentication service
MOCK_AUTH_DIRECTORY: dict[str, dict[str, str]] = {
    "trader": {
        "password": "crypto2026",
        "display_name": "Alex Rivera",
        "role": "Senior Crypto Trader",
        "desk": "Perp-DeltaOne",
    },
    "admin": {
        "password": "prismflow123",
        "display_name": "Morgan Chen",
        "role": "Platform Admin",
        "desk": "Spot-Global",
    },
}


class LoginRequest(BaseModel):
    username: str
    password: str


class UserProfile(BaseModel):
    username: str
    display_name: str
    role: str
    desk: str


async def verify_credentials_with_external_service(
    username: str, password: str
) -> UserProfile | None:
    """
    Validates user credentials against an external authentication service.
    If EXTERNAL_AUTH_URL is configured, delegates via HTTP POST;
    otherwise uses the simulated external directory for local/container testing.
    """
    normalized = username.strip().lower()

    if EXTERNAL_AUTH_URL:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                EXTERNAL_AUTH_URL,
                json={"username": normalized, "password": password},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            return UserProfile(
                username=data["username"],
                display_name=data.get("display_name", normalized),
                role=data.get("role", "Trader"),
                desk=data.get("desk", "Spot-Global"),
            )

    record = MOCK_AUTH_DIRECTORY.get(normalized)
    if not record or record["password"] != password:
        return None

    return UserProfile(
        username=normalized,
        display_name=record["display_name"],
        role=record["role"],
        desk=record["desk"],
    )


def create_jwt_token(user: UserProfile) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "desk": user.desk,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_EXPIRES_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> UserProfile:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return UserProfile(
            username=payload["sub"],
            display_name=payload.get("display_name", payload["sub"]),
            role=payload.get("role", "Trader"),
            desk=payload.get("desk", "Spot-Global"),
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
        ) from exc


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=JWT_EXPIRES_MINUTES * 60,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


async def get_current_user(request: Request) -> UserProfile:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return decode_jwt_token(token)


def verify_websocket_cookie(websocket: WebSocket) -> UserProfile | None:
    token = websocket.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        return decode_jwt_token(token)
    except HTTPException:
        return None
