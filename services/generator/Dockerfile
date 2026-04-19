FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI so the generator can build/run per-app containers
RUN install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" \
       > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY services/generator/pyproject.toml ./
RUN uv pip install --system -e '.[dev]' || uv pip install --system \
        fastapi uvicorn[standard] pydantic pydantic-settings sqlalchemy 'psycopg[binary]' \
        httpx jinja2 python-slugify anyio rich docker pytest pytest-asyncio ruff

COPY services/generator/ /app/
COPY packages/ui /app/packages/ui

ENV PYTHONPATH=/app

EXPOSE 8000
CMD ["uvicorn", "aura_generator.main:app", "--host", "0.0.0.0", "--port", "8000"]
