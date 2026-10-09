import logging
from contextlib import asynccontextmanager

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, FastAPI

from eventsaggregator.core.config import settings
from eventsaggregator.db.db import async_session_factory
from eventsaggregator.routers import health, sync
from eventsaggregator.services.sync import sync_events

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def run_scheduled_sync(http: httpx.AsyncClient) -> None:
    try:
        async with async_session_factory() as session:
            if await sync_events(http, session):
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

    scheduler = AsyncIOScheduler(timezone="Asia/Yekaterinburg")
    scheduler.add_job(
        run_scheduled_sync,
        CronTrigger(hour=3, minute=0),
        args=[app.state.http],
        id="daily_sync",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=3600,
        coalesce=True,
    )
    scheduler.start()

    yield

    scheduler.shutdown(wait=False)
    await app.state.http.aclose()


api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(sync.router)


app = FastAPI(lifespan=lifespan)
app.include_router(api_router)
