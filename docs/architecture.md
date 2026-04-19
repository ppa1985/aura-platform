# Architecture

## Services

### Dashboard — `apps/dashboard`
Next.js 15 App Router with Shadcn-style primitives. Pages:

- `/` — list of generated apps with status.
- `/new` — prompt → Blueprint preview → Generate + Deploy.
- `/apps/[slug]` — per-app detail, Blueprint view, delete.
- `/system` — generator + Ollama health.

Dashboard calls the generator through `/api/generator/*` (rewritten to the
FastAPI service).

### Generator — `services/generator` (FastAPI)

```
POST /blueprints     prompt → Blueprint JSON
POST /apps           prompt | Blueprint → run full pipeline
GET  /apps           list apps in registry
GET  /apps/{slug}    fetch single app (+ parsed blueprint)
DELETE /apps/{slug}  stop container, drop app
GET  /health         generator + Ollama status
```

Pipeline (`pipeline.py`):

1. **Blueprint Engine** (`engine.py`) — Ollama with `format=json`; Pydantic
   validation; deterministic heuristic fallback.
2. **Dynamic Schema Generator** (`db.py`) — creates schema `app_<slug_>`,
   entity tables, and FK constraints. Uses `NUMERIC(18,4)` for `decimal`
   and `JSONB` for `json`.
3. **Auto-Coder** (`codegen.py` + `templates/nextjs/`) — writes a complete
   Next.js 15 app into `generated/<slug>/` with Shadcn components, Zod
   validation, per-entity CRUD pages, and API routes.
4. **Self-Healing** (`selfheal.py`) — runs `tsc --noEmit` on the generated
   app; on failure, asks Ollama to return a replacement file; retries.
5. **Deploy** (`deploy.py`) — two backends:
   - `inprocess` — files only; used by CI and local dev.
   - `docker` — `docker build` + `docker run` with Traefik labels that
     route `/generated/<slug>` to the new container.

### Postgres
A single Postgres instance hosts:

- `aura.apps` — control-plane registry of generated apps.
- `app_<slug_>` — one schema per generated app with its entity tables.

This gives per-app data isolation at the schema level without requiring a
separate database per app.

### Traefik
Reverse-proxy with Docker provider. Dashboard is mounted at `/`, generator
at `/api`, each generated app at `/generated/<slug>`.

```
              :80 (Traefik)
     ┌────────┴────────┬──────────────┬───────────────────┐
     ▼                 ▼              ▼                   ▼
  /           /api                /generated/wms   /generated/crm
  dashboard   generator           aura-app-wms     aura-app-crm
```

## Deterministic vs. LLM-driven

| Step                   | Driver            | Why                                   |
| ---------------------- | ----------------- | ------------------------------------- |
| Blueprint generation   | LLM (+ fallback)  | Natural-language understanding        |
| Schema creation        | Deterministic     | Safety; FKs must match Blueprint      |
| Code generation        | Deterministic     | Reproducible; avoids LLM drift        |
| Self-healing           | LLM               | Only way to react to unexpected errors|

## Extending

- **New page type** → add a Jinja template in
  `services/generator/aura_generator/templates/nextjs/` and wire it in
  `codegen.generate_app`.
- **New field type** → extend `_TYPE_SQL` in `db.py` and `_ts_type` /
  `_zod_type` in `codegen.py`.
- **External LLM** → point `OLLAMA_URL` at an OpenAI-compatible
  `/v1/chat/completions` proxy; `llm.py` uses the native Ollama format so
  swap it for an OpenAI client if needed.
