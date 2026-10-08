from fastapi import FastAPI

from eventsaggregator.core.config import settings

app = FastAPI()


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "db_host": settings.POSTGRES_HOST,
    }
