"""PromptGenerationPack CRUD / Copy / Publish。"""

from __future__ import annotations

import json
import uuid
from copy import deepcopy
from datetime import datetime
from typing import Any

from models import PromptGenerationPack
from domains.agent.pipeline_version import draft_slug
from domains.workflow.manifest import pin_pack_on_publish


def _loads(val: Any) -> Any:
    if isinstance(val, str):
        return json.loads(val)
    return val


def serialize_pack(row: PromptGenerationPack) -> dict[str, Any]:
    return {
        "id": row.id,
        "slug": row.slug,
        "name": row.name,
        "scenario_json": _loads(row.scenario_json) or {},
        "user_needs_json": _loads(row.user_needs_json) or [],
        "techniques_json": _loads(row.techniques_json) or {},
        "harness_pipeline_slug": row.harness_pipeline_slug,
        "status": row.status,
        "version": row.version,
        "parent_id": row.parent_id,
        "skill_version_id": row.skill_version_id,
        "published_at": row.published_at.isoformat() if row.published_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def list_packs(db, status: str | None = None) -> list[dict[str, Any]]:
    q = db.query(PromptGenerationPack).order_by(PromptGenerationPack.updated_at.desc())
    if status:
        q = q.filter(PromptGenerationPack.status == status)
    return [serialize_pack(r) for r in q.all()]


def get_pack(db, pack_id: str) -> dict[str, Any] | None:
    row = db.query(PromptGenerationPack).filter(PromptGenerationPack.id == pack_id).first()
    return serialize_pack(row) if row else None


def create_pack(db, payload: dict[str, Any]) -> dict[str, Any]:
    slug = (payload.get("slug") or f"pack_{uuid.uuid4().hex[:8]}").strip()
    row = PromptGenerationPack(
        id=str(uuid.uuid4()),
        slug=slug,
        name=payload.get("name") or slug,
        scenario_json=json.dumps(payload.get("scenario_json") or {}, ensure_ascii=False),
        user_needs_json=json.dumps(payload.get("user_needs_json") or [], ensure_ascii=False),
        techniques_json=json.dumps(payload.get("techniques_json") or {}, ensure_ascii=False),
        harness_pipeline_slug=payload.get("harness_pipeline_slug") or "lookbook_v1",
        status="draft",
        version=1,
        parent_id=payload.get("parent_id"),
        skill_version_id=payload.get("skill_version_id"),
    )
    db.add(row)
    db.flush()
    return serialize_pack(row)


def update_pack(db, pack_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    row = db.query(PromptGenerationPack).filter(PromptGenerationPack.id == pack_id).first()
    if not row:
        raise ValueError("Pack 不存在")
    if row.status != "draft":
        raise ValueError("仅 draft 可原地编辑；已发布请使用复制")
    for key, col in [
        ("name", "name"),
        ("scenario_json", "scenario_json"),
        ("user_needs_json", "user_needs_json"),
        ("techniques_json", "techniques_json"),
        ("harness_pipeline_slug", "harness_pipeline_slug"),
    ]:
        if key in payload:
            val = payload[key]
            if key.endswith("_json") and not isinstance(val, str):
                val = json.dumps(val, ensure_ascii=False)
            setattr(row, col, val)
    row.updated_at = datetime.utcnow()
    db.flush()
    return serialize_pack(row)


def copy_pack(db, pack_id: str) -> dict[str, Any]:
    src = db.query(PromptGenerationPack).filter(PromptGenerationPack.id == pack_id).first()
    if not src:
        raise ValueError("Pack 不存在")
    ds = draft_slug(src.slug)
    existing_draft = db.query(PromptGenerationPack).filter(PromptGenerationPack.slug == ds).first()
    if existing_draft:
        db.delete(existing_draft)
        db.flush()
    row = PromptGenerationPack(
        id=str(uuid.uuid4()),
        slug=ds,
        name=f"{src.name} (draft)",
        scenario_json=src.scenario_json,
        user_needs_json=src.user_needs_json,
        techniques_json=src.techniques_json,
        harness_pipeline_slug=src.harness_pipeline_slug,
        status="draft",
        version=int(src.version or 1) + 1,
        parent_id=src.id,
        skill_version_id=src.skill_version_id,
    )
    db.add(row)
    db.flush()
    return serialize_pack(row)


def publish_pack(db, pack_id: str) -> dict[str, Any]:
    draft = db.query(PromptGenerationPack).filter(PromptGenerationPack.id == pack_id).first()
    if not draft or draft.status != "draft":
        raise ValueError("只能发布 draft Pack")
    base_slug = draft.slug.replace("_draft", "") if draft.slug.endswith("_draft") else draft.slug
    if draft.slug.endswith("_draft"):
        base_slug = draft.slug[: -len("_draft")]

    published = (
        db.query(PromptGenerationPack)
        .filter(PromptGenerationPack.slug == base_slug)
        .filter(PromptGenerationPack.status == "published")
        .first()
    )
    new_version = (published.version if published else 0) + 1

    if published:
        published.scenario_json = draft.scenario_json
        published.user_needs_json = draft.user_needs_json
        published.techniques_json = draft.techniques_json
        published.harness_pipeline_slug = draft.harness_pipeline_slug
        published.version = new_version
        published.skill_version_id = draft.skill_version_id or published.skill_version_id
        published.published_at = datetime.utcnow()
        published.updated_at = datetime.utcnow()
        target = published
    else:
        target = PromptGenerationPack(
            id=str(uuid.uuid4()),
            slug=base_slug,
            name=draft.name.replace(" (draft)", ""),
            scenario_json=draft.scenario_json,
            user_needs_json=draft.user_needs_json,
            techniques_json=draft.techniques_json,
            harness_pipeline_slug=draft.harness_pipeline_slug,
            status="published",
            version=new_version,
            parent_id=draft.parent_id,
            skill_version_id=draft.skill_version_id,
            published_at=datetime.utcnow(),
        )
        db.add(target)

    draft.status = "archived"
    draft.updated_at = datetime.utcnow()
    db.flush()
    manifest = pin_pack_on_publish(db, target)
    return {"pack": serialize_pack(target), "manifest": manifest}


def list_published_packs(db) -> list[dict[str, Any]]:
    rows = db.query(PromptGenerationPack).filter(PromptGenerationPack.status == "published").all()
    return [serialize_pack(r) for r in rows]
