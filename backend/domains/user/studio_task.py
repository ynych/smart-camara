"""用户域 — 生图工作台任务。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from models import LookbookStudioTask


def _loads(val: Any, default: Any) -> Any:
    if val is None:
        return default
    if isinstance(val, str):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            return default
    return val


def serialize_studio_task(row: LookbookStudioTask) -> dict[str, Any]:
    return {
        "id": row.id,
        "title": row.title,
        "status": row.status,
        "model_id": row.model_id,
        "model_name": row.model_name,
        "clothing_ids": _loads(row.clothing_ids_json, []),
        "reference_id": row.reference_id,
        "scene_id": row.scene_id,
        "size": row.size,
        "quantity": row.quantity,
        "business_context": _loads(row.business_context_json, {}),
        "acceptance_criteria": row.acceptance_criteria or "",
        "prompts": _loads(row.prompts_json, []),
        "prompt_run_id": row.prompt_run_id,
        "lookbook_task_id": row.lookbook_task_id,
        "error_message": row.error_message,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def build_title(model_name: str | None, quantity: int) -> str:
    name = (model_name or "未命名任务").strip()
    ts = datetime.utcnow().strftime("%m-%d %H:%M")
    return f"{name} · {quantity}张 · {ts}"


def list_studio_tasks(db, *, incomplete_only: bool = False) -> list[dict[str, Any]]:
    q = db.query(LookbookStudioTask).order_by(LookbookStudioTask.updated_at.desc())
    if incomplete_only:
        q = q.filter(LookbookStudioTask.status.in_(["draft", "prompts_ready", "generating", "failed"]))
    return [serialize_studio_task(r) for r in q.all()]


def get_studio_task(db, task_id: str) -> dict[str, Any] | None:
    row = db.query(LookbookStudioTask).filter(LookbookStudioTask.id == task_id).first()
    return serialize_studio_task(row) if row else None


def create_studio_task(db, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    qty = int(payload.get("quantity") or 4)
    row = LookbookStudioTask(
        id=str(uuid.uuid4()),
        title=payload.get("title") or build_title(payload.get("model_name"), qty),
        status="draft",
        model_id=payload.get("model_id"),
        model_name=payload.get("model_name"),
        clothing_ids_json=json.dumps(payload.get("clothing_ids") or [], ensure_ascii=False),
        reference_id=payload.get("reference_id"),
        scene_id=payload.get("scene_id"),
        size=payload.get("size") or "3:4",
        quantity=qty,
        business_context_json=json.dumps(payload.get("business_context") or {}, ensure_ascii=False),
        acceptance_criteria=payload.get("acceptance_criteria") or "",
        prompts_json=json.dumps(payload.get("prompts") or [], ensure_ascii=False),
    )
    db.add(row)
    db.flush()
    return serialize_studio_task(row)


def update_studio_task(db, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    row = db.query(LookbookStudioTask).filter(LookbookStudioTask.id == task_id).first()
    if not row:
        raise ValueError("任务不存在")
    if row.status == "completed":
        raise ValueError("已完成任务不可编辑")

    if "model_id" in payload:
        row.model_id = payload["model_id"]
    if "model_name" in payload:
        row.model_name = payload["model_name"]
    if "clothing_ids" in payload:
        row.clothing_ids_json = json.dumps(payload["clothing_ids"], ensure_ascii=False)
    if "reference_id" in payload:
        row.reference_id = payload["reference_id"]
    if "scene_id" in payload:
        row.scene_id = payload["scene_id"]
    if "size" in payload:
        row.size = payload["size"]
    if "quantity" in payload:
        row.quantity = int(payload["quantity"])
    if "business_context" in payload:
        row.business_context_json = json.dumps(payload["business_context"], ensure_ascii=False)
    if "acceptance_criteria" in payload:
        row.acceptance_criteria = payload["acceptance_criteria"]
    if "prompts" in payload:
        row.prompts_json = json.dumps(payload["prompts"], ensure_ascii=False)
    if "prompt_run_id" in payload:
        row.prompt_run_id = payload["prompt_run_id"]
    if "status" in payload:
        row.status = payload["status"]
    if "lookbook_task_id" in payload:
        row.lookbook_task_id = payload["lookbook_task_id"]
    if "error_message" in payload:
        row.error_message = payload["error_message"]
    if "title" in payload:
        row.title = payload["title"]
    elif row.model_name:
        row.title = build_title(row.model_name, row.quantity or 4)

    row.updated_at = datetime.utcnow()
    db.flush()
    return serialize_studio_task(row)


def apply_prompt_preview(db, task_id: str, preview: dict[str, Any]) -> dict[str, Any]:
    prompts = preview.get("prompts") or []
    return update_studio_task(db, task_id, {
        "prompts": prompts,
        "prompt_run_id": preview.get("prompt_run_id"),
        "acceptance_criteria": preview.get("acceptance_criteria") or "",
        "status": "prompts_ready" if prompts else "draft",
    })
