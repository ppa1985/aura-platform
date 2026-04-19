"""End-to-end pipeline: prompt → Blueprint → schema → code → heal → deploy."""

from __future__ import annotations

import logging
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from .blueprint import Blueprint
from .codegen import generate_app
from .config import settings
from .crypto import decrypt
from .db import (
    create_app_schema,
    get_git_account,
    get_user,
    set_app_status,
    upsert_app,
)
from .deploy import deploy
from .engine import blueprint_from_prompt
from .git_push import push_app_to_workspace
from .selfheal import heal

log = logging.getLogger("aura.pipeline")


@dataclass
class GenerationResult:
    blueprint: Blueprint
    app_dir: Path
    schema: str
    heal_ok: bool
    heal_attempts: list[dict] = field(default_factory=list)
    deployment: dict | None = None
    url: str | None = None
    git_pushed_url: str | None = None
    git_push_error: str | None = None
    error: str | None = None


async def generate_from_prompt(
    prompt: str, *, use_llm: bool = True, user_id: int | None = None
) -> GenerationResult:
    bp = await blueprint_from_prompt(prompt, use_llm=use_llm)
    return await generate_from_blueprint(bp, user_id=user_id)


async def generate_from_blueprint(bp: Blueprint, *, user_id: int | None = None) -> GenerationResult:
    bp.ensure_default_pages()
    upsert_app(bp, status="generating", user_id=user_id)
    try:
        schema = create_app_schema(bp)
        app_dir = generate_app(bp)
        heal_ok, heal_attempts = await heal(app_dir)

        deployment = None
        url = f"{settings.public_base_url}/generated/{bp.slug}"
        try:
            # Strip SQLAlchemy dialect prefix: the generated Node.js container
            # uses `pg` (node-postgres), which only accepts `postgres://` or
            # `postgresql://` URLs — not `postgresql+psycopg://`.
            db_url = settings.database_url.replace(
                "postgresql+psycopg://", "postgresql://"
            )
            deployment = deploy(app_dir, bp.slug, database_url=db_url)
            url = deployment.get("url", url)
        except Exception as exc:  # deployment is best-effort; codegen is the deliverable
            deployment = {"backend": "error", "error": str(exc)}

        # Optional: push to the user's linked git workspace.
        git_pushed_url: str | None = None
        git_push_error: str | None = None
        if user_id is not None:
            git_pushed_url, git_push_error = _maybe_push_to_git(user_id, bp.slug, app_dir)

        status = "ready" if heal_ok else "degraded"
        set_app_status(
            bp.slug,
            status,
            last_error=None if heal_ok else "typecheck not clean after self-heal",
            container_id=deployment.get("container_id") if deployment else None,
            git_pushed_url=git_pushed_url,
        )
        return GenerationResult(
            blueprint=bp,
            app_dir=app_dir,
            schema=schema,
            heal_ok=heal_ok,
            heal_attempts=heal_attempts,
            deployment=deployment,
            url=url,
            git_pushed_url=git_pushed_url,
            git_push_error=git_push_error,
        )
    except Exception as exc:
        set_app_status(bp.slug, "failed", last_error=f"{exc}\n{traceback.format_exc()}")
        raise


def _maybe_push_to_git(user_id: int, slug: str, app_dir: Path) -> tuple[str | None, str | None]:
    try:
        acct = get_git_account(user_id)
    except Exception as exc:
        log.warning("git account lookup failed: %s", exc)
        return None, f"git account lookup failed: {exc}"
    if not acct:
        return None, None
    try:
        user = get_user(user_id) or {}
        token = decrypt(acct["token_enc"])
        return push_app_to_workspace(
            app_dir,
            slug=slug,
            provider=acct["provider"],
            token=token,
            workspace_repo=acct["workspace_repo"],
            user_email=user.get("email", "aura@aura.local"),
        ), None
    except Exception as exc:
        log.exception("git push failed for %s: %s", slug, exc)
        return None, str(exc)
