from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class RuntimeEnvPlan:
    """Split runtime configuration into persisted and request-scoped env values.

    The persisted env can safely live in runtime bootstrap config.
    The request env is transient and must never be written into the agent VM's
    `.env` or other user-readable persistent files.
    """

    persisted_env: dict[str, str]
    request_env: dict[str, str]

    def redacted_request_env(self) -> dict[str, str]:
        return {name: "***" for name in self.request_env}


def build_runtime_env_plan(
    *,
    persisted_env: Mapping[str, str] | None = None,
    request_env: Mapping[str, str] | None = None,
) -> RuntimeEnvPlan:
    persisted = dict(persisted_env or {})
    request_scoped = dict(request_env or {})

    overlapping_keys = sorted(set(persisted) & set(request_scoped))
    if overlapping_keys:
        overlap = ", ".join(overlapping_keys)
        raise ValueError(
            "Request-scoped secret env keys may not overlap with persisted env keys: "
            f"{overlap}"
        )

    return RuntimeEnvPlan(
        persisted_env=persisted,
        request_env=request_scoped,
    )
