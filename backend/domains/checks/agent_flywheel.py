"""Agent 域 — Harness 自进化飞轮中间态检查（Sample→Publish）。"""

from __future__ import annotations

from typing import Any

from domains.checks.base import CheckDomain, CheckResult, _result


def check_a1_sample(ctx: dict[str, Any]) -> CheckResult:
    tc = ctx.get("testcase") or {}
    has_input = bool(tc.get("model_id")) or bool(tc.get("source_image_id"))
    has_criteria = bool((tc.get("acceptance_criteria") or "").strip())
    ok = has_input and has_criteria
    return _result(
        "A1_sample",
        CheckDomain.AGENT,
        ok,
        "TestCase 样本就绪" if ok else "TestCase 需素材 ID 或 source_image + 验收标准",
        model_id=tc.get("model_id"),
        source_image_id=tc.get("source_image_id"),
    )


def check_a2_run(ctx: dict[str, Any]) -> CheckResult:
    tc = ctx.get("testcase") or {}
    meta = tc.get("run_meta_json") or tc.get("run_meta") or {}
    if isinstance(meta, str):
        import json
        try:
            meta = json.loads(meta)
        except json.JSONDecodeError:
            meta = {}
    prompts = tc.get("prompts_json") or tc.get("prompts") or []
    if isinstance(prompts, str):
        import json
        try:
            prompts = json.loads(prompts)
        except json.JSONDecodeError:
            prompts = []
    run_id = tc.get("last_run_id") or meta.get("run_id")
    ok = bool(run_id) and len(prompts) >= 1
    return _result(
        "A2_run",
        CheckDomain.AGENT,
        ok,
        "Agent 运行完成" if ok else "缺少 run_id 或 prompts_json",
        run_id=run_id,
        prompt_count=len(prompts),
        source=meta.get("source"),
    )


def check_a3_eval(ctx: dict[str, Any]) -> CheckResult:
    tc = ctx.get("testcase") or {}
    ev = tc.get("evaluation_json") or tc.get("evaluation") or {}
    if isinstance(ev, str):
        import json
        try:
            ev = json.loads(ev)
        except json.JSONDecodeError:
            ev = {}
    text_judge = ev.get("text_judge") or {}
    human = ev.get("human_eval")
    ok = bool(text_judge) and "pass" in text_judge
    return _result(
        "A3_eval",
        CheckDomain.AGENT,
        ok,
        "双轨评测已执行" if ok else "缺少 evaluation_json.text_judge",
        text_pass=text_judge.get("pass"),
        has_human=bool(human),
        overall_pass=ev.get("pass"),
    )


def check_a4_propose(ctx: dict[str, Any]) -> CheckResult:
    pair = ctx.get("pipeline_pair") or {}
    draft = pair.get("draft")
    ok = draft is not None and (draft.get("status") == "draft" or draft.get("slug", "").endswith("_draft"))
    return _result(
        "A4_propose",
        CheckDomain.AGENT,
        ok,
        "存在 draft Pipeline" if ok else "无 draft，需 clone 或 optimize 提案",
        draft_slug=draft.get("slug") if draft else None,
    )


def check_a5_compare(ctx: dict[str, Any]) -> CheckResult:
    cmp = ctx.get("compare_result") or {}
    pub = (cmp.get("published") or {}).get("text") or {}
    drf = (cmp.get("draft") or {}).get("text") or {}
    ok = bool(pub.get("case_count")) and bool(drf.get("case_count"))
    rec = cmp.get("recommendation")
    return _result(
        "A5_compare",
        CheckDomain.AGENT,
        ok,
        "版本对比已完成" if ok else "Compare 缺少 published/draft 文本轨结果",
        recommendation=rec,
        published_pass_rate=pub.get("pass_rate"),
        draft_pass_rate=drf.get("pass_rate"),
    )


def check_a6_publish(ctx: dict[str, Any]) -> CheckResult:
    pair = ctx.get("pipeline_pair") or {}
    published = pair.get("published")
    draft = pair.get("draft")
    agent_uses_published = ctx.get("agent_pipeline_id") == (published or {}).get("id")
    ok = published is not None and published.get("status") == "published"
    if ctx.get("require_no_draft_after_publish"):
        ok = ok and draft is None
    return _result(
        "A6_publish",
        CheckDomain.AGENT,
        ok,
        "published Pipeline 生效" if ok else "无 published 或 Agent 未绑定 published",
        published_version=(published or {}).get("version"),
        agent_bound=agent_uses_published,
        has_draft=bool(draft),
    )


AGENT_FLYWHEEL_CHECKS = [
    check_a1_sample,
    check_a2_run,
    check_a3_eval,
    check_a4_propose,
    check_a5_compare,
    check_a6_publish,
]
