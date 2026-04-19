"""Component Assembler + Auto-Coder.

Given a Blueprint, emit a self-contained Next.js 15 (App Router) app into
`generated/<slug>/` using Jinja templates and a small Shadcn-based component
library. Deterministic: same Blueprint → same files. The Self-Healing loop
can optionally ask the LLM to patch a single file.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .blueprint import Blueprint, Entity, EntityField
from .config import settings


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _kebab(name: str) -> str:
    return _snake(name).replace("_", "-")


def _plural(name: str) -> str:
    # Simple pluralizer: matches how the DB layer names tables.
    return _snake(name) + "s"


def _ts_type(field: EntityField) -> str:
    return {
        "string": "string",
        "text": "string",
        "integer": "number",
        "float": "number",
        "decimal": "number",
        "boolean": "boolean",
        "date": "string",
        "datetime": "string",
        "uuid": "string",
        "json": "any",
    }.get(field.type, "string")


def _zod_type(field: EntityField) -> str:
    base = {
        "string": "z.string()",
        "text": "z.string()",
        "integer": "z.coerce.number().int()",
        "float": "z.coerce.number()",
        "decimal": "z.coerce.number()",
        "boolean": "z.coerce.boolean()",
        "date": "z.string()",
        "datetime": "z.string()",
        "uuid": "z.string().uuid()",
        "json": "z.any()",
    }.get(field.type, "z.string()")
    return base if field.required else f"{base}.optional().nullable()"


def _jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(settings.templates_dir / "nextjs"),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )


def generate_app(bp: Blueprint, root: Path | None = None) -> Path:
    """Write a Next.js app into `generated/<slug>/`. Returns the path."""
    out = (root or settings.generated_dir) / bp.slug
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    env = _jinja_env()
    ctx = _ctx(bp)

    # Static / universal files.
    _render(env, "package.json.j2", out / "package.json", ctx)
    _render(env, "tsconfig.json.j2", out / "tsconfig.json", ctx)
    _render(env, "next.config.ts.j2", out / "next.config.ts", ctx)
    _render(env, "postcss.config.mjs.j2", out / "postcss.config.mjs", ctx)
    _render(env, "tailwind.config.ts.j2", out / "tailwind.config.ts", ctx)
    _render(env, "Dockerfile.j2", out / "Dockerfile", ctx)
    _render(env, ".dockerignore.j2", out / ".dockerignore", ctx)
    _render(env, "README.md.j2", out / "README.md", ctx)
    _render(env, "aura.blueprint.json.j2", out / "aura.blueprint.json", ctx)

    (out / "src").mkdir(exist_ok=True)
    (out / "src/app").mkdir(exist_ok=True)
    (out / "src/app/api").mkdir(exist_ok=True)
    (out / "src/components").mkdir(exist_ok=True)
    (out / "src/components/ui").mkdir(exist_ok=True)
    (out / "src/lib").mkdir(exist_ok=True)

    _render(env, "src/app/layout.tsx.j2", out / "src/app/layout.tsx", ctx)
    _render(env, "src/app/globals.css.j2", out / "src/app/globals.css", ctx)
    _render(env, "src/app/page.tsx.j2", out / "src/app/page.tsx", ctx)
    _render(env, "src/lib/db.ts.j2", out / "src/lib/db.ts", ctx)
    _render(env, "src/lib/utils.ts.j2", out / "src/lib/utils.ts", ctx)
    _render(env, "src/lib/ai.ts.j2", out / "src/lib/ai.ts", ctx)

    # Shadcn-ish UI primitives (copied, not installed, so builds don't need npm net access).
    for name in ("button", "card", "input", "table", "label", "badge"):
        _render(env, f"src/components/ui/{name}.tsx.j2", out / f"src/components/ui/{name}.tsx", ctx)
    _render(env, "src/components/nav.tsx.j2", out / "src/components/nav.tsx", ctx)

    # Per-entity CRUD pages + API routes.
    for entity in bp.entities:
        ectx = {**ctx, "entity": _entity_ctx(entity, bp)}
        e_slug = _kebab(entity.name)

        page_dir = out / f"src/app/{e_slug}"
        page_dir.mkdir(parents=True, exist_ok=True)
        _render(env, "src/app/_entity/page.tsx.j2", page_dir / "page.tsx", ectx)
        (page_dir / "new").mkdir(exist_ok=True)
        _render(env, "src/app/_entity/new/page.tsx.j2", page_dir / "new/page.tsx", ectx)
        (page_dir / "[id]").mkdir(exist_ok=True)
        _render(env, "src/app/_entity/[id]/page.tsx.j2", page_dir / "[id]/page.tsx", ectx)

        api_dir = out / f"src/app/api/{e_slug}"
        api_dir.mkdir(parents=True, exist_ok=True)
        _render(env, "src/app/api/_entity/route.ts.j2", api_dir / "route.ts", ectx)
        (api_dir / "[id]").mkdir(exist_ok=True)
        _render(env, "src/app/api/_entity/[id]/route.ts.j2", api_dir / "[id]/route.ts", ectx)

    # AI route if enabled.
    if bp.ai_enabled:
        ai_dir = out / "src/app/api/ai"
        ai_dir.mkdir(parents=True, exist_ok=True)
        _render(env, "src/app/api/ai/route.ts.j2", ai_dir / "route.ts", ctx)

    return out


def _render(env: Environment, template: str, target: Path, ctx: dict) -> None:
    tpl = env.get_template(template)
    content = tpl.render(**ctx)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)


def _entity_ctx(entity: Entity, bp: Blueprint) -> dict:
    fields = [
        {
            "name": f.name,
            "type": f.type,
            "ts_type": _ts_type(f),
            "zod": _zod_type(f),
            "required": f.required,
            "unique": f.unique,
            "is_textarea": f.type == "text",
            "is_bool": f.type == "boolean",
        }
        for f in entity.fields
    ]
    relations = [
        {
            "name": r.name,
            "target": r.target,
            "target_slug": _kebab(r.target),
            "target_table": _plural(r.target),
            "column": f"{r.name}_id",
            "required": r.required,
        }
        for r in entity.relations
        if r.kind == "many_to_one"
    ]
    return {
        "name": entity.name,
        "slug": _kebab(entity.name),
        "table": _plural(entity.name),
        "snake": _snake(entity.name),
        "fields": fields,
        "relations": relations,
    }


def _ctx(bp: Blueprint) -> dict:
    entities = [_entity_ctx(e, bp) for e in bp.entities]
    nav = [{"name": "Dashboard", "href": "/"}]
    for ec in entities:
        nav.append({"name": ec["name"] + "s", "href": f"/{ec['slug']}"})
    return {
        "bp": {
            "name": bp.name,
            "slug": bp.slug,
            "description": bp.description,
            "ai_enabled": bp.ai_enabled,
        },
        "entities": entities,
        "nav": nav,
        "schema_name": "app_" + bp.slug.replace("-", "_"),
        "blueprint_json": json.dumps(bp.model_dump(), indent=2),
    }
