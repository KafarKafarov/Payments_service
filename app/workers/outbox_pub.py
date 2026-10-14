import asyncio
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.outbox import OutboxEvent
from app.db.session import async_session_factory
from app.message.broker import rabbit_broker
from app.message.topology import ALL_PAYMENT_QUEUES, PAYMENTS_NEW_QUEUE

logger = logging.getLogger(__name__)


async def _load_event(
    session: AsyncSession,
    event_id: uuid.UUID,
) -> OutboxEvent | None:
    stmt = (
        select(OutboxEvent)
        .where(
            OutboxEvent.id == event_id,
            OutboxEvent.published_at.is_(None),
        )
        .with_for_update(skip_locked=True)
    )
    return await session.scalar(stmt)


async def _next_event_ids(
    session: AsyncSession,
    limit: int = 50,
):
    stmt = (
        select(OutboxEvent.id)
        .where(OutboxEvent.published_at.is_(None))
        .order_by(OutboxEvent.created_at)
        .limit(limit)
    )
    return list((await session.scalars(stmt)).all())


async def _record_failure(
    event_id: uuid.UUID,
    exc: Exception,
) -> None:
    async with async_session_factory() as session:
        event = await session.get(OutboxEvent, event_id)
        if event is None:
            return
        event.attempts += 1
        event.last_error = str(exc)[:2_000]
        await session.commit()


async def _publish_one(event_id: uuid.UUID) -> None:
    try:
        async with async_session_factory() as session:
            async with session.begin():
                event = await _load_event(session, event_id)
                if event is None:
                    return

                await rabbit_broker.publish(
                    event.payload,
                    queue=PAYMENTS_NEW_QUEUE,
                    headers={'x-attempt': 1},
                    message_id=str(event.id),
                    persist=True,
                )

                event.attempts += 1
                event.last_error = None
                event.published_at = datetime.now(UTC)
    except Exception as exc:
        await _record_failure(event_id, exc)
        raise


async def run() -> None:
    await rabbit_broker.connect()
    for queue in ALL_PAYMENT_QUEUES:
        await rabbit_broker.declare_queue(queue)

    try:
        while True:
            async with async_session_factory() as session:
                event_ids = await _next_event_ids(session)

            if not event_ids:
                await asyncio.sleep(settings.outbox_poll_interval)
                continue

            for event_id in event_ids:
                try:
                    await _publish_one(event_id)
                except Exception:
                    logger.exception(
                        msg=f'Failed to publish outbox event {event_id}'
                    )
                    await asyncio.sleep(settings.outbox_poll_interval)

    finally:
        await rabbit_broker.stop()


if __name__ == '__main__':
    asyncio.run(run())
