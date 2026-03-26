import importlib
import warnings

import pytest

import gigachat
from gigachat import GigaChatAsyncClient, StructuredChatRequest


def test_top_level_deprecated_structured_alias_warns() -> None:
    with pytest.warns(DeprecationWarning, match=r"gigachat\.ChatV2"):
        assert gigachat.ChatV2 is StructuredChatRequest


def test_top_level_deprecated_model_alias_warns() -> None:
    with pytest.warns(DeprecationWarning, match=r"gigachat\.Model"):
        assert gigachat.Model is gigachat.ModelInfo


def test_async_resource_aliases_warn_and_match() -> None:
    client = GigaChatAsyncClient(base_url="https://example.com")

    with pytest.warns(DeprecationWarning, match=r"GigaChatAsyncClient\.a_assistants"):
        assert client.a_assistants is client.assistants

    with pytest.warns(DeprecationWarning, match=r"GigaChatAsyncClient\.a_threads"):
        assert client.a_threads is client.threads


def test_api_package_keeps_old_module_aliases() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        api = importlib.import_module("gigachat.api")
    with pytest.warns(DeprecationWarning, match=r"gigachat\.api"):
        api = importlib.reload(api)

    assert api.chat is api.legacy_chat
    assert api.chat_v2 is api.structured_chat
    assert api.models is api.model_catalog


def test_models_package_exposes_canonical_aliases() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        models_pkg = importlib.import_module("gigachat.models")
    with pytest.warns(DeprecationWarning, match=r"gigachat\.models"):
        models_pkg = importlib.reload(models_pkg)

    assert models_pkg.StructuredChatRequest is StructuredChatRequest
