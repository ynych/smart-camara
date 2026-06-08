"""进化方向控制 — 三道门检查。"""

from __future__ import annotations

from typing import Any

from harness.defaults import PIPELINE_LOOKBOOK_V1
from harness.module_registry import MODULE_REGISTRY

from domains.checks.base import CheckDomain, CheckResult, _result


def check_gate_signal(ctx: dict[str, Any]) -> CheckResult:
    """信号门：只认人评 ground truth + 验收标准驱动的文本 Judge。"""
    tc = ctx.get("testcase") or {}
    ev = tc.get("evaluation_json") or tc.get("evaluation") or {}
    if isinstance(ev, str):
        import json
        try:
            ev = json.loads(ev)
        except json.JSONDecodeError:
            ev = {}
    human = ev.get("human_eval") or tc.get("human_eval_json")
    criteria = (tc.get("acceptance_criteria") or "").strip()
    text_judge = (ev.get("text_judge") or {}) if isinstance(ev, dict) else {}
    has_human = bool(human)
    has_text = bool(criteria) and bool(text_judge)
    ok = has_human or has_text
    return _result(
        "GATE_signal",
        CheckDomain.GATE,
        ok,
        "进化信号有效（人评或文本 Judge+验收标准）" if ok else "缺少人评快照或验收标准+文本 Judge",
        has_human=has_human,
        has_text_track=has_text,
    )


def check_gate_granularity(ctx: dict[str, Any]) -> CheckResult:
    """粒度门：变更限定在 Harness 模块 A1–E2。"""
    patches = ctx.get("module_patches") or ctx.get("patches") or {}
    if not patches:
        return _result(
            "GATE_granularity",
            CheckDomain.GATE,
            True,
            "无模块补丁（跳过粒度检查）",
            patched=[],
        )
    registry_ids = set(PIPELINE_LOOKBOOK_V1["modules"].keys())
    for layer in MODULE_REGISTRY.values():
        for item in layer:
            registry_ids.add(item.get("module_id") or item.get("key") or item.get("handler_key") or item.get("id"))
    invalid = [key for key in patches if key not in registry_ids]
    ok = len(invalid) == 0
    return _result(
        "GATE_granularity",
        CheckDomain.GATE,
        ok,
        "模块补丁在 Harness 注册表内" if ok else f"存在非模块化补丁: {invalid}",
        patched=list(patches.keys()),
        invalid=invalid,
    )


def check_gate_approval(ctx: dict[str, Any]) -> CheckResult:
    """审批门：draft 不可被用户平台消费；须 Compare 后 Publish。"""
    pair = ctx.get("pipeline_pair") or {}
    draft = pair.get("draft")
    published = pair.get("published")
    user_pipeline_id = ctx.get("user_consumed_pipeline_id")
    compare = ctx.get("compare_result") or {}
    rec = compare.get("recommendation")

    draft_leaked = draft and user_pipeline_id == draft.get("id")
    ok = not draft_leaked and published is not None
    if compare and rec == "reject":
        ok = ok and user_pipeline_id != draft.get("id") if draft else ok

    msg = "用户只消费 published；draft 未泄漏" if ok else "draft 被用户平台使用或缺少 published"
    return _result(
        "GATE_approval",
        CheckDomain.GATE,
        ok,
        msg,
        user_pipeline_id=user_pipeline_id,
        published_id=(published or {}).get("id"),
        draft_id=(draft or {}).get("id") if draft else None,
        recommendation=rec,
    )


EVOLUTION_GATE_CHECKS = [
    check_gate_signal,
    check_gate_granularity,
    check_gate_approval,
]
