"""Thin Ollama client. Stays tiny on purpose."""

from __future__ import annotations

import json
from typing import Any

import httpx

from .config import settings


class OllamaError(RuntimeError):
    pass


async def generate_json(prompt: str, *, system: str | None = None, model: str | None = None) -> dict[str, Any]:
    """Call Ollama's /api/generate with format=json and return the parsed object."""
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
            raise OllamaError(f"Ollama unreachable at {settings.ollama_url}: {exc}") from exc

    if r.status_code != 200:
        raise OllamaError(f"Ollama returned {r.status_code}: {r.text[:500]}")

    data = r.json()
    raw = data.get("response", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OllamaError(f"Ollama returned non-JSON response: {raw[:500]}") from exc


async def generate_text(prompt: str, *, system: str | None = None, model: str | None = None) -> str:
    payload: dict[str, Any] = {
        "model": model or settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2},
    }
    if system:
        payload["system"] = system

    async with httpx.AsyncClient(timeout=600.0) as client:
        r = await client.post(f"{settings.ollama_url}/api/generate", json=payload)
    if r.status_code != 200:
        raise OllamaError(f"Ollama returned {r.status_code}: {r.text[:500]}")
    return r.json().get("response", "")


async def health() -> bool:
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(f"{settings.ollama_url}/api/tags")
            return r.status_code == 200
        except httpx.HTTPError:
            return False
