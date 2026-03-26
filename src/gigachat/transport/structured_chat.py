import json
from typing import Any, AsyncIterator, Dict, Iterator, Mapping, Optional

import httpx

from gigachat.context import chat_v2_url_cvar
from gigachat.schemas.structured_chat import StructuredChatRequest, StructuredChatResponse, StructuredChatStreamChunk
from gigachat.transport.common import (
    EVENT_STREAM,
    build_headers,
    execute_request_async,
    execute_request_sync,
    execute_stream_async,
    execute_stream_sync,
)


def _deep_merge_with_typed_precedence(base: Mapping[str, Any], typed: Mapping[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in typed.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_with_typed_precedence(merged[key], value)
        else:
            merged[key] = value
    return merged


def resolve_structured_chat_url(base_url: str) -> str:
    """Resolve the absolute v2 chat URL from settings or an override context var."""
    override = chat_v2_url_cvar.get()
    parsed_base_url = httpx.URL(base_url)
    origin = parsed_base_url.copy_with(path="/", query=None, fragment=None)

    if override is not None:
        if override.startswith(("http://", "https://")):
            return override
        if override.startswith("/"):
            return str(origin.copy_with(path=override))
        raise ValueError("chat_v2_url_cvar must be an absolute URL or an absolute path starting with '/'")

    base_path = parsed_base_url.path.rstrip("/")
    # Костыль для /v1/token
    # -> /v2/chat/completions
    segments = [segment for segment in base_path.split("/") if segment]

    if len(segments) >= 3 and segments[-2:] == ["chat", "completions"] and segments[-3] == "v2":
        return str(origin.copy_with(path=base_path))

    if segments and segments[-1] == "v2":
        return str(origin.copy_with(path=f"{base_path}/chat/completions"))

    if not segments or segments[-1] != "v1":
        raise ValueError(
            f"Cannot derive v2 chat URL from base_url={base_url!r}; "
            "set chat_v2_url_cvar or use a base_url ending with '/v1' or '/v2'"
        )

    segments[-1] = "v2"
    v2_path = f"/{'/'.join(segments)}/chat/completions"
    return str(origin.copy_with(path=v2_path))


def _build_chat_payload(*, chat: StructuredChatRequest, stream: bool) -> Dict[str, Any]:
    typed_payload = chat.model_dump(exclude_none=True, by_alias=True, exclude={"stream", "additional_fields"})
    additional_fields = chat.additional_fields or {}
    payload = _deep_merge_with_typed_precedence(additional_fields, typed_payload)
    if stream:
        payload["stream"] = True
    return payload


def _get_chat_kwargs(
    *,
    chat: StructuredChatRequest,
    base_url: str,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    headers = build_headers(access_token)
    headers["Content-Type"] = "application/json"
    payload = _build_chat_payload(chat=chat, stream=False)

    return {
        "method": "POST",
        "url": resolve_structured_chat_url(base_url),
        "content": json.dumps(payload, ensure_ascii=False),
        "headers": headers,
    }


def chat_sync(
    client: httpx.Client,
    *,
    chat: StructuredChatRequest,
    base_url: str,
    access_token: Optional[str] = None,
) -> StructuredChatResponse:
    """Return a v2 model response based on the provided messages."""
    kwargs = _get_chat_kwargs(chat=chat, base_url=base_url, access_token=access_token)
    return execute_request_sync(client, kwargs, StructuredChatResponse)


async def chat_async(
    client: httpx.AsyncClient,
    *,
    chat: StructuredChatRequest,
    base_url: str,
    access_token: Optional[str] = None,
) -> StructuredChatResponse:
    """Return an async v2 model response based on the provided messages."""
    kwargs = _get_chat_kwargs(chat=chat, base_url=base_url, access_token=access_token)
    return await execute_request_async(client, kwargs, StructuredChatResponse)


def _get_stream_kwargs(
    *,
    chat: StructuredChatRequest,
    base_url: str,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    headers = build_headers(access_token)
    headers["Accept"] = EVENT_STREAM
    headers["Cache-Control"] = "no-store"
    headers["Content-Type"] = "application/json"
    payload = _build_chat_payload(chat=chat, stream=True)

    return {
        "method": "POST",
        "url": resolve_structured_chat_url(base_url),
        "content": json.dumps(payload, ensure_ascii=False),
        "headers": headers,
    }


def stream_sync(
    client: httpx.Client,
    *,
    chat: StructuredChatRequest,
    base_url: str,
    access_token: Optional[str] = None,
) -> Iterator[StructuredChatStreamChunk]:
    """Return a streaming v2 model response based on the provided messages."""
    kwargs = _get_stream_kwargs(chat=chat, base_url=base_url, access_token=access_token)
    return execute_stream_sync(client, kwargs, StructuredChatStreamChunk)


def stream_async(
    client: httpx.AsyncClient,
    *,
    chat: StructuredChatRequest,
    base_url: str,
    access_token: Optional[str] = None,
) -> AsyncIterator[StructuredChatStreamChunk]:
    """Return an async streaming v2 model response based on the provided messages."""
    kwargs = _get_stream_kwargs(chat=chat, base_url=base_url, access_token=access_token)
    return execute_stream_async(client, kwargs, StructuredChatStreamChunk)


resolve_chat_v2_url = resolve_structured_chat_url
_build_chat_v2_payload = _build_chat_payload
_get_chat_v2_kwargs = _get_chat_kwargs
chat_v2_sync = chat_sync
chat_v2_async = chat_async
_get_stream_v2_kwargs = _get_stream_kwargs
stream_v2_sync = stream_sync
stream_v2_async = stream_async
