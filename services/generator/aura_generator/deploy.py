"""Deployment Sandbox.

Two backends:
  * `inprocess` — just writes files; no container work. Used by CI/tests.
  * `docker`    — builds a Docker image from the generated app, starts a
                  container on the `aura` network with Traefik labels routing
                  `/generated/<slug>` to it, and returns the container id.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .config import settings


def image_name(slug: str) -> str:
    return f"aura-generated-{slug}:latest"


def container_name(slug: str) -> str:
    return f"aura-app-{slug}"


def _run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=check,
        text=True,
        capture_output=True,
    )


def is_docker_available() -> bool:
    try:
        _run(["docker", "version"], check=False)
        return True
    except FileNotFoundError:
        return False


def deploy(app_dir: Path, slug: str, *, database_url: str) -> dict:
    if settings.aura_mode != "docker" or not is_docker_available():
        return {
            "backend": "inprocess",
            "url": f"{settings.public_base_url}/generated/{slug}",
            "note": "Files written; docker deployment skipped.",
        }

    img = image_name(slug)
    name = container_name(slug)

    # Build
    _run(["docker", "build", "-t", img, "."], cwd=app_dir)

    # Remove any previous container
    _run(["docker", "rm", "-f", name], check=False)

    labels = [
        "--label",
        "traefik.enable=true",
        "--label",
        f"traefik.http.routers.{name}.rule=PathPrefix(`/generated/{slug}`)",
        "--label",
        f"traefik.http.routers.{name}.priority=10",
        "--label",
        f"traefik.http.services.{name}.loadbalancer.server.port=3000",
    ]

    proc = _run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "--network",
            "aura",
            "-e",
            f"DATABASE_URL={database_url}",
            "-e",
            f"AURA_BASE_PATH=/generated/{slug}",
            *labels,
            img,
        ]
    )
    container_id = proc.stdout.strip()
    return {
        "backend": "docker",
        "image": img,
        "container_id": container_id,
        "url": f"{settings.public_base_url}/generated/{slug}",
    }


def stop(slug: str) -> None:
    _run(["docker", "rm", "-f", container_name(slug)], check=False)
