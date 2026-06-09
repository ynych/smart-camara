"""Workflow / GenerationPack / Manifest 种子数据。"""

import json
import uuid

from database import SessionLocal
from domains.workflow.defaults import DEFAULT_GENERATION_PACK, LOOKBOOK_PROD_V1
from domains.workflow.manifest import ensure_manifest
from models import PromptGenerationPack, WorkflowDefinition


def seed_workflow_data():
    db = SessionLocal()
    try:
        _seed_workflow_definition(db)
        _seed_default_pack(db)
        ensure_manifest(db)
        db.commit()
    finally:
        db.close()


def _seed_workflow_definition(db):
    wid = LOOKBOOK_PROD_V1["workflow_id"]
    existing = db.query(WorkflowDefinition).filter(WorkflowDefinition.workflow_id == wid).first()
    if existing:
        return
    db.add(WorkflowDefinition(
        id=str(uuid.uuid4()),
        workflow_id=wid,
        name=LOOKBOOK_PROD_V1["name"],
        description=LOOKBOOK_PROD_V1["description"],
        steps_json=json.dumps(LOOKBOOK_PROD_V1["steps"], ensure_ascii=False),
        graph_ref=LOOKBOOK_PROD_V1["graph_ref"],
        status="published",
        version=1,
    ))


def _seed_default_pack(db):
    slug = DEFAULT_GENERATION_PACK["slug"]
    existing = (
        db.query(PromptGenerationPack)
        .filter(PromptGenerationPack.slug == slug)
        .filter(PromptGenerationPack.status == "published")
        .first()
    )
    if existing:
        return
    db.add(PromptGenerationPack(
        id=str(uuid.uuid4()),
        slug=slug,
        name=DEFAULT_GENERATION_PACK["name"],
        scenario_json=json.dumps(DEFAULT_GENERATION_PACK["scenario_json"], ensure_ascii=False),
        user_needs_json=json.dumps(DEFAULT_GENERATION_PACK["user_needs_json"], ensure_ascii=False),
        techniques_json=json.dumps(DEFAULT_GENERATION_PACK["techniques_json"], ensure_ascii=False),
        harness_pipeline_slug=DEFAULT_GENERATION_PACK["harness_pipeline_slug"],
        status="published",
        version=1,
        skill_version_id="local_v1",
    ))
