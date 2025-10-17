from typing import Dict, Literal, Optional, Union

from gigachat.pydantic_v1 import BaseModel, Field


class ResponseFormatText(BaseModel):
    type_: Literal["text"] = Field(..., alias="type")
    """The type of response format being defined. Always `text`."""

class ResponseFormatJSONSchema(BaseModel):
    type_: Literal["json_schema"] = Field(..., alias="type")
    """The type of response format being defined. Always `json_schema`."""

    name: str
    """The name of the response format.

    Must be a-z, A-Z, 0-9, or contain underscores and dashes, with a maximum length
    of 64.
    """

    description: Optional[str]
    """
    A description of what the response format is for, used by the model to determine
    how to respond in the format.
    """

    schema_: Dict[str, object] = Field(default_factory=dict, alias="schema")
    """
    The schema for the response format, described as a JSON Schema object. Learn how
    to build JSON schemas [here](https://json-schema.org/).
    """

    strict: Optional[bool]
    """
    Whether to enable strict schema adherence when generating the output. If set to
    true, the model will always follow the exact schema defined in the `schema`
    field. Only a subset of JSON Schema is supported when `strict` is `true`. To
    learn more, read the
    [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).
    """

ResponseFormat = Union[ResponseFormatJSONSchema, ResponseFormatText]
