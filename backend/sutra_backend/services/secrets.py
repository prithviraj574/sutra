from __future__ import annotations

import base64
import hashlib
import os
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlmodel import Session, and_, select

from sutra_backend.config import Settings
from sutra_backend.models import Secret, User, utcnow


class SecretVaultError(RuntimeError):
    """Raised when secret vault operations cannot be completed safely."""


def _normalize_master_key(raw_key: str) -> bytes:
    try:
        decoded = bytes.fromhex(raw_key)
    except ValueError:
        decoded = raw_key.encode("utf-8")

    return hashlib.sha256(decoded).digest()


def encrypt_secret_value(value: str, *, settings: Settings) -> str:
    if not settings.master_encryption_key:
        raise SecretVaultError("MASTER_ENCRYPTION_KEY is not configured.")

    key = _normalize_master_key(settings.master_encryption_key)
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, value.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt_secret_value(value: str, *, settings: Settings) -> str:
    if not settings.master_encryption_key:
        raise SecretVaultError("MASTER_ENCRYPTION_KEY is not configured.")

    raw = base64.b64decode(value.encode("ascii"))
    nonce, ciphertext = raw[:12], raw[12:]
    key = _normalize_master_key(settings.master_encryption_key)
    plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def list_user_secrets(session: Session, *, user: User) -> list[Secret]:
    return session.exec(
        select(Secret)
        .where(Secret.user_id == user.id)
        .order_by(Secret.updated_at.desc())
    ).all()


def upsert_user_secret(
    session: Session,
    *,
    user: User,
    settings: Settings,
    name: str,
    value: str,
    provider: str | None,
    scope: str,
    team_id: UUID | None,
    agent_id: UUID | None,
) -> Secret:
    encrypted_value = encrypt_secret_value(value, settings=settings)
    secret = session.exec(
        select(Secret).where(
            and_(
                Secret.user_id == user.id,
                Secret.name == name,
                Secret.scope == scope,
                Secret.team_id == team_id,
                Secret.agent_id == agent_id,
            )
        )
    ).first()

    if secret is None:
        secret = Secret(
            user_id=user.id,
            team_id=team_id,
            agent_id=agent_id,
            name=name,
            provider=provider,
            scope=scope,
            encrypted_value=encrypted_value,
        )
        session.add(secret)
    else:
        secret.provider = provider
        secret.encrypted_value = encrypted_value
        secret.updated_at = utcnow()
        session.add(secret)

    session.commit()
    session.refresh(secret)
    return secret


def delete_user_secret(session: Session, *, user: User, secret_id: UUID) -> bool:
    secret = session.exec(
        select(Secret)
        .where(Secret.id == secret_id)
        .where(Secret.user_id == user.id)
    ).first()
    if secret is None:
        return False

    session.delete(secret)
    session.commit()
    return True


def resolve_secret_env(
    session: Session,
    *,
    user: User,
    settings: Settings,
    secret_ids: list[UUID],
) -> dict[str, str]:
    if not secret_ids:
        return {}

    secrets = session.exec(
        select(Secret)
        .where(Secret.user_id == user.id)
        .where(Secret.id.in_(secret_ids))
    ).all()
    if len(secrets) != len(secret_ids):
        raise SecretVaultError("One or more requested secrets were not found.")

    return {
        secret.name: decrypt_secret_value(secret.encrypted_value, settings=settings)
        for secret in secrets
    }
