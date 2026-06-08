"""Harness Tool 注册表（Skill 型，可经 API 调试）。"""

import json
from typing import Any, Callable

from tools.material_tool import MaterialTool


def _describe_material(ctx: dict) -> dict:
    model_id = ctx.get("model_id")
    info = MaterialTool.get(model_id) if model_id else None
    if not info:
        return {"model_desc": ctx.get("model_desc") or "优雅的亚洲女性模特"}
    meta = info.get("metadata") or {}
    desc = meta.get("description") or info.get("name") or ctx.get("model_desc")
    return {"model_desc": desc}


def _describe_clothing(ctx: dict) -> dict:
    ids = ctx.get("clothing_ids") or []
    items = MaterialTool.get_by_ids(ids) if ids else []
    parts = []
    for item in items:
        meta = item.get("metadata") or {}
        outfit = item.get("outfit_set") or meta.get("outfit_set", "")
        shoot = item.get("sub_category") or meta.get("sub_category", "")
        desc = meta.get("description") or item.get("name", "")
        label = f"{outfit}({shoot})：{desc}" if outfit else desc
        parts.append(label)
    clothing_desc = "；".join(parts) if parts else ctx.get("clothing_desc", "时尚服装")
    return {"clothing_desc": clothing_desc}


def _extract_reference_style(ctx: dict) -> dict:
    ref_id = ctx.get("reference_id")
    style_hint = ctx.get("style_hint") or ""
    scene_desc = ctx.get("scene_desc") or "电商Lookbook拍摄场景"
    if ref_id:
        info = MaterialTool.get(ref_id)
        if info:
            meta = info.get("metadata") or {}
            style_hint = meta.get("style") or meta.get("description") or style_hint or info.get("name", "")
    if style_hint and "风格" not in scene_desc:
        style_hint = f"参考图风格：{style_hint}"
    return {"style_hint": style_hint, "scene_desc": scene_desc}


def _build_fusion_prefix(ctx: dict) -> dict:
    slots = ctx.get("seedream_image_slots") or []
    if not slots:
        fusion = ctx.get("fusion_text") or ""
        return {"fusion_text": fusion}
    parts = [f"图{s.get('index')}为{s.get('role')}" for s in slots if s.get("resolved", True)]
    fusion = ""
    if parts:
        fusion = "【多图融合说明】" + "；".join(parts) + "。请严格按各图分工生成，尤其保持图1的Lookbook风格与构图。"
    return {"fusion_text": fusion}


def _apply_feedback_rules(ctx: dict) -> dict:
    ev = ctx.get("evaluation") or {}
    issues = ev.get("issues") or []
    suggestions = ev.get("suggestions") or []
    expert = (ev.get("expert_note") or "").strip()
    chunks = []
    if issues:
        chunks.append("需修正：" + "；".join(issues))
    if suggestions:
        chunks.append("优化方向：" + "；".join(suggestions))
    if expert:
        chunks.append(f"专家备注：{expert}")
    regen_text = " ".join(chunks)
    return {"regen_text": regen_text}


TOOL_REGISTRY: dict[str, dict] = {
    "describe_material": {
        "id": "describe_material",
        "name": "描述模特素材",
        "type": "skill",
        "module_ids": ["role"],
        "input_schema": {"model_id": "string"},
        "output_schema": {"model_desc": "string"},
        "handler": _describe_material,
    },
    "describe_clothing": {
        "id": "describe_clothing",
        "name": "描述服装素材",
        "type": "skill",
        "module_ids": ["subject"],
        "input_schema": {"clothing_ids": "array"},
        "output_schema": {"clothing_desc": "string"},
        "handler": _describe_clothing,
    },
    "extract_reference_style": {
        "id": "extract_reference_style",
        "name": "提取参考图风格",
        "type": "skill",
        "module_ids": ["scene"],
        "input_schema": {"reference_id": "string"},
        "output_schema": {"style_hint": "string", "scene_desc": "string"},
        "handler": _extract_reference_style,
    },
    "build_fusion_prefix": {
        "id": "build_fusion_prefix",
        "name": "构建多图融合前缀",
        "type": "skill",
        "module_ids": ["fusion"],
        "input_schema": {"seedream_image_slots": "array"},
        "output_schema": {"fusion_text": "string"},
        "handler": _build_fusion_prefix,
    },
    "apply_feedback_rules": {
        "id": "apply_feedback_rules",
        "name": "应用反馈规则",
        "type": "skill",
        "module_ids": ["regen"],
        "input_schema": {"evaluation": "object"},
        "output_schema": {"regen_text": "string"},
        "handler": _apply_feedback_rules,
    },
}


def list_tools() -> list[dict]:
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "type": t["type"],
            "module_ids": t["module_ids"],
            "input_schema": t["input_schema"],
            "output_schema": t["output_schema"],
        }
        for t in TOOL_REGISTRY.values()
    ]


def run_tool(tool_id: str, context: dict) -> dict:
    tool = TOOL_REGISTRY.get(tool_id)
    if not tool:
        raise ValueError(f"未知 Tool: {tool_id}")
    handler: Callable = tool["handler"]
    output = handler(context)
    return {
        "tool_id": tool_id,
        "input": context,
        "output": output,
    }
