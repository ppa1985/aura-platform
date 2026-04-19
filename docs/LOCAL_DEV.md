# Local Development Guide

This guide assumes a 16 GB laptop with Docker Desktop capped around **6–8 GB**.
If you have more headroom, everything still works — the profiles below just trade
convenience for RAM.

---

## TL;DR — recommended profile (16 GB laptop, 6.65 GB Docker cap)

Run **Ollama + Postgres in Docker, dashboard + generator natively**. This keeps
the ~5 GB LLM on one side and leaves the Node / Python hot-reload processes on
native tooling where they're fastest.

```bash
# 0. Clone
git clone https://github.com/ppa1985/aura-platform.git
cd aura-platform

# 1. Generate two secrets (do this once; put them in infra/.env)
python3 -c "import secrets; print('AURA_JWT_SECRET=' + secrets.token_urlsafe(48))"
python3 -c "from cryptography.fernet import Fernet; print('AURA_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"

# Paste the two lines into infra/.env along with OLLAMA_MODEL and AURA_MODE.
# See infra/.env.example for the full template.

# 2. Bring up Postgres only (you don't need Traefik locally)
cd infra
docker compose up -d postgres

# 3. If you don't already have Ollama running, start it in Docker too:
docker run -d --name ollama -p 11434:11434 \
  -v ollama:/root/.ollama ollama/ollama:latest
docker exec -it ollama ollama pull llama3.1:latest

# 4. Generator (terminal 1)
cd ../services/generator
uv sync
OLLAMA_URL=http://localhost:11434 \
OLLAMA_MODEL=llama3.1:latest \
DATABASE_URL=postgresql+psycopg://aura:aura@localhost:5432/aura \
AURA_MODE=inprocess \
AURA_JWT_SECRET=$(grep AURA_JWT_SECRET ../../infra/.env | cut -d= -f2) \
AURA_ENCRYPTION_KEY=$(grep AURA_ENCRYPTION_KEY ../../infra/.env | cut -d= -f2) \
uv run uvicorn aura_generator.main:app --reload --port 8000

# 5. Dashboard (terminal 2)
cd ../apps/dashboard
npm install
npm run dev
# → http://localhost:3000
```

That's it. Signup → verify (code logged to the generator stdout) → `/profile` →
link a PAT → `/new` → generate.

---

## Memory budget

Measured with `docker stats` / `ps` after a full warm pipeline run:

| Component | Idle | Under load |
|---|---:|---:|
| Postgres 16 | 150 MB | 250 MB |
| FastAPI generator (uvicorn) | 180 MB | 350 MB |
| Next.js dev server | 500 MB | 1.2 GB (hot reload) |
| Ollama + `llama3.1:latest` (4.9 GB model) | 100 MB | **5.0 GB** during inference |
| Traefik (optional) | 50 MB | 100 MB |

**Total for the recommended profile** (Ollama + Postgres in Docker, rest native):
~5.5 GB resident during an LLM generation. Inside Docker Desktop's 6.65 GB cap
you're using ~5.3 GB — comfortable.

### If you want everything in Docker

Drop the 8B model and use `shweyon:latest` (986 MB) or a 1B-class llama:

```bash
export OLLAMA_MODEL=shweyon:latest   # or: ollama pull llama3.2:1b && export OLLAMA_MODEL=llama3.2:1b
```

Docker total then ~3 GB; you can happily `docker compose up` the full stack
including the dashboard container.

---

## Reusing an existing `ollama-mm` container

If you already run Ollama in its own container (e.g. `docker exec -it ollama-mm ollama list`),
point Aura at it instead of spawning a second Ollama.

1. Check what network it's on:
   ```bash
   docker inspect ollama-mm --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{$v.IPAddress}}{{"\n"}}{{end}}'
   ```

2. **Option A — port is published to the host** (`curl http://localhost:11434/api/tags`
   on the laptop returns something):
   ```bash
   # infra/.env
   OLLAMA_URL=http://host.docker.internal:11434   # from containers
   # or, for a natively-running generator:
   OLLAMA_URL=http://localhost:11434
   ```

3. **Option B — port is NOT published, share the network instead.** Add the
   `ollama-mm` network under `generator.networks` in `infra/docker-compose.yml`:
   ```yaml
   generator:
     networks:
       - aura
       - ollama-mm_default   # <- whatever network inspect showed
     environment:
       OLLAMA_URL: http://ollama-mm:11434
   networks:
     aura:
       # ...
     ollama-mm_default:
       external: true
   ```

Use **whatever model name `docker exec ollama-mm ollama list` shows** — Aura
takes it verbatim. From your setup, `llama3.1:latest` is the right pick; set
`OLLAMA_MODEL=llama3.1:latest` in `infra/.env`.

---

## Full-Docker profile (needs ~8 GB Docker cap)

```bash
cd aura-platform/infra
cp .env.example .env
# edit .env — set AURA_JWT_SECRET, AURA_ENCRYPTION_KEY, OLLAMA_URL, OLLAMA_MODEL
docker compose up --build
# dashboard → http://localhost:3000
# generator → http://localhost:8000
# traefik  → http://localhost:8080
```

The compose file (`infra/docker-compose.yml`) now reads these from `.env`:

| Variable | Default | Notes |
|---|---|---|
| `OLLAMA_URL` | `http://host.docker.internal:11434` | For Docker Desktop on mac/Windows. On Linux set `http://172.17.0.1:11434` or use host network. |
| `OLLAMA_MODEL` | `llama3.1:latest` | Any tag your Ollama has pulled. |
| `AURA_MODE` | `inprocess` | Set to `docker` to actually spawn per-app containers (heavy — see below). |
| `AURA_JWT_SECRET` | *(none — generate one)* | Used to sign session cookies. |
| `AURA_ENCRYPTION_KEY` | *(none — generate one)* | Fernet key for PAT encryption at rest. |

### `AURA_MODE=docker` caveat

When enabled, each generated app becomes its own Next.js container (~1 GB). On
a 6.65 GB cap you can comfortably run **one generated app at a time**; delete
old ones from the dashboard before generating a second. The platform's
`DELETE /apps/{slug}` endpoint also drops the per-app Postgres schema so
nothing leaks.

---

## Generating the first app

1. `http://localhost:3000` → *"Sign up"*. Enter any email (e.g.
   `you@example.com`) and a password.
2. The 6-digit verification code is logged by the generator — grep it from
   stdout or from `/tmp/aura-gen.log` if you redirected there:
   ```bash
   grep "CODE:" <generator-log>
   ```
3. Paste the code into `/verify`.
4. `/profile` → link a GitHub or GitLab PAT. Workspace repo must exist already
   (e.g. `yourname/aura-workspace`).
5. `/new` → type a prompt. **Uncheck "Use Ollama"** for a <1 s heuristic run
   while you're clicking around; check it for the real-LLM path.
6. Done. Your new app's code is pushed to `apps/<slug>/` in the workspace repo,
   and the registry shows status `ready` (or `degraded` if self-heal didn't
   converge — the detail page shows exactly what tsc complained about).

---

## Real-LLM timings (CPU, no GPU)

| Model | Blueprint | Self-heal pass | Notes |
|---|---:|---:|---|
| `llama3.2:3b` (Q4_K_M, 2 GB) | ~2m14s | ~20 s | Reference from our dev VM |
| `llama3.1:latest` (8B Q4, 4.9 GB) | ~3–5 min | ~30–60 s | Higher quality, slower |
| `llama3.2:1b` (Q4, 1.3 GB) | ~30–45 s | ~10 s | Fine for smoke tests |
| heuristic (no LLM) | <1 s | 0 s | Default; toggle on `/new` |

If a blueprint request feels stuck, the generator falls back to the heuristic
path on any Ollama error — you won't hang.

---

## Troubleshooting

**"Connection refused" from generator → Ollama**
Host-gateway resolution only works from containers. If you're running the
generator natively, set `OLLAMA_URL=http://localhost:11434`. If in Docker on
Linux, use `http://172.17.0.1:11434` (or configure `host.docker.internal` via
`extra_hosts`).

**Dashboard can't reach generator**
The Next.js app proxies `/api/generator/*` via `next.config.ts`. Set
`GENERATOR_URL=http://localhost:8000` (native) or `http://generator:8000`
(in-compose) before `npm run dev` / `npm run build`.

**`AURA_JWT_SECRET` warning about key length**
PyJWT warns if the secret is under 32 bytes. Regenerate with
`python3 -c "import secrets; print(secrets.token_urlsafe(48))"`.

**Blueprint JSON from LLM is malformed**
Expected for smaller models. The generator logs the Ollama response, then falls
back to the keyword-heuristic blueprint (Warehouse / Trade / Storefront) and
keeps going. Try `llama3.1:latest` or `llama3.2:3b` for reliable JSON mode.

**Self-heal runs out of attempts**
`self_heal_max_attempts` defaults to 3. Bump with `SELF_HEAL_MAX_ATTEMPTS=5` —
each attempt is one LLM call plus one `tsc --noEmit` run, so expect ~30 s / attempt.
