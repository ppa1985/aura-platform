"""Unified LLM client with pluggable providers.

Supported providers (selected via settings.llm_provider):
- "ollama" — local Ollama instance via /api/generate (JSON format mode).
- "groq"   — Groq's OpenAI-compatible /chat/completions. ~5s blueprints.
- "openai" — OpenAI's /chat/completions.

Every provider must implement the same two coroutines:
    generate_json(prompt, *, system=None, model=None) -> dict
    generate_text(prompt, *, system=None, model=None) -> str
plus a single `health()` coroutine that returns bool.

The public module-level functions dispatch to the active provider so that
callers (engine.py, pipeline.py) don't care which LLM is actually in use.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from .config import settings


class LLMError(RuntimeError):
    """Raised for any provider-level failure. engine.py catches this and
    falls back to the deterministic heuristic path."""


# Back-compat alias: older callers import OllamaError directly.
OllamaError = LLMError


# ---------------------------------------------------------------------------
# Ollama provider
# ---------------------------------------------------------------------------


async def _ollama_generate_json(prompt: str, *, system: str | None, model: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model or settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.2},
    }
    if system:
        payload["system"] = system

    async with httpx.AsyncClient(timeout=600.0) as client:
        try:
            r = await client.post(f"{settings.ollama_url}/api/generate", json=payload)
        except httpx.HTTPError as exc:
            raise LLMError(f"Ollama unreachable at {settings.ollama_url}: {exc}") from exc

    if r.status_code != 200:
        raise LLMError(f"Ollama returned {r.status_code}: {r.text[:500]}")

    raw = r.json().get("response", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMError(f"Ollama returned non-JSON response: {raw[:500]}") from exc


async def _ollama_generate_text(prompt: str, *, system: str | None, model: str | None) -> str:
    payload: dict[str, Any] = {
        "model": model or settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2},
    }
    if system:
        payload["system"] = system

    async with httpx.AsyncClient(timeout=600.0) as client:
        try:
            r = await client.post(f"{settings.ollama_url}/api/generate", json=payload)
        except httpx.HTTPError as exc:
            raise LLMError(f"Ollama unreachable at {settings.ollama_url}: {exc}") from exc
    if r.status_code != 200:
        raise LLMError(f"Ollama returned {r.status_code}: {r.text[:500]}")
    return r.json().get("response", "")


async def _ollama_health() -> bool:
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(f"{settings.ollama_url}/api/tags")
            return r.status_code == 200
        except httpx.HTTPError:
            return False


# ---------------------------------------------------------------------------
# OpenAI-compatible providers (Groq, OpenAI, etc.)
# ---------------------------------------------------------------------------


def _oai_messages(prompt: str, system: str | None) -> list[dict[str, str]]:
    msgs: list[dict[str, str]] = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    return msgs


async def _oai_chat(
    *,
    base_url: str,
    api_key: str,
    default_model: str,
    model: str | None,
    prompt: str,
    system: str | None,
    want_json: bool,
    provider_label: str,
) -> str:
    if not api_key:
        raise LLMError(
            f"{provider_label} is selected as LLM_PROVIDER but no API key is configured. "
            f"Set {provider_label.upper()}_API_KEY in your .env."
        )

    payload: dict[str, Any] = {
        "model": model or default_model,
        "messages": _oai_messages(prompt, system),
        "temperature": 0.2,
        "stream": False,
    }
    if want_json:
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            r = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
            )
        except httpx.HTTPError as exc:
            raise LLMError(f"{provider_label} unreachable at {base_url}: {exc}") from exc

    if r.status_code != 200:
        raise LLMError(f"{provider_label} returned {r.status_code}: {r.text[:500]}")

    body = r.json()
    try:
        return body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"{provider_label} returned unexpected payload: {str(body)[:500]}") from exc


async def _groq_generate_json(prompt: str, *, system: str | None, model: str | None) -> dict[str, Any]:
    raw = await _oai_chat(
        base_url=settings.groq_base_url,
        api_key=settings.groq_api_key,
        default_model=settings.groq_model,
        model=model,
        prompt=prompt,
        system=system,
        want_json=True,
        provider_label="groq",
    )
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        # TypeError covers the case where _oai_chat returned None
        # (OpenAI spec allows content: null, e.g. on refusal).
        raise LLMError(f"Groq returned non-JSON content: {str(raw)[:500]}") from exc


async def _groq_generate_text(prompt: str, *, system: str | None, model: str | None) -> str:
    return await _oai_chat(
        base_url=settings.groq_base_url,
        api_key=settings.groq_api_key,
        default_model=settings.groq_model,
        model=model,
        prompt=prompt,
        system=system,
        want_json=False,
        provider_label="groq",
    )


async def _groq_health() -> bool:
    if not settings.groq_api_key:
        return False
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(
                f"{settings.groq_base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            )
            return r.status_code == 200
        except httpx.HTTPError:
            return False


async def _openai_generate_json(prompt: str, *, system: str | None, model: str | None) -> dict[str, Any]:
    raw = await _oai_chat(
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key,
        default_model=settings.openai_model,
        model=model,
        prompt=prompt,
        system=system,
        want_json=True,
        provider_label="openai",
    )
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        # TypeError covers the case where _oai_chat returned None
        # (OpenAI spec allows content: null, e.g. on refusal).
        raise LLMError(f"OpenAI returned non-JSON content: {str(raw)[:500]}") from exc


async def _openai_generate_text(prompt: str, *, system: str | None, model: str | None) -> str:
    return await _oai_chat(
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key,
        default_model=settings.openai_model,
        model=model,
        prompt=prompt,
        system=system,
        want_json=False,
        provider_label="openai",
    )


async def _openai_health() -> bool:
    if not settings.openai_api_key:
        return False
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(
                f"{settings.openai_base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            )
            return r.status_code == 200
        except httpx.HTTPError:
            return False


# ---------------------------------------------------------------------------
# Public dispatch
# ---------------------------------------------------------------------------


def _active_provider() -> str:
    # Normalize here rather than at config load time so tests can flip it.
    return (settings.llm_provider or "ollama").strip().lower()


async def generate_json(prompt: str, *, system: str | None = None, model: str | None = None) -> dict[str, Any]:
    p = _active_provider()
    if p == "ollama":
        return await _ollama_generate_json(prompt, system=system, model=model)
    if p == "groq":
        return await _groq_generate_json(prompt, system=system, model=model)
    if p == "openai":
        return await _openai_generate_json(prompt, system=system, model=model)
    raise LLMError(
        f"Unknown LLM_PROVIDER={p!r}. Valid values: 'ollama', 'groq', 'openai'."
    )


async def generate_text(prompt: str, *, system: str | None = None, model: str | None = None) -> str:
    p = _active_provider()
    if p == "ollama":
        return await _ollama_generate_text(prompt, system=system, model=model)
    if p == "groq":
        return await _groq_generate_text(prompt, system=system, model=model)
    if p == "openai":
        return await _openai_generate_text(prompt, system=system, model=model)
    raise LLMError(
        f"Unknown LLM_PROVIDER={p!r}. Valid values: 'ollama', 'groq', 'openai'."
    )


async def health() -> bool:
    p = _active_provider()
    if p == "ollama":
        return await _ollama_health()
    if p == "groq":
        return await _groq_health()
    if p == "openai":
        return await _openai_health()
    return False


def active_model() -> str:
    """Model tag of the currently-active provider, for /health reporting."""
    p = _active_provider()
    if p == "groq":
        return settings.groq_model
    if p == "openai":
        return settings.openai_model
    return settings.ollama_model
