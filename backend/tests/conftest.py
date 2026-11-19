"""Pytest configuration and isolated database/client fixtures for GoldProof."""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings  # noqa: E402
from app.core.crypto import get_signing_key  # noqa: E402
from app.database import Base, create_db_engine, get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.seed import DEMO_PASSWORD, seed_demo_data  # noqa: E402


@pytest.fixture()
def test_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "test_goldproof.db"
    key_dir = tmp_path / "keys"
    db_url = f"sqlite:///{db_file.as_posix()}"

    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("DEV_KEY_DIR", str(key_dir))
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("JWT_SECRET", "test-secret-goldproof-at-least-32-bytes-long")
    get_settings.cache_clear()
    get_signing_key.cache_clear()

    engine = create_db_engine(db_url)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        seed_demo_data(db)
    finally:
        db.close()

    app = create_app()

    def _override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as client:
        yield client, TestingSessionLocal

    engine.dispose()
    get_settings.cache_clear()
    get_signing_key.cache_clear()


def auth_headers(client: TestClient, email: str, password: str = DEMO_PASSWORD) -> dict[str, str]:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
