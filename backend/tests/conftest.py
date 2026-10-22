import os
import tempfile

# Must be set before app modules are imported: the engine is built at import time.
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["FOOTBALL_DATA_KEY"] = ""
os.environ["AUTH_SECRET"] = "test-secret"

import pytest

from app.auth import limiter
from app.db.database import Base, SessionLocal, engine, init_db


@pytest.fixture(autouse=True)
def _fresh_limiter():
    limiter.reset()
    yield


@pytest.fixture()
def db():
    init_db()
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
