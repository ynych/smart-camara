import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Scene

router = APIRouter(prefix="/api/scenes", tags=["场景管理"])


class SceneCreate(BaseModel):
    name: str
    scene_type: str  # indoor / outdoor
    description: Optional[str] = None


class SceneUpdate(BaseModel):
    name: Optional[str] = None
    scene_type: Optional[str] = None
    description: Optional[str] = None


@router.get("")
def get_scenes(db: Session = Depends(get_db)):
    """获取场景列表"""
    result = db.execute(select(Scene).order_by(Scene.created_at.desc()))
    scenes = result.scalars().all()

    return {
        "scenes": [
            {
                "id": s.id,
                "name": s.name,
                "scene_type": s.scene_type,
                "description": s.description,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in scenes
        ]
    }


@router.post("")
def create_scene(request: SceneCreate, db: Session = Depends(get_db)):
    """创建场景"""
    scene = Scene(
        id=str(uuid.uuid4()),
        name=request.name,
        scene_type=request.scene_type,
        description=request.description,
    )
    db.add(scene)
    db.commit()

    return {
        "message": "场景创建成功",
        "scene": {
            "id": scene.id,
            "name": scene.name,
            "scene_type": scene.scene_type,
            "description": scene.description,
            "created_at": scene.created_at.isoformat() if scene.created_at else None,
        },
    }


@router.put("/{scene_id}")
def update_scene(
    scene_id: str, request: SceneUpdate, db: Session = Depends(get_db)
):
    """更新场景"""
    result = db.execute(select(Scene).where(Scene.id == scene_id))
    scene = result.scalar_one_or_none()

    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")

    if request.name is not None:
        scene.name = request.name
    if request.scene_type is not None:
        scene.scene_type = request.scene_type
    if request.description is not None:
        scene.description = request.description

    db.commit()

    return {
        "message": "场景更新成功",
        "scene": {
            "id": scene.id,
            "name": scene.name,
            "scene_type": scene.scene_type,
            "description": scene.description,
            "created_at": scene.created_at.isoformat() if scene.created_at else None,
        },
    }


@router.delete("/{scene_id}")
def delete_scene(scene_id: str, db: Session = Depends(get_db)):
    """删除场景"""
    result = db.execute(select(Scene).where(Scene.id == scene_id))
    scene = result.scalar_one_or_none()

    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")

    db.delete(scene)
    db.commit()

    return {"message": "场景已删除"}
