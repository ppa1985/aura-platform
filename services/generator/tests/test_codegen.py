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
