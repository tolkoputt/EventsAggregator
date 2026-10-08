FROM python:3.12-slim

RUN addgroup --system --gid 1000 appuser && \
    adduser --system --uid 1000 --ingroup appuser appuser

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./

RUN uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/

RUN uv sync --frozen --no-dev

RUN chown -R appuser:appuser /app

USER appuser

CMD ["uv", "run", "uvicorn", "src.eventsaggregator.main:app", "--host", "0.0.0.0", "--port", "8000"]