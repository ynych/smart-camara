from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from database import get_db
from models import GeneratedImage, PromptFeedback

router = APIRouter(prefix="/api/review", tags=["验收管理"])


class RejectRequest(BaseModel):
    feedback: str


@router.get("/images")
def get_review_images(
    task_id: Optional[str] = Query(None, description="按任务ID过滤"),
    status: Optional[str] = Query(None, description="按状态过滤: pending/approved/rejected"),
    db: Session = Depends(get_db),
):
    """获取待验收图片列表"""
    query = select(GeneratedImage)

    if task_id:
        query = query.where(GeneratedImage.task_id == task_id)
    if status:
        query = query.where(GeneratedImage.status == status)

    query = query.order_by(GeneratedImage.created_at.desc())
    result = db.execute(query)
    images = result.scalars().all()

    return {
        "images": [
            {
                "id": img.id,
                "task_id": img.task_id,
                "file_path": img.file_path,
                "status": img.status,
                "feedback": img.feedback,
                "created_at": img.created_at.isoformat() if img.created_at else None,
            }
            for img in images
        ]
    }


@router.post("/images/{image_id}/approve")
def approve_image(image_id: str, db: Session = Depends(get_db)):
    """标记图片合格"""
    result = db.execute(
        select(GeneratedImage).where(GeneratedImage.id == image_id)
    )
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")

    image.status = "approved"
    db.commit()

    return {"message": "图片已标记为合格", "image_id": image_id, "status": "approved"}


@router.post("/images/{image_id}/reject")
def reject_image(
    image_id: str, request: RejectRequest, db: Session = Depends(get_db)
):
    """标记图片不合格"""
    result = db.execute(
        select(GeneratedImage).where(GeneratedImage.id == image_id)
    )
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")

    image.status = "rejected"
    image.feedback = request.feedback
    db.commit()

    # 同时记录到 PromptFeedback
    # 获取关联的任务信息
    from models import GenerationTask
    task_result = db.execute(
        select(GenerationTask).where(GenerationTask.id == image.task_id)
    )
    task = task_result.scalar_one_or_none()

    if task:
        import uuid
        from datetime import datetime
        feedback_record = PromptFeedback(
            id=str(uuid.uuid4()),
            task_id=image.task_id,
            prompt_used=task.prompt or "",
            result="rejected",
            feedback=request.feedback,
            created_at=datetime.utcnow(),
        )
        db.add(feedback_record)
        db.commit()

    return {"message": "图片已标记为不合格", "image_id": image_id, "status": "rejected"}


@router.get("/stats")
def get_review_stats(db: Session = Depends(get_db)):
    """获取验收统计"""
    # 总数
    total_result = db.execute(select(func.count(GeneratedImage.id)))
    total = total_result.scalar() or 0

    # 合格数
    approved_result = db.execute(
        select(func.count(GeneratedImage.id)).where(GeneratedImage.status == "approved")
    )
    approved = approved_result.scalar() or 0

    # 不合格数
    rejected_result = db.execute(
        select(func.count(GeneratedImage.id)).where(GeneratedImage.status == "rejected")
    )
    rejected = rejected_result.scalar() or 0

    # 待验收数
    pending_result = db.execute(
        select(func.count(GeneratedImage.id)).where(GeneratedImage.status == "pending")
    )
    pending = pending_result.scalar() or 0

    approval_rate = round(approved / total * 100, 1) if total > 0 else 0.0

    return {
        "total": total,
        "approved": approved,
        "rejected": rejected,
        "pending": pending,
        "approval_rate": approval_rate,
    }


@router.get("/feedbacks")
def get_feedbacks(db: Session = Depends(get_db)):
    """获取反馈历史"""
    result = db.execute(
        select(PromptFeedback).order_by(PromptFeedback.created_at.desc())
    )
    feedbacks = result.scalars().all()

    return {
        "feedbacks": [
            {
                "id": f.id,
                "task_id": f.task_id,
                "prompt_used": f.prompt_used,
                "result": f.result,
                "feedback": f.feedback,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in feedbacks
        ]
    }
