"""End-to-end pipeline: prompt → Blueprint → schema → code → heal → deploy."""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from pathlib import Path

from .blueprint import Blueprint
from .codegen import generate_app
from .config import settings
from .db import create_app_schema, set_app_status, upsert_app
from .deploy import deploy
from .engine import blueprint_from_prompt
from .selfheal import heal


@dataclass
class GenerationResult:
    blueprint: Blueprint
    app_dir: Path
    schema: str
    heal_ok: bool
    heal_attempts: list[dict] = field(default_factory=list)
    deployment: dict | None = None
    url: str | None = None
    error: str | None = None


async def generate_from_prompt(prompt: str, *, use_llm: bool = True) -> GenerationResult:
    bp = await blueprint_from_prompt(prompt, use_llm=use_llm)
    return await generate_from_blueprint(bp)


async def generate_from_blueprint(bp: Blueprint) -> GenerationResult:
    bp.ensure_default_pages()
    upsert_app(bp, status="generating")
    try:
        schema = create_app_schema(bp)
        app_dir = generate_app(bp)
        heal_ok, heal_attempts = await heal(app_dir)

        deployment = None
        url = f"{settings.public_base_url}/generated/{bp.slug}"
        try:
            deployment = deploy(app_dir, bp.slug, database_url=settings.database_url)
            url = deployment.get("url", url)
        except Exception as exc:  # deployment is best-effort; codegen is the deliverable
            deployment = {"backend": "error", "error": str(exc)}

        status = "ready" if heal_ok else "degraded"
        set_app_status(
            bp.slug,
            status,
            last_error=None if heal_ok else "typecheck not clean after self-heal",
            container_id=deployment.get("container_id") if deployment else None,
        )
        return GenerationResult(
            blueprint=bp,
            app_dir=app_dir,
            schema=schema,
            heal_ok=heal_ok,
            heal_attempts=heal_attempts,
            deployment=deployment,
            url=url,
        )
    except Exception as exc:
        set_app_status(bp.slug, "failed", last_error=f"{exc}\n{traceback.format_exc()}")
        raise
