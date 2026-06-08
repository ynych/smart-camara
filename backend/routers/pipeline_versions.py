"""Pipeline 版本管理：draft / publish / compare。"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from services.pipeline_version import (
    clone_to_draft,
    get_version_pair,
    publish_draft,
    reject_draft,
    update_draft_modules,
)
from services.seed_admin_data import BUILTIN_PIPELINE_SLUG
from services.version_compare import compare_versions

router = APIRouter(prefix="/api/agent-runtime/pipeline", tags=["pipeline-versions"])


class UpdateDraftBody(BaseModel):
    modules: dict
    module_order: list[str] | None = None


class CompareBody(BaseModel):
    slug: str = BUILTIN_PIPELINE_SLUG
    testcase_ids: list[str] | None = None


@router.get("/versions")
def list_versions(slug: str = BUILTIN_PIPELINE_SLUG, db: Session = Depends(get_db)):
    return get_version_pair(db, slug)


@router.post("/versions/clone-draft")
def api_clone_draft(slug: str = BUILTIN_PIPELINE_SLUG, db: Session = Depends(get_db)):
    try:
        return {"draft": clone_to_draft(db, slug), "slug": slug}
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/versions/publish")
def api_publish(slug: str = BUILTIN_PIPELINE_SLUG, db: Session = Depends(get_db)):
    try:
        return publish_draft(db, slug)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/versions/reject")
def api_reject(slug: str = BUILTIN_PIPELINE_SLUG, db: Session = Depends(get_db)):
    try:
        return reject_draft(db, slug)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.put("/versions/draft/modules")
def api_update_draft(body: UpdateDraftBody, slug: str = BUILTIN_PIPELINE_SLUG, db: Session = Depends(get_db)):
    try:
        return update_draft_modules(db, slug, body.modules, body.module_order)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/versions/compare")
async def api_compare(body: CompareBody, db: Session = Depends(get_db)):
    try:
        return await compare_versions(db, slug=body.slug, testcase_ids=body.testcase_ids)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
