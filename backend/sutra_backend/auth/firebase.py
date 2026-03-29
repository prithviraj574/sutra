from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

from sutra_backend.config import get_settings


class FirebaseAuthError(RuntimeError):
    """Raised when a Firebase token cannot be verified."""


@dataclass(frozen=True)
class FirebaseIdentity:
    uid: str
    email: str
    name: str | None = None
    picture: str | None = None


def _resolve_service_account_path(raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate

    backend_root = Path(__file__).resolve().parents[2]
    return backend_root / candidate


@lru_cache
def get_firebase_app() -> firebase_admin.App:
    settings = get_settings()
    if not settings.firebase_service_account_json:
        raise FirebaseAuthError("Firebase service account configuration is missing.")

    credential_path = _resolve_service_account_path(settings.firebase_service_account_json)
    if not credential_path.exists():
        raise FirebaseAuthError("Firebase service account file was not found.")

    return firebase_admin.initialize_app(
        credentials.Certificate(str(credential_path)),
        name="sutra-backend",
    )


def verify_firebase_token(id_token: str) -> FirebaseIdentity:
    try:
        decoded = firebase_auth.verify_id_token(id_token, app=get_firebase_app())
    except Exception as exc:  # pragma: no cover - provider SDK boundary
        raise FirebaseAuthError("Firebase token verification failed.") from exc

    uid = decoded.get("uid")
    email = decoded.get("email")
    if not isinstance(uid, str) or not uid:
        raise FirebaseAuthError("Firebase token is missing a user id.")
    if not isinstance(email, str) or not email:
        raise FirebaseAuthError("Firebase token is missing an email address.")

    name = decoded.get("name")
    picture = decoded.get("picture")
    return FirebaseIdentity(
        uid=uid,
        email=email,
        name=name if isinstance(name, str) else None,
        picture=picture if isinstance(picture, str) else None,
    )
