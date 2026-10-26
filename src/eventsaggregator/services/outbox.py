import logging
from datetime import UTC, datetime
from uuid import UUID

from eventsaggregator.client.capashino import (
    CapashinoPermanentError,
    CapashinoProviderClient,
    CapashinoTransientError,
    NotificationAlreadyExists,
    NotificationCreated,
)
from eventsaggregator.db.repositories import EventRepository

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 5


class OutBoxService:
    def __init__(
        self, events: EventRepository, client: CapashinoProviderClient
    ) -> None:
        self.events = events
        self.client = client

    async def worker(self) -> None:
        while elem := await self.events.get_outbox(MAX_ATTEMPTS):
            try:
                ticket_id = UUID(elem.payload["ticket_id"])
            except (KeyError, TypeError, ValueError) as exc:
                elem.attempt_count = MAX_ATTEMPTS
                await self.events.session.commit()
                logger.error("Outbox %s has invalid ticket_id: %s", elem.id, exc)
                continue

            event_id = await self.events.get_event_id_by_ticket(ticket_id)
            event_data = await self.events.one_event(event_id) if event_id else None
            if event_data is None:
                elem.attempt_count = MAX_ATTEMPTS
                await self.events.session.commit()
                logger.error("Outbox %s references a missing ticket or event", elem.id)
                continue

            try:
                result = await self.client.create_notifi(
                    f"Вы успешно зарегистрированы на мероприятие - {event_data.name}",
                    ticket_id,
                    str(elem.id),
                )
            except CapashinoTransientError as exc:
                elem.attempt_count += 1
                await self.events.session.commit()
                logger.warning(
                    "Temporary Capashino error for outbox %s (attempt %s/%s): %s",
                    elem.id,
                    elem.attempt_count,
                    MAX_ATTEMPTS,
                    exc,
                )
                continue
            except CapashinoPermanentError as exc:
                elem.attempt_count = MAX_ATTEMPTS
                await self.events.session.commit()
                logger.error(
                    "Permanent Capashino error for outbox %s: %s", elem.id, exc
                )
                continue

            if isinstance(result, NotificationCreated):
                elem.payload = result.response.model_dump(mode="json")
            elif not isinstance(result, NotificationAlreadyExists):
                raise TypeError(f"Unexpected Capashino result: {type(result).__name__}")

            elem.status = True
            elem.last_sync_time = datetime.now(tz=UTC)
            await self.events.session.commit()
