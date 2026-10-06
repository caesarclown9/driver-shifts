from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app.main import Settings, create_app
from app.store import TripStore

SEED = Path(__file__).resolve().parents[2] / "data" / "trips.json"
TZ = ZoneInfo("Asia/Bishkek")


def make_settings(tmp_path: Path, seed: Path | None = None) -> Settings:
    return Settings(db_path=tmp_path / "trips.db", seed_path=seed, timezone=TZ, currency="KGS")


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(make_settings(tmp_path)))


@pytest.fixture
def seeded_client(tmp_path):
    return TestClient(create_app(make_settings(tmp_path, SEED)))


@pytest.fixture
def store(tmp_path):
    return TripStore(tmp_path / "trips.db")


def trip_payload(**overrides) -> dict:
    payload = {
        "id": "2b0f2c1e-5d7a-4f8e-9c3b-1a2b3c4d5e6f",
        "started_at": "2026-10-06T10:00:00+06:00",
        "ended_at": "2026-10-06T10:25:00+06:00",
        "amount": "420.00",
        "payment": "cash",
        "commission": "63.00",
    }
    payload.update(overrides)
    return {k: v for k, v in payload.items() if v is not None}
