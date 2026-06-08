"""从任务/图片构建 Harness 上下文。"""

import json

from database import SessionLocal
from harness.context import HarnessContext
from models import GeneratedImage, ImageEvaluation, LookbookTask, Requirement, PromptModuleRun
from tools.material_tool import MaterialTool


def _parse_json(text: str | None, default=None):
    if not text:
        return default if default is not None else {}
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else {}


def _latest_evaluation(db, image_id: str) -> dict:
    ev = (
        db.query(ImageEvaluation)
        .filter(ImageEvaluation.image_id == image_id)
        .order_by(ImageEvaluation.updated_at.desc())
        .first()
    )
    if not ev:
        return {}
    return {
        "overall": ev.overall,
        "scores": _parse_json(ev.scores_json, {}),
        "issues": _parse_json(ev.issues_json, []),
        "suggestions": _parse_json(ev.suggestions_json, []),
        "expert_note": ev.expert_note or "",
        "ai_draft": ev.ai_draft or "",
    }


def build_context_from_task(
    task: LookbookTask,
    *,
    angle_name: str = "",
    angle_desc: str = "",
    image_id: str = "",
    evaluation: dict | None = None,
    previous_prompt: str = "",
) -> HarnessContext:
    db = SessionLocal()
    try:
        req = db.query(Requirement).filter(Requirement.id == task.requirement_id).first()
        sel = _parse_json(task.selected_materials, {})
        model_id = sel.get("model_id") or ""
        clothing_ids = sel.get("clothing_ids") or []
        reference_id = sel.get("reference_id") or ""
        scene_id = sel.get("scene_id") or ""
        business_context = sel.get("business_context") or {}
        seedream_slots = sel.get("seedream_image_slots") or []

        ctx_dict = {
            "task_id": task.id,
            "image_id": image_id,
            "size": task.size or "3:4",
            "quantity": task.quantity or 4,
            "model_id": model_id,
            "clothing_ids": clothing_ids,
            "reference_id": reference_id,
            "scene_id": scene_id,
            "goal_text": (business_context.get("merchant_need") or "电商 Lookbook 主图/详情页展示"),
            "constraint_text": task.acceptance_criteria or "",
            "angle_name": angle_name,
            "angle_desc": angle_desc,
            "seedream_image_slots": seedream_slots,
            "business_context": business_context,
            "previous_prompt": previous_prompt,
            "evaluation": evaluation or {},
        }
        if image_id and not evaluation:
            ctx_dict["evaluation"] = _latest_evaluation(db, image_id)

        material_ids = [x for x in [model_id, *clothing_ids, reference_id, scene_id] if x]
        materials = {m["id"]: m for m in MaterialTool.get_by_ids(material_ids)} if material_ids else {}
        ctx_dict["materials"] = materials

        if req and req.source_image_path:
            ctx_dict.setdefault("scene_desc", "电商Lookbook拍摄场景")

        return HarnessContext.from_dict(ctx_dict)
    finally:
        db.close()


def build_context_from_image(image_id: str) -> HarnessContext:
    db = SessionLocal()
    try:
        image = db.query(GeneratedImage).filter(GeneratedImage.id == image_id).first()
        if not image:
            raise ValueError("图片不存在")
        task = db.query(LookbookTask).filter(LookbookTask.id == image.task_id).first()
        if not task:
            raise ValueError("关联任务不存在")
        evaluation = _latest_evaluation(db, image_id)
        return build_context_from_task(
            task,
            angle_name=image.angle or "",
            angle_desc=image.angle or "",
            image_id=image_id,
            evaluation=evaluation,
            previous_prompt=image.prompt or "",
        )
    finally:
        db.close()


def save_module_runs(image_id: str, task_id: str, pipeline_result: dict) -> None:
    db = SessionLocal()
    try:
        for mod in pipeline_result.get("modules") or []:
            db.add(
                PromptModuleRun(
                    image_id=image_id,
                    task_id=task_id,
                    pipeline_id=pipeline_result.get("pipeline_id"),
                    module_id=mod.get("module_id"),
                    input_json=json.dumps(mod.get("params_snapshot") or {}, ensure_ascii=False),
                    output_text=mod.get("text") or "",
                    tool_traces_json=json.dumps(mod.get("tool_traces") or [], ensure_ascii=False),
                )
            )
        db.commit()
    finally:
        db.close()
