from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from urllib.parse import urlencode
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from sutra_backend.auth.dependencies import get_current_user
from sutra_backend.config import Settings, get_app_settings
from sutra_backend.db import get_session
from sutra_backend.models import GitHubConnection, User, utcnow
from sutra_backend.schemas.github import (
    GitHubConnectionRead,
    GitHubConnectionStatusResponse,
    GitHubOAuthCallbackResponse,
)


GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_USER_INSTALLATIONS_URL = "https://api.github.com/user/installations"
GITHUB_OAUTH_STATE_COOKIE = "sutra_github_oauth_state"
GITHUB_OAUTH_STATE_MAX_AGE_SECONDS = 600

github_router = APIRouter(prefix="/auth/github", tags=["auth"])


def _state_secret(settings: Settings) -> str:
    if settings.github_client_secret:
        return settings.github_client_secret
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="GitHub OAuth is not configured.",
    )


def _encode_state(*, user_id: UUID, nonce: str, settings: Settings) -> str:
    payload = json.dumps(
        {
            "user_id": str(user_id),
            "nonce": nonce,
            "iat": int(time.time()),
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload).decode("utf-8").rstrip("=")
    signature = hmac.new(
        _state_secret(settings).encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{encoded_payload}.{signature}"


def _decode_state(*, state: str, settings: Settings) -> dict[str, object]:
    encoded_payload, separator, signature = state.partition(".")
    if not separator or not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid GitHub OAuth state.",
        )

    expected_signature = hmac.new(
        _state_secret(settings).encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid GitHub OAuth state.",
        )

    padding = "=" * (-len(encoded_payload) % 4)

    try:
        payload = json.loads(base64.urlsafe_b64decode(f"{encoded_payload}{padding}").decode("utf-8"))
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid GitHub OAuth state.",
        ) from exc

    issued_at = payload.get("iat")
    if not isinstance(issued_at, int) or (time.time() - issued_at) > GITHUB_OAUTH_STATE_MAX_AGE_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub OAuth state expired.",
        )

    return payload


def _frontend_redirect_url(settings: Settings, *, github_status: str) -> str:
    base = settings.frontend_url.rstrip("/")
    return f"{base}/?github={github_status}"


def _require_github_oauth_settings(settings: Settings) -> None:
    if settings.github_client_id and settings.github_client_secret:
        return

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="GitHub OAuth is not configured.",
    )


def _github_api_headers(access_token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {access_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


@github_router.get("", response_class=RedirectResponse)
def start_github_oauth(
    request: Request,
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_app_settings),
) -> RedirectResponse:
    _require_github_oauth_settings(settings)

    nonce = secrets.token_urlsafe(24)
    redirect_uri = str(request.url_for("complete_github_oauth"))
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": redirect_uri,
        "state": _encode_state(user_id=user.id, nonce=nonce, settings=settings),
        "allow_signup": "false",
    }

    response = RedirectResponse(
        url=f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}",
        status_code=status.HTTP_302_FOUND,
    )
    response.set_cookie(
        GITHUB_OAUTH_STATE_COOKIE,
        nonce,
        max_age=GITHUB_OAUTH_STATE_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        path="/api/auth/github",
    )
    return response


@github_router.get("/connection", response_model=GitHubConnectionStatusResponse)
def read_github_connection(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> GitHubConnectionStatusResponse:
    connection = session.exec(select(GitHubConnection).where(GitHubConnection.user_id == user.id)).first()
    return GitHubConnectionStatusResponse(
        connection=(
            GitHubConnectionRead.model_validate(connection, from_attributes=True) if connection is not None else None
        )
    )


@github_router.get("/callback", response_class=RedirectResponse)
def complete_github_oauth(
    code: str,
    state: str,
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> RedirectResponse:
    _require_github_oauth_settings(settings)

    state_payload = _decode_state(state=state, settings=settings)
    oauth_cookie = request.cookies.get(GITHUB_OAUTH_STATE_COOKIE)
    state_nonce = state_payload.get("nonce")
    if not oauth_cookie or not isinstance(state_nonce, str) or not secrets.compare_digest(oauth_cookie, state_nonce):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub OAuth state mismatch.",
        )

    user_id = UUID(str(state_payload["user_id"]))
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    redirect_uri = str(request.url_for("complete_github_oauth"))

    try:
        token_response = httpx.post(
            GITHUB_ACCESS_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "state": state,
            },
            timeout=10.0,
        )
        token_response.raise_for_status()
        token_payload = token_response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub token exchange failed.",
        ) from exc

    access_token = token_payload.get("access_token")
    if not access_token:
        detail = token_payload.get("error_description") or "GitHub token exchange failed."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    headers = _github_api_headers(access_token)

    try:
        github_user_response = httpx.get(GITHUB_USER_URL, headers=headers, timeout=10.0)
        github_user_response.raise_for_status()
        github_user = github_user_response.json()

        installations_response = httpx.get(GITHUB_USER_INSTALLATIONS_URL, headers=headers, timeout=10.0)
        installations_response.raise_for_status()
        installations_payload = installations_response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub account lookup failed.",
        ) from exc

    installations = installations_payload.get("installations", [])
    if not installations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No GitHub App installation found for authenticated user.",
        )

    installation = installations[0]
    account = installation.get("account") or {}
    now = utcnow()
    installation_id = str(installation["id"])
    account_login = account.get("login") or github_user.get("login")

    if not account_login:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub account login was not returned.",
        )

    connection = session.exec(
        select(GitHubConnection).where(
            (GitHubConnection.user_id == user.id) | (GitHubConnection.installation_id == installation_id)
        )
    ).first()

    if connection is None:
        connection = GitHubConnection(
            user_id=user.id,
            installation_id=installation_id,
            account_login=account_login,
            account_type=str(account.get("type") or github_user.get("type") or "user").lower(),
            connected_at=now,
        )
        session.add(connection)
    else:
        connection.user_id = user.id
        connection.installation_id = installation_id
        connection.account_login = account_login
        connection.account_type = str(account.get("type") or github_user.get("type") or "user").lower()
        connection.connected_at = now
        connection.updated_at = now

    session.commit()
    session.refresh(connection)

    response = RedirectResponse(
        url=_frontend_redirect_url(settings, github_status="connected"),
        status_code=status.HTTP_302_FOUND,
    )
    response.delete_cookie(GITHUB_OAUTH_STATE_COOKIE, path="/api/auth/github")
    return response
