from __future__ import annotations

import json
import os
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query, Body
from sqlalchemy.orm import Session
from database import get_db
from models import Requirement, LookbookTask, StyleTemplate, GeneratedImage, LookbookStudioTask
from skills.lookbook_skill import LookbookSkill
from tools.file_tool import FileTool
from tools.material_tool import MaterialTool
from config import UPLOADS_DIR, ASSETS_DIR

router = APIRouter(prefix="/api/lookbook", tags=["Lookbook"])
skill = LookbookSkill()


def _resolve_source_materials(task: LookbookTask, req: Requirement | None) -> dict:
    """解析任务关联的模特、服装、参考图、场景素材。"""
    raw = task.selected_materials if task else None
    if not raw and req and req.selected_materials:
        raw = req.selected_materials
    if not raw:
        return {"model": None, "clothing": [], "reference": None, "scene": None}

    try:
        selected = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"model": None, "clothing": [], "reference": None, "scene": None}

    model_id = selected.get("model_id")
    clothing_ids = selected.get("clothing_ids") or []
    reference_id = selected.get("reference_id")
    scene_id = selected.get("scene_id")

    id_list = []
    if model_id:
        id_list.append(model_id)
    id_list.extend(clothing_ids)
    if reference_id:
        id_list.append(reference_id)
    if scene_id and scene_id not in id_list:
        id_list.append(scene_id)

    materials = {m["id"]: m for m in MaterialTool.get_by_ids(id_list)}
    return {
        "model": materials.get(model_id),
        "clothing": [materials[cid] for cid in clothing_ids if cid in materials],
        "reference": materials.get(reference_id) if reference_id else None,
        "scene": materials.get(scene_id) if scene_id else None,
        "business_context": selected.get("business_context"),
    }

@router.post("/upload")
def upload_source_image(
    files: list[UploadFile] = File(..., description="上传图片文件（支持多个）"),
    category: str = Form("clothing", description="分类: model/clothing"),
    description: str = Form("", description="服装描述（可选）"),
    db: Session = Depends(get_db),
):
    """上传素材图片，支持多文件，创建需求"""
    uploaded = []
    source_image_path = None

    for file in files:
        content = file.file.read()
        file_path = FileTool.save_upload(content, file.filename)
        material_id = MaterialTool.create(
            name=file.filename,
            type="upload",
            category=category,
            file_path=file_path,
        )
        uploaded.append({"id": material_id, "file_path": file_path})
        # 使用第一个上传的文件作为source_image_path
        if source_image_path is None:
            source_image_path = file_path

    # 创建需求
    result = skill.create_requirement(source_image_path, description)

    # 如果有描述，直接分析
    if description:
        skill.analyze_requirement(result["id"], description)

    return {
        "requirement_id": result["id"],
        "source_image_path": source_image_path,
        "uploaded": uploaded,
        "message": f"上传{len(uploaded)}个文件成功",
    }

@router.get("/requirements")
def get_requirements(status: str = Query(None), db: Session = Depends(get_db)):
    """获取需求列表"""
    query = db.query(Requirement).order_by(Requirement.created_at.desc())
    if status:
        query = query.filter(Requirement.status == status)
    requirements = query.all()
    return {
        "requirements": [
            {
                "id": r.id,
                "status": r.status,
                "source_image_path": r.source_image_path,
                "detected_features": json.loads(r.detected_features) if r.detected_features else None,
                "selected_style": r.selected_style,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in requirements
        ]
    }

@router.get("/requirements/{requirement_id}")
def get_requirement(requirement_id: str, db: Session = Depends(get_db)):
    """获取需求详情"""
    req = db.query(Requirement).filter(Requirement.id == requirement_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="需求不存在")
    return {
        "id": req.id,
        "status": req.status,
        "source_image_path": req.source_image_path,
        "detected_features": json.loads(req.detected_features) if req.detected_features else None,
        "selected_style": req.selected_style,
        "user_edits": json.loads(req.user_edits) if req.user_edits else None,
        "created_at": req.created_at.isoformat() if req.created_at else None,
    }

@router.put("/requirements/{requirement_id}")
def update_requirement(requirement_id: str, data: dict, db: Session = Depends(get_db)):
    """更新需求"""
    req = db.query(Requirement).filter(Requirement.id == requirement_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="需求不存在")

    if "detected_features" in data:
        req.detected_features = json.dumps(data["detected_features"], ensure_ascii=False)
    if "selected_style" in data:
        req.selected_style = data["selected_style"]
    if "user_edits" in data:
        req.user_edits = json.dumps(data["user_edits"], ensure_ascii=False)
    if "reference_image_path" in data:
        req.reference_image_path = data["reference_image_path"]
    if "prompt_overrides" in data:
        req.prompt_overrides = json.dumps(data["prompt_overrides"], ensure_ascii=False)

    db.commit()
    return {"message": "更新成功"}

@router.post("/requirements/{requirement_id}/analyze")
def analyze_requirement(requirement_id: str, data: dict = None, db: Session = Depends(get_db)):
    """分析服装特征"""
    description = ""
    if data and "description" in data:
        description = data["description"]

    features = skill.analyze_requirement(requirement_id, description)
    return {"features": features}

@router.get("/styles")
def get_styles(db: Session = Depends(get_db)):
    """获取风格模板列表"""
    styles = db.query(StyleTemplate).order_by(StyleTemplate.sort_order).all()
    return {
        "styles": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "angles": json.loads(s.angles) if s.angles else [],
                "variables": json.loads(s.variables) if s.variables else {},
            }
            for s in styles
        ]
    }

# ---------- 生图工作台任务 ----------

@router.get("/studio-tasks")
def list_studio_tasks(db: Session = Depends(get_db)):
    from domains.user.studio_task import list_studio_tasks as _list

    return {"tasks": _list(db)}


@router.post("/studio-tasks")
def create_studio_task(data: dict | None = None, db: Session = Depends(get_db)):
    from domains.user.studio_task import create_studio_task as _create

    try:
        task = _create(db, data or {})
        db.commit()
        return task
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e)) from e


@router.get("/studio-tasks/{task_id}")
def get_studio_task_detail(task_id: str, db: Session = Depends(get_db)):
    from domains.user.studio_task import get_studio_task

    task = get_studio_task(db, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    return task


@router.patch("/studio-tasks/{task_id}")
def patch_studio_task(
    task_id: str,
    data: dict = Body(...),
    db: Session = Depends(get_db),
):
    from domains.user.studio_task import update_studio_task

    try:
        task = update_studio_task(db, task_id, data)
        db.commit()
        return task
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e)) from e


@router.post("/generate-prompt")
async def generate_prompt(data: dict, db: Session = Depends(get_db)):
    """U3：Workflow 预览 prompts，落 prompt_run_record。"""
    from domains.user.studio_task import apply_prompt_preview, get_studio_task, update_studio_task
    from domains.workflow.runner import run_workflow_preview

    studio_task_id = data.get("studio_task_id")
    try:
        if studio_task_id and not get_studio_task(db, studio_task_id):
            raise HTTPException(404, "工作台任务不存在")

        result = await run_workflow_preview(
            data,
            source="user_preview",
            session_id=data.get("session_id") or data.get("langfuse_session_id"),
            user_id="workbench",
            include_user_trace=False,
            studio_task_id=studio_task_id,
        )
        if studio_task_id:
            apply_prompt_preview(db, studio_task_id, result)
            db.commit()
        return {
            **result,
            "prompt_source": result.get("prompt_source"),
            "studio_task_id": studio_task_id,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.post("/generate")
async def generate_lookbook(data: dict, db: Session = Depends(get_db)):
    """U4：确认生图（inline prompts 优先，支持 studio_task_id）。"""
    from domains.user.studio_task import get_studio_task, update_studio_task
    from domains.workflow.records import get_prompt_run_record

    studio_task_id = data.get("studio_task_id")
    try:
        merged = dict(data)
        if studio_task_id:
            st = get_studio_task(db, studio_task_id)
            if not st:
                raise HTTPException(404, "工作台任务不存在")
            if st["status"] == "completed":
                raise HTTPException(400, "任务已完成")
            merged.setdefault("model_id", st.get("model_id"))
            merged.setdefault("clothing_ids", st.get("clothing_ids"))
            merged.setdefault("reference_id", st.get("reference_id"))
            merged.setdefault("scene_id", st.get("scene_id"))
            merged.setdefault("size", st.get("size"))
            merged.setdefault("acceptance_criteria", st.get("acceptance_criteria"))
            merged.setdefault("business_context", st.get("business_context"))
            if not merged.get("prompts"):
                merged["prompts"] = st.get("prompts") or []

        if merged.get("prompts"):
            pass
        elif merged.get("prompt_run_id"):
            record = get_prompt_run_record(db, merged["prompt_run_id"])
            if not record:
                raise HTTPException(status_code=404, detail="prompt_run_id 不存在")
            inputs = record.get("inputs_json") or {}
            merged = {
                **inputs,
                **merged,
                "prompts": record.get("prompts_json") or [],
                "acceptance_criteria": merged.get("acceptance_criteria") or record.get("acceptance_criteria") or "",
            }

        if studio_task_id:
            update_studio_task(db, studio_task_id, {"status": "generating", "prompts": merged.get("prompts") or []})

        if merged.get("model_id") or merged.get("clothing_ids"):
            result = await skill.generate_from_selection(merged)
        else:
            requirement_id = merged.get("requirement_id")
            if not requirement_id:
                raise HTTPException(status_code=400, detail="缺少 requirement_id 或素材")
            result = await skill.generate(
                requirement_id,
                quantity=merged.get("quantity", 4),
                reference_image_path=merged.get("reference_image_path"),
            )

        if studio_task_id:
            update_studio_task(db, studio_task_id, {
                "status": "completed",
                "lookbook_task_id": result.get("task_id"),
                "prompts": merged.get("prompts") or [],
                "error_message": None,
            })
            db.commit()

        return {"message": "生成完成", "task_id": result["task_id"], "images": result["images"], "studio_task_id": studio_task_id}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        if studio_task_id:
            try:
                update_studio_task(db, studio_task_id, {"status": "failed", "error_message": str(e)})
                db.commit()
            except Exception:
                db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.get("/tasks")
def get_tasks(status: str = Query(None), db: Session = Depends(get_db)):
    """获取任务列表"""
    query = db.query(LookbookTask).order_by(LookbookTask.created_at.desc())
    if status:
        query = query.filter(LookbookTask.status == status)
    tasks = query.all()
    return {
        "tasks": [
            {
                "id": t.id,
                "requirement_id": t.requirement_id,
                "style_id": t.style_id,
                "status": t.status,
                "progress": t.progress,
                "quantity": t.quantity,
                "size": t.size,
                "acceptance_criteria": t.acceptance_criteria,
                "generated_images": json.loads(t.generated_images) if t.generated_images else [],
                "error_message": t.error_message,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            }
            for t in tasks
        ]
    }

@router.get("/tasks/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)):
    """获取任务详情"""
    task = db.query(LookbookTask).filter(LookbookTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {
        "id": task.id,
        "requirement_id": task.requirement_id,
        "style_id": task.style_id,
        "status": task.status,
        "progress": task.progress,
        "quantity": task.quantity,
        "size": task.size,
        "acceptance_criteria": task.acceptance_criteria,
        "prompts": json.loads(task.prompt_overrides) if task.prompt_overrides else [],
        "generated_images": json.loads(task.generated_images) if task.generated_images else [],
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }

def _item_matches_gallery_filters(item: dict, task_id_q, model_id, clothing_id, reference_id) -> bool:
    if task_id_q and task_id_q.strip().lower() not in item["task_id"].lower():
        return False
    sm = item.get("source_materials") or {}
    if model_id and (not sm.get("model") or sm["model"].get("id") != model_id):
        return False
    if clothing_id and not any(c.get("id") == clothing_id for c in sm.get("clothing") or []):
        return False
    if reference_id and (not sm.get("reference") or sm["reference"].get("id") != reference_id):
        return False
    return True


def _task_display_images(db: Session, task: LookbookTask) -> list:
    """优先从 generated_images 表读取，含每张图的 prompt。"""
    rows = (
        db.query(GeneratedImage)
        .filter(GeneratedImage.task_id == task.id)
        .order_by(GeneratedImage.created_at.asc())
        .all()
    )
    if rows:
        return [
            {
                "id": g.id,
                "angle": g.angle,
                "path": g.file_path,
                "prompt": g.prompt,
                "status": g.status,
                "feedback": g.feedback,
                "generation_round": g.generation_round or 1,
                "parent_image_id": g.parent_image_id,
            }
            for g in rows
        ]
    if task.generated_images:
        try:
            return json.loads(task.generated_images)
        except (json.JSONDecodeError, TypeError):
            pass
    return []


def _parse_seedream_plan(task: LookbookTask, req: Requirement | None) -> list | None:
    raw = task.selected_materials if task else None
    if not raw and req and req.selected_materials:
        raw = req.selected_materials
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data.get("seedream_image_slots")
    except (json.JSONDecodeError, TypeError):
        return None


def _collect_filter_options(items: list) -> dict:
    models_map = {}
    clothing_map = {}
    refs_map = {}
    for item in items:
        sm = item.get("source_materials") or {}
        model = sm.get("model")
        if model and model.get("id"):
            models_map[model["id"]] = model.get("name") or model["id"][:8]
        for c in sm.get("clothing") or []:
            if c.get("id"):
                clothing_map[c["id"]] = c.get("name") or c["id"][:8]
        ref = sm.get("reference")
        if ref and ref.get("id"):
            refs_map[ref["id"]] = ref.get("name") or ref["id"][:8]
    return {
        "models": [{"id": k, "name": v} for k, v in models_map.items()],
        "clothing": [{"id": k, "name": v} for k, v in clothing_map.items()],
        "references": [{"id": k, "name": v} for k, v in refs_map.items()],
    }


@router.get("/gallery")
def get_gallery(
    task_id: str = Query(None, description="任务 ID（支持部分匹配）"),
    model_id: str = Query(None, description="模特素材 ID"),
    clothing_id: str = Query(None, description="服装素材 ID"),
    reference_id: str = Query(None, description="参考图素材 ID"),
    db: Session = Depends(get_db),
):
    """历史任务列表，支持按模特/服装/参考图/任务 ID 筛选。"""
    tasks = db.query(LookbookTask).order_by(LookbookTask.created_at.desc()).all()
    all_items = []
    for task in tasks:
        req = db.query(Requirement).filter(Requirement.id == task.requirement_id).first()
        images = _task_display_images(db, task)
        prompts = []
        if task.prompt_overrides:
            try:
                prompts = json.loads(task.prompt_overrides)
            except (json.JSONDecodeError, TypeError):
                prompts = []
        all_items.append({
            "task_id": task.id,
            "requirement_id": task.requirement_id,
            "style_id": task.style_id,
            "status": task.status,
            "progress": task.progress,
            "error_message": task.error_message,
            "images": images,
            "prompts": prompts,
            "seedream_image_slots": _parse_seedream_plan(task, req),
            "source_image": req.source_image_path if req else None,
            "size": task.size,
            "acceptance_criteria": task.acceptance_criteria,
            "source_materials": _resolve_source_materials(task, req),
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        })

    has_filter = any([task_id, model_id, clothing_id, reference_id])
    filtered = (
        [item for item in all_items if _item_matches_gallery_filters(item, task_id, model_id, clothing_id, reference_id)]
        if has_filter
        else all_items
    )

    return {
        "gallery": filtered,
        "total": len(filtered),
        "filter_options": _collect_filter_options(all_items),
    }

@router.post("/images/{image_id}/review")
def review_image(image_id: str, data: dict):
    """标记生成图片是否合格，并记录反馈用于后续提示词优化。"""
    status = data.get("status")
    feedback = data.get("feedback", "")
    try:
        return skill.review_image(image_id, status, feedback)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/tasks/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    """删除任务记录及关联验收图片记录。"""
    task = db.query(LookbookTask).filter(LookbookTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    db.query(GeneratedImage).filter(GeneratedImage.task_id == task_id).delete()
    db.delete(task)
    db.commit()
    return {"message": "任务已删除"}
