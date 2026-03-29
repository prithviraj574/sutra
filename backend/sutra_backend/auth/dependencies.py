from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from sutra_backend.auth.firebase import FirebaseAuthError, FirebaseIdentity, verify_firebase_token
from sutra_backend.db import get_session
from sutra_backend.models import User, utcnow
from sutra_backend.services.bootstrap import ensure_personal_workspace

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
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


def get_current_user(
    identity: FirebaseIdentity = Depends(get_current_identity),
    session: Session = Depends(get_session),
) -> User:
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
    ensure_personal_workspace(session, user)
    return user
