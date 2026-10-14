from faststream.rabbit import RabbitQueue

from app.core.constants import (
    DEFAULT_EXCHANGE_NAME,
    FIRST_RETRY_NUMBER,
    MAX_RETRIES,
    PAYMENTS_DLQ_NAME,
    PAYMENTS_NEW_QUEUE_NAME,
    PAYMENTS_RETRY_QUEUE_PREFIX,
    RETRY_QUEUE_TTLS_MS,
)

PAYMENTS_NEW_QUEUE = RabbitQueue(
    name=PAYMENTS_NEW_QUEUE_NAME,
    durable=True,
    arguments={
        'x-dead-letter-exchange': DEFAULT_EXCHANGE_NAME,
        'x-dead-letter-routing-key': PAYMENTS_DLQ_NAME,
    },
)

PAYMENTS_RETRY_QUEUES = tuple(
    RabbitQueue(
        name=f'{PAYMENTS_RETRY_QUEUE_PREFIX}.{retry_number}',
        durable=True,
        arguments={
            'x-message-ttl': ttl_ms,
            'x-dead-letter-exchange': DEFAULT_EXCHANGE_NAME,
            'x-dead-letter-routing-key': PAYMENTS_NEW_QUEUE_NAME,
        },
    )
    for retry_number, ttl_ms in enumerate(
        RETRY_QUEUE_TTLS_MS,
        start=FIRST_RETRY_NUMBER,
    )
)

PAYMENTS_DLQ = RabbitQueue(
    name=PAYMENTS_DLQ_NAME,
    durable=True,
)

ALL_PAYMENT_QUEUES = (
    PAYMENTS_NEW_QUEUE,
    *PAYMENTS_RETRY_QUEUES,
    PAYMENTS_DLQ,
)


def retry_queue_for(retry_number: int) -> RabbitQueue:
    if not FIRST_RETRY_NUMBER <= retry_number <= MAX_RETRIES:
        raise ValueError(f'Неподдерживаемый номер retry: {retry_number}')

    return PAYMENTS_RETRY_QUEUES[retry_number - FIRST_RETRY_NUMBER]
