import os
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from database import get_db
from models import Delivery, GeneratedImage, GenerationTask, Material
from services.image2_service import Image2Service
from services.prompt_builder import PromptBuilder

router = APIRouter(prefix="/api/deliveries", tags=["交付物管理"])


# 交付物类型选项
DELIVERY_TYPES = [
    {
        "value": "main_image",
        "label": "电商主图",
        "description": "淘宝/京东等平台商品主图"
    },
    {
        "value": "detail_image",
        "label": "详情页图",
        "description": "商品详情展示图"
    },
    {
        "value": "lookbook",
        "label": "Lookbook",
        "description": "时尚画册风格"
    },
    {
        "value": "outfit",
        "label": "穿搭图",
        "description": "模特上身效果图"
    },
    {
        "value": "flat_lay",
        "label": "平铺图",
        "description": "服装平铺展示"
    },
    {
        "value": "scene",
        "label": "场景图",
        "description": "特定场景下的服装展示"
    },
]


# Pydantic 请求模型
class CreateDeliveryRequest(BaseModel):
    name: str
    delivery_type: str
    task_id: Optional[str] = None
    clothing_material_id: Optional[str] = None
    model_material_id: Optional[str] = None
    scene_material_id: Optional[str] = None
    model_gender: Optional[str] = "female"
    scene_type: Optional[str] = "indoor"
    size: Optional[str] = "1:1"
    prompt: Optional[str] = None


class UpdateDeliveryRequest(BaseModel):
    name: Optional[str] = None
    delivery_type: Optional[str] = None
    prompt: Optional[str] = None


# 服务实例
image2_service = Image2Service()
prompt_builder = PromptBuilder()


@router.get("/types")
def get_delivery_types():
    """获取交付物类型列表"""
    return {"types": DELIVERY_TYPES}


@router.get("")
def get_deliveries(
    status: Optional[str] = Query(None, description="按状态筛选"),
    delivery_type: Optional[str] = Query(None, description="按类型筛选"),
    task_id: Optional[str] = Query(None, description="按任务ID筛选"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """获取交付物列表"""
    query = select(Delivery).order_by(Delivery.created_at.desc())

    # 按状态筛选
    if status:
        query = query.where(Delivery.status == status)

    # 按类型筛选
    if delivery_type:
        query = query.where(Delivery.delivery_type == delivery_type)

    # 按任务ID筛选
    if task_id:
        query = query.where(Delivery.task_id == task_id)

    # 分页
    query = query.offset(offset).limit(limit)
    result = db.execute(query)
    deliveries = result.scalars().all()

    # 获取每个交付物的图片数量和关联的任务信息
    delivery_ids = [d.id for d in deliveries]
    image_counts = {}
    if delivery_ids:
        count_query = (
            select(GeneratedImage.delivery_id, func.count(GeneratedImage.id).label("count"))
            .where(GeneratedImage.delivery_id.in_(delivery_ids))
            .group_by(GeneratedImage.delivery_id)
        )
        count_result = db.execute(count_query)
        for row in count_result:
            image_counts[row.delivery_id] = row.count

    return {
        "deliveries": [
            {
                "id": d.id,
                "name": d.name,
                "delivery_type": d.delivery_type,
                "status": d.status,
                "feedback": d.feedback,
                "prompt": d.prompt,
                "model_gender": d.model_gender,
                "scene_type": d.scene_type,
                "size": d.size,
                "task_id": d.task_id,
                "image_count": image_counts.get(d.id, 0),
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "updated_at": d.updated_at.isoformat() if d.updated_at else None,
            }
            for d in deliveries
        ],
        "total": len(deliveries),
        "limit": limit,
        "offset": offset,
    }


@router.get("/{delivery_id}")
def get_delivery(delivery_id: str, db: Session = Depends(get_db)):
    """获取交付物详情（含生成图片）"""
    result = db.execute(
        select(Delivery).where(Delivery.id == delivery_id)
    )
    delivery = result.scalar_one_or_none()

    if not delivery:
        raise HTTPException(status_code=404, detail="交付物不存在")

    # 获取关联的生成图片
    images_result = db.execute(
        select(GeneratedImage).where(GeneratedImage.delivery_id == delivery_id)
    )
    images = images_result.scalars().all()

    # 获取关联的任务信息
    task_info = None
    if delivery.task_id:
        task_result = db.execute(
            select(GenerationTask).where(GenerationTask.id == delivery.task_id)
        )
        task = task_result.scalar_one_or_none()
        if task:
            task_info = {
                "id": task.id,
                "name": task.name,
                "status": task.status,
                "created_at": task.created_at.isoformat() if task.created_at else None,
            }

    # 获取关联的素材信息
    clothing_material_info = None
    if delivery.clothing_material_id:
        mat_result = db.execute(
            select(Material).where(Material.id == delivery.clothing_material_id)
        )
        mat = mat_result.scalar_one_or_none()
        if mat:
            clothing_material_info = {
                "id": mat.id,
                "name": mat.name,
                "category": mat.category,
            }

    return {
        "delivery": {
            "id": delivery.id,
            "name": delivery.name,
            "delivery_type": delivery.delivery_type,
            "status": delivery.status,
            "feedback": delivery.feedback,
            "prompt": delivery.prompt,
            "model_gender": delivery.model_gender,
            "scene_type": delivery.scene_type,
            "size": delivery.size,
            "task_id": delivery.task_id,
            "clothing_material_id": delivery.clothing_material_id,
            "model_material_id": delivery.model_material_id,
            "scene_material_id": delivery.scene_material_id,
            "created_at": delivery.created_at.isoformat() if delivery.created_at else None,
            "updated_at": delivery.updated_at.isoformat() if delivery.updated_at else None,
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
        "task": task_info,
        "clothing_material": clothing_material_info,
    }


@router.post("")
def create_delivery(
    request: CreateDeliveryRequest,
    db: Session = Depends(get_db)
):
    """创建交付物"""
    # 验证交付物类型
    valid_types = [t["value"] for t in DELIVERY_TYPES]
    if request.delivery_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"无效的交付物类型，可选值: {valid_types}"
        )

    # 验证任务（如果提供）
    if request.task_id:
        task_result = db.execute(
            select(GenerationTask).where(GenerationTask.id == request.task_id)
        )
        task = task_result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

    # 验证素材（如果提供）
    if request.clothing_material_id:
        mat_result = db.execute(
            select(Material).where(Material.id == request.clothing_material_id)
        )
        mat = mat_result.scalar_one_or_none()
        if not mat:
            raise HTTPException(status_code=404, detail="服装素材不存在")

    # 创建交付物
    delivery_id = str(uuid.uuid4())
    delivery = Delivery(
        id=delivery_id,
        name=request.name,
        delivery_type=request.delivery_type,
        task_id=request.task_id,
        clothing_material_id=request.clothing_material_id,
        model_material_id=request.model_material_id,
        scene_material_id=request.scene_material_id,
        model_gender=request.model_gender,
        scene_type=request.scene_type,
        size=request.size,
        prompt=request.prompt,
        status="pending",
    )
    db.add(delivery)
    db.commit()

    return {
        "message": "交付物创建成功",
        "delivery_id": delivery_id,
    }


@router.put("/{delivery_id}")
def update_delivery(
    delivery_id: str,
    request: UpdateDeliveryRequest,
    db: Session = Depends(get_db)
):
    """更新交付物（编辑提示词等）"""
    result = db.execute(
        select(Delivery).where(Delivery.id == delivery_id)
    )
    delivery = result.scalar_one_or_none()

    if not delivery:
        raise HTTPException(status_code=404, detail="交付物不存在")

    # 验证交付物类型（如果提供）
    if request.delivery_type is not None:
        valid_types = [t["value"] for t in DELIVERY_TYPES]
        if request.delivery_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"无效的交付物类型，可选值: {valid_types}"
            )
        delivery.delivery_type = request.delivery_type

    if request.name is not None:
        delivery.name = request.name

    if request.prompt is not None:
        delivery.prompt = request.prompt

    delivery.updated_at = datetime.utcnow()
    db.commit()

    return {
        "message": "交付物更新成功",
        "delivery_id": delivery_id,
    }


@router.delete("/{delivery_id}")
def delete_delivery(delivery_id: str, db: Session = Depends(get_db)):
    """删除交付物"""
    result = db.execute(
        select(Delivery).where(Delivery.id == delivery_id)
    )
    delivery = result.scalar_one_or_none()

    if not delivery:
        raise HTTPException(status_code=404, detail="交付物不存在")

    # 删除关联的生成图片文件
    images_result = db.execute(
        select(GeneratedImage).where(GeneratedImage.delivery_id == delivery_id)
    )
    images = images_result.scalars().all()

    for img in images:
        if os.path.exists(img.file_path):
            try:
                os.remove(img.file_path)
            except Exception:
                pass  # 忽略文件删除错误

    # 删除交付物（级联删除关联的图片记录）
    db.delete(delivery)
    db.commit()

    return {"message": "交付物删除成功", "delivery_id": delivery_id}


@router.post("/{delivery_id}/regenerate")
def regenerate_from_delivery(
    delivery_id: str,
    db: Session = Depends(get_db)
):
    """基于已有交付物重新生成"""
    result = db.execute(
        select(Delivery).where(Delivery.id == delivery_id)
    )
    delivery = result.scalar_one_or_none()

    if not delivery:
        raise HTTPException(status_code=404, detail="交付物不存在")

    # 检查服装素材是否存在
    if not delivery.clothing_material_id:
        raise HTTPException(
            status_code=400,
            detail="交付物没有关联的服装素材，无法重新生成"
        )

    mat_result = db.execute(
        select(Material).where(Material.id == delivery.clothing_material_id)
    )
    clothing_material = mat_result.scalar_one_or_none()
    if not clothing_material:
        raise HTTPException(status_code=404, detail="关联的服装素材不存在")

    # 创建新任务
    task_id = str(uuid.uuid4())
    task = GenerationTask(
        id=task_id,
        name=f"重新生成-{delivery.name}",
        status="pending",
        clothing_material_id=delivery.clothing_material_id,
        model_material_id=delivery.model_material_id,
        scene_material_id=delivery.scene_material_id,
        size=delivery.size or "1:1",
        quantity="1",
        model_gender=delivery.model_gender or "female",
        scene_type=delivery.scene_type or "indoor",
        prompt=delivery.prompt,
    )
    db.add(task)

    # 创建新交付物
    new_delivery_id = str(uuid.uuid4())
    new_delivery = Delivery(
        id=new_delivery_id,
        name=f"{delivery.name}-重新生成",
        delivery_type=delivery.delivery_type,
        task_id=task_id,
        clothing_material_id=delivery.clothing_material_id,
        model_material_id=delivery.model_material_id,
        scene_material_id=delivery.scene_material_id,
        model_gender=delivery.model_gender,
        scene_type=delivery.scene_type,
        size=delivery.size,
        prompt=delivery.prompt,
        status="pending",
    )
    db.add(new_delivery)
    db.commit()

    return {
        "message": "已创建新的生成任务和交付物",
        "task_id": task_id,
        "delivery_id": new_delivery_id,
    }


@router.post("/{delivery_id}/approve")
def approve_delivery(
    delivery_id: str,
    db: Session = Depends(get_db)
):
    """标记交付物合格"""
    result = db.execute(
        select(Delivery).where(Delivery.id == delivery_id)
    )
    delivery = result.scalar_one_or_none()

    if not delivery:
        raise HTTPException(status_code=404, detail="交付物不存在")

    delivery.status = "approved"
    delivery.feedback = None
    delivery.updated_at = datetime.utcnow()
    db.commit()

    return {
        "message": "交付物已标记为合格",
        "delivery_id": delivery_id,
        "status": delivery.status,
    }


@router.post("/{delivery_id}/reject")
def reject_delivery(
    delivery_id: str,
    feedback: str = Query(..., description="不合格原因"),
    db: Session = Depends(get_db)
):
    """标记交付物不合格"""
    result = db.execute(
        select(Delivery).where(Delivery.id == delivery_id)
    )
    delivery = result.scalar_one_or_none()

    if not delivery:
        raise HTTPException(status_code=404, detail="交付物不存在")

    delivery.status = "rejected"
    delivery.feedback = feedback
    delivery.updated_at = datetime.utcnow()
    db.commit()

    return {
        "message": "交付物已标记为不合格",
        "delivery_id": delivery_id,
        "status": delivery.status,
        "feedback": feedback,
    }


@router.post("/{delivery_id}/reset")
def reset_delivery_status(
    delivery_id: str,
    db: Session = Depends(get_db)
):
    """重置交付物状态为待审核"""
    result = db.execute(
        select(Delivery).where(Delivery.id == delivery_id)
    )
    delivery = result.scalar_one_or_none()

    if not delivery:
        raise HTTPException(status_code=404, detail="交付物不存在")

    delivery.status = "pending"
    delivery.feedback = None
    delivery.updated_at = datetime.utcnow()
    db.commit()

    return {
        "message": "交付物状态已重置为待审核",
        "delivery_id": delivery_id,
        "status": delivery.status,
    }


@router.get("/{delivery_id}/statistics")
def get_delivery_statistics(
    delivery_id: str,
    db: Session = Depends(get_db)
):
    """获取交付物统计信息"""
    result = db.execute(
        select(Delivery).where(Delivery.id == delivery_id)
    )
    delivery = result.scalar_one_or_none()

    if not delivery:
        raise HTTPException(status_code=404, detail="交付物不存在")

    # 获取图片统计
    images_result = db.execute(
        select(GeneratedImage).where(GeneratedImage.delivery_id == delivery_id)
    )
    images = images_result.scalars().all()

    total_images = len(images)
    approved_images = sum(1 for img in images if img.status == "approved")
    rejected_images = sum(1 for img in images if img.status == "rejected")
    pending_images = sum(1 for img in images if img.status == "pending")

    return {
        "delivery_id": delivery_id,
        "delivery_name": delivery.name,
        "delivery_status": delivery.status,
        "total_images": total_images,
        "approved_images": approved_images,
        "rejected_images": rejected_images,
        "pending_images": pending_images,
    }


@router.get("/statistics/summary")
def get_deliveries_summary(
    db: Session = Depends(get_db)
):
    """获取交付物汇总统计"""
    # 获取所有交付物
    result = db.execute(select(Delivery))
    deliveries = result.scalars().all()

    # 按状态统计
    pending_count = sum(1 for d in deliveries if d.status == "pending")
    approved_count = sum(1 for d in deliveries if d.status == "approved")
    rejected_count = sum(1 for d in deliveries if d.status == "rejected")

    # 按类型统计
    type_counts = {}
    for d in deliveries:
        type_counts[d.delivery_type] = type_counts.get(d.delivery_type, 0) + 1

    # 获取所有图片
    image_result = db.execute(select(GeneratedImage))
    images = image_result.scalars().all()

    total_images = len(images)
    approved_images = sum(1 for img in images if img.status == "approved")
    rejected_images = sum(1 for img in images if img.status == "rejected")
    pending_images = sum(1 for img in images if img.status == "pending")

    return {
        "total_deliveries": len(deliveries),
        "deliveries_by_status": {
            "pending": pending_count,
            "approved": approved_count,
            "rejected": rejected_count,
        },
        "deliveries_by_type": type_counts,
        "total_images": total_images,
        "images_by_status": {
            "pending": pending_images,
            "approved": approved_images,
            "rejected": rejected_images,
        },
    }
