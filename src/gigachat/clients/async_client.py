import asyncio
import warnings
from typing import Any, AsyncIterator, Dict, List, Literal, Optional, Tuple, Type, TypeVar, Union, overload

import httpx
import pydantic
from typing_extensions import Self

from gigachat._compat import warn_deprecated_symbol
from gigachat._types import FileContent, FileTypes
from gigachat.authentication import _awith_auth, _awith_auth_stream
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
from gigachat.resources import AssistantsAsyncClient, ThreadsAsyncClient
from gigachat.retry import _awith_retry, _awith_retry_stream
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


class GigaChatAsyncClient(_BaseClient):
    """Asynchronous GigaChat client."""

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
        self.assistants = AssistantsAsyncClient(self)
        self.threads = ThreadsAsyncClient(self)
        self._async_token_lock = asyncio.Lock()
        self._aclient_instance: Optional[httpx.AsyncClient] = None
        self._auth_aclient_instance: Optional[httpx.AsyncClient] = None

    @property
    def a_assistants(self) -> AssistantsAsyncClient:
        warn_deprecated_symbol("GigaChatAsyncClient.a_assistants", "GigaChatAsyncClient.assistants", stacklevel=2)
        return self.assistants

    @property
    def a_threads(self) -> ThreadsAsyncClient:
        warn_deprecated_symbol("GigaChatAsyncClient.a_threads", "GigaChatAsyncClient.threads", stacklevel=2)
        return self.threads

    @property
    def _aclient(self) -> httpx.AsyncClient:
        if self._aclient_instance is None:
            self._aclient_instance = httpx.AsyncClient(**_get_kwargs(self._settings))
        return self._aclient_instance

    @property
    def _auth_aclient(self) -> httpx.AsyncClient:
        if self._auth_aclient_instance is None:
            self._auth_aclient_instance = httpx.AsyncClient(**_get_auth_kwargs(self._settings))
        return self._auth_aclient_instance

    async def aclose(self) -> None:
        if self._aclient_instance:
            await self._aclient_instance.aclose()
        if self._auth_aclient_instance:
            await self._auth_aclient_instance.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    async def _aupdate_token(self) -> None:
        if authorization_cvar.get() is not None:
            return
        async with self._async_token_lock:
            if self._is_token_usable():
                return
            if self._settings.credentials:
                credentials = self._settings.credentials.get_secret_value()
                self._access_token = await auth.auth_async(
                    self._auth_aclient,
                    url=self._settings.auth_url,
                    credentials=credentials,
                    scope=self._settings.scope,
                )
                logger.debug("Token refreshed via OAuth")
            elif self._settings.user and self._settings.password:
                password = self._settings.password.get_secret_value()
                self._access_token = _build_access_token(
                    await auth.token_async(
                        self._aclient,
                        user=self._settings.user,
                        password=password,
                    )
                )
                logger.debug("Token refreshed via password auth")

    async def aget_token(self) -> Optional[AccessToken]:
        await self._aupdate_token()
        return self._access_token

    @_awith_retry
    @_awith_auth
    async def atokens_count(self, input_: List[str], model: Optional[str] = None) -> List[TokensCount]:
        if not model:
            model = self._settings.model or GIGACHAT_MODEL
        return await tools.tokens_count_async(self._aclient, input_=input_, model=model, access_token=self.token)

    @_awith_retry
    @_awith_auth
    async def aembeddings(self, texts: List[str], model: str = "Embeddings") -> Embeddings:
        return await embeddings.embeddings_async(self._aclient, access_token=self.token, input_=texts, model=model)

    @_awith_retry
    @_awith_auth
    async def acreate_batch(self, file: FileContent, method: Literal["chat_completions", "embedder"]) -> Batch:
        return await batches.create_batch_async(self._aclient, file=file, method=method, access_token=self.token)

    @_awith_retry
    @_awith_auth
    async def aget_batches(self, batch_id: Optional[str] = None) -> BatchList:
        return await batches.get_batches_async(self._aclient, batch_id=batch_id, access_token=self.token)

    @_awith_retry
    @_awith_auth
    async def aget_models(self) -> ModelList:
        return await model_catalog.get_models_async(self._aclient, access_token=self.token)

    async def alist_models(self) -> ModelList:
        return await self.aget_models()

    @_awith_retry
    @_awith_auth
    async def aget_model(self, model: str) -> ModelInfo:
        return await model_catalog.get_model_async(self._aclient, model=model, access_token=self.token)

    async def aget_model_info(self, model: str) -> ModelInfo:
        return await self.aget_model(model)

    @_awith_retry
    @_awith_auth
    async def aget_file_content(self, file_id: str) -> File:
        return await files.get_file_content_async(self._aclient, file_id=file_id, access_token=self.token)

    @_awith_retry
    @_awith_auth
    async def aget_image(self, file_id: str) -> File:
        warnings.warn(
            "Method 'aget_image' is deprecated, use 'aget_file_content'",
            DeprecationWarning,
            stacklevel=2,
        )
        return await self.aget_file_content(file_id=file_id)

    @_awith_retry
    @_awith_auth
    async def alegacy_chat(self, payload: Union[LegacyChatRequest, Dict[str, Any], str]) -> ChatCompletion:
        chat_data = _parse_legacy_chat(payload, self._settings)
        return await legacy_chat.chat_async(self._aclient, chat=chat_data, access_token=self.token)

    async def achat(self, payload: Union[LegacyChatRequest, Dict[str, Any], str]) -> ChatCompletion:
        return await self.alegacy_chat(payload)

    @_awith_retry
    @_awith_auth
    async def astructured_chat(self, payload: Union[StructuredChatRequest, Dict[str, Any], str]) -> ChatCompletionV2:
        chat_data = _parse_structured_chat(payload, self._settings)
        return await structured_chat.chat_async(
            self._aclient,
            chat=chat_data,
            base_url=self._settings.base_url,
            access_token=self.token,
        )

    async def achat_v2(self, payload: Union[StructuredChatRequest, Dict[str, Any], str]) -> ChatCompletionV2:
        return await self.astructured_chat(payload)

    @overload
    async def aparse_legacy_chat(
        self,
        payload: Union[LegacyChatRequest, Dict[str, Any], str],
        *,
        response_model: Type[_ModelT],
        strict: Optional[bool] = None,
    ) -> Tuple[ChatCompletion, _ModelT]: ...

    @overload
    async def aparse_legacy_chat(
        self,
        payload: Union[LegacyChatRequest, Dict[str, Any], str],
        *,
        response_model: pydantic.TypeAdapter[_AdaptedT],
        strict: Optional[bool] = None,
    ) -> Tuple[ChatCompletion, _AdaptedT]: ...

    @overload
    async def aparse_legacy_chat(
        self,
        payload: Union[LegacyChatRequest, Dict[str, Any], str],
        *,
        response_model: Any,
        strict: Optional[bool] = None,
    ) -> Tuple[ChatCompletion, Any]: ...

    async def aparse_legacy_chat(
        self,
        payload: Union[LegacyChatRequest, Dict[str, Any], str],
        *,
        response_model: Any,
        strict: Optional[bool] = None,
    ) -> Tuple[ChatCompletion, Any]:
        chat_data = _prepare_legacy_chat_for_parse(payload, self._settings, response_model, strict)
        completion = await self.alegacy_chat(chat_data)
        parsed: Any = _parse_completion(completion, response_model)
        return completion, parsed

    async def achat_parse(
        self,
        payload: Union[LegacyChatRequest, Dict[str, Any], str],
        *,
        response_model: Any,
        strict: Optional[bool] = None,
    ) -> Tuple[ChatCompletion, Any]:
        return await self.aparse_legacy_chat(payload, response_model=response_model, strict=strict)

    @overload
    async def aparse_structured_chat(
        self,
        payload: Union[StructuredChatRequest, Dict[str, Any], str],
        *,
        response_model: Type[_ModelT],
        strict: Optional[bool] = None,
    ) -> Tuple[ChatCompletionV2, _ModelT]: ...

    @overload
    async def aparse_structured_chat(
        self,
        payload: Union[StructuredChatRequest, Dict[str, Any], str],
        *,
        response_model: pydantic.TypeAdapter[_AdaptedT],
        strict: Optional[bool] = None,
    ) -> Tuple[ChatCompletionV2, _AdaptedT]: ...

    @overload
    async def aparse_structured_chat(
        self,
        payload: Union[StructuredChatRequest, Dict[str, Any], str],
        *,
        response_model: Any,
        strict: Optional[bool] = None,
    ) -> Tuple[ChatCompletionV2, Any]: ...

    async def aparse_structured_chat(
        self,
        payload: Union[StructuredChatRequest, Dict[str, Any], str],
        *,
        response_model: Any,
        strict: Optional[bool] = None,
    ) -> Tuple[ChatCompletionV2, Any]:
        chat_data = _prepare_structured_chat_for_parse(payload, self._settings, response_model, strict)
        completion = await self.astructured_chat(chat_data)
        parsed: Any = _parse_completion_v2(completion, response_model)
        return completion, parsed

    async def achat_parse_v2(
        self,
        payload: Union[StructuredChatRequest, Dict[str, Any], str],
        *,
        response_model: Any,
        strict: Optional[bool] = None,
    ) -> Tuple[ChatCompletionV2, Any]:
        return await self.aparse_structured_chat(payload, response_model=response_model, strict=strict)

    @_awith_retry
    @_awith_auth
    async def aupload_file(
        self,
        file: FileTypes,
        purpose: Literal["general", "assistant"] = "general",
    ) -> UploadedFile:
        return await files.upload_file_async(self._aclient, file=file, purpose=purpose, access_token=self.token)

    @_awith_retry
    @_awith_auth
    async def aget_file(self, file: str) -> UploadedFile:
        return await files.get_file_async(self._aclient, file=file, access_token=self.token)

    @_awith_retry
    @_awith_auth
    async def aget_files(self) -> UploadedFiles:
        return await files.get_files_async(self._aclient, access_token=self.token)

    async def alist_files(self) -> UploadedFiles:
        return await self.aget_files()

    @_awith_retry
    @_awith_auth
    async def adelete_file(self, file: str) -> DeletedFile:
        return await files.delete_file_async(self._aclient, file=file, access_token=self.token)

    @_awith_retry
    @_awith_auth
    async def aget_balance(self) -> Balance:
        return await tools.get_balance_async(self._aclient, access_token=self.token)

    @_awith_retry
    @_awith_auth
    async def aopenapi_function_convert(self, openapi_function: str) -> OpenApiFunctions:
        return await tools.functions_convert_async(
            self._aclient,
            openapi_function=openapi_function,
            access_token=self.token,
        )

    @_awith_retry
    @_awith_auth
    async def avalidate_function(self, function: Union[Function, Dict[str, Any]]) -> FunctionValidationResult:
        return await tools.function_validate_async(self._aclient, function=function, access_token=self.token)

    @_awith_retry
    @_awith_auth
    async def acheck_ai(self, text: str, model: str) -> AICheckResult:
        return await tools.ai_check_async(self._aclient, input_=text, model=model, access_token=self.token)

    @_awith_retry_stream
    @_awith_auth_stream
    def astream_legacy_chat(
        self, payload: Union[LegacyChatRequest, Dict[str, Any], str]
    ) -> AsyncIterator[ChatCompletionChunk]:
        chat_data = _parse_legacy_chat(payload, self._settings)
        return legacy_chat.stream_async(self._aclient, chat=chat_data, access_token=self.token)

    def astream(self, payload: Union[LegacyChatRequest, Dict[str, Any], str]) -> AsyncIterator[ChatCompletionChunk]:
        return self.astream_legacy_chat(payload)

    @_awith_retry_stream
    @_awith_auth_stream
    def astream_structured_chat(
        self,
        payload: Union[StructuredChatRequest, Dict[str, Any], str],
    ) -> AsyncIterator[ChatCompletionV2Chunk]:
        chat_data = _parse_structured_chat(payload, self._settings)
        return structured_chat.stream_async(
            self._aclient,
            chat=chat_data,
            base_url=self._settings.base_url,
            access_token=self.token,
        )

    def astream_v2(
        self, payload: Union[StructuredChatRequest, Dict[str, Any], str]
    ) -> AsyncIterator[ChatCompletionV2Chunk]:
        return self.astream_structured_chat(payload)
