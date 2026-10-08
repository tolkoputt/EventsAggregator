FROM python:3.12-slim

RUN groupadd --system --gid 1000 appuser && \
    useradd --system --uid 1000 --gid appuser --create-home appuser

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_LINK_MODE=copy
ENV UV_CACHE_DIR=/tmp/uv-cache

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=appuser:appuser src/ ./src/

RUN uv sync --frozen --no-dev

USER appuser

CMD ["uv", "run", "uvicorn", "src.eventsaggregator.main:app", "--host", "0.0.0.0", "--port", "8000"]