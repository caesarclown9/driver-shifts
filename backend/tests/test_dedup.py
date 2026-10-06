import threading
import uuid

from app.main import create_app, load_seed
from app.schemas import TripIn
from app.store import TripStore

from .conftest import SEED, make_settings, trip_payload


def day_count(client, day="2026-10-06") -> int:
    return client.get(f"/api/days/{day}").json()["summary"]["trips"]


def test_resend_same_trip_returns_existing(client):
    first = client.post("/api/trips", json=trip_payload())
    second = client.post("/api/trips", json=trip_payload())
    assert (first.status_code, first.json()["created"]) == (201, True)
    assert (second.status_code, second.json()["created"]) == (200, False)
    assert second.json()["trip"] == first.json()["trip"]
    assert day_count(client) == 1


def test_resend_without_id_is_deduplicated(client):
    first = client.post("/api/trips", json=trip_payload(id=None))
    second = client.post("/api/trips", json=trip_payload(id=None))
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json()["trip"]["id"] == second.json()["trip"]["id"]
    assert day_count(client) == 1


def test_same_trip_under_new_id_is_deduplicated(client):
    first = client.post("/api/trips", json=trip_payload())
    second = client.post("/api/trips", json=trip_payload(id=str(uuid.uuid4())))
    assert second.status_code == 200
    assert second.json()["trip"]["id"] == first.json()["trip"]["id"]
    assert day_count(client) == 1


def test_same_instant_in_other_offset_is_same_trip(client):
    client.post("/api/trips", json=trip_payload(id=None))
    utc = client.post(
        "/api/trips",
        json=trip_payload(id=None, started_at="2026-10-06T04:00:00Z", ended_at="2026-10-06T04:25:00Z"),
    )
    assert utc.status_code == 200
    assert day_count(client) == 1


def test_same_id_with_different_data_is_conflict(client):
    client.post("/api/trips", json=trip_payload())
    clash = client.post("/api/trips", json=trip_payload(amount="999.00"))
    assert clash.status_code == 409
    assert clash.json()["detail"]["code"] == "trip_conflict"
    day = client.get("/api/days/2026-10-06").json()
    assert day["summary"]["trips"] == 1
    assert day["trips"][0]["amount"] == "420.00"  # original untouched


def test_different_trips_are_both_kept(client):
    client.post("/api/trips", json=trip_payload(id=None))
    other = client.post(
        "/api/trips",
        json=trip_payload(id=None, started_at="2026-10-06T11:00:00+06:00", ended_at="2026-10-06T11:10:00+06:00"),
    )
    assert other.status_code == 201
    assert day_count(client) == 2


def test_concurrent_submits_create_one_row(store):
    trip = TripIn.model_validate(trip_payload()).to_trip()
    results, errors = [], []
    barrier = threading.Barrier(16)

    def submit():
        try:
            barrier.wait()
            results.append(store.add(trip)[1])
        except Exception as exc:  # surfaced below, never swallowed
            errors.append(exc)

    threads = [threading.Thread(target=submit) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert results.count(True) == 1
    assert store.count() == 1


def test_concurrent_same_content_new_ids_create_one_row(store):
    trips = [TripIn.model_validate(trip_payload(id=str(uuid.uuid4()))).to_trip() for _ in range(16)]
    barrier = threading.Barrier(len(trips))
    created = []

    def submit(t):
        barrier.wait()
        created.append(store.add(t)[1])

    threads = [threading.Thread(target=submit, args=(t,)) for t in trips]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert created.count(True) == 1
    assert store.count() == 1


def test_restart_does_not_duplicate_seed(tmp_path):
    settings = make_settings(tmp_path, SEED)
    create_app(settings)
    create_app(settings)  # second start over the same database
    store = TripStore(settings.db_path)
    total, created = load_seed(store, SEED)
    assert created == 0
    assert store.count() == total
