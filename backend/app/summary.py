from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from .domain import Trip

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class PaymentTotals:
    trips: int
    revenue: Decimal


@dataclass(frozen=True)
class DaySummary:
    trips: int
    revenue: Decimal
    commission: Decimal
    net: Decimal  # «на руки»: revenue minus commission
    cash: PaymentTotals
    card: PaymentTotals


def summarize(trips: Iterable[Trip]) -> DaySummary:
    count = 0
    revenue = commission = ZERO
    by_payment = {"cash": [0, ZERO], "card": [0, ZERO]}
    for trip in trips:
        count += 1
        revenue += trip.amount
        commission += trip.commission
        totals = by_payment[trip.payment]
        totals[0] += 1
        totals[1] += trip.amount
    return DaySummary(
        trips=count,
        revenue=revenue,
        commission=commission,
        net=revenue - commission,
        cash=PaymentTotals(*by_payment["cash"]),
        card=PaymentTotals(*by_payment["card"]),
    )
