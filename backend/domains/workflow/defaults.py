"""内置 Workflow / Pack 默认定义。"""

LOOKBOOK_PROD_V1 = {
    "workflow_id": "lookbook_prod_v1",
    "name": "Lookbook 生产工作流 v1",
    "description": "validate → 选包 → Harness → C1 → 校验 → [Seedream]",
    "graph_ref": "lookbook_prompt_graph",
    "steps": [
        {"id": "validate_input", "label": "校验入参", "type": "validate_input"},
        {"id": "route_pack", "label": "选 Prompt 生成包", "type": "route_pack"},
        {"id": "run_tools", "label": "B* 工具", "type": "langgraph_node"},
        {"id": "retrieve_knowledge", "label": "D1 检索", "type": "langgraph_node"},
        {"id": "assemble_pipeline", "label": "A* 组装", "type": "langgraph_node"},
        {"id": "llm_generate", "label": "C1 生成", "type": "langgraph_node"},
        {"id": "validate_output", "label": "校验 prompts", "type": "validate_output"},
        {"id": "seedream", "label": "Seedream 生图", "type": "seedream", "optional": True},
    ],
}

DEFAULT_GENERATION_PACK = {
    "slug": "lookbook_default",
    "name": "Lookbook 默认生成包",
    "scenario_json": {
        "tags": ["lookbook", "ecommerce", "default"],
        "summary": "电商 Lookbook 默认策略",
        "match_rules": {},
    },
    "user_needs_json": [
        "服装版型与参考图一致",
        "多角度覆盖",
        "克制专业的电商语气",
    ],
    "techniques_json": {
        "module_patches": {},
        "generation_hints": {
            "angle_strategy": "四角度：正面/侧面/细节/环境",
        },
        "acceptance_criteria_template": "尺寸{size}，数量{quantity}。{constraint_text}",
    },
    "harness_pipeline_slug": "lookbook_v1",
}

DEFAULT_MANIFEST = {
    "slug": "lookbook_default",
    "workflow_id": "lookbook_prod_v1",
    "default_pack_slug": "lookbook_default",
    "pack_version_pin_json": {"lookbook_default": 1},
    "skill_version_id": "local_v1",
    "fallback_skill_version_id": "local_v1",
    "harness_pipeline_slug": "lookbook_v1",
}
