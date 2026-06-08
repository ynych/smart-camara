"""Agent 域 — Pipeline 版本管理（从 services 迁入）。"""

import json
import uuid
from copy import deepcopy

from data.services import AgentDefinitionService, PipelineConfigService
from models import PipelineConfig
from services.seed_admin_data import BUILTIN_AGENT_SLUG, BUILTIN_PIPELINE_SLUG


def draft_slug(slug: str) -> str:
    return f"{slug}_draft"


def get_version_pair(db, slug: str = BUILTIN_PIPELINE_SLUG) -> dict:
    svc = PipelineConfigService(db)
    published = svc.get_published_by_slug(slug)
    draft_row = db.query(PipelineConfig).filter(PipelineConfig.slug == draft_slug(slug)).first()
    draft = svc.serialize(draft_row) if draft_row else None
    return {"slug": slug, "published": published, "draft": draft}


def clone_to_draft(db, slug: str = BUILTIN_PIPELINE_SLUG) -> dict:
    svc = PipelineConfigService(db)
    published = svc.get_published_by_slug(slug)
    if not published:
        raise ValueError(f"无已发布 Pipeline: {slug}")

    ds = draft_slug(slug)
    existing = db.query(PipelineConfig).filter(PipelineConfig.slug == ds).first()
    modules = published.get("modules_json") or published.get("modules")
    order = published.get("module_order_json") or published.get("module_order")
    if isinstance(modules, str):
        modules = json.loads(modules)
    if isinstance(order, str):
        order = json.loads(order)

    payload = {
        "name": f"{published.get('name')} (draft)",
        "description": published.get("description"),
        "module_order_json": order,
        "modules_json": modules,
        "status": "draft",
        "version": (published.get("version") or 1) + 1,
    }

    if existing:
        return svc.update(existing.id, payload)

    return svc.create({
        "id": str(uuid.uuid4()),
        "slug": ds,
        **payload,
    })


def publish_draft(db, slug: str = BUILTIN_PIPELINE_SLUG) -> dict:
    svc = PipelineConfigService(db)
    published = svc.get_published_by_slug(slug)
    if not published:
        raise ValueError(f"无已发布 Pipeline: {slug}")

    ds = draft_slug(slug)
    draft_row = db.query(PipelineConfig).filter(PipelineConfig.slug == ds).first()
    if not draft_row:
        raise ValueError("无 draft 可发布，请先创建或编辑 draft")

    draft = svc.serialize(draft_row)
    new_version = (published.get("version") or 1) + 1
    updated = svc.update(published["id"], {
        "module_order_json": draft.get("module_order_json") or draft.get("module_order"),
        "modules_json": draft.get("modules_json") or draft.get("modules"),
        "version": new_version,
        "status": "published",
    })

    db.delete(draft_row)
    db.flush()

    agent_svc = AgentDefinitionService(db)
    agents = agent_svc.list_all()
    for agent in agents:
        if agent.get("slug") == BUILTIN_AGENT_SLUG or agent.get("pipeline_config_id") == published["id"]:
            agent_svc.update(agent["id"], {"pipeline_config_id": updated["id"]})

    db.commit()
    return {"published": updated, "version": new_version}


def reject_draft(db, slug: str = BUILTIN_PIPELINE_SLUG) -> dict:
    svc = PipelineConfigService(db)
    ds = draft_slug(slug)
    draft_row = db.query(PipelineConfig).filter(PipelineConfig.slug == ds).first()
    if not draft_row:
        raise ValueError("无 draft 可驳回")
    draft_id = draft_row.id
    db.delete(draft_row)
    db.commit()
    return {"rejected": draft_id, "slug": ds}


def update_draft_modules(db, slug: str, modules: dict, module_order: list | None = None) -> dict:
    pair = get_version_pair(db, slug)
    if not pair.get("draft"):
        clone_to_draft(db, slug)
        pair = get_version_pair(db, slug)

    draft = pair["draft"]
    svc = PipelineConfigService(db)
    current_modules = draft.get("modules_json") or draft.get("modules") or {}
    if isinstance(current_modules, str):
        current_modules = json.loads(current_modules)

    merged = deepcopy(current_modules)
    for mid, patch in (modules or {}).items():
        if mid not in merged:
            merged[mid] = patch
        elif isinstance(patch, dict):
            merged[mid] = {**merged[mid], **patch}
        else:
            merged[mid] = patch

    payload: dict = {"modules_json": merged}
    if module_order is not None:
        payload["module_order_json"] = module_order
    return svc.update(draft["id"], payload)
