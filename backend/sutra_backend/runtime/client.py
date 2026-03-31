from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from typing import Any

import httpx

RUNTIME_ENV_HEADER = "X-Sutra-Run-Env"


@dataclass(frozen=True)
class HermesRuntimeTarget:
    base_url: str
    api_key: str


@dataclass(frozen=True)
class ResponsesRequest:
    input: str | list[dict[str, Any]]
    instructions: str | None = None
    previous_response_id: str | None = None
    conversation: str | None = None
    store: bool = True
    model: str = "hermes-agent"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "input": self.input,
            "model": self.model,
            "store": self.store,
        }
        if self.instructions is not None:
            payload["instructions"] = self.instructions
        if self.previous_response_id is not None:
            payload["previous_response_id"] = self.previous_response_id
        if self.conversation is not None:
            payload["conversation"] = self.conversation
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


@dataclass(frozen=True)
class HermesResponse:
    response_id: str
    output_text: str
    raw_response: dict[str, Any]


@dataclass(frozen=True)
class RuntimeHealthProbe:
    reachable: bool
    status_code: int | None
    checked_url: str | None
    detail: str


def encode_runtime_env_header(request_env: dict[str, str] | None) -> str | None:
    if not request_env:
        return None

    encoded = json.dumps(request_env, sort_keys=True).encode("utf-8")
    return base64.b64encode(encoded).decode("ascii")


def extract_output_text(payload: dict[str, Any]) -> str:
    text_parts: list[str] = []

    for item in payload.get("output", []):
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    text = content.get("text")
                    if isinstance(text, str):
                        text_parts.append(text)
        elif item.get("type") == "output_text":
            text = item.get("text")
            if isinstance(text, str):
                text_parts.append(text)

    return "\n".join(part for part in text_parts if part)


def probe_runtime_health(
    target: HermesRuntimeTarget,
    *,
    transport: httpx.BaseTransport | None = None,
    timeout_seconds: float = 5.0,
) -> RuntimeHealthProbe:
    headers = {"Authorization": f"Bearer {target.api_key}"}
    attempted_urls: list[str] = []
    last_detail = "Runtime health probe did not receive a response."
    last_status_code: int | None = None

    with httpx.Client(
        base_url=target.base_url,
        timeout=timeout_seconds,
        transport=transport,
    ) as client:
        for path in ("health", "healthz", ""):
            attempted_urls.append(
                f"{target.base_url.rstrip('/')}/{path}".rstrip("/")
            )
            try:
                response = client.get(path, headers=headers)
            except httpx.HTTPError as exc:
                last_detail = str(exc)
                continue

            last_status_code = response.status_code
            if response.status_code < 500:
                return RuntimeHealthProbe(
                    reachable=True,
                    status_code=response.status_code,
                    checked_url=str(response.request.url),
                    detail="Runtime endpoint is reachable.",
                )
            last_detail = f"Runtime responded with {response.status_code}."

    return RuntimeHealthProbe(
        reachable=False,
        status_code=last_status_code,
        checked_url=attempted_urls[-1] if attempted_urls else None,
        detail=last_detail,
    )


class HermesRuntimeClient:
    """
    Sutra-owned wrapper for a persistent Hermes runtime.

    The runtime process can consume `X-Sutra-Run-Env` and inject those values
    only for the current request before forwarding the body to Hermes. That
    keeps per-run secrets out of persisted `HERMES_HOME` files.
    """

    def __init__(
        self,
        target: HermesRuntimeTarget,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout_seconds: float = 900.0,
    ) -> None:
        self._target = target
        self._transport = transport
        self._timeout_seconds = timeout_seconds

    def _headers(self, request_env: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._target.api_key}",
            "Content-Type": "application/json",
        }
        encoded_env = encode_runtime_env_header(request_env)
        if encoded_env is not None:
            headers[RUNTIME_ENV_HEADER] = encoded_env
        return headers

    async def create_response(
        self,
        request: ResponsesRequest,
        *,
        request_env: dict[str, str] | None = None,
    ) -> HermesResponse:
        async with httpx.AsyncClient(
            base_url=self._target.base_url,
            timeout=self._timeout_seconds,
            transport=self._transport,
        ) as client:
            response = await client.post(
                "v1/responses",
                headers=self._headers(request_env),
                json=request.to_payload(),
            )
            response.raise_for_status()
            payload = response.json()

        return HermesResponse(
            response_id=str(payload["id"]),
            output_text=extract_output_text(payload),
            raw_response=payload,
        )

    async def create_chat_completion(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str = "hermes-agent",
        request_env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self._target.base_url,
            timeout=self._timeout_seconds,
            transport=self._transport,
        ) as client:
            response = await client.post(
                "v1/chat/completions",
                headers=self._headers(request_env),
                json={"model": model, "messages": messages},
            )
            response.raise_for_status()
            return response.json()
