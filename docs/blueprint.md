# App Blueprint

The **App Blueprint** is the declarative contract that drives everything in
Aura. It's produced by the Blueprint Engine from a user prompt, and consumed
by the Dynamic Schema Generator, Component Assembler, Auto-Coder, and
Self-Healing loop.

## Shape

```jsonc
{
  "name": "Warehouse Management System",
  "slug": "warehouse-management-system",
  "description": "Short paragraph about the app.",
  "ai_enabled": true,
  "ai_config": {
    "provider": "ollama",
    "model": "llama3.2:3b",
    "system_prompt": "You are a warehouse assistant..."
  },
  "entities": [
    {
      "name": "Product",
      "description": "Stock-keeping unit.",
      "fields": [
        { "name": "name",       "type": "string",  "required": true },
        { "name": "sku",        "type": "string",  "required": true, "unique": true },
        { "name": "unit_price", "type": "decimal" }
      ],
      "relations": [
        { "name": "supplier",  "target": "Supplier",  "kind": "many_to_one" }
      ]
    }
  ],
  "pages": [
    { "type": "dashboard", "title": "Overview" },
    { "type": "list",      "entity": "Product", "title": "Products" },
    { "type": "form",      "entity": "Product", "title": "New Product" },
    { "type": "detail",    "entity": "Product", "title": "Product Detail" }
  ]
}
```

## Normalization rules

Aura enforces strict naming so every generated artifact lines up:

| Thing          | Convention        | Example                   |
| -------------- | ----------------- | ------------------------- |
| Entity name    | PascalCase        | `InventoryLevel`          |
| Field name     | snake_case        | `reorder_point`           |
| Relation name  | snake_case        | `warehouse`               |
| Relation target| PascalCase        | `Warehouse`               |
| DB schema      | `app_<slug_>`     | `app_warehouse_management_system` |
| Table name     | snake_plural      | `inventory_levels`        |
| Route path     | kebab-case        | `/inventory-level`        |

System columns (`id`, `created_at`, `updated_at`) and `<relation>_id` FK
columns are added automatically — **don't** include them in the Blueprint.

## Field types

`string`, `text`, `integer`, `float`, `decimal`, `boolean`, `date`,
`datetime`, `uuid`, `json`.

## AI integration

Set `ai_enabled: true` to wire the generated app to Ollama (or any
OpenAI-compatible endpoint). The generator emits `/api/ai` in the new app
that forwards prompts to `$OLLAMA_URL` and returns the completion.
