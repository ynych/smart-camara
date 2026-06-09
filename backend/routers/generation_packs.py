"""Admin — PromptGenerationPack API。"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from domains.workflow import pack_service
from domains.workflow.manifest import get_manifest

router = APIRouter(prefix="/api/admin/generation-packs", tags=["generation-packs"])


class PackBody(BaseModel):
    slug: str | None = None
    name: str | None = None
    scenario_json: dict | list | None = None
    user_needs_json: list | None = None
    techniques_json: dict | None = None
    harness_pipeline_slug: str | None = None


@router.get("")
def list_packs(status: str | None = None, db: Session = Depends(get_db)):
    return {"items": pack_service.list_packs(db, status=status)}


@router.get("/manifest")
def read_manifest(db: Session = Depends(get_db)):
    m = get_manifest(db)
    if not m:
        raise HTTPException(404, "manifest 未初始化")
    return m


@router.get("/{pack_id}")
def get_pack(pack_id: str, db: Session = Depends(get_db)):
    item = pack_service.get_pack(db, pack_id)
    if not item:
        raise HTTPException(404, "Pack 不存在")
    return item


@router.post("")
def create_pack(body: PackBody, db: Session = Depends(get_db)):
    try:
        item = pack_service.create_pack(db, body.model_dump(exclude_none=True))
        db.commit()
        return item
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e)) from e


@router.patch("/{pack_id}")
def update_pack(pack_id: str, body: PackBody, db: Session = Depends(get_db)):
    try:
        item = pack_service.update_pack(db, pack_id, body.model_dump(exclude_none=True))
        db.commit()
        return item
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e)) from e


@router.post("/{pack_id}/copy")
def copy_pack(pack_id: str, db: Session = Depends(get_db)):
    try:
        item = pack_service.copy_pack(db, pack_id)
        db.commit()
        return item
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e)) from e


@router.post("/{pack_id}/publish")
def publish_pack(pack_id: str, db: Session = Depends(get_db)):
    try:
        result = pack_service.publish_pack(db, pack_id)
        db.commit()
        return result
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e)) from e
