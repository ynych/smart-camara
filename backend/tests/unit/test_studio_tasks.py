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


def test_patch_studio_task_restores_selection_and_prompts(client):
    tid = client.post("/api/lookbook/studio-tasks", json={}).json()["id"]
    r = client.patch(
        f"/api/lookbook/studio-tasks/{tid}",
        json={
            "model_id": "model-1",
            "model_name": "模特 A",
            "clothing_ids": ["cloth-1", "cloth-2"],
            "reference_id": "ref-1",
            "size": "3:4",
            "quantity": 4,
            "business_context": {"merchant_need": "主图", "target_audience": "女性"},
            "acceptance_criteria": "验收标准",
            "prompts": [{"index": 0, "angle_name": "正面", "prompt": "提示词内容"}],
            "status": "prompts_ready",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["model_id"] == "model-1"
    assert body["clothing_ids"] == ["cloth-1", "cloth-2"]
    assert body["reference_id"] == "ref-1"
    assert body["prompts"][0]["prompt"] == "提示词内容"
    assert body["status"] == "prompts_ready"

    r2 = client.get(f"/api/lookbook/studio-tasks/{tid}")
    assert r2.status_code == 200
    assert r2.json()["model_name"] == "模特 A"
