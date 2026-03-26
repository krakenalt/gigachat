import inspect
import json
from typing import Any, Dict, Optional, Type, TypeVar, Union, get_origin, overload

import pydantic

from gigachat.clients.base import GIGACHAT_MODEL
from gigachat.exceptions import (
    ContentFilterFinishReasonError,
    ContentParseError,
    ContentValidationError,
    LengthFinishReasonError,
)
from gigachat.schemas import (
    ChatCompletion,
    ChatCompletionV2,
    ChatV2ModelOptions,
    ChatV2ResponseFormat,
    ChatV2Storage,
    JsonSchemaResponseFormat,
    LegacyChatRequest,
    LegacyChatResponse,
    LegacyMessage,
    LegacyMessageRole,
    StructuredChatRequest,
    StructuredChatResponse,
    StructuredContentPart,
    StructuredMessage,
)
from gigachat.settings import Settings

_ModelT = TypeVar("_ModelT")
_AdaptedT = TypeVar("_AdaptedT")


def _parse_legacy_chat(payload: Union[LegacyChatRequest, Dict[str, Any], str], settings: Settings) -> LegacyChatRequest:
    if isinstance(payload, str):
        chat = LegacyChatRequest(messages=[LegacyMessage(role=LegacyMessageRole.USER, content=payload)])
    else:
        chat = LegacyChatRequest.model_validate(payload)
    using_assistant = chat.storage is not None and (chat.storage.assistant_id or chat.storage.thread_id)
    if not using_assistant and chat.model is None:
        chat.model = settings.model or GIGACHAT_MODEL
    if chat.profanity_check is None:
        chat.profanity_check = settings.profanity_check
    if chat.flags is None:
        chat.flags = settings.flags
    return chat


def _prepare_legacy_chat_for_parse(
    payload: Union[LegacyChatRequest, Dict[str, Any], str],
    settings: Settings,
    response_model: Any,
    strict: Optional[bool],
) -> LegacyChatRequest:
    """Prepare a legacy chat request with response_format derived from *response_model*."""
    chat_data = _parse_legacy_chat(payload, settings)
    chat_data.response_format = JsonSchemaResponseFormat(schema=response_model, strict=strict)
    return chat_data


def _parse_structured_chat(
    payload: Union[StructuredChatRequest, Dict[str, Any], str],
    settings: Settings,
) -> StructuredChatRequest:
    if isinstance(payload, str):
        chat_data = StructuredChatRequest(
            messages=[StructuredMessage(role="user", content=[StructuredContentPart(text=payload)])]
        )
    else:
        chat_data = StructuredChatRequest.model_validate(payload)

    storage_thread_id = chat_data.storage.thread_id if isinstance(chat_data.storage, ChatV2Storage) else None
    using_assistant = chat_data.assistant_id is not None or storage_thread_id is not None
    if not using_assistant and chat_data.model is None:
        chat_data.model = settings.model or GIGACHAT_MODEL
    if chat_data.flags is None:
        chat_data.flags = settings.flags
    return chat_data


def _prepare_structured_chat_for_parse(
    payload: Union[StructuredChatRequest, Dict[str, Any], str],
    settings: Settings,
    response_model: Any,
    strict: Optional[bool],
) -> StructuredChatRequest:
    """Prepare a structured chat request with response_format derived from *response_model*."""
    chat_data = _parse_structured_chat(payload, settings)
    if chat_data.model_options is None:
        chat_data.model_options = ChatV2ModelOptions()
    chat_data.model_options.response_format = ChatV2ResponseFormat(
        type="json_schema",
        schema=response_model,
        strict=strict,
    )
    return chat_data


def _get_response_model_adapter(response_model: Any) -> Optional[pydantic.TypeAdapter[Any]]:
    """Return a TypeAdapter for supported typing annotations and adapters."""
    if isinstance(response_model, pydantic.TypeAdapter):
        return response_model

    if inspect.isclass(response_model) and issubclass(response_model, pydantic.BaseModel):
        return None

    if get_origin(response_model) is not None:
        return pydantic.TypeAdapter(response_model)

    return None


def _parse_response_content(
    content: Any,
    completion: Union[LegacyChatResponse, StructuredChatResponse],
    response_model: Any,
) -> Any:
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ContentParseError(content, completion) from exc

    try:
        adapter = _get_response_model_adapter(response_model)
        if adapter is not None:
            return adapter.validate_python(data)
        return response_model.model_validate(data)
    except pydantic.ValidationError as exc:
        raise ContentValidationError(content, completion, exc) from exc


@overload
def _parse_legacy_completion(completion: ChatCompletion, response_model: Type[_ModelT]) -> _ModelT: ...


@overload
def _parse_legacy_completion(
    completion: ChatCompletion,
    response_model: pydantic.TypeAdapter[_AdaptedT],
) -> _AdaptedT: ...


@overload
def _parse_legacy_completion(
    completion: ChatCompletion,
    response_model: Any,
) -> Any: ...


def _parse_legacy_completion(
    completion: ChatCompletion,
    response_model: Any,
) -> Any:
    if not completion.choices:
        raise ContentParseError("", completion)

    choice = completion.choices[0]

    if choice.finish_reason == "length":
        raise LengthFinishReasonError(completion)
    if choice.finish_reason == "content_filter":
        raise ContentFilterFinishReasonError(completion)

    return _parse_response_content(choice.message.content, completion, response_model)


@overload
def _parse_structured_completion(completion: ChatCompletionV2, response_model: Type[_ModelT]) -> _ModelT: ...


@overload
def _parse_structured_completion(
    completion: ChatCompletionV2,
    response_model: pydantic.TypeAdapter[_AdaptedT],
) -> _AdaptedT: ...


@overload
def _parse_structured_completion(
    completion: ChatCompletionV2,
    response_model: Any,
) -> Any: ...


def _parse_structured_completion(
    completion: ChatCompletionV2,
    response_model: Any,
) -> Any:
    if not completion.messages:
        raise ContentParseError("", completion)

    if completion.finish_reason == "length":
        raise LengthFinishReasonError(completion)
    if completion.finish_reason == "content_filter":
        raise ContentFilterFinishReasonError(completion)

    content = ""
    for message in completion.messages:
        text_parts = [part.text for part in message.content if part.text is not None]
        if text_parts:
            content = "".join(text_parts)
            break

    return _parse_response_content(content, completion, response_model)


_parse_chat = _parse_legacy_chat
_prepare_chat_for_parse = _prepare_legacy_chat_for_parse
_parse_chat_v2 = _parse_structured_chat
_prepare_chat_v2_for_parse = _prepare_structured_chat_for_parse
_parse_completion = _parse_legacy_completion
_parse_completion_v2 = _parse_structured_completion
