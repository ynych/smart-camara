"""可迭代优化的 Harness 模块注册表（用户选定 A1–A8, B1–B3, C1, D1–D2, E1–E2）。"""

MODULE_REGISTRY = {
    "pipeline": [
        {"id": "A1", "module_id": "fusion", "label": "多图融合", "layer": "pipeline", "optimizable": ["template", "order"]},
        {"id": "A2", "module_id": "role", "label": "角色/模特", "layer": "pipeline", "optimizable": ["template"]},
        {"id": "A3", "module_id": "subject", "label": "服装主体", "layer": "pipeline", "optimizable": ["template"]},
        {"id": "A4", "module_id": "scene", "label": "场景风格", "layer": "pipeline", "optimizable": ["template"]},
        {"id": "A5", "module_id": "camera", "label": "镜头构图", "layer": "pipeline", "optimizable": ["template"]},
        {"id": "A6", "module_id": "goal", "label": "商家目标", "layer": "pipeline", "optimizable": ["template"]},
        {"id": "A7", "module_id": "constraint", "label": "验收约束", "layer": "pipeline", "optimizable": ["template"]},
        {"id": "A8", "module_id": "regen", "label": "迭代补丁", "layer": "pipeline", "optimizable": ["template"]},
    ],
    "tools": [
        {"id": "B1", "handler_key": "describe_material", "label": "描述模特", "layer": "tool"},
        {"id": "B2", "handler_key": "describe_clothing", "label": "描述服装", "layer": "tool"},
        {"id": "B3", "handler_key": "extract_reference_style", "label": "参考图风格", "layer": "tool"},
    ],
    "llm": [
        {"id": "C1", "key": "llm_generate_prompt", "label": "多角度 LLM 提示词", "layer": "llm"},
    ],
    "knowledge": [
        {"id": "D1", "key": "pageindex_query", "label": "知识树检索 Query", "layer": "knowledge"},
        {"id": "D2", "key": "pageindex_ingest", "label": "知识节点沉淀规则", "layer": "knowledge"},
    ],
    "eval": [
        {"id": "E1", "key": "text_judge", "label": "文本 Judge Prompt", "layer": "eval"},
        {"id": "E2", "key": "pass_threshold", "label": "Pass 阈值", "layer": "eval", "default": {"min_avg": 3.5, "min_pass_rate": 70}},
    ],
}

SELECTED_MODULE_IDS = [
    "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8",
    "B1", "B2", "B3", "C1", "D1", "D2", "E1", "E2",
]


def get_selected_modules() -> list[dict]:
    out = []
    for group in MODULE_REGISTRY.values():
        for m in group:
            if m["id"] in SELECTED_MODULE_IDS:
                out.append(m)
    return out
