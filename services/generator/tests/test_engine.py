from unittest.mock import AsyncMock, patch

import pytest

from aura_generator.engine import _coerce, blueprint_from_prompt


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


def test_coerce_normalizes_unknown_field_types():
    """Real LLMs (e.g. llama3.1) emit SQL-ish field types like 'reference',
    'varchar', 'timestamp'. _coerce must map them onto the closed FieldType
    Literal before Pydantic validation, not 500."""
    bp = _coerce(
        {
            "name": "Sample",
            "entities": [
                {
                    "name": "Item",
                    "fields": [
                        {"name": "warehouse_id", "type": "reference"},
                        {"name": "sku", "type": "varchar"},
                        {"name": "stock", "type": "bigint"},
                        {"name": "price", "type": "money"},
                        {"name": "active", "type": "bool"},
                        {"name": "meta", "type": "jsonb"},
                        {"name": "created", "type": "timestamp"},
                        {"name": "tags", "type": "array"},
                        {"name": "made_up", "type": "fizzbuzz"},
                    ],
                }
            ],
        },
        fallback_name="Sample",
    )
    types = {f.name: f.type for f in bp.entities[0].fields}
    assert types == {
        "warehouse_id": "uuid",
        "sku": "string",
        "stock": "integer",
        "price": "decimal",
        "active": "boolean",
        "meta": "json",
        "created": "datetime",
        "tags": "json",
        "made_up": "string",
    }


def test_coerce_remaps_unknown_ai_provider():
    """llama3.1 was observed hallucinating ai_config.provider='googlecloud'.
    Force unknown providers to 'ollama' rather than letting Pydantic blow up."""
    bp = _coerce(
        {
            "name": "Sample",
            "entities": [{"name": "Item", "fields": [{"name": "x", "type": "string"}]}],
            "ai_enabled": True,
            "ai_config": {"provider": "googlecloud", "model": "gemini-pro"},
        },
        fallback_name="Sample",
    )
    assert bp.ai_config is not None
    assert bp.ai_config.provider == "ollama"
    assert bp.ai_config.model == "gemini-pro"


@pytest.mark.asyncio
async def test_llm_validation_error_falls_back_to_heuristic():
    """If the LLM returns JSON that _coerce cannot rescue (e.g. ai_config is
    not an object), the endpoint must fall back to the heuristic path rather
    than surfacing ValidationError as a 500."""
    # ai_config set to a non-dict, non-None value that _coerce leaves alone and
    # that Blueprint(...) then rejects in Pydantic validation.
    unrescuable = {
        "name": "Bad",
        "entities": [{"name": "X", "fields": [{"name": "x", "type": "string"}]}],
        "ai_enabled": True,
        "ai_config": 5,
    }
    with patch(
        "aura_generator.engine.generate_json",
        new=AsyncMock(return_value=unrescuable),
    ):
        bp = await blueprint_from_prompt(
            "Build me a Warehouse Management System", use_llm=True
        )
    assert bp.entities, "heuristic fallback should have produced entities"
    assert any(e.name == "Warehouse" for e in bp.entities)
