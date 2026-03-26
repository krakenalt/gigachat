from typing import Any, Dict, Optional

import httpx

from gigachat.schemas.model_catalog import ModelInfo, ModelList
from gigachat.transport.common import build_headers, execute_request_async, execute_request_sync


def _get_models_kwargs(
    *,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    headers = build_headers(access_token)

    return {
        "method": "GET",
        "url": "/models",
        "headers": headers,
    }


def get_models_sync(
    client: httpx.Client,
    *,
    access_token: Optional[str] = None,
) -> ModelList:
    """Return a list of available models."""
    kwargs = _get_models_kwargs(access_token=access_token)
    return execute_request_sync(client, kwargs, ModelList)


async def get_models_async(
    client: httpx.AsyncClient,
    *,
    access_token: Optional[str] = None,
) -> ModelList:
    """Return a list of available models."""
    kwargs = _get_models_kwargs(access_token=access_token)
    return await execute_request_async(client, kwargs, ModelList)


def _get_model_kwargs(
    *,
    model: str,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    headers = build_headers(access_token)

    return {
        "method": "GET",
        "url": f"/models/{model}",
        "headers": headers,
    }


def get_model_sync(
    client: httpx.Client,
    *,
    model: str,
    access_token: Optional[str] = None,
) -> ModelInfo:
    """Return a description of a specific model."""
    kwargs = _get_model_kwargs(model=model, access_token=access_token)
    return execute_request_sync(client, kwargs, ModelInfo)


async def get_model_async(
    client: httpx.AsyncClient,
    *,
    model: str,
    access_token: Optional[str] = None,
) -> ModelInfo:
    """Return a description of a specific model."""
    kwargs = _get_model_kwargs(model=model, access_token=access_token)
    return await execute_request_async(client, kwargs, ModelInfo)
