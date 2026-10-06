import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    PlainValidator,
    ValidationInfo,
    WithJsonSchema,
    field_validator,
)

from .domain import MAX_TRIP_DURATION, Payment, Trip, to_utc
from .money import MAX_AMOUNT, format_money, parse_money, to_cents

# Trips sent without an id get one derived from their content, so a blind
# retry of the same trip maps to the same id instead of a new row.
TRIP_ID_NAMESPACE = uuid.UUID("6f1d3c52-8f0e-4c55-9d3a-7b2f4e1a9c10")

Money = Annotated[
    Decimal,
    PlainValidator(parse_money),
    WithJsonSchema({"type": "string", "pattern": r"^\d{1,9}(\.\d{1,2})?$", "examples": ["350.00"]}),
]


class TripIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID | None = None
    started_at: AwareDatetime
    ended_at: AwareDatetime
    amount: Money
    payment: Payment
    commission: Money

    # Cross-field checks live on the later field so the error points at it
    # (loc = ended_at / commission), which the client shows next to the input.
    @field_validator("ended_at")
    @classmethod
    def _ends_after_start(cls, ended_at: datetime, info: ValidationInfo) -> datetime:
        started_at = info.data.get("started_at")
        if started_at is None:
            return ended_at
        if ended_at <= started_at:
            raise ValueError("trip must end after it starts")
        if ended_at - started_at > MAX_TRIP_DURATION:
            raise ValueError("trip cannot be longer than 24 hours")
        return ended_at

    @field_validator("amount")
    @classmethod
    def _amount_in_range(cls, amount: Decimal) -> Decimal:
        if amount <= 0:
            raise ValueError("amount must be greater than 0")
        if amount > MAX_AMOUNT:
            raise ValueError(f"amount cannot exceed {MAX_AMOUNT}")
        return amount

    @field_validator("commission")
    @classmethod
    def _commission_in_range(cls, commission: Decimal, info: ValidationInfo) -> Decimal:
        if commission < 0:
            raise ValueError("commission cannot be negative")
        amount = info.data.get("amount")
        if amount is not None and commission > amount:
            raise ValueError("commission cannot exceed the trip amount")
        return commission

    def to_trip(self) -> Trip:
        started_at = to_utc(self.started_at)
        ended_at = to_utc(self.ended_at)
        trip_id = self.id or uuid.uuid5(
            TRIP_ID_NAMESPACE,
            "|".join(
                [
                    started_at.isoformat(),
                    ended_at.isoformat(),
                    str(to_cents(self.amount)),
                    self.payment,
                    str(to_cents(self.commission)),
                ]
            ),
        )
        return Trip(
            id=str(trip_id),
            started_at=started_at,
            ended_at=ended_at,
            amount=self.amount,
            payment=self.payment,
            commission=self.commission,
        )


class SeedFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trips: list[TripIn]


def trip_out(trip: Trip, tz) -> dict:
    return {
        "id": trip.id,
        "started_at": trip.started_at.astimezone(tz).isoformat(),
        "ended_at": trip.ended_at.astimezone(tz).isoformat(),
        "duration_min": int((trip.ended_at - trip.started_at).total_seconds() // 60),
        "amount": format_money(trip.amount),
        "commission": format_money(trip.commission),
        "net": format_money(trip.net),
        "payment": trip.payment,
    }
