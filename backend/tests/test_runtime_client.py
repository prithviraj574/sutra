from __future__ import annotations

import base64
import json

import httpx
import pytest

from sutra_backend.runtime.client import (
    HermesRuntimeClient,
    HermesRuntimeTarget,
    ResponsesRequest,
)


@pytest.mark.anyio
async def test_responses_request_sends_ephemeral_env_in_header_not_body() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = request.content.decode("utf-8")
        return httpx.Response(
            200,
            json={
                "id": "resp_123",
                "object": "response",
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Ready"}],
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    target = HermesRuntimeTarget(base_url="http://runtime.internal", api_key="runtime-key")
    client = HermesRuntimeClient(target=target, transport=transport)

    response = await client.create_response(
        ResponsesRequest(input="List the repository files", instructions="Stay concise."),
        request_env={"GITHUB_TOKEN": "super-secret"},
    )

    assert response.response_id == "resp_123"
    assert response.output_text == "Ready"
    assert captured["url"] == "http://runtime.internal/v1/responses"
    headers = captured["headers"]
    assert headers["authorization"] == "Bearer runtime-key"
    assert "super-secret" not in captured["body"]

    encoded_env = headers["x-sutra-run-env"]
    decoded_env = json.loads(base64.b64decode(encoded_env).decode("utf-8"))
    assert decoded_env == {"GITHUB_TOKEN": "super-secret"}


@pytest.mark.anyio
async def test_chat_completions_request_uses_fallback_path() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request.content.decode("utf-8")
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl_123",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Fallback completed.",
                        }
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    target = HermesRuntimeTarget(base_url="http://runtime.internal", api_key="runtime-key")
    client = HermesRuntimeClient(target=target, transport=transport)

    payload = await client.create_chat_completion(
        [
            {"role": "system", "content": "You are a build agent."},
            {"role": "user", "content": "Summarize the repo."},
        ]
    )

    assert captured["url"] == "http://runtime.internal/v1/chat/completions"
    body = json.loads(captured["body"])
    assert body["messages"][1]["content"] == "Summarize the repo."
    assert payload["choices"][0]["message"]["content"] == "Fallback completed."
