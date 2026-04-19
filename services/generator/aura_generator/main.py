"""FastAPI entrypoint for the Aura generator service."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .blueprint import Blueprint
from .config import settings
from .db import delete_app, get_app, init_registry, list_apps
from .deploy import stop as stop_deployment
from .engine import blueprint_from_prompt
from .llm import health as ollama_health
from .pipeline import generate_from_blueprint, generate_from_prompt

log = logging.getLogger("aura.generator")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        init_registry()
        log.info("registry initialized")
    except Exception as exc:  # pragma: no cover - informational
        log.warning("registry init failed: %s", exc)
    yield


app = FastAPI(title="Aura Generator", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- models ----------


class PromptIn(BaseModel):
    prompt: str
    use_llm: bool = True


class GenerateIn(BaseModel):
    prompt: str | None = None
    blueprint: Blueprint | None = None
    use_llm: bool = True


# ---------- routes ----------


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "ollama": await ollama_health(),
        "mode": settings.aura_mode,
        "model": settings.ollama_model,
    }


@app.post("/blueprints")
async def create_blueprint(body: PromptIn) -> Blueprint:
    return await blueprint_from_prompt(body.prompt, use_llm=body.use_llm)


@app.post("/apps")
async def create_app(body: GenerateIn) -> dict[str, Any]:
    if not body.prompt and not body.blueprint:
        raise HTTPException(400, "Provide either `prompt` or `blueprint`.")
    result = (
        await generate_from_blueprint(body.blueprint)
        if body.blueprint
        else await generate_from_prompt(body.prompt or "", use_llm=body.use_llm)
    )
    return {
        "slug": result.blueprint.slug,
        "name": result.blueprint.name,
        "url": result.url,
        "schema": result.schema,
        "heal_ok": result.heal_ok,
        "heal_attempts": result.heal_attempts,
        "deployment": result.deployment,
        "blueprint": result.blueprint.model_dump(),
    }


@app.get("/apps")
async def get_apps() -> list[dict]:
    return list_apps()


@app.get("/apps/{slug}")
async def get_single_app(slug: str) -> dict:
    a = get_app(slug)
    if not a:
        raise HTTPException(404, "app not found")
    return a


@app.delete("/apps/{slug}")
async def delete_single_app(slug: str) -> dict:
    try:
        stop_deployment(slug)
    except Exception:
        pass
    delete_app(slug)
    return {"ok": True}
