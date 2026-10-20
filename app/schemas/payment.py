from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.constants import Currency, PaymentStatus
from app.core.constants import (
    PAYMENT_AMOUNT_DECIMAL_PLACES,
    PAYMENT_AMOUNT_MAX_DIGITS,
)


class PaymentCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            'examples': [
                {
                    'amount': '199.90',
                    'currency': 'RUB',
                    'description': 'Заказ №42',
                    'metadata': {'order_id': 42},
                    'webhook_url': 'https://httpbin.org/post',
                }
            ]
        }
    )

    amount: Decimal = Field(
        gt=0,
        max_digits=PAYMENT_AMOUNT_MAX_DIGITS,
        decimal_places=PAYMENT_AMOUNT_DECIMAL_PLACES,
    )
    currency: Currency
    description: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    webhook_url: HttpUrl


class PaymentAccepted(BaseModel):
    payment_id: UUID
    status: PaymentStatus
    created_at: datetime


class PaymentDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_id: UUID
    amount: Decimal
    currency: Currency
    description: str
    metadata: dict[str, Any]
    status: PaymentStatus
    idempotency_key: str
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None
