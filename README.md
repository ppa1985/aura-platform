# Aura — Autonomous App Generation Platform

Aura turns a natural-language prompt into a running, containerized full-stack app.

```
┌──────────────┐    prompt     ┌──────────────────┐   Blueprint    ┌─────────────────────┐
│  Dashboard   │ ────────────▶ │  Generator API   │ ─────────────▶ │ Schema + Codegen    │
│ (Next.js 15) │               │    (FastAPI)     │                │ (Postgres + Tmpls)  │
└──────────────┘               └──────────────────┘                └──────────┬──────────┘
                                       │                                      │
                                       ▼                                      ▼
                                ┌──────────────┐                   ┌────────────────────┐
                                │  Self-Heal   │◀── build errors ──│  Per-app Container │
                                │  (Ollama)    │                   │  (via Traefik)     │
                                └──────────────┘                   └────────────────────┘
```

## Components

| Path                      | What                                                   |
| ------------------------- | ------------------------------------------------------ |
| `apps/dashboard`          | Next.js 15 App Router UI for managing generated apps   |
| `services/generator`      | FastAPI generator: Blueprint Engine, Schema Gen, Codegen, Self-Healing |
| `infra`                   | Docker Compose, Traefik reverse proxy config           |
| `generated/`              | Per-app workspaces written by the Auto-Coder           |
| `docs/`                   | Architecture docs, Blueprint schema reference          |

## Quick start

Aura's generator talks to a pluggable LLM backend via `LLM_PROVIDER`. Pick one:

- **`ollama`** (default, fully local). Free, but slow on CPU: ~3–8 min per blueprint.
- **`groq`** (recommended for fast demos). Free tier, ~2–5 s per blueprint.
- **`openai`** (paid, ~$0.15 / 1M tokens with `gpt-4o-mini`).

### Option A — Groq (fast, free)

```bash
# 1. Grab an API key at https://console.groq.com (no credit card)

# 2. Configure + boot
cp infra/.env.example infra/.env
# Edit infra/.env and set:
#   LLM_PROVIDER=groq
#   GROQ_API_KEY=gsk_...
#   AURA_JWT_SECRET=...  (see comment in file)
#   AURA_ENCRYPTION_KEY=...  (see comment in file)
make up

# 3. Open http://localhost:3000
```

### Option B — Local Ollama

```bash
# 1. Start Ollama on the host and pull a model (CPU-friendly)
ollama serve &
ollama pull llama3.2:3b

# 2. Boot the stack (dashboard, generator, postgres, traefik)
cp infra/.env.example infra/.env   # fill in AURA_JWT_SECRET + AURA_ENCRYPTION_KEY
make up

# 3. Open the dashboard
open http://aura.local        # or http://localhost via /etc/hosts
```

> Running on a 16 GB laptop with Docker Desktop capped? See
> [`docs/LOCAL_DEV.md`](docs/LOCAL_DEV.md) for a 6.65 GB-friendly profile,
> instructions for reusing an existing Ollama container, and real-LLM timing
> benchmarks on CPU.

## Generating an app

```bash
# From the dashboard, enter a prompt such as:
#   "Build me a Warehouse Management System with products, warehouses,
#    inventory levels, and inbound/outbound shipments."
#
# Aura will:
#   1. Call Ollama → produce a validated App Blueprint (JSON)
#   2. Create a dedicated Postgres schema and tables
#   3. Write a Next.js app into generated/<slug>/ using Shadcn templates
#   4. Build + run the app in its own Docker container
#   5. On build failure, run the Self-Healing loop (LLM-assisted fixes)
#   6. Serve the new app at http://aura.local/generated/<slug>
```

## The Blueprint

See [`docs/blueprint.md`](docs/blueprint.md) for the canonical schema. High level:

```jsonc
{
  "name": "Warehouse Management System",
  "slug": "warehouse-management-system",
  "description": "...",
  "ai_enabled": true,
  "ai_config": { "provider": "ollama", "model": "llama3.2:3b" },
  "entities": [
    { "name": "Product", "fields": [ /* ... */ ], "relations": [ /* ... */ ] }
  ],
  "pages": [
    { "type": "dashboard", "title": "Overview" },
    { "type": "list",      "entity": "Product", "title": "Products" },
    { "type": "form",      "entity": "Product", "title": "New Product" },
    { "type": "detail",    "entity": "Product", "title": "Product Detail" }
  ]
}
```

## Development

```bash
make up        # start everything
make logs      # tail logs
make gen-wms   # generate the Warehouse Management System demo
make down      # stop everything
make fmt       # lint + format
```
