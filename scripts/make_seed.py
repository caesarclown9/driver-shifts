"""Generate data/trips.json: a week of plausible Bishkek taxi shifts.

Deterministic (fixed seed) so the file and the numbers in the README stay stable.
Run: uv run --project backend python scripts/make_seed.py
"""

import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

BISHKEK = timezone(timedelta(hours=6))
COMMISSION_RATE = Decimal("0.15")
FIRST_DAY = datetime(2026, 9, 28, tzinfo=BISHKEK)
DAYS = 7
DAY_OFF = 3  # one weekday without trips, so the client shows an empty day

rng = random.Random(20261006)
trips = []
for day_index in range(DAYS):
    if day_index == DAY_OFF:
        continue
    cursor = FIRST_DAY + timedelta(days=day_index, hours=rng.choice([7, 8, 9]), minutes=rng.randrange(0, 60))
    # The last shift runs past midnight to exercise "trip belongs to its start day".
    shift_end = cursor + timedelta(hours=10 if day_index != DAYS - 1 else 16)
    while cursor < shift_end:
        duration = timedelta(minutes=rng.randrange(8, 45))
        amount = Decimal(rng.randrange(150, 900, 10))
        trips.append(
            {
                "id": str(uuid.UUID(int=rng.getrandbits(128), version=4)),
                "started_at": cursor.isoformat(),
                "ended_at": (cursor + duration).isoformat(),
                "amount": str(amount.quantize(Decimal("0.01"))),
                "payment": rng.choices(["cash", "card"], weights=[55, 45])[0],
                "commission": str((amount * COMMISSION_RATE).quantize(Decimal("0.01"), ROUND_HALF_UP)),
            }
        )
        cursor += duration + timedelta(minutes=rng.randrange(5, 40))

out = Path(__file__).resolve().parents[1] / "data" / "trips.json"
out.write_text(json.dumps({"trips": trips}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"{len(trips)} trips -> {out}")
