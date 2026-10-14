import logging
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OutboxEvent, Payment
from app.schemas.payment import PaymentCreate

logger = logging.getLogger(__name__)


def is_same(payment: Payment, data: PaymentCreate) -> bool:
    return (
        payment.amount == data.amount
        and payment.currency == data.currency
        and payment.description == data.description
        and payment.metadata_ == data.metadata
        and payment.webhook_url == str(data.webhook_url)
    )


class IdempotencyConflict(Exception):
    pass


async def _get_by_idempotency_key(
    session: AsyncSession,
    key: str,
) -> Payment | None:
    stmt = select(Payment).where(Payment.idempotency_key == key)
    return await session.scalar(stmt)


async def get_create_payment(
    session: AsyncSession,
    data: PaymentCreate,
    idempotency_key: str,
) -> Payment:
    logger.info(f'Платежи: проверка Idempotency-Key={idempotency_key}')

    existing = await _get_by_idempotency_key(
        session=session,
        key=idempotency_key,
    )
    if existing is not None:
        if not is_same(existing, data):
            logger.warning(
                f'Платежи: конфликт Idempotency-Key={idempotency_key}; '
                f'параметры запроса отличаются'
            )
            raise IdempotencyConflict()

        logger.info(
            f'Платежи: повторный запрос Idempotency-Key='
            f'{idempotency_key}; возвращается payment_id={existing.id}'
        )
        return existing

    payment = Payment(
        id=uuid4(),
        amount=data.amount,
        currency=data.currency,
        description=data.description,
        metadata_=data.metadata,
        idempotency_key=idempotency_key,
        webhook_url=str(data.webhook_url),
    )

    logger.info(
        f'Платежи: создается payment_id={payment.id}, '
        f'Idempotency-Key={idempotency_key}'
    )
    try:
        async with session.begin_nested():
            session.add(payment)
            await session.flush()

            session.add(
                OutboxEvent(
                    event_type='payment_created',
                    aggregate_id=payment.id,
                    payload={'payment_id': str(payment.id)},
                )
            )
        await session.commit()
        logger.info(
            f'Платежи: payment_id={payment.id} и outbox-событие '
            f'успешно сохранены одной транзакцией'
        )
        return payment
    except IntegrityError as e:
        await session.rollback()
        logger.warning(
            f'Платежи: обнаружена конкурентная вставка для '
            f'Idempotency-Key={idempotency_key}: {e}'
        )

        existing = await _get_by_idempotency_key(
            session=session,
            key=idempotency_key,
        )

        if existing is None:
            logger.exception(
                f'Платежи: IntegrityError не связан с '
                f'Idempotency-Key={idempotency_key}'
            )
            raise

        if not is_same(
            payment=existing,
            data=data,
        ):
            logger.warning(
                f'Платежи: конкурентный конфликт '
                f'Idempotency-Key={idempotency_key}'
            )
            raise IdempotencyConflict()

        logger.info(
            f'Платежи: после конкурентной вставки найден '
            f'payment_id={existing.id}'
        )
        return existing


async def get_payment(
    session: AsyncSession,
    payment_id: UUID,
) -> Payment | None:
    payment = await session.get(Payment, payment_id)
    logger.info(
        f'Платежи: запрос payment_id={payment_id}; найден={payment is not None}'
    )
    return payment
