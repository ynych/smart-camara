"""用户域 — 5 步旅程中间态检查（U1–U5）。"""

from __future__ import annotations

from typing import Any

from domains.checks.base import CheckDomain, CheckResult, _result


def check_u1_materials(ctx: dict[str, Any]) -> CheckResult:
    grouped = ctx.get("materials_grouped") or {}
    models = grouped.get("models") or []
    clothing = grouped.get("clothing_sets") or grouped.get("clothing") or []
    ok = len(models) >= 1 and len(clothing) >= 1
    return _result(
        "U1_materials",
        CheckDomain.USER,
        ok,
        "素材分组可用（模特 + 服装）" if ok else "缺少模特卡或服装套装",
        model_count=len(models),
        clothing_set_count=len(clothing),
    )


def check_u2_selection(ctx: dict[str, Any]) -> CheckResult:
    sel = ctx.get("selection") or {}
    model_id = (sel.get("model_id") or "").strip()
    clothing_ids = sel.get("clothing_ids") or []
    ok = bool(model_id) and len(clothing_ids) >= 1
    return _result(
        "U2_selection",
        CheckDomain.USER,
        ok,
        "已选模特与服装" if ok else "需选择 model_id 与至少 1 件服装",
        model_id=model_id or None,
        clothing_count=len(clothing_ids),
    )


def check_u3_prompts(ctx: dict[str, Any]) -> CheckResult:
    pr = ctx.get("prompt_result") or {}
    source = pr.get("prompt_source") or pr.get("source")
    prompts = pr.get("prompts") or []
    quantity = int(ctx.get("quantity") or pr.get("quantity") or 1)
    llm_err = pr.get("llm_error")
    ok = source == "llm" and len(prompts) >= quantity and not llm_err
    msg = "LLM 提示词就绪" if ok else f"提示词未达标 source={source} count={len(prompts)}"
    return _result(
        "U3_prompts",
        CheckDomain.USER,
        ok,
        msg,
        prompt_source=source,
        prompt_count=len(prompts),
        quantity=quantity,
        llm_error=llm_err,
    )


def check_u4_generation(ctx: dict[str, Any]) -> CheckResult:
    gen = ctx.get("generation_result") or {}
    images = gen.get("images") or gen.get("generated_images") or []
    task_id = gen.get("task_id")
    ok = bool(task_id) and len(images) >= 1
    return _result(
        "U4_generation",
        CheckDomain.USER,
        ok,
        "生图任务完成" if ok else "缺少 task_id 或成图",
        task_id=task_id,
        image_count=len(images),
    )


def check_u5_evaluation(ctx: dict[str, Any]) -> CheckResult:
    ev = ctx.get("evaluation") or ctx.get("human_eval") or {}
    overall = ev.get("overall")
    scores = ev.get("scores") or {}
    ok = overall in ("good", "fair", "poor") or bool(scores)
    return _result(
        "U5_evaluation",
        CheckDomain.USER,
        ok,
        "专家评价已写入" if ok else "缺少结构化评价（overall 或 scores）",
        overall=overall,
        has_scores=bool(scores),
    )


USER_JOURNEY_CHECKS = [
    check_u1_materials,
    check_u2_selection,
    check_u3_prompts,
    check_u4_generation,
    check_u5_evaluation,
]
