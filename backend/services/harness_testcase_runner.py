"""Harness TestCase：提示词生成 + 双轨评价（文本 Judge + SQLite 人评）。"""

import json
import time

from agents.prompt_agent import call_ark_chat, extract_responses_text
from config import get_chat_api_config
from data.services import HarnessTestCaseService
from services.observability.run_ledger import record_run


def _parse_json(value, default=None):
    if value is None:
        return default if default is not None else {}
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default if default is not None else {}
    return default if default is not None else {}


def _case_inputs(case: dict) -> dict:
    clothing_ids = _parse_json(case.get("clothing_ids_json") or case.get("clothing_ids"), [])
    business_context = _parse_json(case.get("business_context_json") or case.get("business_context"), {})
    prompts = _parse_json(case.get("prompts_json") or case.get("prompts"), [])
    return {
        "model_id": case.get("model_id"),
        "clothing_ids": clothing_ids,
        "reference_id": case.get("reference_id"),
        "scene_id": case.get("scene_id"),
        "size": case.get("size") or "3:4",
        "quantity": case.get("quantity") or 4,
        "business_context": business_context,
        "acceptance_criteria": case.get("acceptance_criteria") or "",
        "prompts": prompts,
    }


async def _text_judge(prompts: list, ctx: dict, endpoint: str, api_key: str) -> dict:
    quantity = int(ctx.get("quantity") or 4)
    text = "\n---\n".join(p.get("prompt", "") for p in prompts[:quantity])
    system = "你是 Lookbook 提示词质检员。输出 JSON：{\"avg\":1-5,\"pass\":true/false,\"notes\":\"\"}"
    user = f"验收标准：{ctx.get('acceptance_criteria','')}\n数量要求：{quantity}\n提示词：\n{text}"
    body, _ = await call_ark_chat(
        api_key, endpoint,
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=256,
        temperature=0,
    )
    if not body:
        return {"avg": 0, "pass": len(prompts) >= quantity, "notes": "judge skipped"}
    content = extract_responses_text(body)
    try:
        chunk = content[content.find("{") : content.rfind("}") + 1]
        return json.loads(chunk)
    except json.JSONDecodeError:
        return {"avg": 3, "pass": len(prompts) >= quantity, "notes": content[:200]}


async def run_testcase_evaluation(db, case_id: str) -> dict:
    svc = HarnessTestCaseService(db)
    case = svc.get(case_id)
    if not case:
        raise ValueError("TestCase 不存在")

    started = time.perf_counter()
    inputs = _case_inputs(case)
    prompts = inputs["prompts"]

    config = get_chat_api_config()
    endpoint = (config.get("endpoint") or "").strip()
    api_key = (config.get("api_key") or "").strip()

    text_judge = None
    if prompts:
        ctx = {
            "quantity": inputs["quantity"],
            "acceptance_criteria": inputs["acceptance_criteria"],
        }
        if endpoint and api_key:
            text_judge = await _text_judge(prompts, ctx, endpoint, api_key)
        else:
            text_judge = {
                "avg": 3.0,
                "pass": len(prompts) >= int(inputs["quantity"] or 1),
                "notes": "未配置对话模型，仅检查提示词数量",
            }

    human_eval = _parse_json(case.get("human_eval_json"), {})
    if not human_eval and (case.get("source_image_id") or case.get("source_evaluation_id")):
        from models import ImageEvaluation
        ev = None
        if case.get("source_evaluation_id"):
            ev = db.query(ImageEvaluation).filter(ImageEvaluation.id == case["source_evaluation_id"]).first()
        elif case.get("source_image_id"):
            ev = (
                db.query(ImageEvaluation)
                .filter(ImageEvaluation.image_id == case["source_image_id"])
                .order_by(ImageEvaluation.updated_at.desc())
                .first()
            )
        if ev:
            human_eval = {
                "overall": ev.overall,
                "scores": _parse_json(ev.scores_json, {}),
                "issues": _parse_json(ev.issues_json, []),
                "suggestions": _parse_json(ev.suggestions_json, []),
                "expert_note": ev.expert_note,
                "reviewer_name": ev.reviewer_name,
                "source": "sqlite_image_evaluations",
            }

    text_pass = bool(text_judge.get("pass")) if text_judge else False
    human_pass = True
    if human_eval:
        human_pass = human_eval.get("overall") in ("good", "fair")

    passed = text_pass and human_pass if human_eval else text_pass
    evaluation = {
        "text_judge": text_judge,
        "human_eval": human_eval or None,
        "pass": passed,
        "summary": _build_summary(text_judge, human_eval, passed),
        "tracks": {
            "text": {"pass": text_pass, "weight": 0.5},
            "human": {"pass": human_pass, "weight": 0.5 if human_eval else 0},
        },
    }

    run_id = record_run(
        run_type="harness_eval",
        status="success" if passed else "failed",
        session_id=f"harness-tc-{case_id}",
        user_id="harness",
        ref_type="harness_testcase",
        ref_id=case_id,
        input={"case_id": case_id, "prompt_count": len(prompts), "has_human_eval": bool(human_eval)},
        output=evaluation,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )

    svc.update(case_id, {
        "evaluation_json": evaluation,
        "pass_label": 1 if passed else 0,
        "status": "passed" if passed else "failed",
        "last_run_id": run_id,
    })

    return {"case_id": case_id, "evaluation": evaluation, "pass": passed, "run_id": run_id}


def _build_summary(text_judge: dict | None, human_eval: dict | None, passed: bool) -> str:
    parts = []
    if text_judge:
        parts.append(f"文本 Judge avg={text_judge.get('avg')} pass={text_judge.get('pass')}")
    if human_eval:
        parts.append(f"专家人评 overall={human_eval.get('overall')}")
    parts.append("整体通过" if passed else "未通过")
    return "；".join(parts)
