import os
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from database import get_db
from models import Material, GenerationTask, GeneratedImage, Delivery
from services.image2_service import Image2Service
from services.prompt_builder import PromptBuilder
from services.prompt_optimizer import PromptOptimizer

router = APIRouter(prefix="/api/generate", tags=["图片生成"])


# Pydantic 请求模型
class GenerateRequest(BaseModel):
    clothing_material_id: str
    model_material_id: Optional[str] = None
    scene_material_id: Optional[str] = None
    size: str = "1:1"
    quantity: str = "1"
    model_gender: str = "female"
    scene_type: str = "indoor"
    prompt: Optional[str] = None


class PreviewPromptRequest(BaseModel):
    clothing_material_id: str
    model_gender: str = "female"
    scene_type: str = "indoor"
    size: str = "1:1"
    prompt: Optional[str] = None
    clothing_desc: Optional[str] = None


class UpdateTaskRequest(BaseModel):
    name: Optional[str] = None
    prompt: Optional[str] = None


# Pydantic 响应模型
class TaskListItem(BaseModel):
    id: str
    name: str
    status: str
    size: str
    quantity: str
    model_gender: str
    scene_type: str
    prompt: Optional[str]
    created_at: Optional[str]
    completed_at: Optional[str]
    image_count: int = 0


class ImageItem(BaseModel):
    id: str
    file_path: str
    status: str
    feedback: Optional[str]
    created_at: Optional[str]


class TaskDetailResponse(BaseModel):
    task: dict
    images: List[dict]


# 服务实例
image2_service = Image2Service()
prompt_builder = PromptBuilder()
prompt_optimizer = PromptOptimizer()


@router.post("/preview-prompt")
def preview_prompt(request: PreviewPromptRequest, db: Session = Depends(get_db)):
    """预览生成的提示词（不实际生图）"""
    # 获取服装素材
    result = db.execute(
        select(Material).where(Material.id == request.clothing_material_id)
    )
    clothing_material = result.scalar_one_or_none()
    if not clothing_material:
        raise HTTPException(status_code=404, detail="服装素材不存在")

    # 获取服装描述
    clothing_desc = request.clothing_desc or clothing_material.name

    # 如果用户提供了自定义提示词，直接使用
    if request.prompt:
        final_prompt = request.prompt
    else:
        # 自动生成提示词
        final_prompt = prompt_builder.build_prompt(
            clothing_desc=clothing_desc,
            model_gender=request.model_gender,
            scene_type=request.scene_type,
            size=request.size,
        )

    return {
        "prompt": final_prompt,
        "clothing_desc": clothing_desc,
        "model_gender": request.model_gender,
        "scene_type": request.scene_type,
        "size": request.size,
    }


@router.post("")
def create_generation_task(request: GenerateRequest, db: Session = Depends(get_db)):
    """创建生成任务（后台执行）"""
    # 验证服装素材
    result = db.execute(
        select(Material).where(Material.id == request.clothing_material_id)
    )
    clothing_material = result.scalar_one_or_none()
    if not clothing_material:
        raise HTTPException(status_code=404, detail="服装素材不存在")

    # 验证模特素材（如果提供）
    if request.model_material_id:
        result = db.execute(
            select(Material).where(Material.id == request.model_material_id)
        )
        model_material = result.scalar_one_or_none()
        if not model_material:
            raise HTTPException(status_code=404, detail="模特素材不存在")

    # 验证场景素材（如果提供）
    if request.scene_material_id:
        result = db.execute(
            select(Material).where(Material.id == request.scene_material_id)
        )
        scene_material = result.scalar_one_or_none()
        if not scene_material:
            raise HTTPException(status_code=404, detail="场景素材不存在")

    # 创建任务后立即返回，不等待生图完成
    task_id = str(uuid.uuid4())
    task = GenerationTask(
        id=task_id,
        name=f"生成任务-{task_id[:8]}",
        status="pending",
        clothing_material_id=request.clothing_material_id,
        model_material_id=request.model_material_id,
        scene_material_id=request.scene_material_id,
        size=request.size,
        quantity=request.quantity,
        model_gender=request.model_gender,
        scene_type=request.scene_type,
        prompt=request.prompt,
    )
    db.add(task)
    db.commit()

    # 返回任务ID，让前端可以查询进度
    return {
        "task_id": task.id,
        "status": task.status,
        "message": "任务已创建，请在任务列表中查看进度"
    }


@router.get("/tasks")
def get_tasks(
    status: Optional[str] = Query(None, description="按状态筛选"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """获取任务列表（支持筛选）"""
    query = select(GenerationTask).order_by(GenerationTask.created_at.desc())

    # 按状态筛选
    if status:
        query = query.where(GenerationTask.status == status)

    # 分页
    query = query.offset(offset).limit(limit)
    result = db.execute(query)
    tasks = result.scalars().all()

    # 获取每个任务的图片数量
    task_ids = [t.id for t in tasks]
    image_counts = {}
    if task_ids:
        count_query = (
            select(GeneratedImage.task_id, func.count(GeneratedImage.id).label("count"))
            .where(GeneratedImage.task_id.in_(task_ids))
            .group_by(GeneratedImage.task_id)
        )
        count_result = db.execute(count_query)
        for row in count_result:
            image_counts[row.task_id] = row.count

    return {
        "tasks": [
            {
                "id": t.id,
                "name": t.name,
                "status": t.status,
                "size": t.size,
                "quantity": t.quantity,
                "model_gender": t.model_gender,
                "scene_type": t.scene_type,
                "prompt": t.prompt,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "image_count": image_counts.get(t.id, 0),
            }
            for t in tasks
        ],
        "total": len(tasks),
        "limit": limit,
        "offset": offset,
    }


@router.get("/tasks/{task_id}")
def get_task_detail(task_id: str, db: Session = Depends(get_db)):
    """获取任务详情（含生成图片）"""
    result = db.execute(
        select(GenerationTask).where(GenerationTask.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 获取关联的生成图片
    images_result = db.execute(
        select(GeneratedImage).where(GeneratedImage.task_id == task_id)
    )
    images = images_result.scalars().all()

    # 获取关联的交付物
    deliveries_result = db.execute(
        select(Delivery).where(Delivery.task_id == task_id)
    )
    deliveries = deliveries_result.scalars().all()

    return {
        "task": {
            "id": task.id,
            "name": task.name,
            "status": task.status,
            "clothing_material_id": task.clothing_material_id,
            "model_material_id": task.model_material_id,
            "scene_material_id": task.scene_material_id,
            "size": task.size,
            "quantity": task.quantity,
            "model_gender": task.model_gender,
            "scene_type": task.scene_type,
            "prompt": task.prompt,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        },
        "images": [
            {
                "id": img.id,
                "file_path": img.file_path,
                "status": img.status,
                "feedback": img.feedback,
                "created_at": img.created_at.isoformat() if img.created_at else None,
            }
            for img in images
        ],
        "deliveries": [
            {
                "id": d.id,
                "name": d.name,
                "delivery_type": d.delivery_type,
                "status": d.status,
                "feedback": d.feedback,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in deliveries
        ],
    }


@router.get("/tasks/{task_id}/status")
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """获取任务状态"""
    result = db.execute(
        select(GenerationTask).where(GenerationTask.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 获取图片数量
    count_result = db.execute(
        select(func.count(GeneratedImage.id)).where(GeneratedImage.task_id == task_id)
    )
    image_count = count_result.scalar()

    return {
        "task_id": task.id,
        "status": task.status,
        "name": task.name,
        "image_count": image_count,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


@router.post("/tasks/{task_id}")
def update_task(
    task_id: str,
    request: UpdateTaskRequest,
    db: Session = Depends(get_db)
):
    """更新任务信息"""
    result = db.execute(
        select(GenerationTask).where(GenerationTask.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if request.name is not None:
        task.name = request.name
    if request.prompt is not None:
        task.prompt = request.prompt

    task.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "任务更新成功", "task_id": task.id}


@router.delete("/tasks/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    """删除任务"""
    result = db.execute(
        select(GenerationTask).where(GenerationTask.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 删除关联的生成图片文件
    images_result = db.execute(
        select(GeneratedImage).where(GeneratedImage.task_id == task_id)
    )
    images = images_result.scalars().all()

    for img in images:
        if os.path.exists(img.file_path):
            try:
                os.remove(img.file_path)
            except Exception:
                pass  # 忽略文件删除错误

    # 删除任务（级联删除生成的图片）
    db.delete(task)
    db.commit()

    return {"message": "任务删除成功", "task_id": task_id}


@router.post("/tasks/{task_id}/retry")
def retry_task(task_id: str, db: Session = Depends(get_db)):
    """重试失败的任务"""
    result = db.execute(
        select(GenerationTask).where(GenerationTask.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status not in ["failed", "completed"]:
        raise HTTPException(
            status_code=400,
            detail="只能重试失败或已完成的任务"
        )

    # 重置任务状态
    task.status = "pending"
    task.completed_at = None
    db.commit()

    return {
        "message": "任务已重置为待执行状态",
        "task_id": task.id,
        "status": task.status
    }


@router.post("/tasks/{task_id}/execute")
async def execute_task(task_id: str, db: Session = Depends(get_db)):
    """执行生图任务（同步执行）"""
    result = db.execute(
        select(GenerationTask).where(GenerationTask.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status == "generating":
        raise HTTPException(status_code=400, detail="任务正在执行中")

    # 获取服装素材
    result = db.execute(
        select(Material).where(Material.id == task.clothing_material_id)
    )
    clothing_material = result.scalar_one_or_none()
    if not clothing_material:
        raise HTTPException(status_code=404, detail="服装素材不存在")

    # 生成提示词
    if task.prompt:
        final_prompt = task.prompt
    else:
        final_prompt = prompt_builder.build_prompt(
            clothing_desc=clothing_material.name,
            model_gender=task.model_gender,
            scene_type=task.scene_type,
            size=task.size,
        )

    task.prompt = final_prompt
    task.status = "generating"
    db.commit()

    # 调用 image2 API 生成图片
    try:
        n = int(task.quantity)
        image_path = clothing_material.file_path

        urls = await image2_service.generate_image(
            image_path=image_path,
            prompt=final_prompt,
            size=task.size,
            n=n,
        )

        # 下载并保存生成的图片
        os.makedirs("generated", exist_ok=True)
        for i, url in enumerate(urls):
            image_id = str(uuid.uuid4())
            save_path = os.path.join("generated", f"{image_id}.png")

            local_path = await image2_service.download_image(url, save_path)

            generated_image = GeneratedImage(
                id=image_id,
                task_id=task_id,
                file_path=local_path,
                status="pending",
            )
            db.add(generated_image)

        task.status = "completed"
        task.completed_at = datetime.utcnow()
        db.commit()

        return {
            "message": "图片生成完成",
            "task_id": task.id,
            "status": task.status,
            "image_count": len(urls),
        }

    except Exception as e:
        task.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"图片生成失败: {str(e)}")


@router.post("/tasks/{task_id}/create-delivery")
def create_delivery_from_task(
    task_id: str,
    delivery_name: str = Query(..., description="交付物名称"),
    delivery_type: str = Query(..., description="交付物类型"),
    db: Session = Depends(get_db)
):
    """基于任务创建交付物"""
    # 获取任务
    result = db.execute(
        select(GenerationTask).where(GenerationTask.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 获取任务关联的生成图片
    images_result = db.execute(
        select(GeneratedImage).where(GeneratedImage.task_id == task_id)
    )
    images = images_result.scalars().all()

    # 创建交付物
    delivery_id = str(uuid.uuid4())
    delivery = Delivery(
        id=delivery_id,
        name=delivery_name,
        delivery_type=delivery_type,
        task_id=task_id,
        clothing_material_id=task.clothing_material_id,
        model_material_id=task.model_material_id,
        scene_material_id=task.scene_material_id,
        model_gender=task.model_gender,
        scene_type=task.scene_type,
        size=task.size,
        prompt=task.prompt,
        status="pending",
    )
    db.add(delivery)

    # 更新图片的 delivery_id
    for img in images:
        img.delivery_id = delivery_id

    db.commit()

    return {
        "message": "交付物创建成功",
        "delivery_id": delivery_id,
        "image_count": len(images),
    }
