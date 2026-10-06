from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

Payment = Literal["cash", "card"]

MAX_TRIP_DURATION = timedelta(hours=24)


@dataclass(frozen=True)
class Trip:
    id: str
    started_at: datetime  # timezone-aware, UTC
    ended_at: datetime
    amount: Decimal
    payment: Payment
    commission: Decimal

    @property
    def net(self) -> Decimal:
        return self.amount - self.commission

    def same_content(self, other: "Trip") -> bool:
        return (
            self.started_at == other.started_at
            and self.ended_at == other.ended_at
            and self.amount == other.amount
            and self.payment == other.payment
            and self.commission == other.commission
        )


def to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("datetime must include a timezone offset")
    return value.astimezone(UTC)
