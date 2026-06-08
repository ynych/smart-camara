import json
import os
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Requirement, LookbookTask, StyleTemplate, GeneratedImage
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

@router.post("/generate-prompt")
async def generate_prompt(data: dict, db: Session = Depends(get_db)):
    """预生成 prompt 列表（LangGraph Agent，失败回退 Harness）。"""
    from data.services import AgentDefinitionService
    from agents.graphs.lookbook_prompt_graph import run_prompt_agent
    from services.seed_admin_data import BUILTIN_AGENT_SLUG
    import json as _json

    model_id = data.get("model_id")
    clothing_ids = data.get("clothing_ids", [])
    reference_id = data.get("reference_id")
    scene_id = data.get("scene_id")
    quantity = data.get("quantity", 4)
    size = data.get("size", "3:4")
    business_context = data.get("business_context") or {}
    acceptance_criteria = data.get("acceptance_criteria") or ""

    try:
        criteria = acceptance_criteria or skill.build_acceptance_criteria(
            size=size,
            quantity=quantity,
            business_context=business_context,
        )
        agent_svc = AgentDefinitionService(db)
        rows = agent_svc.list_all()
        agent_row = next((r for r in rows if r.get("slug") == BUILTIN_AGENT_SLUG), rows[0] if rows else None)
        if not agent_row:
            prompts, prompt_source, llm_error = await skill.build_prompts_async(
                model_id, clothing_ids, reference_id, quantity, size=size,
                scene_id=scene_id, business_context=business_context, acceptance_criteria=criteria,
            )
            return {"prompts": prompts, "acceptance_criteria": criteria, "prompt_source": prompt_source, "llm_error": llm_error}

        tool_ids = agent_row.get("tool_ids_json")
        if isinstance(tool_ids, str):
            tool_ids = _json.loads(tool_ids)
        agent_config = {
            "pipeline_config_id": agent_row.get("pipeline_config_id"),
            "tool_ids": tool_ids or [],
            "knowledge_tree_id": agent_row.get("knowledge_tree_id"),
        }
        inputs = {
            "model_id": model_id,
            "clothing_ids": clothing_ids,
            "reference_id": reference_id,
            "scene_id": scene_id,
            "size": size,
            "quantity": quantity,
            "business_context": business_context,
            "acceptance_criteria": criteria,
        }
        result = await run_prompt_agent(
            inputs,
            agent_config,
            session_id=data.get("session_id") or data.get("langfuse_session_id"),
            user_id="workbench",
            ref_type="workbench",
        )
        return {
            "prompts": result.get("prompts") or [],
            "acceptance_criteria": criteria,
            "prompt_source": result.get("source"),
            "agent_slug": agent_row.get("slug"),
            "agent_id": agent_row.get("id"),
            "llm_error": result.get("llm_error"),
            "trace": result.get("trace"),
            "run_id": result.get("run_id"),
            "session_id": result.get("session_id"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate")
async def generate_lookbook(data: dict):
    """开始生成Lookbook"""
    requirement_id = data.get("requirement_id")
    quantity = data.get("quantity", 4)
    reference_image_path = data.get("reference_image_path")

    try:
        if data.get("model_id") or data.get("clothing_ids"):
            result = await skill.generate_from_selection(data)
        else:
            if not requirement_id:
                raise HTTPException(status_code=400, detail="缺少requirement_id")
            result = await skill.generate(requirement_id, quantity=quantity, reference_image_path=reference_image_path)
        return {"message": "生成完成", "task_id": result["task_id"], "images": result["images"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
