"""从用户评价导入黄金评测集。"""

import json

from data.services import GoldenEvalCaseService
from models import GeneratedImage, ImageEvaluation, LookbookTask


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
    sel = {}
    if task and task.selected_materials:
        try:
            sel = json.loads(task.selected_materials)
        except json.JSONDecodeError:
            sel = {}

    context = {
        "model_id": sel.get("model_id"),
        "clothing_ids": sel.get("clothing_ids") or [],
        "reference_id": sel.get("reference_id"),
        "scene_id": sel.get("scene_id"),
        "size": task.size if task else "3:4",
        "quantity": 1,
        "business_context": sel.get("business_context") or {},
        "acceptance_criteria": image.acceptance_criteria or (task.acceptance_criteria if task else ""),
        "angle": image.angle,
    }
    human_eval = {}
    if ev:
        human_eval = {
            "overall": ev.overall,
            "scores": json.loads(ev.scores_json) if ev.scores_json else {},
            "issues": json.loads(ev.issues_json) if ev.issues_json else [],
            "suggestions": json.loads(ev.suggestions_json) if ev.suggestions_json else [],
            "expert_note": ev.expert_note,
        }

    svc = GoldenEvalCaseService(db)
    return svc.create({
        "name": f"评价导入 {image.angle or image_id[:8]}",
        "source_type": "evaluation",
        "source_ref": image_id,
        "context_json": context,
        "human_eval_json": human_eval,
        "baseline_output_json": {"prompt": image.prompt},
        "pass_label": 1 if ev and ev.overall == "good" else 0 if ev and ev.overall == "poor" else None,
        "notes": ev.expert_note if ev else "",
    })
