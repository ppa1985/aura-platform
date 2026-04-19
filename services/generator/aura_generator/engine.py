"""Blueprint Engine.

Takes a user prompt, asks the LLM to produce a Blueprint JSON, validates it
with Pydantic, and falls back to a deterministic keyword-based skeleton if
the LLM is unavailable or returns something unusable. That fallback is what
lets CI and demos work without a live model.
"""

from __future__ import annotations

import re
from typing import Any

from slugify import slugify

from .blueprint import AIConfig, Blueprint, Entity, EntityField, Page, Relation
from .llm import OllamaError, generate_json

SYSTEM_PROMPT = """You are Aura's Blueprint Engine. Given a natural-language
description of an application, produce a JSON App Blueprint describing its
entities, fields, relations, and pages.

Rules:
- Output ONLY valid JSON. No prose.
- Use PascalCase for entity names (Product, Warehouse, InventoryLevel).
- Use snake_case for field names (name, sku, created_at).
- Field "type" must be one of: string, text, integer, float, decimal, boolean,
  date, datetime, uuid, json.
- Every entity should include at least: a `name` field of type string, and
  fields describing its core attributes. Do NOT include id/created_at/updated_at;
  those are added automatically.
- Relations reference other entities by their PascalCase name.
- Pages: include one "dashboard" page, and for each entity produce "list",
  "form", and "detail" pages.
- `ai_enabled` is true iff the app description mentions AI, ML, recommendations,
  chat, summarization, analysis, or similar capabilities.

Schema (for reference):
{
  "name": "Human readable name",
  "slug": "kebab-case-slug",
  "description": "1-2 sentences",
  "ai_enabled": false,
  "ai_config": {"provider": "ollama", "model": "llama3.2:3b", "system_prompt": "..."},
  "entities": [
    {
      "name": "Product",
      "description": "...",
      "fields": [
        {"name": "name", "type": "string", "required": true},
        {"name": "sku", "type": "string", "unique": true, "required": true}
      ],
      "relations": [
        {"name": "warehouse", "target": "Warehouse", "kind": "many_to_one", "required": true}
      ]
    }
  ],
  "pages": [
    {"type": "dashboard", "title": "Overview"},
    {"type": "list", "entity": "Product", "title": "Products"}
  ]
}
"""


async def blueprint_from_prompt(prompt: str, *, use_llm: bool = True) -> Blueprint:
    if use_llm:
        try:
            raw = await generate_json(
                f"Application description:\n\n{prompt}\n\nReturn the JSON Blueprint now.",
                system=SYSTEM_PROMPT,
            )
            bp = _coerce(raw, fallback_name=prompt[:60])
            if bp.entities:
                bp.ensure_default_pages()
                return bp
        except OllamaError:
            # Fall through to heuristic fallback
            pass

    bp = _heuristic(prompt)
    bp.ensure_default_pages()
    return bp


def _coerce(raw: dict[str, Any], *, fallback_name: str) -> Blueprint:
    """Best-effort normalization of LLM output into Blueprint shape."""
    data = dict(raw)
    data.setdefault("name", fallback_name.strip() or "Generated App")
    data.setdefault("slug", slugify(data["name"]))
    data.setdefault("description", "")

    # Normalize entities
    ents = []
    for e in data.get("entities", []) or []:
        if not isinstance(e, dict) or not e.get("name"):
            continue
        fields = [f for f in (e.get("fields") or []) if isinstance(f, dict) and f.get("name")]
        rels = [r for r in (e.get("relations") or []) if isinstance(r, dict) and r.get("name") and r.get("target")]
        # Drop system field names the LLM sometimes emits
        fields = [f for f in fields if f["name"].lower() not in {"id", "created_at", "updated_at"}]
        # Default type
        for f in fields:
            f.setdefault("type", "string")
        ents.append({"name": e["name"], "description": e.get("description"), "fields": fields, "relations": rels})
    data["entities"] = ents

    pages = []
    for p in data.get("pages", []) or []:
        if isinstance(p, dict) and p.get("type") in {"dashboard", "list", "form", "detail"}:
            pages.append(p)
    data["pages"] = pages

    ai_enabled = bool(data.get("ai_enabled", False))
    ai_config = data.get("ai_config")
    if ai_enabled and not ai_config:
        data["ai_config"] = {"provider": "ollama", "model": "llama3.2:3b"}

    return Blueprint(**data)


# ---------------------------------------------------------------------------
# Deterministic fallback: good enough to unblock CI and demo flows.
# ---------------------------------------------------------------------------

_DEFAULT_ENTITY_FIELDS: dict[str, list[EntityField]] = {
    "Product": [
        EntityField(name="name", type="string", required=True),
        EntityField(name="sku", type="string", required=True, unique=True),
        EntityField(name="description", type="text"),
        EntityField(name="unit_price", type="decimal"),
    ],
    "Warehouse": [
        EntityField(name="name", type="string", required=True),
        EntityField(name="code", type="string", required=True, unique=True),
        EntityField(name="address", type="text"),
    ],
    "InventoryLevel": [
        EntityField(name="quantity", type="integer", required=True),
        EntityField(name="min_quantity", type="integer"),
        EntityField(name="reorder_point", type="integer"),
    ],
    "Shipment": [
        EntityField(name="reference", type="string", required=True, unique=True),
        EntityField(name="direction", type="string", required=True),  # inbound|outbound
        EntityField(name="status", type="string", required=True),
        EntityField(name="shipped_at", type="datetime"),
    ],
    "Supplier": [
        EntityField(name="name", type="string", required=True),
        EntityField(name="contact_email", type="string"),
        EntityField(name="phone", type="string"),
    ],
    "Customer": [
        EntityField(name="name", type="string", required=True),
        EntityField(name="email", type="string", unique=True),
    ],
    "Order": [
        EntityField(name="reference", type="string", required=True, unique=True),
        EntityField(name="status", type="string", required=True),
        EntityField(name="total", type="decimal"),
    ],
    "NewsItem": [
        EntityField(name="headline", type="string", required=True),
        EntityField(name="body", type="text"),
        EntityField(name="url", type="string"),
        EntityField(name="published_at", type="datetime"),
    ],
    "Trade": [
        EntityField(name="symbol", type="string", required=True),
        EntityField(name="side", type="string", required=True),
        EntityField(name="quantity", type="decimal", required=True),
        EntityField(name="price", type="decimal", required=True),
        EntityField(name="executed_at", type="datetime"),
    ],
}


def _heuristic(prompt: str) -> Blueprint:
    """Keyword-driven skeleton for when the LLM is not available."""
    p = prompt.lower()
    picks: list[str] = []

    if any(k in p for k in ["warehouse", "inventory", "wms"]):
        picks = ["Warehouse", "Product", "InventoryLevel", "Shipment", "Supplier"]
        name = "Warehouse Management System"
    elif any(k in p for k in ["trade", "trading", "stock", "market"]):
        picks = ["Trade", "NewsItem"]
        name = "Trade Assistant"
    elif any(k in p for k in ["order", "store", "shop", "ecommerce", "commerce"]):
        picks = ["Product", "Customer", "Order"]
        name = "Storefront"
    else:
        picks = ["Product"]
        name = "Generated App"

    entities: list[Entity] = []
    for p_name in picks:
        entities.append(Entity(name=p_name, fields=list(_DEFAULT_ENTITY_FIELDS[p_name])))

    # Wire up common relations
    names = {e.name for e in entities}
    for e in entities:
        if e.name == "InventoryLevel":
            if "Product" in names:
                e.relations.append(Relation(name="product", target="Product", required=True))
            if "Warehouse" in names:
                e.relations.append(Relation(name="warehouse", target="Warehouse", required=True))
        elif e.name == "Shipment":
            if "Warehouse" in names:
                e.relations.append(Relation(name="warehouse", target="Warehouse", required=True))
            if "Supplier" in names:
                e.relations.append(Relation(name="supplier", target="Supplier"))
        elif e.name == "Product":
            if "Supplier" in names:
                e.relations.append(Relation(name="supplier", target="Supplier"))
        elif e.name == "Order":
            if "Customer" in names:
                e.relations.append(Relation(name="customer", target="Customer", required=True))

    ai_enabled = any(k in p for k in ["ai", "llm", "news analysis", "recommend", "summariz", "chat", "assistant"])

    bp = Blueprint(
        name=_pretty_name(prompt) or name,
        description=prompt.strip()[:280],
        entities=entities,
        ai_enabled=ai_enabled,
        ai_config=AIConfig() if ai_enabled else None,
    )
    bp.pages.append(Page(type="dashboard", title="Overview"))
    return bp


def _pretty_name(prompt: str) -> str | None:
    m = re.search(r"(?:build me|build|create)\s+(?:a|an)?\s*([A-Za-z0-9 \-_/]+)", prompt, re.I)
    if not m:
        return None
    raw = m.group(1).strip().split(" with ")[0].strip(" .,:;-")
    return " ".join(w.capitalize() for w in raw.split()) or None
