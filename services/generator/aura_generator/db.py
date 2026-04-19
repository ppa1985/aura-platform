"""Database utilities: registry tables and Dynamic Schema Generator."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Engine,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.engine import Connection

from .blueprint import Blueprint, Entity, EntityField
from .config import settings

_engine: Engine | None = None

_registry_meta = MetaData(schema="aura")

apps_table = Table(
    "apps",
    _registry_meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("slug", String(120), unique=True, nullable=False),
    Column("name", String(200), nullable=False),
    Column("description", Text),
    Column("blueprint_json", Text, nullable=False),
    Column("status", String(40), nullable=False, default="pending"),
    Column("container_id", String(80)),
    Column("url_path", String(200)),
    Column("last_error", Text),
    Column("created_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    Column("updated_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    Column("ai_enabled", Boolean, default=False),
)


def engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
    return _engine


def init_registry() -> None:
    with engine().begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS aura"))
        _registry_meta.create_all(conn)


# ---------------------------------------------------------------------------
# Dynamic Schema Generator
# ---------------------------------------------------------------------------

_TYPE_SQL = {
    "string": "VARCHAR(255)",
    "text": "TEXT",
    "integer": "INTEGER",
    "float": "DOUBLE PRECISION",
    "decimal": "NUMERIC(18,4)",
    "boolean": "BOOLEAN",
    "date": "DATE",
    "datetime": "TIMESTAMPTZ",
    "uuid": "UUID",
    "json": "JSONB",
}


def _schema_name(slug: str) -> str:
    return "app_" + slug.replace("-", "_")


def _table_for(entity: Entity) -> str:
    import re as _re

    snake = _re.sub(r"(?<!^)(?=[A-Z])", "_", entity.name).lower()
    return snake + "s"


def create_app_schema(bp: Blueprint) -> str:
    """Create a dedicated schema and tables for the app. Idempotent."""
    schema = _schema_name(bp.slug)
    statements: list[str] = [f'CREATE SCHEMA IF NOT EXISTS "{schema}"']
    # Entity tables
    for entity in bp.entities:
        cols = [
            "id BIGSERIAL PRIMARY KEY",
            "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
            "updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
        ]
        for f in entity.fields:
            cols.append(_col_sql(f))
        for rel in entity.relations:
            if rel.kind == "many_to_one":
                cols.append(_rel_col_sql(rel))
        table = _table_for(entity)
        cols_sql = ",\n  ".join(cols)
        statements.append(f'CREATE TABLE IF NOT EXISTS "{schema}"."{table}" (\n  {cols_sql}\n)')
    with engine().begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
        _add_fks(conn, bp, schema)
    return schema


def _col_sql(f: EntityField) -> str:
    sql_type = _TYPE_SQL.get(f.type, "VARCHAR(255)")
    parts = [f'"{f.name}" {sql_type}']
    if f.required:
        parts.append("NOT NULL")
    if f.unique:
        parts.append("UNIQUE")
    return " ".join(parts)


def _rel_col_sql(rel) -> str:  # type: ignore[no-untyped-def]
    col = f"{rel.name}_id"
    not_null = " NOT NULL" if rel.required else ""
    return f'"{col}" BIGINT{not_null}'


def _add_fks(conn: Connection, bp: Blueprint, schema: str) -> None:
    import re as _re

    by_name = {e.name: e for e in bp.entities}
    for entity in bp.entities:
        table = _table_for(entity)
        for rel in entity.relations:
            if rel.kind != "many_to_one":
                continue
            target = by_name.get(rel.target)
            if not target:
                continue
            target_table = _re.sub(r"(?<!^)(?=[A-Z])", "_", target.name).lower() + "s"
            constraint = f"fk_{table}_{rel.name}"
            col = f"{rel.name}_id"
            # Add FK if it doesn't already exist.
            exists = conn.execute(
                text(
                    """
                    SELECT 1 FROM information_schema.table_constraints
                    WHERE table_schema = :s AND table_name = :t AND constraint_name = :c
                    """
                ),
                {"s": schema, "t": table, "c": constraint},
            ).first()
            if exists:
                continue
            conn.execute(
                text(
                    f'ALTER TABLE "{schema}"."{table}" '
                    f'ADD CONSTRAINT "{constraint}" '
                    f'FOREIGN KEY ("{col}") REFERENCES "{schema}"."{target_table}"(id)'
                )
            )


def drop_app_schema(slug: str) -> None:
    schema = _schema_name(slug)
    with engine().begin() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))


# ---------------------------------------------------------------------------
# Registry CRUD
# ---------------------------------------------------------------------------


def upsert_app(bp: Blueprint, *, status: str = "pending", url_path: str | None = None) -> None:
    now = datetime.now(timezone.utc)
    with engine().begin() as conn:
        existing = conn.execute(select(apps_table.c.id).where(apps_table.c.slug == bp.slug)).first()
        payload = {
            "slug": bp.slug,
            "name": bp.name,
            "description": bp.description,
            "blueprint_json": bp.model_dump_json(),
            "status": status,
            "url_path": url_path or f"/generated/{bp.slug}",
            "ai_enabled": bp.ai_enabled,
            "updated_at": now,
        }
        if existing:
            conn.execute(update(apps_table).where(apps_table.c.slug == bp.slug).values(**payload))
        else:
            conn.execute(insert(apps_table).values(created_at=now, **payload))


def set_app_status(slug: str, status: str, *, last_error: str | None = None, container_id: str | None = None) -> None:
    with engine().begin() as conn:
        values: dict[str, object] = {"status": status, "updated_at": datetime.now(timezone.utc)}
        if last_error is not None:
            values["last_error"] = last_error
        if container_id is not None:
            values["container_id"] = container_id
        conn.execute(update(apps_table).where(apps_table.c.slug == slug).values(**values))


def list_apps() -> list[dict]:
    with engine().begin() as conn:
        rows = conn.execute(select(apps_table).order_by(apps_table.c.created_at.desc())).mappings().all()
    return [dict(r) for r in rows]


def get_app(slug: str) -> dict | None:
    with engine().begin() as conn:
        row = conn.execute(select(apps_table).where(apps_table.c.slug == slug)).mappings().first()
    if not row:
        return None
    d = dict(row)
    try:
        d["blueprint"] = json.loads(d["blueprint_json"])
    except Exception:
        d["blueprint"] = None
    return d


def delete_app(slug: str) -> None:
    with engine().begin() as conn:
        conn.execute(apps_table.delete().where(apps_table.c.slug == slug))
