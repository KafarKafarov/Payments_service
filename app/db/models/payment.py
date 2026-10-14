from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import (
    JSONB,
)
from sqlalchemy.dialects.postgresql import (
    UUID as PG_UUID,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.constants import (
    Currency,
    PaymentStatus,
)
from app.core.constants import (
    PAYMENT_AMOUNT_DECIMAL_PLACES,
    PAYMENT_AMOUNT_MAX_DIGITS,
)
from app.db.base import Base


class Payment(Base):
    __tablename__ = 'payments'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(
            precision=PAYMENT_AMOUNT_MAX_DIGITS,
            scale=PAYMENT_AMOUNT_DECIMAL_PLACES,
        ),
    )
    currency: Mapped[Currency] = mapped_column(
        Enum(
            Currency,
            name='payment_currency',
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        )
    )
    description: Mapped[str] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        'metadata',
        JSONB,
        default=dict,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(
            PaymentStatus,
            name='payment_status',
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=PaymentStatus.PENDING,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(128),
        unique=True,
    )
    webhook_url: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    webhook_delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
