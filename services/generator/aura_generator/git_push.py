"""Push generated apps to a user-linked git workspace repo as `apps/<slug>/`."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import httpx

log = logging.getLogger("aura.git")

_CRED_IN_URL = re.compile(r"(https?://)[^/@\s]+@")


def _redact(s: str) -> str:
    """Mask any `user:token@` credential embedded in a URL before logging."""
    return _CRED_IN_URL.sub(r"\1***@", s)

USER_AGENT = "aura-platform/0.1"


def verify_token(provider: str, token: str) -> dict:
    """Call the provider's 'who am I' API to confirm the PAT works.

    Returns {"username": str} on success; raises ValueError on failure.
    """
    if provider == "github":
        r = httpx.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": USER_AGENT,
            },
            timeout=15,
        )
        if r.status_code != 200:
            raise ValueError(f"GitHub token rejected ({r.status_code}): {r.text[:200]}")
        return {"username": r.json().get("login", "")}
    if provider == "gitlab":
        r = httpx.get(
            "https://gitlab.com/api/v4/user",
            headers={"PRIVATE-TOKEN": token, "User-Agent": USER_AGENT},
            timeout=15,
        )
        if r.status_code != 200:
            raise ValueError(f"GitLab token rejected ({r.status_code}): {r.text[:200]}")
        return {"username": r.json().get("username", "")}
    raise ValueError(f"unsupported provider: {provider}")


def _remote_url(provider: str, token: str, workspace_repo: str) -> str:
    if provider == "github":
        # Use x-access-token convention; any non-empty username with token is fine.
        return f"https://x-access-token:{token}@github.com/{workspace_repo}.git"
    if provider == "gitlab":
        return f"https://oauth2:{token}@gitlab.com/{workspace_repo}.git"
    raise ValueError(f"unsupported provider: {provider}")


def _run(cmd: list[str], cwd: Path, env: dict | None = None) -> None:
    safe_cmd = [_redact(c) for c in cmd]
    log.info("git exec: %s (cwd=%s)", " ".join(safe_cmd), cwd)
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = _redact(result.stderr.strip() or result.stdout.strip())
        raise RuntimeError(f"git command failed ({safe_cmd[:2]}): {stderr}")


def push_app_to_workspace(
    app_dir: Path,
    *,
    slug: str,
    provider: str,
    token: str,
    workspace_repo: str,
    user_email: str,
    commit_message: str | None = None,
) -> str:
    """Clone `workspace_repo`, overlay the generated app under `apps/<slug>/`, push.

    Returns the resulting remote URL (without the token).
    """
    url_with_token = _remote_url(provider, token, workspace_repo)
    public_url = (
        f"https://github.com/{workspace_repo}"
        if provider == "github"
        else f"https://gitlab.com/{workspace_repo}"
    )
    msg = commit_message or f"aura: generate {slug}"

    with tempfile.TemporaryDirectory(prefix="aura-push-") as tmp:
        workdir = Path(tmp) / "repo"
        env = {
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_AUTHOR_NAME": "Aura Bot",
            "GIT_AUTHOR_EMAIL": user_email,
            "GIT_COMMITTER_NAME": "Aura Bot",
            "GIT_COMMITTER_EMAIL": user_email,
            "PATH": "/usr/bin:/bin:/usr/local/bin",
        }

        # Try to clone. If it's empty (no default branch yet), init instead.
        clone = subprocess.run(
            ["git", "clone", "--depth", "1", url_with_token, str(workdir)],
            capture_output=True, text=True, env=env,
        )
        created_empty = False
        if clone.returncode != 0:
            log.warning("clone failed, initializing new repo: %s", _redact(clone.stderr.strip()))
            workdir.mkdir(parents=True, exist_ok=True)
            _run(["git", "init", "-b", "main"], workdir, env)
            _run(["git", "remote", "add", "origin", url_with_token], workdir, env)
            created_empty = True

        # Overlay app under apps/<slug>/ (replace if already there).
        target = workdir / "apps" / slug
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(app_dir, target, ignore=shutil.ignore_patterns("node_modules", ".next"))

        # README on first push.
        readme = workdir / "README.md"
        if not readme.exists():
            readme.write_text(
                f"# {workspace_repo.split('/')[-1]}\n\n"
                "Aura-generated application workspace. Each subdirectory under `apps/` is a\n"
                "separate app produced by the Aura platform from a natural-language prompt.\n"
            )

        _run(["git", "add", "-A"], workdir, env)
        # Nothing to commit? still push (e.g. the commit came from a prior run).
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=workdir, env=env, capture_output=True, text=True
        )
        if status.stdout.strip():
            _run(["git", "commit", "-m", msg], workdir, env)

        if created_empty:
            _run(["git", "push", "-u", "origin", "main"], workdir, env)
        else:
            _run(["git", "push", "origin", "HEAD"], workdir, env)

    return public_url
