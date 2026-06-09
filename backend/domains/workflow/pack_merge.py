"""将 Pack.techniques 合并进 Harness pipeline。"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any


def _parse_json_field(val: Any) -> Any:
    if isinstance(val, str):
        return json.loads(val)
    return val or {}


def merge_pack_into_pipeline(pipeline: dict[str, Any], techniques: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(pipeline)
    modules = out.get("modules") or {}
    patches = (techniques or {}).get("module_patches") or {}
    for mod_id, patch in patches.items():
        if mod_id not in modules:
            continue
        mod = deepcopy(modules[mod_id])
        if "template" in patch:
            mod["template"] = patch["template"]
        if "append" in patch and mod.get("template"):
            mod["template"] = f"{mod['template']}{patch['append']}"
        elif "append" in patch:
            mod["template"] = patch["append"]
        modules[mod_id] = mod
    out["modules"] = modules
    return out


def format_acceptance_from_pack(
    techniques: dict[str, Any],
    *,
    size: str,
    quantity: int,
    constraint_text: str,
    base: str = "",
) -> str:
    tpl = (techniques or {}).get("acceptance_criteria_template") or ""
    if not tpl:
        return base
    try:
        extra = tpl.format(size=size, quantity=quantity, constraint_text=constraint_text or "无")
    except (KeyError, ValueError):
        extra = tpl
    if base:
        return f"{base}\n{extra}".strip()
    return extra.strip()


def pack_to_overlay(pack: dict[str, Any]) -> dict[str, Any]:
    techniques = _parse_json_field(pack.get("techniques_json") or pack.get("techniques"))
    return {
        "pack_id": pack.get("id"),
        "pack_version": pack.get("version"),
        "pack_slug": pack.get("slug"),
        "techniques": techniques,
    }
