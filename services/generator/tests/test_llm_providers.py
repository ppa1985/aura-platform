"""Unit tests for the multi-provider LLM dispatch.

We mock httpx at the transport layer so no real network calls are made.
"""

from __future__ import annotations

import json

import httpx
import pytest

from aura_generator import llm
from aura_generator.config import settings


def _mock_transport(handler):
    """Wrap a request-level handler as a MockTransport and patch
    httpx.AsyncClient to use it."""
    return httpx.MockTransport(handler)


@pytest.fixture
def groq_settings(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "gsk_test_key")
    monkeypatch.setattr(settings, "groq_base_url", "https://api.groq.com/openai/v1")
    monkeypatch.setattr(settings, "groq_model", "llama-3.1-8b-instant")


@pytest.fixture
def openai_settings(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "sk-test-key")
    monkeypatch.setattr(settings, "openai_base_url", "https://api.openai.com/v1")
    monkeypatch.setattr(settings, "openai_model", "gpt-4o-mini")


def _patch_client(monkeypatch, handler):
    """Replace httpx.AsyncClient with one whose transport is our handler."""
    original = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


@pytest.mark.asyncio
async def test_groq_generate_json_success(monkeypatch, groq_settings):
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"role": "assistant", "content": '{"name":"WMS"}'}}
                ]
            },
        )

    _patch_client(monkeypatch, handler)
    out = await llm.generate_json("describe a warehouse app", system="sys")

    assert out == {"name": "WMS"}
    assert captured["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured["auth"] == "Bearer gsk_test_key"
    assert captured["body"]["model"] == "llama-3.1-8b-instant"
    assert captured["body"]["response_format"] == {"type": "json_object"}
    assert captured["body"]["messages"][0] == {"role": "system", "content": "sys"}
    assert captured["body"]["messages"][1] == {
        "role": "user",
        "content": "describe a warehouse app",
    }


@pytest.mark.asyncio
async def test_groq_non_200_raises_llmerror(monkeypatch, groq_settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid key"}})

    _patch_client(monkeypatch, handler)
    with pytest.raises(llm.LLMError, match="groq returned 401"):
        await llm.generate_json("anything")


@pytest.mark.asyncio
async def test_groq_non_json_content_raises_llmerror(monkeypatch, groq_settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Sure! Here you go:"}}]},
        )

    _patch_client(monkeypatch, handler)
    with pytest.raises(llm.LLMError, match="Groq returned non-JSON"):
        await llm.generate_json("anything")


@pytest.mark.asyncio
async def test_groq_missing_api_key_raises(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "")
    with pytest.raises(llm.LLMError, match="no API key is configured"):
        await llm.generate_json("anything")


@pytest.mark.asyncio
async def test_openai_uses_configured_model(monkeypatch, openai_settings):
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"ok":true}'}}]},
        )

    _patch_client(monkeypatch, handler)
    out = await llm.generate_json("hi")

    assert out == {"ok": True}
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["body"]["model"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_unknown_provider_raises(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "llamasoft-9000")
    with pytest.raises(llm.LLMError, match="Unknown LLM_PROVIDER"):
        await llm.generate_json("hi")


@pytest.mark.asyncio
async def test_groq_health_true_on_200(monkeypatch, groq_settings):
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://api.groq.com/openai/v1/models"
        return httpx.Response(200, json={"data": []})

    _patch_client(monkeypatch, handler)
    assert await llm.health() is True


@pytest.mark.asyncio
async def test_groq_health_false_without_key(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "")
    assert await llm.health() is False


def test_active_model_follows_provider(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_model", "llama-3.3-70b-versatile")
    assert llm.active_model() == "llama-3.3-70b-versatile"

    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_model", "gpt-4o")
    assert llm.active_model() == "gpt-4o"

    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "ollama_model", "llama3.2:1b")
    assert llm.active_model() == "llama3.2:1b"


def test_ollama_error_alias_is_llm_error():
    """Existing callers (engine.py, selfheal.py) import OllamaError directly
    and catch it. The alias must be identical to LLMError."""
    assert llm.OllamaError is llm.LLMError
