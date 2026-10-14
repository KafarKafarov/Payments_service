import logging

from faststream import AckPolicy, FastStream
from faststream.rabbit import RabbitMessage

from app.core.constants import (
    ATTEMPT_HEADER_NAME,
    INITIAL_ATTEMPT,
    MAX_ATTEMPTS,
)
from app.db.session import async_session_factory
from app.message.broker import rabbit_broker
from app.message.topology import (
    ALL_PAYMENT_QUEUES,
    PAYMENTS_NEW_QUEUE,
    retry_queue_for,
)
from app.schemas.events import PaymentCreatedEvent
from app.services.process import (
    PaymentGateway,
    PaymentNotFound,
    PaymentProcessor,
)
from app.services.webhook import WebhookClient, WebhookError

logger = logging.getLogger(__name__)

app = FastStream(rabbit_broker)


payment_processor = PaymentProcessor(
    session_factory=async_session_factory,
    gateway=PaymentGateway(),
    webhook=WebhookClient(),
)


@rabbit_broker.subscriber(
    PAYMENTS_NEW_QUEUE,
    ack_policy=AckPolicy.MANUAL,
)
async def handle_payment(
    event: PaymentCreatedEvent,
    msg: RabbitMessage,
) -> None:
    try:
        await payment_processor.process(payment_id=event.payment_id)
    except PaymentNotFound:
        logger.error(f'Платеж с id {event.payment_id} не найден')
        await msg.reject(requeue=False)
    except WebhookError:
        attempt = int(msg.headers.get(ATTEMPT_HEADER_NAME, INITIAL_ATTEMPT))
        logger.warning(
            f'Webhook не доставлен: payment_id={event.payment_id}, '
            f'попытка: {attempt}'
            )
        await schedule_retry(event, msg)
    except Exception as e:
        logger.exception(
            f'Платеж с id {event.payment_id} не прошел по причине: {e}'
        )
        await schedule_retry(event, msg)
    else:
        await msg.ack()


@app.after_startup
async def declare_auxiliary_queues() -> None:
    for queue in ALL_PAYMENT_QUEUES:
        await rabbit_broker.declare_queue(queue)


async def schedule_retry(
    event: PaymentCreatedEvent,
    msg: RabbitMessage,
) -> None:
    attempt = int(msg.headers.get(ATTEMPT_HEADER_NAME, INITIAL_ATTEMPT))

    if attempt >= MAX_ATTEMPTS:
        logger.warning(
            f'Попытки исчерпаны: payment_id={event.payment_id}; '
            'сообщение отправляется в payments.dlq',
        )
        await msg.reject(requeue=False)
        return

    next_attempt = attempt + 1
    queue = retry_queue_for(next_attempt - INITIAL_ATTEMPT)

    try:
        await rabbit_broker.publish(
            event.model_dump(mode='json'),
            queue=queue,
            headers={ATTEMPT_HEADER_NAME: next_attempt},
            message_id=msg.message_id,
            persist=True,
        )
    except Exception:
        await msg.nack(requeue=True)
        return

    await msg.ack()
