"""ProductionManifest 读写与 Publish 时 pin 更新（P2）。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from models import ProductionManifest, PromptGenerationPack
from domains.workflow.defaults import DEFAULT_MANIFEST


def _json_load(val: Any, default: Any) -> Any:
    if val is None:
        return default
    if isinstance(val, str):
        return json.loads(val)
    return val


def serialize_manifest(row: ProductionManifest) -> dict[str, Any]:
    return {
        "id": row.id,
        "slug": row.slug,
        "workflow_id": row.workflow_id,
        "default_pack_id": row.default_pack_id,
        "default_pack_slug": row.default_pack_slug,
        "pack_version_pin_json": _json_load(row.pack_version_pin_json, {}),
        "skill_version_id": row.skill_version_id,
        "fallback_skill_version_id": row.fallback_skill_version_id,
        "harness_pipeline_slug": row.harness_pipeline_slug,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def get_manifest(db, slug: str = "lookbook_default") -> dict[str, Any] | None:
    row = db.query(ProductionManifest).filter(ProductionManifest.slug == slug).first()
    return serialize_manifest(row) if row else None


def ensure_manifest(db) -> dict[str, Any]:
    row = db.query(ProductionManifest).filter(ProductionManifest.slug == DEFAULT_MANIFEST["slug"]).first()
    if row:
        return serialize_manifest(row)
    pack = (
        db.query(PromptGenerationPack)
        .filter(PromptGenerationPack.slug == DEFAULT_MANIFEST["default_pack_slug"])
        .filter(PromptGenerationPack.status == "published")
        .first()
    )
    row = ProductionManifest(
        id=str(uuid.uuid4()),
        slug=DEFAULT_MANIFEST["slug"],
        workflow_id=DEFAULT_MANIFEST["workflow_id"],
        default_pack_id=pack.id if pack else None,
        default_pack_slug=DEFAULT_MANIFEST["default_pack_slug"],
        pack_version_pin_json=json.dumps(DEFAULT_MANIFEST["pack_version_pin_json"], ensure_ascii=False),
        skill_version_id=DEFAULT_MANIFEST["skill_version_id"],
        fallback_skill_version_id=DEFAULT_MANIFEST["fallback_skill_version_id"],
        harness_pipeline_slug=DEFAULT_MANIFEST["harness_pipeline_slug"],
        updated_at=datetime.utcnow(),
    )
    db.add(row)
    db.flush()
    return serialize_manifest(row)


def pin_pack_on_publish(db, pack: PromptGenerationPack, manifest_slug: str = "lookbook_default") -> dict[str, Any]:
    row = db.query(ProductionManifest).filter(ProductionManifest.slug == manifest_slug).first()
    if not row:
        ensure_manifest(db)
        row = db.query(ProductionManifest).filter(ProductionManifest.slug == manifest_slug).first()
    pins = _json_load(row.pack_version_pin_json, {})
    pins[pack.slug] = int(pack.version or 1)
    row.default_pack_id = pack.id
    row.default_pack_slug = pack.slug
    row.pack_version_pin_json = json.dumps(pins, ensure_ascii=False)
    row.updated_at = datetime.utcnow()
    db.flush()
    return serialize_manifest(row)
