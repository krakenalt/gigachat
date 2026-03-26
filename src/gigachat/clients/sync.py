import threading
import warnings
from typing import Any, Dict, Iterator, List, Literal, Optional, Tuple, Type, TypeVar, Union, overload

import httpx
import pydantic
from typing_extensions import Self

from gigachat._types import FileContent, FileTypes
from gigachat.authentication import _with_auth, _with_auth_stream
from gigachat.clients.base import (
    GIGACHAT_MODEL,
    SecretValue,
    _BaseClient,
    _build_access_token,
    _get_auth_kwargs,
    _get_kwargs,
    logger,
)
from gigachat.clients.parsing import (
    _parse_completion,
    _parse_completion_v2,
    _parse_legacy_chat,
    _parse_structured_chat,
    _prepare_legacy_chat_for_parse,
    _prepare_structured_chat_for_parse,
)
from gigachat.context import authorization_cvar
from gigachat.resources import AssistantsSyncClient, ThreadsSyncClient
from gigachat.retry import _with_retry, _with_retry_stream
from gigachat.schemas import (
    AccessToken,
    AICheckResult,
    Balance,
    Batch,
    BatchList,
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionV2,
    ChatCompletionV2Chunk,
    Embeddings,
    Function,
    FunctionValidationResult,
    LegacyChatRequest,
    ModelInfo,
    ModelList,
    OpenApiFunctions,
    StructuredChatRequest,
    TokensCount,
    UploadedFile,
    UploadedFiles,
)
from gigachat.schemas.files import DeletedFile, File
from gigachat.transport import auth, batches, embeddings, files, legacy_chat, model_catalog, structured_chat, tools

_ModelT = TypeVar("_ModelT")
_AdaptedT = TypeVar("_AdaptedT")


class GigaChatSyncClient(_BaseClient):
    """Synchronous GigaChat client."""

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
        self.assistants = AssistantsSyncClient(self)
        self.threads = ThreadsSyncClient(self)
        self._sync_token_lock = threading.RLock()
        self._client_instance: Optional[httpx.Client] = None
        self._auth_client_instance: Optional[httpx.Client] = None

    @property
    def _client(self) -> httpx.Client:
        if self._client_instance is None:
            with self._sync_token_lock:
                if self._client_instance is None:
                    self._client_instance = httpx.Client(**_get_kwargs(self._settings))
        return self._client_instance

    @property
    def _auth_client(self) -> httpx.Client:
        if self._auth_client_instance is None:
            with self._sync_token_lock:
                if self._auth_client_instance is None:
                    self._auth_client_instance = httpx.Client(**_get_auth_kwargs(self._settings))
        return self._auth_client_instance

    def close(self) -> None:
        if self._client_instance:
            self._client_instance.close()
        if self._auth_client_instance:
            self._auth_client_instance.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def _update_token(self) -> None:
        if authorization_cvar.get() is not None:
            return

        with self._sync_token_lock:
            if self._is_token_usable():
                return

            if self._settings.credentials:
                credentials = self._settings.credentials.get_secret_value()
                self._access_token = auth.auth_sync(
                    self._auth_client,
                    url=self._settings.auth_url,
                    credentials=credentials,
                    scope=self._settings.scope,
                )
                logger.debug("Token refreshed via OAuth")
            elif self._settings.user and self._settings.password:
                password = self._settings.password.get_secret_value()
                self._access_token = _build_access_token(
                    auth.token_sync(
                        self._client,
                        user=self._settings.user,
                        password=password,
                    )
                )
                logger.debug("Token refreshed via password auth")

    def get_token(self) -> Optional[AccessToken]:
        self._update_token()
        return self._access_token

    @_with_retry
    @_with_auth
    def tokens_count(self, input_: List[str], model: Optional[str] = None) -> List[TokensCount]:
        if not model:
            model = self._settings.model or GIGACHAT_MODEL
        return tools.tokens_count_sync(self._client, input_=input_, model=model, access_token=self.token)

    @_with_retry
    @_with_auth
    def embeddings(self, texts: List[str], model: str = "Embeddings") -> Embeddings:
        return embeddings.embeddings_sync(self._client, access_token=self.token, input_=texts, model=model)

    @_with_retry
    @_with_auth
    def create_batch(self, file: FileContent, method: Literal["chat_completions", "embedder"]) -> Batch:
        return batches.create_batch_sync(self._client, file=file, method=method, access_token=self.token)

    @_with_retry
    @_with_auth
    def get_batches(self, batch_id: Optional[str] = None) -> BatchList:
        return batches.get_batches_sync(self._client, batch_id=batch_id, access_token=self.token)

    @_with_retry
    @_with_auth
    def get_models(self) -> ModelList:
        return model_catalog.get_models_sync(self._client, access_token=self.token)

    def list_models(self) -> ModelList:
        return self.get_models()

    @_with_retry
    @_with_auth
    def get_model(self, model: str) -> ModelInfo:
        return model_catalog.get_model_sync(self._client, model=model, access_token=self.token)

    def get_model_info(self, model: str) -> ModelInfo:
        return self.get_model(model)

    @_with_retry
    @_with_auth
    def get_file_content(self, file_id: str) -> File:
        return files.get_file_content_sync(self._client, file_id=file_id, access_token=self.token)

    @_with_retry
    @_with_auth
    def get_image(self, file_id: str) -> File:
        warnings.warn(
            "Method 'get_image' is deprecated, use 'get_file_content'",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.get_file_content(file_id=file_id)

    @_with_retry
    @_with_auth
    def upload_file(
        self,
        file: FileTypes,
        purpose: Literal["general", "assistant"] = "general",
    ) -> UploadedFile:
        return files.upload_file_sync(self._client, file=file, purpose=purpose, access_token=self.token)

    @_with_retry
    @_with_auth
    def get_file(self, file: str) -> UploadedFile:
        return files.get_file_sync(self._client, file=file, access_token=self.token)

    @_with_retry
    @_with_auth
    def get_files(self) -> UploadedFiles:
        return files.get_files_sync(self._client, access_token=self.token)

    def list_files(self) -> UploadedFiles:
        return self.get_files()

    @_with_retry
    @_with_auth
    def delete_file(self, file: str) -> DeletedFile:
        return files.delete_file_sync(self._client, file=file, access_token=self.token)

    @_with_retry
    @_with_auth
    def legacy_chat(self, payload: Union[LegacyChatRequest, Dict[str, Any], str]) -> ChatCompletion:
        chat_data = _parse_legacy_chat(payload, self._settings)
        return legacy_chat.chat_sync(self._client, chat=chat_data, access_token=self.token)

    def chat(self, payload: Union[LegacyChatRequest, Dict[str, Any], str]) -> ChatCompletion:
        return self.legacy_chat(payload)

    @_with_retry
    @_with_auth
    def structured_chat(self, payload: Union[StructuredChatRequest, Dict[str, Any], str]) -> ChatCompletionV2:
        chat_data = _parse_structured_chat(payload, self._settings)
        return structured_chat.chat_sync(
            self._client,
            chat=chat_data,
            base_url=self._settings.base_url,
            access_token=self.token,
        )

    def chat_v2(self, payload: Union[StructuredChatRequest, Dict[str, Any], str]) -> ChatCompletionV2:
        return self.structured_chat(payload)

    @overload
    def parse_legacy_chat(
        self,
        payload: Union[LegacyChatRequest, Dict[str, Any], str],
        *,
        response_model: Type[_ModelT],
        strict: Optional[bool] = None,
    ) -> Tuple[ChatCompletion, _ModelT]: ...

    @overload
    def parse_legacy_chat(
        self,
        payload: Union[LegacyChatRequest, Dict[str, Any], str],
        *,
        response_model: pydantic.TypeAdapter[_AdaptedT],
        strict: Optional[bool] = None,
    ) -> Tuple[ChatCompletion, _AdaptedT]: ...

    @overload
    def parse_legacy_chat(
        self,
        payload: Union[LegacyChatRequest, Dict[str, Any], str],
        *,
        response_model: Any,
        strict: Optional[bool] = None,
    ) -> Tuple[ChatCompletion, Any]: ...

    def parse_legacy_chat(
        self,
        payload: Union[LegacyChatRequest, Dict[str, Any], str],
        *,
        response_model: Any,
        strict: Optional[bool] = None,
    ) -> Tuple[ChatCompletion, Any]:
        chat_data = _prepare_legacy_chat_for_parse(payload, self._settings, response_model, strict)
        completion = self.legacy_chat(chat_data)
        parsed: Any = _parse_completion(completion, response_model)
        return completion, parsed

    def chat_parse(
        self,
        payload: Union[LegacyChatRequest, Dict[str, Any], str],
        *,
        response_model: Any,
        strict: Optional[bool] = None,
    ) -> Tuple[ChatCompletion, Any]:
        return self.parse_legacy_chat(payload, response_model=response_model, strict=strict)

    @overload
    def parse_structured_chat(
        self,
        payload: Union[StructuredChatRequest, Dict[str, Any], str],
        *,
        response_model: Type[_ModelT],
        strict: Optional[bool] = None,
    ) -> Tuple[ChatCompletionV2, _ModelT]: ...

    @overload
    def parse_structured_chat(
        self,
        payload: Union[StructuredChatRequest, Dict[str, Any], str],
        *,
        response_model: pydantic.TypeAdapter[_AdaptedT],
        strict: Optional[bool] = None,
    ) -> Tuple[ChatCompletionV2, _AdaptedT]: ...

    @overload
    def parse_structured_chat(
        self,
        payload: Union[StructuredChatRequest, Dict[str, Any], str],
        *,
        response_model: Any,
        strict: Optional[bool] = None,
    ) -> Tuple[ChatCompletionV2, Any]: ...

    def parse_structured_chat(
        self,
        payload: Union[StructuredChatRequest, Dict[str, Any], str],
        *,
        response_model: Any,
        strict: Optional[bool] = None,
    ) -> Tuple[ChatCompletionV2, Any]:
        chat_data = _prepare_structured_chat_for_parse(payload, self._settings, response_model, strict)
        completion = self.structured_chat(chat_data)
        parsed: Any = _parse_completion_v2(completion, response_model)
        return completion, parsed

    def chat_parse_v2(
        self,
        payload: Union[StructuredChatRequest, Dict[str, Any], str],
        *,
        response_model: Any,
        strict: Optional[bool] = None,
    ) -> Tuple[ChatCompletionV2, Any]:
        return self.parse_structured_chat(payload, response_model=response_model, strict=strict)

    @_with_retry
    @_with_auth
    def get_balance(self) -> Balance:
        return tools.get_balance_sync(self._client, access_token=self.token)

    @_with_retry
    @_with_auth
    def openapi_function_convert(self, openapi_function: str) -> OpenApiFunctions:
        return tools.functions_convert_sync(self._client, openapi_function=openapi_function, access_token=self.token)

    @_with_retry
    @_with_auth
    def validate_function(self, function: Union[Function, Dict[str, Any]]) -> FunctionValidationResult:
        return tools.function_validate_sync(self._client, function=function, access_token=self.token)

    @_with_retry
    @_with_auth
    def check_ai(self, text: str, model: str) -> AICheckResult:
        return tools.ai_check_sync(self._client, input_=text, model=model, access_token=self.token)

    @_with_retry_stream
    @_with_auth_stream
    def stream_legacy_chat(
        self, payload: Union[LegacyChatRequest, Dict[str, Any], str]
    ) -> Iterator[ChatCompletionChunk]:
        chat_data = _parse_legacy_chat(payload, self._settings)
        yield from legacy_chat.stream_sync(self._client, chat=chat_data, access_token=self.token)

    def stream(self, payload: Union[LegacyChatRequest, Dict[str, Any], str]) -> Iterator[ChatCompletionChunk]:
        yield from self.stream_legacy_chat(payload)

    @_with_retry_stream
    @_with_auth_stream
    def stream_structured_chat(
        self,
        payload: Union[StructuredChatRequest, Dict[str, Any], str],
    ) -> Iterator[ChatCompletionV2Chunk]:
        chat_data = _parse_structured_chat(payload, self._settings)
        yield from structured_chat.stream_sync(
            self._client,
            chat=chat_data,
            base_url=self._settings.base_url,
            access_token=self.token,
        )

    def stream_v2(self, payload: Union[StructuredChatRequest, Dict[str, Any], str]) -> Iterator[ChatCompletionV2Chunk]:
        yield from self.stream_structured_chat(payload)
