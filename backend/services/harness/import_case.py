"""从用户平台 ImageEvaluation 导入 Harness TestCase。"""

import json
import uuid

from data.services import AgentDefinitionService, HarnessTestCaseService
from models import GeneratedImage, ImageEvaluation, LookbookTask
from services.seed_admin_data import BUILTIN_AGENT_SLUG


def _human_eval_from_row(ev: ImageEvaluation | None) -> dict:
    if not ev:
        return {}
    return {
        "overall": ev.overall,
        "scores": json.loads(ev.scores_json) if ev.scores_json else {},
        "issues": json.loads(ev.issues_json) if ev.issues_json else [],
        "suggestions": json.loads(ev.suggestions_json) if ev.suggestions_json else [],
        "expert_note": ev.expert_note,
        "reviewer_name": ev.reviewer_name,
    }


def import_from_evaluation(db, image_id: str) -> dict:
    image = db.query(GeneratedImage).filter(GeneratedImage.id == image_id).first()
    if not image:
        raise ValueError("图片不存在")

    ev = (
        db.query(ImageEvaluation)
        .filter(ImageEvaluation.image_id == image_id)
        .order_by(ImageEvaluation.updated_at.desc())
        .first()
    )

    task = db.query(LookbookTask).filter(LookbookTask.id == image.task_id).first()
    sel: dict = {}
    if task and task.selected_materials:
        try:
            sel = json.loads(task.selected_materials)
        except json.JSONDecodeError:
            sel = {}

    business_context = sel.get("business_context") or {}
    if isinstance(business_context, str):
        try:
            business_context = json.loads(business_context)
        except json.JSONDecodeError:
            business_context = {}

    agent_row = None
    rows = AgentDefinitionService(db).list_all()
    agent_row = next((r for r in rows if r.get("slug") == BUILTIN_AGENT_SLUG), None)

    human_eval = _human_eval_from_row(ev)
    name = f"评价导入 · {image.angle or image_id[:8]}"

    svc = HarnessTestCaseService(db)
    existing = svc.list_all()
    for row in existing:
        if row.get("source_image_id") == image_id:
            return svc.update(row["id"], {
                "human_eval_json": human_eval,
                "source_evaluation_id": ev.id if ev else None,
                "acceptance_criteria": image.acceptance_criteria or (task.acceptance_criteria if task else ""),
                "notes": ev.expert_note if ev else row.get("notes"),
            })

    payload = {
        "id": str(uuid.uuid4()),
        "name": name,
        "status": "ready" if human_eval else "draft",
        "agent_id": agent_row.get("id") if agent_row else None,
        "model_id": sel.get("model_id"),
        "clothing_ids_json": sel.get("clothing_ids") or [],
        "reference_id": sel.get("reference_id"),
        "scene_id": sel.get("scene_id"),
        "size": task.size if task else "3:4",
        "quantity": task.quantity if task else 4,
        "business_context_json": business_context,
        "acceptance_criteria": image.acceptance_criteria or (task.acceptance_criteria if task else ""),
        "source_image_id": image_id,
        "source_evaluation_id": ev.id if ev else None,
        "human_eval_json": human_eval,
        "notes": ev.expert_note if ev else f"来自历史任务 {image.task_id[:8] if image.task_id else ''}",
        "prompts_json": [{"angle": image.angle, "prompt": image.prompt}] if image.prompt else [],
    }
    return svc.create(payload)
