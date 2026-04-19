from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://aura:aura@localhost:5432/aura"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"

    generated_dir: Path = Path("/workspace/generated")
    templates_dir: Path = Path(__file__).parent / "templates"
    ui_package_dir: Path = Path("/app/packages/ui")

    # "docker" builds real per-app containers; "inprocess" only writes files (for CI/tests).
    aura_mode: str = "inprocess"

    # Reverse-proxy base where generated apps are reachable.
    public_base_url: str = "http://aura.local"

    # Self-healing
    self_heal_max_attempts: int = 3
    self_heal_timeout_seconds: int = 180

    # Auth
    jwt_secret: str = "dev-not-a-real-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24 * 7
    # 32-byte urlsafe base64 Fernet key; override in production via env.
    encryption_key: str = "dev-insecure-fernet-key-change-change-change="

    # Email backend: "console" (log codes) or "smtp" (future).
    email_backend: str = "console"
    email_from: str = "Aura <no-reply@aura.local>"


settings = Settings()  # type: ignore[call-arg]
