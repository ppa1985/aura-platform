import pytest

from aura_generator.engine import blueprint_from_prompt


@pytest.mark.asyncio
async def test_heuristic_wms():
    bp = await blueprint_from_prompt(
        "Build me a Warehouse Management System with products, warehouses, "
        "inventory levels, and inbound/outbound shipments.",
        use_llm=False,
    )
    names = {e.name for e in bp.entities}
    assert "Warehouse" in names and "Product" in names and "InventoryLevel" in names
    assert bp.slug
    assert bp.pages, "default pages should be populated"


@pytest.mark.asyncio
async def test_heuristic_trade_assistant_enables_ai():
    bp = await blueprint_from_prompt(
        "Build me a Trade Assistant with real-time news analysis.",
        use_llm=False,
    )
    assert bp.ai_enabled is True
    assert {e.name for e in bp.entities} >= {"Trade", "NewsItem"}


@pytest.mark.asyncio
async def test_heuristic_default_when_no_keywords():
    bp = await blueprint_from_prompt("something unclassified", use_llm=False)
    assert bp.entities, "should still produce at least one entity"
