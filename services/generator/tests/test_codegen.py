from pathlib import Path

import pytest

from aura_generator.codegen import generate_app
from aura_generator.engine import blueprint_from_prompt


@pytest.mark.asyncio
async def test_codegen_wms_writes_complete_nextjs_app(tmp_path: Path):
    bp = await blueprint_from_prompt(
        "Warehouse Management System with products and warehouses.", use_llm=False
    )
    out = generate_app(bp, root=tmp_path)

    # Project-level files
    assert (out / "package.json").exists()
    assert (out / "tsconfig.json").exists()
    assert (out / "next.config.ts").exists()
    assert (out / "Dockerfile").exists()
    assert (out / "aura.blueprint.json").exists()

    # App shell
    assert (out / "src/app/layout.tsx").exists()
    assert (out / "src/app/page.tsx").exists()
    assert (out / "src/lib/db.ts").exists()
    assert (out / "src/components/nav.tsx").exists()

    # Per-entity pages + API routes for at least one entity
    entity_slugs = [p.name for p in (out / "src/app").iterdir() if p.is_dir() and p.name != "api"]
    assert len(entity_slugs) >= 2
    sample = entity_slugs[0]
    assert (out / "src/app" / sample / "page.tsx").exists()
    assert (out / "src/app" / sample / "new/page.tsx").exists()
    assert (out / "src/app" / sample / "[id]/page.tsx").exists()
    assert (out / "src/app/api" / sample / "route.ts").exists()
    assert (out / "src/app/api" / sample / "[id]/route.ts").exists()

    # Files are non-empty
    for p in out.rglob("*.ts*"):
        assert p.stat().st_size > 0, p

    # Project documentation is emitted alongside the code.
    for doc in ("BRD", "SAD", "API", "SETUP", "DEVELOPER"):
        path = out / "docs" / f"{doc}.md"
        assert path.exists(), path
        assert path.stat().st_size > 0
    brd = (out / "docs/BRD.md").read_text()
    api = (out / "docs/API.md").read_text()
    # BRD names the Blueprint and lists every entity.
    assert bp.name in brd
    for e in bp.entities:
        assert e.name in brd
    # API doc enumerates CRUD endpoints for every entity.
    for e in bp.entities:
        assert f"/api/{e.name[:1].lower() + e.name[1:]}" in api or e.name in api
