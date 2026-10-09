from fastapi import APIRouter

from eventsaggregator.core.config import settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    return {
        "status": "ok",
        "db_host": settings.POSTGRES_HOST,
    }
