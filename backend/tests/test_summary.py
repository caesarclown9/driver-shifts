import json
from datetime import UTC, datetime
from decimal import Decimal

from app.domain import Trip
from app.summary import summarize

from .conftest import SEED, trip_payload


def trip(amount: str, commission: str, payment: str = "cash", n: int = 0) -> Trip:
    start = datetime(2026, 10, 6, 4, n, tzinfo=UTC)
    return Trip(
        id=f"t{n}",
        started_at=start,
        ended_at=start.replace(minute=n + 1),
        amount=Decimal(amount),
        payment=payment,
        commission=Decimal(commission),
    )


def test_empty_day_is_all_zeros():
    s = summarize([])
    assert (s.trips, s.revenue, s.commission, s.net) == (0, Decimal("0.00"), Decimal("0.00"), Decimal("0.00"))
    assert (s.cash.trips, s.cash.revenue, s.card.trips, s.card.revenue) == (0, 0, 0, 0)


def test_mixed_payments():
    s = summarize(
        [
            trip("500.00", "75.00", "cash", 1),
            trip("320.50", "48.08", "card", 2),
            trip("180.00", "27.00", "cash", 3),
        ]
    )
    assert s.trips == 3
    assert s.revenue == Decimal("1000.50")
    assert s.commission == Decimal("150.08")
    assert s.net == Decimal("850.42")
    assert (s.cash.trips, s.cash.revenue) == (2, Decimal("680.00"))
    assert (s.card.trips, s.card.revenue) == (1, Decimal("320.50"))


def test_sums_are_exact_not_float():
    # 0.1 + 0.2 in float is 0.30000000000000004
    s = summarize([trip("0.10", "0.00", n=1), trip("0.20", "0.00", n=2)])
    assert s.revenue == Decimal("0.30")
    assert str(s.revenue) == "0.30"


def test_api_day_matches_file(seeded_client):
    """Invariant: for every day the API totals equal a direct sum over the seed file."""
    seed = json.loads(SEED.read_text())["trips"]
    days = seeded_client.get("/api/days").json()["days"]
    assert sum(d["trips"] for d in days) == len(seed)

    for day in days:
        body = seeded_client.get(f"/api/days/{day['date']}").json()
        expected = [t for t in seed if datetime.fromisoformat(t["started_at"]).date().isoformat() == day["date"]]
        s = body["summary"]
        assert s["trips"] == len(expected) == len(body["trips"])
        revenue = sum(Decimal(t["amount"]) for t in expected)
        commission = sum(Decimal(t["commission"]) for t in expected)
        assert Decimal(s["revenue"]) == revenue
        assert Decimal(s["commission"]) == commission
        assert Decimal(s["net"]) == revenue - commission
        assert Decimal(s["cash"]["revenue"]) + Decimal(s["card"]["revenue"]) == revenue
        assert s["cash"]["trips"] + s["card"]["trips"] == s["trips"]


def test_day_response_shape(client):
    client.post("/api/trips", json=trip_payload())
    body = client.get("/api/days/2026-10-06").json()
    assert body["summary"] == {
        "trips": 1,
        "revenue": "420.00",
        "commission": "63.00",
        "net": "357.00",
        "cash": {"trips": 1, "revenue": "420.00"},
        "card": {"trips": 0, "revenue": "0.00"},
    }
    assert body["trips"][0]["duration_min"] == 25
    assert body["trips"][0]["started_at"] == "2026-10-06T10:00:00+06:00"


def test_empty_day_via_api(client):
    body = client.get("/api/days/2026-01-01").json()
    assert body["trips"] == []
    assert body["summary"]["revenue"] == "0.00"


def test_trip_belongs_to_local_start_day(client):
    # 00:30 in Bishkek is 18:30 UTC of the previous day — must land on the local day.
    client.post(
        "/api/trips",
        json=trip_payload(id=None, started_at="2026-10-07T00:30:00+06:00", ended_at="2026-10-07T00:50:00+06:00"),
    )
    # Crosses midnight — counted on the day it started.
    client.post(
        "/api/trips",
        json=trip_payload(id=None, started_at="2026-10-06T23:50:00+06:00", ended_at="2026-10-07T00:20:00+06:00"),
    )
    assert client.get("/api/days/2026-10-06").json()["summary"]["trips"] == 1
    assert client.get("/api/days/2026-10-07").json()["summary"]["trips"] == 1
    assert [d["date"] for d in client.get("/api/days").json()["days"]] == ["2026-10-06", "2026-10-07"]


def test_bad_date_is_422(client):
    assert client.get("/api/days/2026-13-45").status_code == 422
