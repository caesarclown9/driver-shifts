import sqlite3
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .domain import Trip
from .money import from_cents, to_cents

SCHEMA = """
CREATE TABLE IF NOT EXISTS trips (
    id               TEXT PRIMARY KEY,
    started_at       TEXT NOT NULL,  -- UTC, fixed-width ISO so text order = time order
    ended_at         TEXT NOT NULL,
    amount_cents     INTEGER NOT NULL CHECK (amount_cents > 0),
    payment          TEXT NOT NULL CHECK (payment IN ('cash', 'card')),
    commission_cents INTEGER NOT NULL CHECK (commission_cents >= 0 AND commission_cents <= amount_cents),
    created_at       TEXT NOT NULL,
    CHECK (ended_at > started_at),
    -- The same trip resent under a new id is still the same trip.
    UNIQUE (started_at, ended_at, amount_cents, payment, commission_cents)
);
CREATE INDEX IF NOT EXISTS trips_started_at ON trips (started_at);
"""

COLUMNS = "id, started_at, ended_at, amount_cents, payment, commission_cents"


class TripConflict(Exception):
    def __init__(self, existing: Trip):
        super().__init__(f"trip {existing.id} already exists with different data")
        self.existing = existing


def _ts(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _row_to_trip(row: sqlite3.Row) -> Trip:
    return Trip(
        id=row["id"],
        started_at=datetime.fromisoformat(row["started_at"]),
        ended_at=datetime.fromisoformat(row["ended_at"]),
        amount=from_cents(row["amount_cents"]),
        payment=row["payment"],
        commission=from_cents(row["commission_cents"]),
    )


class TripStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        # A connection per call: FastAPI runs sync handlers in a thread pool.
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def add(self, trip: Trip) -> tuple[Trip, bool]:
        """Insert a trip once. Returns (stored trip, created).

        Same id + same data or same data under another id -> the stored trip,
        created=False. Same id + different data -> TripConflict.
        BEGIN IMMEDIATE takes the write lock before the lookups, so two
        concurrent submits of one trip cannot both pass the check.
        """
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(f"SELECT {COLUMNS} FROM trips WHERE id = ?", (trip.id,)).fetchone()
                if row is not None:
                    existing = _row_to_trip(row)
                    if not existing.same_content(trip):
                        raise TripConflict(existing)
                    conn.execute("ROLLBACK")
                    return existing, False

                params = (
                    _ts(trip.started_at),
                    _ts(trip.ended_at),
                    to_cents(trip.amount),
                    trip.payment,
                    to_cents(trip.commission),
                )
                row = conn.execute(
                    f"SELECT {COLUMNS} FROM trips WHERE started_at = ? AND ended_at = ?"
                    " AND amount_cents = ? AND payment = ? AND commission_cents = ?",
                    params,
                ).fetchone()
                if row is not None:
                    conn.execute("ROLLBACK")
                    return _row_to_trip(row), False

                conn.execute(
                    f"INSERT INTO trips ({COLUMNS}, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (trip.id, *params, _ts(datetime.now(UTC))),
                )
                conn.execute("COMMIT")
                return trip, True
            except BaseException:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise

    def trips_on(self, day: date, tz: ZoneInfo) -> list[Trip]:
        # A trip belongs to the day it started on, in the driver's timezone.
        start = datetime.combine(day, time.min, tzinfo=tz)
        end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT {COLUMNS} FROM trips WHERE started_at >= ? AND started_at < ? ORDER BY started_at",
                (_ts(start), _ts(end)),
            ).fetchall()
        return [_row_to_trip(r) for r in rows]

    def day_counts(self, tz: ZoneInfo) -> dict[date, int]:
        with self._connect() as conn:
            rows = conn.execute("SELECT started_at FROM trips").fetchall()
        counts = Counter(datetime.fromisoformat(r["started_at"]).astimezone(tz).date() for r in rows)
        return dict(sorted(counts.items()))

    def count(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM trips").fetchone()[0]
