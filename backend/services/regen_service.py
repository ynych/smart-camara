"""单张图片 prompt 优化与局部重生。"""

import json

from database import SessionLocal
from harness.engine import run_pipeline
from models import GeneratedImage, LookbookTask
from services.harness_service import build_context_from_image, save_module_runs
from skills.lookbook_skill import LookbookSkill
from tools.material_tool import MaterialTool


async def optimize_prompt_for_image(image_id: str, *, confirmed_prompt: str | None = None) -> dict:
    """根据评价 Harness 组装优化后的 prompt（人工确认前返回 diff 预览）。"""
    db = SessionLocal()
    try:
        image = db.query(GeneratedImage).filter(GeneratedImage.id == image_id).first()
        if not image:
            raise ValueError("图片不存在")
        previous = image.prompt or ""
    finally:
        db.close()

    ctx = build_context_from_image(image_id)
    ctx.previous_prompt = previous
    ctx.regen_text = ctx.evaluation.get("expert_note") or ""
    result = run_pipeline(ctx, include_regen=True)
    optimized = result["prompt"]
    if confirmed_prompt:
        optimized = confirmed_prompt.strip()

    return {
        "image_id": image_id,
        "previous_prompt": previous,
        "optimized_prompt": optimized,
        "modules": result.get("modules") or [],
        "pipeline_id": result.get("pipeline_id"),
        "needs_confirmation": confirmed_prompt is None,
    }


async def regenerate_image(image_id: str, prompt: str) -> dict:
    """单张局部重生：使用确认后的 prompt，保留素材与 Seedream 图序。"""
    if not (prompt or "").strip():
        raise ValueError("请提供确认后的 prompt")

    db = SessionLocal()
    try:
        parent = db.query(GeneratedImage).filter(GeneratedImage.id == image_id).first()
        if not parent:
            raise ValueError("原图不存在")
        task = db.query(LookbookTask).filter(LookbookTask.id == parent.task_id).first()
        if not task:
            raise ValueError("任务不存在")

        sel = {}
        if task.selected_materials:
            try:
                sel = json.loads(task.selected_materials)
            except json.JSONDecodeError:
                sel = {}

        model_id = sel.get("model_id")
        clothing_ids = sel.get("clothing_ids") or []
        reference_id = sel.get("reference_id")
        scene_id = sel.get("scene_id")
        size = task.size or "3:4"
        parent_round = parent.generation_round or 1
        task_round = (task.generation_round or 1) + 1
        parent_angle = parent.angle or ""
        parent_task_id = parent.task_id
        parent_acceptance = parent.acceptance_criteria
        parent_id = parent.id
    finally:
        db.close()

    skill = LookbookSkill()
    material_ids = [x for x in [model_id, *clothing_ids, reference_id, scene_id] if x]
    materials = MaterialTool.get_by_ids(material_ids)
    material_map = {m["id"]: m for m in materials}
    reference_images, image_roles_prefix, _image_slots = skill._build_seedream_reference_bundle(
        material_map, model_id, clothing_ids, reference_id, scene_id,
    )

    ctx = build_context_from_image(image_id)
    ctx.angle_name = parent_angle
    ctx.angle_desc = parent_angle
    ctx.regen_text = ctx.evaluation.get("expert_note") or ""
    pipeline_result = run_pipeline(ctx, include_regen=True)
    final_prompt = skill._prepend_image_roles(prompt.strip(), image_roles_prefix)

    image_content = await skill.image_tool.generate(
        final_prompt, image_paths=reference_images, size=size,
    )
    file_path = skill.file_tool.save_generated(parent_task_id, image_content, task_round)

    db = SessionLocal()
    try:
        child = GeneratedImage(
            task_id=parent_task_id,
            file_path=file_path,
            angle=parent_angle,
            prompt=final_prompt,
            status="pending",
            acceptance_criteria=parent_acceptance,
            generation_round=parent_round + 1,
            parent_image_id=parent_id,
            prompt_modules_json=json.dumps(pipeline_result.get("modules") or [], ensure_ascii=False),
        )
        db.add(child)
        task = db.query(LookbookTask).filter(LookbookTask.id == parent_task_id).first()
        if task:
            task.generation_round = task_round
            images = json.loads(task.generated_images) if task.generated_images else []
            images.append({
                "id": None,
                "angle": parent_angle,
                "path": file_path,
                "prompt": final_prompt,
                "status": "pending",
                "parent_image_id": parent_id,
                "generation_round": parent_round + 1,
            })
        db.commit()
        db.refresh(child)
        if task:
            for item in images:
                if item.get("id") is None and item.get("path") == file_path:
                    item["id"] = child.id
            task.generated_images = json.dumps(images, ensure_ascii=False)
            db.commit()

        save_module_runs(child.id, parent_task_id, pipeline_result)
        return {
            "parent_image_id": parent_id,
            "image": {
                "id": child.id,
                "angle": child.angle,
                "path": child.file_path,
                "prompt": child.prompt,
                "status": child.status,
                "generation_round": child.generation_round,
                "parent_image_id": child.parent_image_id,
            },
        }
    finally:
        db.close()
