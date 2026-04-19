"""FastAPI entrypoint for the Aura generator service."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from email_validator import EmailNotValidError, validate_email
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .auth import (
    SESSION_COOKIE,
    current_user,
    generate_verification_code,
    hash_password,
    issue_token,
    verify_password,
)
from .blueprint import Blueprint
from .config import settings
from .crypto import encrypt
from .db import (
    SlugTakenError,
    consume_verification,
    create_user,
    create_verification,
    delete_app,
    delete_git_account,
    drop_app_schema,
    get_app,
    get_git_account,
    get_user,
    get_user_by_email,
    init_registry,
    list_apps,
    mark_user_verified,
    upsert_git_account,
)
from .deploy import stop as stop_deployment
from .email_sender import send_verification_code
from .engine import blueprint_from_prompt
from .git_push import verify_token
from .llm import active_model, health as llm_health
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
    allow_credentials=True,
)


# ---------- models ----------


class PromptIn(BaseModel):
    prompt: str
    use_llm: bool = True


class GenerateIn(BaseModel):
    prompt: str | None = None
    blueprint: Blueprint | None = None
    use_llm: bool = True


class SignupIn(BaseModel):
    email: str
    password: str


class VerifyIn(BaseModel):
    email: str
    code: str


class LoginIn(BaseModel):
    email: str
    password: str


class ResendIn(BaseModel):
    email: str


class GitAccountIn(BaseModel):
    provider: str  # "github" | "gitlab"
    token: str
    workspace_repo: str  # "owner/repo"


# ---------- routes ----------


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "llm_reachable": await llm_health(),
        "mode": settings.aura_mode,
        "model": active_model(),
    }


# ---------- auth ----------


def _normalize_email(raw: str) -> str:
    try:
        info = validate_email(raw, check_deliverability=False)
        return info.normalized.lower()
    except EmailNotValidError as exc:
        raise HTTPException(400, f"invalid email: {exc}") from exc


def _set_session_cookie(resp: Response, token: str) -> None:
    resp.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=False,  # local dev; flip to True behind TLS
        max_age=settings.jwt_expire_hours * 3600,
        path="/",
    )


@app.post("/auth/signup")
async def auth_signup(body: SignupIn) -> dict:
    email = _normalize_email(body.email)
    if len(body.password) < 8:
        raise HTTPException(400, "password must be at least 8 characters")
    try:
        user = create_user(email, hash_password(body.password))
    except ValueError:
        raise HTTPException(409, "email already registered") from None
    code = generate_verification_code()
    create_verification(user["id"], code)
    send_verification_code(email, code)
    return {"email": email, "verified": False, "message": "verification code sent"}


@app.post("/auth/verify")
async def auth_verify(body: VerifyIn, response: Response) -> dict:
    email = _normalize_email(body.email)
    u = get_user_by_email(email)
    if not u:
        raise HTTPException(404, "user not found")
    if u["verified"]:
        # idempotent
        token = issue_token(u["id"], u["email"])
        _set_session_cookie(response, token)
        return {"email": email, "verified": True}
    if not consume_verification(u["id"], body.code):
        raise HTTPException(400, "invalid or expired code")
    mark_user_verified(u["id"])
    token = issue_token(u["id"], u["email"])
    _set_session_cookie(response, token)
    return {"email": email, "verified": True}


@app.post("/auth/resend")
async def auth_resend(body: ResendIn) -> dict:
    email = _normalize_email(body.email)
    u = get_user_by_email(email)
    if not u:
        raise HTTPException(404, "user not found")
    if u["verified"]:
        return {"email": email, "verified": True, "message": "already verified"}
    code = generate_verification_code()
    create_verification(u["id"], code)
    send_verification_code(email, code)
    return {"email": email, "verified": False, "message": "verification code resent"}


@app.post("/auth/login")
async def auth_login(body: LoginIn, response: Response) -> dict:
    email = _normalize_email(body.email)
    u = get_user_by_email(email)
    if not u or not verify_password(body.password, u["password_hash"]):
        raise HTTPException(401, "invalid email or password")
    if not u["verified"]:
        raise HTTPException(403, "email not verified")
    token = issue_token(u["id"], u["email"])
    _set_session_cookie(response, token)
    return {"email": email, "verified": True}


@app.post("/auth/logout")
async def auth_logout(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@app.get("/auth/me")
async def auth_me(user: dict = Depends(current_user)) -> dict:
    u = get_user(user["id"]) or {}
    acct = get_git_account(user["id"])
    return {
        "id": user["id"],
        "email": user["email"],
        "verified": bool(u.get("verified")),
        "git_account": (
            {
                "provider": acct["provider"],
                "username": acct["username"],
                "workspace_repo": acct["workspace_repo"],
            }
            if acct
            else None
        ),
    }


# ---------- git accounts ----------


@app.post("/git-accounts")
async def link_git_account(body: GitAccountIn, user: dict = Depends(current_user)) -> dict:
    if body.provider not in ("github", "gitlab"):
        raise HTTPException(400, "provider must be 'github' or 'gitlab'")
    if "/" not in body.workspace_repo:
        raise HTTPException(400, "workspace_repo must look like 'owner/repo'")
    try:
        info = verify_token(body.provider, body.token)
    except Exception as exc:
        raise HTTPException(400, f"token verification failed: {exc}") from exc
    upsert_git_account(
        user["id"],
        body.provider,
        info.get("username") or "",
        body.workspace_repo,
        encrypt(body.token),
    )
    return {
        "provider": body.provider,
        "username": info.get("username"),
        "workspace_repo": body.workspace_repo,
    }


@app.get("/git-accounts/me")
async def get_my_git_account(user: dict = Depends(current_user)) -> dict | None:
    acct = get_git_account(user["id"])
    if not acct:
        return None
    return {
        "provider": acct["provider"],
        "username": acct["username"],
        "workspace_repo": acct["workspace_repo"],
    }


@app.delete("/git-accounts/me")
async def delete_my_git_account(user: dict = Depends(current_user)) -> dict:
    delete_git_account(user["id"])
    return {"ok": True}


# ---------- blueprints / apps ----------


@app.post("/blueprints")
async def create_blueprint(body: PromptIn, _: dict = Depends(current_user)) -> Blueprint:
    return await blueprint_from_prompt(body.prompt, use_llm=body.use_llm)


@app.post("/apps")
async def create_app_route(body: GenerateIn, user: dict = Depends(current_user)) -> dict[str, Any]:
    if not body.prompt and not body.blueprint:
        raise HTTPException(400, "Provide either `prompt` or `blueprint`.")
    try:
        result = (
            await generate_from_blueprint(body.blueprint, user_id=user["id"])
            if body.blueprint
            else await generate_from_prompt(
                body.prompt or "", use_llm=body.use_llm, user_id=user["id"]
            )
        )
    except SlugTakenError as exc:
        raise HTTPException(
            409,
            f"The app name '{exc.slug}' is already taken by another user. "
            "Please choose a different name.",
        ) from exc
    return {
        "slug": result.blueprint.slug,
        "name": result.blueprint.name,
        "url": result.url,
        "schema": result.schema,
        "heal_ok": result.heal_ok,
        "heal_attempts": result.heal_attempts,
        "deployment": result.deployment,
        "git_pushed_url": result.git_pushed_url,
        "git_push_error": result.git_push_error,
        "blueprint": result.blueprint.model_dump(),
    }


@app.get("/apps")
async def get_apps(user: dict = Depends(current_user)) -> list[dict]:
    return list_apps(user_id=user["id"])


@app.get("/apps/{slug}")
async def get_single_app(slug: str, user: dict = Depends(current_user)) -> dict:
    a = get_app(slug, user_id=user["id"])
    if not a:
        raise HTTPException(404, "app not found")
    return a


@app.delete("/apps/{slug}")
async def delete_single_app(slug: str, user: dict = Depends(current_user)) -> dict:
    existing = get_app(slug, user_id=user["id"])
    if not existing:
        raise HTTPException(404, "app not found")
    try:
        stop_deployment(slug)
    except Exception:
        log.warning("stop_deployment failed for %s", slug, exc_info=True)
    try:
        drop_app_schema(slug)
    except Exception:
        log.warning("drop_app_schema failed for %s", slug, exc_info=True)
    delete_app(slug, user_id=user["id"])
    return {"ok": True}
