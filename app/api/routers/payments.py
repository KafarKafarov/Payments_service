from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_api_key
from app.db.models import Payment
from app.db.session import get_session
from app.schemas.payment import PaymentAccepted, PaymentCreate, PaymentDetail
from app.services import payments
from app.services.payments import IdempotencyConflict

router = APIRouter(
    prefix='/api/v1/payments',
    tags=['payments'],
    dependencies=[Depends(require_api_key)],
)


def to_accepted(payment: Payment) -> PaymentAccepted:
    return PaymentAccepted(
        payment_id=payment.id,
        status=payment.status,
        created_at=payment.created_at,
    )


def to_detail(payment: Payment) -> PaymentDetail:
    return PaymentDetail(
        payment_id=payment.id,
        amount=payment.amount,
        currency=payment.currency,
        description=payment.description,
        metadata=payment.metadata_,
        status=payment.status,
        idempotency_key=payment.idempotency_key,
        webhook_url=payment.webhook_url,
        created_at=payment.created_at,
        processed_at=payment.processed_at,
    )


@router.post(
    path='',
    response_model=PaymentAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    tags=['payments'],
)
async def create_payment(
    data: PaymentCreate,
    idempotency_key: Annotated[
        str,
        Header(
            alias='idempotency-key',
            min_length=1,
            max_length=128,
            description='Уникальный ключ запроса.',
        ),
    ],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PaymentAccepted:
    try:
        payment = await payments.get_create_payment(
            session, data, idempotency_key
        )
    except IdempotencyConflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Conflict, key already exists',
        )
    return to_accepted(payment)


@router.get(
    path='/{payment_id}',
    response_model=PaymentDetail,
)
async def get_payment(
    payment_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PaymentDetail:
    payment = await payments.get_payment(session, payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Payment not found'
        )
    return to_detail(payment)
