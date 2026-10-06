"""Money is Decimal end to end: strings on the wire, integer tyiyn in SQLite.

All inputs are limited to 2 decimal places and the summary only adds and
subtracts them, so no rounding happens anywhere — there is no rounding rule
to keep consistent between backend, client and reports.
"""

import re
from decimal import Decimal

CENT = Decimal("0.01")
MAX_AMOUNT = Decimal("1000000.00")

_MONEY_RE = re.compile(r"^-?\d{1,9}(\.\d{1,2})?$")


def parse_money(raw: object) -> Decimal:
    # Floats are rejected on purpose: 0.1 + 0.2 must stay 0.3.
    if not isinstance(raw, str):
        raise ValueError("money must be a string like \"350.00\", not a number")
    text = raw.strip()
    if not _MONEY_RE.fullmatch(text):
        raise ValueError("money must look like \"350\" or \"350.50\" (max 2 decimal places)")
    return Decimal(text).quantize(CENT)


def to_cents(value: Decimal) -> int:
    cents = value * 100
    if cents != cents.to_integral_value():
        raise ValueError(f"{value} has more than 2 decimal places")
    return int(cents)


def from_cents(cents: int) -> Decimal:
    return (Decimal(cents) / 100).quantize(CENT)


def format_money(value: Decimal) -> str:
    return str(value.quantize(CENT))
