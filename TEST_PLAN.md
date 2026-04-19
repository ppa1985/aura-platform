# Test plan — Aura app generation platform (PR #1)

## What I'm testing

The single claim this PR has to prove: **a user can type a natural-language
prompt into Aura's dashboard and get back a fully-scaffolded, registered,
healed Next.js app whose Blueprint and artifacts match the prompt**.

I'll drive this through the UI (not curl) with the Warehouse Management
System prompt the user asked for as the demo. Heuristic path (`use_llm=false`)
so the video is seconds, not minutes — I already verified the real-LLM path
end-to-end separately (prompt: "Build me a simple blog with posts and
comments" → entities `Post`, `Comment`, 2m14s on CPU).

## Preconditions (already satisfied; not in the video)

- Postgres on :5432 (docker `aura-pg`)
- Generator on :8000 (`/health` returns `{status: ok, ollama: true, mode: inprocess}`)
- Dashboard on :3000
- No apps in the registry (clean slate)

## Test cases

### T1 — Dashboard shows empty state on a clean registry

**Steps**

1. Open `http://localhost:3000/`.

**Pass/fail**

- ✅ Page heading reads "**Generated apps**".
- ✅ Subtitle contains "**0 apps**" (not "1 apps", not missing).
- ✅ Subtitle contains "**Generator online (llama3.2:3b)**".
- ✅ The empty-state card is visible with the "Build me a Warehouse Management
  System …" example prompt and a "**Generate a demo app**" button.

*Would a broken build look the same?* No — if the generator is down the
subtitle would say "Generator offline"; if app listing is broken the count
would be wrong or the page would 500.

### T2 — Blueprint preview reflects the WMS prompt

**Steps**

1. Click **+ New app** → `/new`.
2. The default prompt is the WMS prompt. Leave it.
3. **Uncheck** the "Use Ollama" checkbox.
4. Click **Preview Blueprint**.

**Pass/fail**

- ✅ A new card titled "**Warehouse Management System**" appears with slug
  `warehouse-management-system`.
- ✅ The card lists **exactly 5 entities** with these PascalCase names, in
  this order: `Warehouse`, `Product`, `InventoryLevel`, `Shipment`,
  `Supplier`.
- ✅ `InventoryLevel` shows relations containing `product → Product` **and**
  `warehouse → Warehouse` (two FKs).
- ✅ `Shipment` shows a relation containing `supplier → Supplier`.
- ✅ No `Generate + Deploy` result card is shown yet (preview only).

*Would a broken build look the same?* No — a broken Blueprint Engine would
produce the wrong entities, miss relations, or error out. Off-by-one naming
(e.g. `warehouses` vs `Warehouse`) would fail the exact-string checks.

### T3 — Generate + Deploy actually creates and registers the app

**Steps**

1. From the same `/new` page, click **Generate + Deploy**.
2. Wait for the result card (heuristic mode: <5s).

**Pass/fail**

- ✅ Result card title reads "**Warehouse Management System generated**".
- ✅ Schema label reads exactly `app_warehouse_management_system`.
- ✅ Self-heal label reads `self-heal ✓` (not "degraded").
- ✅ Deployment label reads `deployment inprocess`.
- ✅ Clicking **Manage** navigates to `/apps/warehouse-management-system`.

*Would a broken build look the same?* No — schema name is
deterministically derived; self-heal "✓" means the generated TypeScript
passed `tsc`; a broken pipeline would show "degraded" or an error toast.

### T4 — Detail page faithfully reflects the committed Blueprint

**Steps**

1. On `/apps/warehouse-management-system`, inspect the Deployment and
   Blueprint cards.

**Pass/fail**

- ✅ Status badge reads "**ready**" (green).
- ✅ Deployment card shows `slug: warehouse-management-system`,
  `URL: http://aura.local/generated/warehouse-management-system`.
- ✅ Blueprint card shows header "**5 entities · 9 pages**" (1 dashboard +
  2 per entity × 4 = matches `ensure_default_pages`).
- ✅ Each of the 5 entity subsections lists fields separated by `·` with the
  correct types — e.g. `Product` shows `name: string · sku: string · unit_price: decimal`.
- ✅ `InventoryLevel` relations line reads
  `relations: product → Product, warehouse → Warehouse`.

*Would a broken build look the same?* No — the fields/types are emitted
from the same Pydantic model the schema generator uses; a broken emitter
would drop or rename fields.

### T5 — Home page now shows the generated app

**Steps**

1. Click "← Back to apps".

**Pass/fail**

- ✅ Subtitle now reads "**1 app**".
- ✅ A card titled "Warehouse Management System" is visible with status
  badge "**ready**" and an **Open app** button.
- ✅ The card's slug line reads `slug: warehouse-management-system`.

*Would a broken build look the same?* No — the registry would either be
empty or list the wrong name/slug/status.

### T6 (regression) — Artifact files exist on disk

**Steps (shell, not in the video)**

1. `ls generated/warehouse-management-system/src/app/ | sort`

**Pass/fail**

- ✅ Output contains `api`, `inventory-level`, `product`, `shipment`,
  `supplier`, `warehouse`, `layout.tsx`, `page.tsx`, `globals.css`.

## What I'm **not** testing (and why)

- Opening the generated app at `http://aura.local/generated/warehouse-management-system`
  — in `AURA_MODE=inprocess` the app is only on disk; Traefik routing
  requires `AURA_MODE=docker` + `make up`. I'm not bringing up the full
  Traefik stack in this session; the artifact-level proof + the fact that
  `next build` passes on the generated app is enough evidence.
- Real-LLM Blueprint generation — verified separately via API, too slow
  (2+ min on CPU) to record.
- The Self-Healing loop's patching behavior — verified in unit tests;
  triggering a real fix would require deliberately breaking a template.
