import json
import logging
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Response, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .money import format_money
from .schemas import SeedFile, TripIn, trip_out
from .store import TripConflict, TripStore
from .summary import DaySummary, summarize

log = logging.getLogger("driver_shifts")

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    db_path: Path
    seed_path: Path | None
    timezone: ZoneInfo
    currency: str
    static_dir: Path | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        seed = os.environ.get("DS_SEED_PATH", str(ROOT / "data" / "trips.json"))
        return cls(
            db_path=Path(os.environ.get("DS_DB_PATH", str(ROOT / "backend" / "var" / "trips.db"))),
            seed_path=Path(seed) if seed else None,
            timezone=ZoneInfo(os.environ.get("DS_TIMEZONE", "Asia/Bishkek")),
            currency=os.environ.get("DS_CURRENCY", "KGS"),
            static_dir=Path(os.environ["DS_STATIC_DIR"]) if os.environ.get("DS_STATIC_DIR") else None,
        )


def load_seed(store: TripStore, path: Path) -> tuple[int, int]:
    """Load trips from the JSON file. Safe to run on every start: known trips are skipped.

    One invalid trip fails the whole load with its index — silently skipping it
    would make the day totals quietly wrong.
    """
    seed = SeedFile.model_validate(json.loads(path.read_text(encoding="utf-8")))
    created = 0
    for trip_in in seed.trips:
        _, was_created = store.add(trip_in.to_trip())
        created += was_created
    return len(seed.trips), created


def summary_out(summary: DaySummary) -> dict:
    return {
        "trips": summary.trips,
        "revenue": format_money(summary.revenue),
        "commission": format_money(summary.commission),
        "net": format_money(summary.net),
        "cash": {"trips": summary.cash.trips, "revenue": format_money(summary.cash.revenue)},
        "card": {"trips": summary.card.trips, "revenue": format_money(summary.card.revenue)},
    }


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    store = TripStore(settings.db_path)
    if settings.seed_path and settings.seed_path.exists():
        total, created = load_seed(store, settings.seed_path)
        log.info("seed %s: %d trips in file, %d new", settings.seed_path, total, created)

    app = FastAPI(title="Driver shift diary")
    tz = settings.timezone

    @app.get("/api/days")
    def list_days() -> dict:
        return {
            "timezone": tz.key,
            "currency": settings.currency,
            "days": [{"date": d.isoformat(), "trips": n} for d, n in store.day_counts(tz).items()],
        }

    @app.get("/api/days/{day}")
    def get_day(day: date) -> dict:
        trips = store.trips_on(day, tz)
        return {
            "date": day.isoformat(),
            "timezone": tz.key,
            "currency": settings.currency,
            "summary": summary_out(summarize(trips)),
            "trips": [trip_out(t, tz) for t in trips],
        }

    @app.post("/api/trips", status_code=status.HTTP_201_CREATED)
    def add_trip(payload: TripIn, response: Response):
        trip = payload.to_trip()
        try:
            stored, created = store.add(trip)
        except TripConflict as exc:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "detail": {
                        "code": "trip_conflict",
                        "message": "A trip with this id already exists with different data",
                        "existing": trip_out(exc.existing, tz),
                    }
                },
            )
        if not created:
            response.status_code = status.HTTP_200_OK
        return {"created": created, "trip": trip_out(stored, tz)}

    # Production image: the built client is served by the API itself, one origin, no CORS.
    # Mounted last so /api routes win.
    if settings.static_dir:
        if not (settings.static_dir / "index.html").exists():
            raise RuntimeError(f"DS_STATIC_DIR={settings.static_dir} has no index.html — build the client first")
        app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="web")

    return app
