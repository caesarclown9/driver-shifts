import pytest

from .conftest import trip_payload


def error_fields(response) -> set[str]:
    return {str(e["loc"][-1]) for e in response.json()["detail"]}


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"amount": "0"}, "amount"),
        ({"amount": "0.00"}, "amount"),
        ({"amount": "-100"}, "amount"),
        ({"amount": 420.0}, "amount"),  # numbers rejected: money travels as strings
        ({"amount": "420.005"}, "amount"),
        ({"amount": "abc"}, "amount"),
        ({"amount": "1000000.01"}, "amount"),
        ({"ended_at": "2026-10-06T10:00:00+06:00"}, "ended_at"),  # equal to start
        ({"ended_at": "2026-10-06T09:59:00+06:00"}, "ended_at"),  # before start
        ({"ended_at": "2026-10-07T10:01:00+06:00"}, "ended_at"),  # > 24h
        ({"started_at": "2026-10-06T10:00:00"}, "started_at"),  # no timezone
        ({"payment": "crypto"}, "payment"),
        ({"commission": "-1"}, "commission"),
        ({"commission": "420.01"}, "commission"),
        ({"id": "not-a-uuid"}, "id"),
    ],
)
def test_invalid_trip_is_rejected(client, overrides, field):
    response = client.post("/api/trips", json=trip_payload(**overrides))
    assert response.status_code == 422
    assert field in error_fields(response)
    assert client.get("/api/days/2026-10-06").json()["summary"]["trips"] == 0


def test_missing_field_is_rejected(client):
    payload = trip_payload()
    del payload["commission"]
    response = client.post("/api/trips", json=payload)
    assert response.status_code == 422
    assert "commission" in error_fields(response)


def test_unknown_field_is_rejected(client):
    response = client.post("/api/trips", json=trip_payload(tip="50.00"))
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("amount", "stored"),
    [("0.01", "0.01"), ("1", "1.00"), ("350.5", "350.50"), ("999999.99", "999999.99"), ("1000000", "1000000.00")],
)
def test_boundary_amounts_are_accepted(client, amount, stored):
    response = client.post("/api/trips", json=trip_payload(id=None, amount=amount, commission="0"))
    assert response.status_code == 201
    assert response.json()["trip"]["amount"] == stored


def test_zero_commission_and_full_commission_accepted(client):
    assert client.post("/api/trips", json=trip_payload(id=None, commission="0")).status_code == 201
    r = client.post(
        "/api/trips",
        json=trip_payload(id=None, commission="420.00", started_at="2026-10-06T12:00:00+06:00", ended_at="2026-10-06T12:30:00+06:00"),
    )
    assert r.status_code == 201
