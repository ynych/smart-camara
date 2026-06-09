"""Pack / Workflow 域检查（P1/P2/W1）。"""

from __future__ import annotations

from typing import Any

from domains.checks.base import CheckDomain, CheckResult, _result
from domains.workflow.schema import validate_workflow_input, validate_workflow_output, WorkflowValidationError


def check_p1_pack_routing(ctx: dict[str, Any]) -> CheckResult:
    sel = ctx.get("pack_selection") or {}
    ok = bool(sel.get("pack_id")) and sel.get("status") == "published"
    return _result(
        "P1_pack_routing",
        CheckDomain.AGENT,
        ok,
        "已选中 published Pack" if ok else "Pack 路由失败",
        **sel,
    )


def check_p2_pack_publish(ctx: dict[str, Any]) -> CheckResult:
    manifest = ctx.get("manifest") or {}
    pack = ctx.get("published_pack") or {}
    pins = manifest.get("pack_version_pin_json") or {}
    slug = pack.get("slug")
    version = int(pack.get("version") or 0)
    ok = slug and pins.get(slug) == version and manifest.get("default_pack_id") == pack.get("id")
    return _result(
        "P2_pack_publish",
        CheckDomain.AGENT,
        ok,
        "manifest pin 已更新" if ok else "Publish 后 manifest 未 pin",
        slug=slug,
        version=version,
        pins=pins,
    )


def check_w1_workflow_schema(ctx: dict[str, Any]) -> CheckResult:
    inp = ctx.get("workflow_input") or {}
    out_prompts = ctx.get("workflow_output_prompts") or []
    quantity = int(inp.get("quantity") or 1)
    try:
        validate_workflow_input(inp)
        if out_prompts:
            validate_workflow_output(out_prompts, quantity)
        ok = True
        msg = "Workflow I/O schema 校验通过"
    except WorkflowValidationError as e:
        ok = False
        msg = str(e)
    return _result("W1_workflow_schema", CheckDomain.AGENT, ok, msg)


PACK_WORKFLOW_CHECKS = [
    check_p1_pack_routing,
    check_p2_pack_publish,
    check_w1_workflow_schema,
]
