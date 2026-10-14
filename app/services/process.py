import asyncio
import logging
import random
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.constants import PaymentStatus
from app.db.models.payment import Payment
from app.services.webhook import WebhookClient

logger = logging.getLogger(__name__)


class PaymentNotFound(Exception):
    pass


class PaymentGateway:
    async def charge(self) -> PaymentStatus:
        delay = random.uniform(2, 5)
        logger.info(
            f'Платежный шлюз: начало эмуляции обработки; '
            f'задержка={delay:.2f} сек.'
        )
        await asyncio.sleep(delay)
        status = (
            PaymentStatus.SUCCESS
            if random.random() < 0.9
            else PaymentStatus.FAILED
        )
        logger.info(
            f'Платежный шлюз: эмуляция завершена; результат={status.value}'
        )
        return status


class PaymentProcessor:
    def __init__(
        self,
        session_factory: async_sessionmaker,
        gateway: PaymentGateway,
        webhook: WebhookClient,
    ) -> None:
        self._session_factory = session_factory
        self._gateway = gateway
        self._webhook = webhook

    async def _load(self, payment_id: UUID) -> Payment:
        async with self._session_factory() as session:
            payment = await session.get(Payment, payment_id)
            if payment is None:
                logger.error(
                    f'Обработка платежа: payment_id={payment_id} не найден'
                )
                raise PaymentNotFound
            logger.info(
                f'Обработка платежа: загружен payment_id={payment_id}, '
                f'status={payment.status.value}, '
                f'webhook_delivered='
                f'{payment.webhook_delivered_at is not None}'
            )
            return payment

    async def _set_status_if_pending(
        self,
        payment_id: UUID,
        status: PaymentStatus,
    ) -> None:
        async with self._session_factory() as session:
            stmt = (
                update(Payment)
                .where(
                    Payment.id == payment_id,
                    Payment.status == PaymentStatus.PENDING,
                )
                .values(
                    status=status,
                    processed_at=datetime.now(UTC),
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def _mark_webhook_delivered(
        self,
        payment_id: UUID,
    ) -> None:
        async with self._session_factory() as session:
            stmt = (
                update(Payment)
                .where(
                    Payment.id == payment_id,
                    Payment.webhook_delivered_at.is_(None),
                )
                .values(webhook_delivered_at=datetime.now(UTC))
            )
            await session.execute(stmt)
            await session.commit()

    async def process(self, payment_id: UUID) -> None:
        payment = await self._load(payment_id)

        if payment.status == PaymentStatus.PENDING:
            logger.info(
                f'Обработка платежа: payment_id={payment_id} '
                f'имеет pending-статус; вызывается шлюз'
            )
            new_status = await self._gateway.charge()
            await self._set_status_if_pending(payment_id, new_status)
        else:
            logger.info(
                f'Обработка платежа: payment_id={payment_id} уже '
                f'обработан; повторный вызов шлюза пропущен'
            )

        payment = await self._load(payment_id)

        if payment.webhook_delivered_at is None:
            logger.info(
                f'Обработка платежа: отправка webhook payment_id={payment_id}'
            )
            await self._webhook.send(
                url=payment.webhook_url,
                payment_id=payment.id,
                status=payment.status,
            )
            await self._mark_webhook_delivered(payment.id)
        else:
            logger.info(
                f'Обработка платежа: webhook для '
                f'payment_id={payment_id} уже был доставлен'
            )

        logger.info(f'Обработка платежа: завершение payment_id={payment_id}')
