from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

from .conftest import make_settings


def test_serves_built_client_and_api(tmp_path):
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("<!doctype html><title>Дневник смен</title>", encoding="utf-8")
    client = TestClient(create_app(replace(make_settings(tmp_path), static_dir=web)))
    assert "Дневник смен" in client.get("/").text
    assert client.get("/api/days").status_code == 200  # API routes win over the static mount


def test_missing_client_build_fails_fast(tmp_path):
    with pytest.raises(RuntimeError, match="index.html"):
        create_app(replace(make_settings(tmp_path), static_dir=tmp_path / "nope"))
