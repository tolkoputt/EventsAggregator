from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from eventsaggregator.db.db import get_async_session
from eventsaggregator.db.query import list_events
from eventsaggregator.http.schemas import Page, PageParams

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/events", response_model=Page)
async def get_events(
    request: Request,
    params: Annotated[PageParams, Query()],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    items, total = await list_events(session, params)

    def link(page: int) -> str:
        return str(request.url.include_query_params(page=page))

    return Page(
        count=total,
        next=link(params.page + 1)
        if (params.page + 1) * params.page_size < total
        else None,
        previous=link(params.page - 1) if params.page > 1 else None,
        results=items,
    )
