"""Harness 流水线引擎：模块渲染 + 组装。"""

import re
import time
from typing import Any

from harness.context import HarnessContext
from harness.defaults import PIPELINE_LOOKBOOK_V1
from harness.tools import run_tool


def _safe_format(template: str, variables: dict) -> str:
    """仅替换已知占位符，避免 KeyError。"""

    def repl(match):
        key = match.group(1)
        val = variables.get(key, "")
        return str(val) if val is not None else ""

    return re.sub(r"\{(\w+)\}", repl, template).strip()


def run_module(
    module_id: str,
    ctx: HarnessContext,
    *,
    pipeline: dict | None = None,
) -> dict[str, Any]:
    pipeline = pipeline or PIPELINE_LOOKBOOK_V1
    mod_cfg = pipeline["modules"].get(module_id)
    if not mod_cfg:
        raise ValueError(f"未知模块: {module_id}")

    tool_traces = []
    ctx_dict = ctx.to_dict()
    for tool_id in mod_cfg.get("tools") or []:
        trace = run_tool(tool_id, ctx_dict)
        tool_traces.append(trace)
        ctx.tool_outputs.update(trace.get("output") or {})
        ctx_dict.update(trace.get("output") or {})

    variables = ctx.render_vars()
    text = _safe_format(mod_cfg["template"], variables)
    return {
        "module_id": module_id,
        "label": mod_cfg.get("label", module_id),
        "text": text,
        "params_snapshot": {k: variables.get(k) for k in variables if k in mod_cfg["template"]},
        "tool_traces": tool_traces,
    }


def run_pipeline(
    ctx: HarnessContext,
    *,
    pipeline: dict | None = None,
    enabled_modules: list[str] | None = None,
    include_regen: bool = False,
) -> dict[str, Any]:
    pipeline = pipeline or PIPELINE_LOOKBOOK_V1
    order = enabled_modules or pipeline["module_order"]
    module_outputs = []
    started = time.time()

    for module_id in order:
        mod_cfg = pipeline["modules"].get(module_id)
        if not mod_cfg:
            continue
        if mod_cfg.get("optional") and module_id == "regen" and not include_regen:
            if not (ctx.regen_text or ctx.evaluation):
                continue
        out = run_module(module_id, ctx, pipeline=pipeline)
        if not out["text"]:
            continue
        module_outputs.append(out)

    parts = [m["text"] for m in module_outputs if m["text"]]
    prompt = "\n".join(parts)
    return {
        "pipeline_id": pipeline["id"],
        "prompt": prompt,
        "modules": module_outputs,
        "elapsed_ms": int((time.time() - started) * 1000),
        "context": ctx.to_dict(),
    }


def get_pipeline_config(pipeline_id: str = "lookbook_v1") -> dict:
    if pipeline_id == "lookbook_v1":
        return PIPELINE_LOOKBOOK_V1
    raise ValueError(f"未知 pipeline: {pipeline_id}")
