"""Admin — WorkflowDefinition + dry-run。"""

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from domains.workflow.defaults import LOOKBOOK_PROD_V1
from domains.workflow.runner import run_workflow_preview
from models import WorkflowDefinition

router = APIRouter(prefix="/api/admin/workflows", tags=["workflows"])


def _serialize_wf(row: WorkflowDefinition) -> dict:
    return {
        "id": row.id,
        "workflow_id": row.workflow_id,
        "name": row.name,
        "description": row.description,
        "steps_json": json.loads(row.steps_json) if row.steps_json else [],
        "graph_ref": row.graph_ref,
        "status": row.status,
        "version": row.version,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("")
def list_workflows(db: Session = Depends(get_db)):
    rows = db.query(WorkflowDefinition).order_by(WorkflowDefinition.updated_at.desc()).all()
    return {"items": [_serialize_wf(r) for r in rows]}


@router.get("/{workflow_id}")
def get_workflow(workflow_id: str, db: Session = Depends(get_db)):
    row = db.query(WorkflowDefinition).filter(WorkflowDefinition.workflow_id == workflow_id).first()
    if not row:
        raise HTTPException(404, "Workflow 不存在")
    return _serialize_wf(row)


class DryRunBody(BaseModel):
    model_id: str
    clothing_ids: list[str]
    reference_id: str | None = None
    scene_id: str | None = None
    quantity: int = 4
    size: str = "3:4"
    business_context: dict | None = None
    acceptance_criteria: str | None = None
    workflow_version: str | None = LOOKBOOK_PROD_V1["workflow_id"]


@router.post("/dry-run")
async def dry_run(body: DryRunBody):
    try:
        return await run_workflow_preview(
            body.model_dump(),
            source="admin_dry_run",
            user_id="admin",
            include_user_trace=True,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
