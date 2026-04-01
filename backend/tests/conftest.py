from __future__ import annotations

import os
import random
import shutil
import subprocess
import tempfile
from collections.abc import Generator

import pytest

from sutra_backend.config import get_settings
from sutra_backend.db import get_engine


@pytest.fixture(autouse=True)
def clear_cached_settings() -> Generator[None, None, None]:
    get_settings.cache_clear()
    get_engine.cache_clear()
    yield
    get_settings.cache_clear()
    get_engine.cache_clear()


@pytest.fixture(scope="session")
def postgres_database_url() -> Generator[str, None, None]:
    initdb = shutil.which("initdb")
    pg_ctl = shutil.which("pg_ctl")
    createdb = shutil.which("createdb")

    if not initdb or not pg_ctl or not createdb:
        pytest.skip("PostgreSQL server binaries are not available locally.")

    with tempfile.TemporaryDirectory(prefix="sutra-postgres-") as tmpdir:
        data_dir = os.path.join(tmpdir, "data")
        log_path = os.path.join(tmpdir, "postgres.log")
        port = random.randint(45000, 55000)

        subprocess.run(
            [initdb, "-D", data_dir, "-A", "trust", "-U", "postgres"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )

        subprocess.run(
            [
                pg_ctl,
                "-D",
                data_dir,
                "-l",
                log_path,
                "-w",
                "start",
                "-o",
                f"-F -h 127.0.0.1 -p {port}",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )

        try:
            subprocess.run(
                [createdb, "-h", "127.0.0.1", "-p", str(port), "-U", "postgres", "sutra_test"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
            yield f"postgresql://postgres@127.0.0.1:{port}/sutra_test"
        finally:
            subprocess.run(
                [pg_ctl, "-D", data_dir, "-w", "stop", "-m", "fast"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
            )
