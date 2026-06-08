"""Lookbook 提示词 Harness 默认配置（MVP：核心四模块 + fusion/subject/camera + regen）。"""

PIPELINE_LOOKBOOK_V1 = {
    "id": "lookbook_v1",
    "name": "Lookbook 标准流水线",
    "module_order": [
        "fusion",
        "role",
        "subject",
        "scene",
        "camera",
        "goal",
        "constraint",
        "regen",
    ],
    "modules": {
        "fusion": {
            "label": "多图融合",
            "template": "{fusion_text}",
            "tools": ["build_fusion_prefix"],
        },
        "role": {
            "label": "角色",
            "template": "一位{model_desc}，姿态自然专业。",
            "tools": ["describe_material"],
        },
        "subject": {
            "label": "服装主体",
            "template": "穿着{clothing_desc}，服装版型与颜色需与参考服装图一致。",
            "tools": ["describe_clothing"],
        },
        "scene": {
            "label": "场景",
            "template": "{scene_desc}。{style_hint}",
            "tools": ["extract_reference_style"],
        },
        "camera": {
            "label": "镜头构图",
            "template": "{angle_desc}，{size_hint}，85mm镜头浅景深，高清电商Lookbook。",
            "tools": [],
        },
        "goal": {
            "label": "目标",
            "template": "{goal_text}",
            "tools": [],
        },
        "constraint": {
            "label": "约束",
            "template": "验收约束：{constraint_text}",
            "tools": [],
        },
        "regen": {
            "label": "迭代补丁",
            "template": "{regen_text}",
            "tools": ["apply_feedback_rules"],
            "optional": True,
        },
    },
}

SIZE_HINTS = {
    "1:1": "正方形构图，主体居中",
    "3:4": "竖版3:4构图，完整展示穿搭",
    "9:16": "9:16长竖构图，适合移动端",
}
