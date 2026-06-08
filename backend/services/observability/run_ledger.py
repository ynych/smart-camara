"""本地 SQLite 运行账本（替代 Langfuse，单机零依赖）。"""

import json
import time
from contextlib import contextmanager
from typing import Any, Generator
from uuid import uuid4

from database import SessionLocal
from models import AgentRun


def _dump(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


@contextmanager
def agent_run(
    run_type: str,
    *,
    session_id: str | None = None,
    user_id: str = "admin",
    agent_id: str | None = None,
    ref_type: str | None = None,
    ref_id: str | None = None,
    input: dict | None = None,
    metadata: dict | None = None,
) -> Generator[dict[str, Any], None, None]:
    """创建运行记录，退出时写入 output / steps / 耗时。"""
    run_id = str(uuid4())
    sid = session_id or str(uuid4())
    ctx: dict[str, Any] = {
        "run_id": run_id,
        "session_id": sid,
        "steps": [],
        "output": None,
        "error": None,
        "module_snapshot": metadata.get("module_snapshot") if metadata else None,
    }
    started = time.perf_counter()
    db = SessionLocal()
    try:
        row = AgentRun(
            id=run_id,
            run_type=run_type,
            session_id=sid,
            user_id=user_id,
            agent_id=agent_id,
            ref_type=ref_type,
            ref_id=ref_id,
            status="running",
            input_json=_dump(input),
            meta_json=_dump(metadata),
        )
        db.add(row)
        db.commit()
    finally:
        db.close()

    try:
        yield ctx
        status = "failed" if ctx.get("error") else "success"
        _finalize(run_id, ctx, started, status)
    except Exception as exc:
        ctx["error"] = str(exc)
        _finalize(run_id, ctx, started, "failed")
        raise


def _finalize(run_id: str, ctx: dict, started: float, status: str):
    duration_ms = int((time.perf_counter() - started) * 1000)
    db = SessionLocal()
    try:
        row = db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not row:
            return
        row.status = status
        row.duration_ms = duration_ms
        row.output_json = _dump(ctx.get("output"))
        steps = ctx.get("steps")
        if steps:
            row.steps_json = _dump(steps)
        if ctx.get("error"):
            row.error_message = ctx["error"]
        if ctx.get("module_snapshot"):
            row.module_snapshot_json = _dump(ctx["module_snapshot"])
        db.commit()
    finally:
        db.close()


def record_run(
    *,
    run_type: str,
    status: str = "success",
    session_id: str | None = None,
    user_id: str = "admin",
    agent_id: str | None = None,
    ref_type: str | None = None,
    ref_id: str | None = None,
    input: dict | None = None,
    output: dict | None = None,
    steps: list | None = None,
    error_message: str | None = None,
    duration_ms: int | None = None,
    module_snapshot: list | None = None,
) -> str:
    """一次性写入运行记录（Harness 生图/评价等）。"""
    run_id = str(uuid4())
    db = SessionLocal()
    try:
        db.add(AgentRun(
            id=run_id,
            run_type=run_type,
            session_id=session_id or str(uuid4()),
            user_id=user_id,
            agent_id=agent_id,
            ref_type=ref_type,
            ref_id=ref_id,
            status=status,
            input_json=_dump(input),
            output_json=_dump(output),
            steps_json=_dump(steps),
            error_message=error_message,
            duration_ms=duration_ms,
            module_snapshot_json=_dump(module_snapshot),
        ))
        db.commit()
    finally:
        db.close()
    return run_id
