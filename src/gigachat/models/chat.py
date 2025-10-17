import inspect
from typing import List, Literal, Optional, Union

from pydantic import BaseModel as ModelV2

from gigachat.api.utils import type_to_response_format_param
from gigachat.models.chat_function_call import ChatFunctionCall
from gigachat.models.function import Function
from gigachat.models.messages import Messages
from gigachat.models.response_format import ResponseFormat
from gigachat.models.storage import Storage
from gigachat.pydantic_v1 import BaseModel, validator


class Chat(BaseModel):
    """Параметры запроса"""

    model: Optional[str] = None
    """Название модели, от которой нужно получить ответ"""
    messages: List[Messages]
    """Массив сообщений"""
    temperature: Optional[float] = None
    """Температура выборки в диапазоне от ноля до двух"""
    top_p: Optional[float] = None
    """Альтернатива параметру температуры"""
    n: Optional[int] = None
    """Количество вариантов ответов, которые нужно сгенерировать для каждого входного сообщения"""
    stream: Optional[bool] = None
    """Указывает, что сообщения надо передавать по частям в потоке"""
    max_tokens: Optional[int] = None
    """Максимальное количество токенов, которые будут использованы для создания ответов"""
    repetition_penalty: Optional[float] = None
    """Количество повторений слов"""
    update_interval: Optional[float] = None
    """Интервал в секундах между отправкой токенов в потоке"""
    profanity_check: Optional[bool] = None
    """Параметр цензуры"""
    function_call: Optional[Union[Literal["auto", "none"], ChatFunctionCall]] = None
    """Правила вызова функций"""
    functions: Optional[List[Function]] = None
    """Набор функций, которые могут быть вызваны моделью"""
    response_format: Optional[ResponseFormat] = None
    """Формат ответа"""
    flags: Optional[List[str]] = None
    """Флаги, включающие особенные фичи"""
    storage: Optional[Storage] = None
    """Данные для хранения контекста на стороне GigaChat"""
    additional_fields: Optional[dict] = None
    """Дополнительные поля, которые прокидываются в API /chat/completions"""
    reasoning_effort: Optional[Literal["low", "medium", "high"]] = None
    """Глубина рассуждений"""

    @validator("response_format", pre=True)
    def response_format_validator(cls, value):
        if inspect.isclass(value):
            if issubclass(value, ModelV2) or issubclass(value, BaseModel):
                return type_to_response_format_param(value)

        return value
