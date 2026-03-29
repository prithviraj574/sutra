from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from sutra_backend.config import get_settings


def create_database_engine(database_url: str, *, echo: bool = False) -> Engine:
    connect_args: dict[str, object] = {}
    engine_kwargs: dict[str, object] = {"echo": echo}

    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    else:
        engine_kwargs["pool_pre_ping"] = True

    return create_engine(
        database_url,
        connect_args=connect_args,
        **engine_kwargs,
    )


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_database_engine(settings.database_url, echo=settings.debug)


def create_all_tables(engine: Engine | None = None) -> None:
    SQLModel.metadata.create_all(engine or get_engine())


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
