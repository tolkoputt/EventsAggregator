from contextlib import asynccontextmanager

import httpx
from fastapi import APIRouter, FastAPI

from eventsaggregator.core.config import settings
from eventsaggregator.routers import health, sync


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(
        base_url=settings.EXTERNAL_API_URL,
        timeout=httpx.Timeout(10.0, connect=3.0),
    )

    yield

    await app.state.http.aclose()


api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(sync.router)


app = FastAPI(lifespan=lifespan)
app.include_router(api_router)
