"""Admin 默认数据种子（AI 无关配置）。"""

import json
import uuid

from database import SessionLocal
from harness.defaults import PIPELINE_LOOKBOOK_V1
from harness.tools import TOOL_REGISTRY
from models import (
    AgentDefinition,
    AgentTestCase,
    HarnessTestCase,
    KnowledgeTree,
    PipelineConfig,
    ToolDefinition,
)


BUILTIN_AGENT_SLUG = "lookbook_prompt_agent_v1"
BUILTIN_PIPELINE_SLUG = "lookbook_v1"
BUILTIN_KNOWLEDGE_SLUG = "lookbook_knowledge"


def seed_admin_data():
    import models  # noqa: F401 — 确保所有表注册到 metadata
    from database import engine, Base

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        tool_id_map = _seed_tools(db)
        pipeline_id = _seed_pipeline(db)
        tree_id = _seed_knowledge_tree(db)
        agent_id = _seed_agent(db, pipeline_id, tree_id, tool_id_map)
        if agent_id:
            _seed_harness_testcase(db, agent_id)
        db.commit()
    finally:
        db.close()


def _seed_tools(db) -> dict[str, str]:
    mapping = {}
    for key, tool in TOOL_REGISTRY.items():
        existing = db.query(ToolDefinition).filter(ToolDefinition.slug == key).first()
        if existing:
            mapping[key] = existing.id
            continue
        row = ToolDefinition(
            id=str(uuid.uuid4()),
            slug=key,
            name=tool["name"],
            description=f"内置 Skill Tool: {key}",
            handler_key=key,
            module_ids_json=json.dumps(tool.get("module_ids") or [], ensure_ascii=False),
            input_schema_json=json.dumps(tool.get("input_schema") or {}, ensure_ascii=False),
            output_schema_json=json.dumps(tool.get("output_schema") or {}, ensure_ascii=False),
            status="published",
        )
        db.add(row)
        mapping[key] = row.id
    return mapping


def _seed_pipeline(db) -> str:
    existing = db.query(PipelineConfig).filter(PipelineConfig.slug == BUILTIN_PIPELINE_SLUG).first()
    if existing:
        return existing.id
    row = PipelineConfig(
        id=str(uuid.uuid4()),
        slug=BUILTIN_PIPELINE_SLUG,
        name=PIPELINE_LOOKBOOK_V1["name"],
        description="Lookbook 标准 Harness 流水线",
        module_order_json=json.dumps(PIPELINE_LOOKBOOK_V1["module_order"], ensure_ascii=False),
        modules_json=json.dumps(PIPELINE_LOOKBOOK_V1["modules"], ensure_ascii=False),
        status="published",
        version=1,
    )
    db.add(row)
    return row.id


def _seed_knowledge_tree(db) -> str:
    existing = db.query(KnowledgeTree).filter(KnowledgeTree.slug == BUILTIN_KNOWLEDGE_SLUG).first()
    if existing:
        return existing.id
    row = KnowledgeTree(
        id=str(uuid.uuid4()),
        slug=BUILTIN_KNOWLEDGE_SLUG,
        name="Lookbook 知识库",
        description="PageIndex 风格知识树，随迭代增量写入",
        version=1,
    )
    db.add(row)
    return row.id


def _seed_agent(db, pipeline_id: str, tree_id: str, tool_id_map: dict[str, str]) -> str | None:
    existing = db.query(AgentDefinition).filter(AgentDefinition.slug == BUILTIN_AGENT_SLUG).first()
    if existing:
        return existing.id
    tool_ids = [
        tool_id_map.get("describe_material"),
        tool_id_map.get("describe_clothing"),
        tool_id_map.get("extract_reference_style"),
        tool_id_map.get("build_fusion_prefix"),
    ]
    tool_ids = [x for x in tool_ids if x]
    agent_id = str(uuid.uuid4())
    db.add(AgentDefinition(
        id=agent_id,
        slug=BUILTIN_AGENT_SLUG,
        name="Lookbook 提示词 Agent",
        description="根据模特/服装/参考图与商家需求生成多角度生图提示词",
        role_prompt="你是电商 Lookbook 摄影导演，负责编写 Seedream 图生图中文提示词。",
        pipeline_config_id=pipeline_id,
        tool_ids_json=json.dumps(tool_ids, ensure_ascii=False),
        knowledge_tree_id=tree_id,
        graph_config_json=json.dumps({"graph": "lookbook_prompt_v1"}, ensure_ascii=False),
        status="published",
        is_builtin=1,
    ))
    db.add(AgentTestCase(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        name="默认 4 张 3:4",
        description="预置 TestCase，请在 Admin 填写素材 ID",
        inputs_json=json.dumps({
            "model_id": "",
            "clothing_ids": [],
            "reference_id": "",
            "scene_id": "",
            "size": "3:4",
            "quantity": 4,
            "business_context": {
                "merchant_need": "电商主图与详情页展示",
                "target_audience": "25-35 岁都市女性",
            },
            "acceptance_criteria": "服装颜色准确，构图专业，光线自然",
        }, ensure_ascii=False),
        expected_json=json.dumps({"min_prompts": 4}, ensure_ascii=False),
        sort_order=0,
    ))
    return agent_id


def _seed_harness_testcase(db, agent_id: str):
    if db.query(HarnessTestCase).count() > 0:
        return
    db.add(HarnessTestCase(
        id=str(uuid.uuid4()),
        name="默认 Harness TestCase",
        agent_id=agent_id,
        size="3:4",
        quantity=4,
        clothing_ids_json="[]",
        business_context_json=json.dumps({
            "merchant_need": "电商主图与详情页展示",
            "target_audience": "25-35 岁都市女性",
        }, ensure_ascii=False),
        acceptance_criteria="服装颜色准确，构图专业，光线自然",
        status="draft",
    ))
