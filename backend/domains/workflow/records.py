"""prompt_run_records 持久化。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from models import PromptRunRecord


def create_prompt_run_record(
    db,
    *,
    pack_id: str | None,
    pack_version: int | None,
    inputs: dict[str, Any],
    prompts: list[Any],
    acceptance_criteria: str,
    source: str,
    workflow_version: str,
    agent_run_id: str | None = None,
    studio_task_id: str | None = None,
) -> dict[str, Any]:
    row = PromptRunRecord(
        id=str(uuid.uuid4()),
        pack_id=pack_id,
        pack_version=pack_version,
        inputs_json=json.dumps(inputs, ensure_ascii=False),
        prompts_json=json.dumps(prompts, ensure_ascii=False),
        acceptance_criteria=acceptance_criteria,
        source=source,
        workflow_version=workflow_version,
        agent_run_id=agent_run_id,
        studio_task_id=studio_task_id,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.flush()
    return serialize_record(row)


def get_prompt_run_record(db, record_id: str) -> dict[str, Any] | None:
    row = db.query(PromptRunRecord).filter(PromptRunRecord.id == record_id).first()
    return serialize_record(row) if row else None


def serialize_record(row: PromptRunRecord) -> dict[str, Any]:
    return {
        "id": row.id,
        "pack_id": row.pack_id,
        "pack_version": row.pack_version,
        "inputs_json": json.loads(row.inputs_json) if row.inputs_json else {},
        "prompts_json": json.loads(row.prompts_json) if row.prompts_json else [],
        "acceptance_criteria": row.acceptance_criteria,
        "source": row.source,
        "workflow_version": row.workflow_version,
        "agent_run_id": row.agent_run_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
