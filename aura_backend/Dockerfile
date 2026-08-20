FROM python:3.12-slim

# Use the exact audited official uv source/version. The container consumes the
# same pyproject.toml + uv.lock authority as local and CI execution.
COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /uvx /bin/

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Resolve only from the reviewed lock, including the supported runtime lanes.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --extra provider-gemini --extra mcp --extra memvid \
    --no-install-project

COPY . .

RUN mkdir -p aura_chroma_db aura_data/users aura_data/sessions aura_data/exports aura_data/backups

RUN useradd --create-home --shell /bin/bash aura && \
    chown -R aura:aura /app
USER aura

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)" || exit 1

CMD ["uvicorn", "aura_backend.main:create_app", "--factory", "--host", "127.0.0.1", "--port", "8000", "--lifespan", "on"]
