from gigachat._compat import warn_deprecated_symbol
from gigachat.transport import (
    assistants,
    auth,
    batches,
    common,
    embeddings,
    files,
    legacy_chat,
    model_catalog,
    structured_chat,
    threads,
    tools,
)

chat = legacy_chat
chat_v2 = structured_chat
models = model_catalog
utils = common

__all__ = [
    "assistants",
    "auth",
    "batches",
    "chat",
    "chat_v2",
    "common",
    "embeddings",
    "files",
    "legacy_chat",
    "model_catalog",
    "models",
    "structured_chat",
    "threads",
    "tools",
    "utils",
]

warn_deprecated_symbol("gigachat.api", "gigachat.transport", stacklevel=2)
