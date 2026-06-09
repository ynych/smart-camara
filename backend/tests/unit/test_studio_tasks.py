"""生图工作台任务 API / 域逻辑。"""

from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import LookbookStudioTask


@pytest.fixture()
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    def _get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    os.unlink(path)


def test_list_studio_tasks_empty(client):
    r = client.get("/api/lookbook/studio-tasks")
    assert r.status_code == 200
    assert r.json() == {"tasks": []}


def test_create_and_list_studio_task(client):
    r = client.post("/api/lookbook/studio-tasks", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["id"]
    assert body["status"] == "draft"
    assert body["quantity"] == 4

    r2 = client.get("/api/lookbook/studio-tasks")
    assert r2.status_code == 200
    tasks = r2.json()["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["id"] == body["id"]
