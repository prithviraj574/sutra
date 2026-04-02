from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from sutra_backend.auth.firebase import FirebaseAuthError, FirebaseIdentity, verify_firebase_token
from sutra_backend.config import Settings, get_app_settings
from sutra_backend.db import get_session
from sutra_backend.models import User, utcnow
from sutra_backend.services.bootstrap import ensure_personal_workspace

bearer_scheme = HTTPBearer(auto_error=False)


def _resolve_identity(
    credentials: HTTPAuthorizationCredentials | None,
) -> FirebaseIdentity:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    try:
        return verify_firebase_token(credentials.credentials)
    except FirebaseAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        ) from exc


def get_current_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> FirebaseIdentity:
    return _resolve_identity(credentials)


def _get_or_create_dev_bypass_user(session: Session, *, settings: Settings) -> User:
    dev_user_id = settings.dev_auth_bypass_user_id
    firebase_uid = str(dev_user_id)

    user = session.get(User, dev_user_id)
    if user is None:
        user = session.exec(select(User).where(User.firebase_uid == firebase_uid)).first()

    if user is None:
        user = User(
            id=dev_user_id,
            firebase_uid=firebase_uid,
            email=settings.dev_auth_bypass_email,
            display_name=settings.dev_auth_bypass_display_name,
        )
        session.add(user)
    else:
        user.firebase_uid = firebase_uid
        user.email = settings.dev_auth_bypass_email
        user.display_name = settings.dev_auth_bypass_display_name
        user.updated_at = utcnow()

    session.commit()
    session.refresh(user)
    ensure_personal_workspace(session, user, settings=settings)
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> User:
    if settings.dev_auth_bypass_active:
        return _get_or_create_dev_bypass_user(session, settings=settings)

    identity = _resolve_identity(credentials)
    user = session.exec(select(User).where(User.firebase_uid == identity.uid)).first()

    if user is None:
        user = User(
            firebase_uid=identity.uid,
            email=identity.email,
            display_name=identity.name,
            photo_url=identity.picture,
        )
        session.add(user)
    else:
        user.email = identity.email
        user.display_name = identity.name
        user.photo_url = identity.picture
        user.updated_at = utcnow()

    session.commit()
    session.refresh(user)
    ensure_personal_workspace(session, user, settings=settings)
    return user
