import logging
from contextlib import asynccontextmanager

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from eventsaggregator.client.provider import EventProviderClient
from eventsaggregator.core.config import settings
from eventsaggregator.core.exceptions import ProviderError
from eventsaggregator.db.db import async_session_factory
from eventsaggregator.db.repositories import EventRepository
from eventsaggregator.routers import events, health, sync, ticket
from eventsaggregator.services.cache import EventsCache
from eventsaggregator.services.sync import SyncService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def run_scheduled_sync(provider: EventProviderClient) -> None:
    try:
        async with async_session_factory() as session:
            repository = EventRepository(session)
            service = SyncService(events=repository, client=provider)

            if await service.sync_events():
                logger.info("Scheduled sync finished")
            else:
                logger.warning("Scheduled sync skipped: another sync is running")
    except Exception:
        logger.exception("Scheduled sync failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(
        base_url=settings.EXTERNAL_API_URL,
        timeout=httpx.Timeout(10.0, connect=3.0),
        follow_redirects=True,
    )

    provider = EventProviderClient(app.state.http, settings.EXTERNAL_API_KEY)

    scheduler = AsyncIOScheduler(timezone="Asia/Yekaterinburg")
    scheduler.add_job(
        run_scheduled_sync,
        CronTrigger(hour=3, minute=0),
        args=[provider],
        id="daily_sync",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=3600,
        coalesce=True,
    )
    scheduler.start()

    app.state.cache = EventsCache()

    yield

    scheduler.shutdown(wait=False)
    app.state.cache = None
    await app.state.http.aclose()


api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(sync.router)
api_router.include_router(events.router)
api_router.include_router(ticket.router)


app = FastAPI(lifespan=lifespan)
app.include_router(api_router)


@app.exception_handler(ProviderError)
async def provider_error_handler(request: Request, exc: ProviderError):
    logger.error("Provider error on %s %s: %s", request.method, request.url, exc)
    return JSONResponse(status_code=502, content={"detail": "External provider error"})


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request, exc: RequestValidationError
):
    if (
        request.method == "POST"
        and request.url.path == "/api/tickets"
        and any(error["loc"][0] == "body" for error in exc.errors())
    ):
        return JSONResponse(status_code=400, content={"detail": "Invalid body"})

    return await request_validation_exception_handler(request, exc)
