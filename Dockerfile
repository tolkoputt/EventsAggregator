FROM python:3.13-slim

RUN groupadd --system --gid 1000 appuser && \
    useradd --system --uid 1000 --gid appuser --create-home appuser && \
    mkdir -p /app /home/appuser/.cache/uv && \
    chown -R appuser:appuser /app /home/appuser

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_LINK_MODE=copy
ENV UV_CACHE_DIR=/home/appuser/.cache/uv

USER appuser

COPY --chown=appuser:appuser pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser migrations/ ./migrations/

RUN uv sync --frozen --no-dev

CMD ["sh", "-c", "uv run --no-sync alembic upgrade head && exec uv run --no-sync uvicorn eventsaggregator.main:app --host 0.0.0.0 --port 8000"]