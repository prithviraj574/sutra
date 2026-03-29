from __future__ import annotations

import pytest

from sutra_backend.runtime.env_policy import build_runtime_env_plan


def test_secret_env_is_never_added_to_persisted_runtime_env() -> None:
    plan = build_runtime_env_plan(
        persisted_env={"API_SERVER_PORT": "8642", "SUTRA_ENV": "development"},
        request_env={"GITHUB_TOKEN": "secret-token"},
    )

    assert plan.persisted_env == {
        "API_SERVER_PORT": "8642",
        "SUTRA_ENV": "development",
    }
    assert plan.request_env == {"GITHUB_TOKEN": "secret-token"}
    assert "GITHUB_TOKEN" not in plan.persisted_env


def test_overlapping_secret_and_persisted_keys_are_rejected() -> None:
    with pytest.raises(ValueError, match="GITHUB_TOKEN"):
        build_runtime_env_plan(
            persisted_env={"GITHUB_TOKEN": "unsafe"},
            request_env={"GITHUB_TOKEN": "secret-token"},
        )


def test_redacted_request_env_masks_values_for_logging() -> None:
    plan = build_runtime_env_plan(
        persisted_env={"API_SERVER_PORT": "8642"},
        request_env={"OPENAI_API_KEY": "sk-live-secret"},
    )

    assert plan.redacted_request_env() == {"OPENAI_API_KEY": "***"}
