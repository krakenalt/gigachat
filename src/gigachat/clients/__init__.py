from typing import Any, List, Optional, Tuple

from gigachat.clients.async_client import GigaChatAsyncClient
from gigachat.clients.base import (
    GIGACHAT_MODEL,
    SecretValue,
    _BaseClient,
    _build_access_token,
    _get_auth_kwargs,
    _get_kwargs,
    _unwrap_secret,
    logger,
)
from gigachat.clients.parsing import (
    _get_response_model_adapter,
    _parse_chat,
    _parse_chat_v2,
    _parse_completion,
    _parse_completion_v2,
    _parse_legacy_chat,
    _parse_response_content,
    _parse_structured_chat,
    _prepare_chat_for_parse,
    _prepare_chat_v2_for_parse,
    _prepare_legacy_chat_for_parse,
    _prepare_structured_chat_for_parse,
)
from gigachat.clients.sync import GigaChatSyncClient
from gigachat.resources import AssistantsAsyncClient, ThreadsAsyncClient

__all__ = [
    "GIGACHAT_MODEL",
    "SecretValue",
    "_BaseClient",
    "_build_access_token",
    "_get_auth_kwargs",
    "_get_kwargs",
    "_unwrap_secret",
    "logger",
    "_get_response_model_adapter",
    "_parse_chat",
    "_parse_chat_v2",
    "_parse_completion",
    "_parse_completion_v2",
    "_parse_legacy_chat",
    "_parse_response_content",
    "_parse_structured_chat",
    "_prepare_chat_for_parse",
    "_prepare_chat_v2_for_parse",
    "_prepare_legacy_chat_for_parse",
    "_prepare_structured_chat_for_parse",
    "GigaChatSyncClient",
    "GigaChatAsyncClient",
    "GigaChat",
]


class GigaChat(GigaChatSyncClient, GigaChatAsyncClient):
    """Hybrid sync/async compatibility client."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        auth_url: Optional[str] = None,
        credentials: Optional[SecretValue] = None,
        scope: Optional[str] = None,
        access_token: Optional[SecretValue] = None,
        model: Optional[str] = None,
        profanity_check: Optional[bool] = None,
        user: Optional[str] = None,
        password: Optional[SecretValue] = None,
        timeout: Optional[float] = None,
        verify_ssl_certs: Optional[bool] = None,
        ca_bundle_file: Optional[str] = None,
        cert_file: Optional[str] = None,
        key_file: Optional[str] = None,
        key_file_password: Optional[SecretValue] = None,
        ssl_context: Optional[Any] = None,
        flags: Optional[List[str]] = None,
        max_connections: Optional[int] = None,
        max_retries: Optional[int] = None,
        retry_backoff_factor: Optional[float] = None,
        retry_on_status_codes: Optional[Tuple[int, ...]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            base_url=base_url,
            auth_url=auth_url,
            credentials=credentials,
            scope=scope,
            access_token=access_token,
            model=model,
            profanity_check=profanity_check,
            user=user,
            password=password,
            timeout=timeout,
            verify_ssl_certs=verify_ssl_certs,
            ca_bundle_file=ca_bundle_file,
            cert_file=cert_file,
            key_file=key_file,
            key_file_password=key_file_password,
            ssl_context=ssl_context,
            flags=flags,
            max_connections=max_connections,
            max_retries=max_retries,
            retry_backoff_factor=retry_backoff_factor,
            retry_on_status_codes=retry_on_status_codes,
            **kwargs,
        )
        self._async_assistants = AssistantsAsyncClient(self)
        self._async_threads = ThreadsAsyncClient(self)

    @property
    def a_assistants(self) -> AssistantsAsyncClient:
        return self._async_assistants

    @property
    def a_threads(self) -> ThreadsAsyncClient:
        return self._async_threads

    async def aclose(self) -> None:
        self.close()
        await super().aclose()
