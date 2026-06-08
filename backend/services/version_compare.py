"""Pipeline 版本双轨对比：文本 Judge + SQLite 人评基线。"""

import json
from statistics import mean

from agents.graphs.lookbook_prompt_graph import run_prompt_agent
from data.services import AgentDefinitionService, HarnessTestCaseService
from models import ImageEvaluation
from services.harness_testcase_runner import _text_judge
from domains.agent.pipeline_version import get_version_pair
from domains.agent.recommendation import recommend_publish
from services.seed_admin_data import BUILTIN_AGENT_SLUG, BUILTIN_PIPELINE_SLUG
from config import get_chat_api_config


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


def _human_score(human_eval: dict) -> float:
    if not human_eval:
        return 0.0
    scores = human_eval.get("scores") or {}
    if scores:
        vals = [float(v) for v in scores.values() if isinstance(v, (int, float))]
        if vals:
            return mean(vals)
    overall_map = {"good": 5.0, "fair": 3.0, "poor": 1.0}
    return overall_map.get(human_eval.get("overall"), 3.0)


def _aggregate_human(cases: list[dict]) -> dict:
    with_human = [c for c in cases if c.get("human_eval")]
    if not with_human:
        return {"case_count": 0, "good_rate": None, "avg_score": None, "cases": []}
    good = sum(1 for c in with_human if c["human_eval"].get("overall") == "good")
    scores = [_human_score(c["human_eval"]) for c in with_human]
    return {
        "case_count": len(with_human),
        "good_rate": round(good / len(with_human) * 100, 1),
        "avg_score": round(mean(scores), 2),
        "cases": with_human,
    }


async def _run_pipeline_on_case(agent_config: dict, pipeline_id: str, case: dict) -> dict:
    cfg = {**agent_config, "pipeline_config_id": pipeline_id}
    clothing_ids = _parse_json(case.get("clothing_ids_json") or case.get("clothing_ids"), [])
    business_context = _parse_json(case.get("business_context_json") or case.get("business_context"), {})
    inputs = {
        "model_id": case.get("model_id"),
        "clothing_ids": clothing_ids,
        "reference_id": case.get("reference_id"),
        "scene_id": case.get("scene_id"),
        "size": case.get("size") or "3:4",
        "quantity": case.get("quantity") or 4,
        "business_context": business_context,
        "acceptance_criteria": case.get("acceptance_criteria") or "",
    }
    result = await run_prompt_agent(
        inputs,
        cfg,
        session_id=f"compare-tc-{case.get('id')}",
        user_id="version-compare",
        ref_type="harness_testcase",
        ref_id=case.get("id"),
    )
    prompts = result.get("prompts") or []
    chat_cfg = get_chat_api_config()
    endpoint = (chat_cfg.get("endpoint") or "").strip()
    api_key = (chat_cfg.get("api_key") or "").strip()
    text_judge = None
    if prompts and endpoint and api_key:
        text_judge = await _text_judge(
            prompts,
            {"quantity": inputs["quantity"], "acceptance_criteria": inputs["acceptance_criteria"]},
            endpoint,
            api_key,
        )
    elif prompts:
        text_judge = {
            "avg": 3.0,
            "pass": len(prompts) >= int(inputs["quantity"] or 1),
            "notes": "未配置对话模型",
        }
    return {
        "case_id": case.get("id"),
        "case_name": case.get("name"),
        "prompt_count": len(prompts),
        "text_judge": text_judge,
        "pass": bool(text_judge.get("pass")) if text_judge else False,
        "avg": text_judge.get("avg") if text_judge else None,
    }


def _aggregate_text(results: list[dict]) -> dict:
    if not results:
        return {"case_count": 0, "pass_rate": 0, "avg_score": 0, "cases": []}
    passed = sum(1 for r in results if r.get("pass"))
    avgs = [float(r["avg"]) for r in results if r.get("avg") is not None]
    return {
        "case_count": len(results),
        "pass_rate": round(passed / len(results) * 100, 1),
        "avg_score": round(mean(avgs), 2) if avgs else 0,
        "cases": results,
    }


def _load_human_eval(db, case: dict) -> dict | None:
    human = _parse_json(case.get("human_eval_json"), {})
    if human:
        return human
    ev_id = case.get("source_evaluation_id")
    img_id = case.get("source_image_id")
    ev = None
    if ev_id:
        ev = db.query(ImageEvaluation).filter(ImageEvaluation.id == ev_id).first()
    elif img_id:
        ev = (
            db.query(ImageEvaluation)
            .filter(ImageEvaluation.image_id == img_id)
            .order_by(ImageEvaluation.updated_at.desc())
            .first()
        )
    if not ev:
        return None
    return {
        "overall": ev.overall,
        "scores": json.loads(ev.scores_json) if ev.scores_json else {},
        "issues": json.loads(ev.issues_json) if ev.issues_json else [],
        "expert_note": ev.expert_note,
    }


def _recommendation(published_text: dict, draft_text: dict, human: dict) -> str:
    return recommend_publish(published_text, draft_text, human)


async def compare_versions(
    db,
    *,
    slug: str = BUILTIN_PIPELINE_SLUG,
    testcase_ids: list[str] | None = None,
) -> dict:
    pair = get_version_pair(db, slug)
    published = pair.get("published")
    draft = pair.get("draft")
    if not published:
        raise ValueError(f"无已发布 Pipeline: {slug}")
    if not draft:
        raise ValueError("无 draft，请先「从 published 克隆 draft」或运行优化脚本")

    agent_row = None
    rows = AgentDefinitionService(db).list_all()
    agent_row = next((r for r in rows if r.get("slug") == BUILTIN_AGENT_SLUG), None)
    if not agent_row:
        raise ValueError("Agent 不存在")

    tool_ids = agent_row.get("tool_ids_json") or agent_row.get("tool_ids") or []
    if isinstance(tool_ids, str):
        tool_ids = json.loads(tool_ids)
    agent_config = {
        "id": agent_row["id"],
        "slug": agent_row.get("slug"),
        "pipeline_config_id": published["id"],
        "tool_ids": tool_ids,
        "knowledge_tree_id": agent_row.get("knowledge_tree_id"),
    }

    tc_svc = HarnessTestCaseService(db)
    all_cases = tc_svc.list_all()
    if testcase_ids:
        cases = [c for c in all_cases if c.get("id") in testcase_ids]
    else:
        cases = all_cases[:10]
    if not cases:
        raise ValueError("无 TestCase 可对比")

    human_cases = []
    for case in cases:
        he = _load_human_eval(db, case)
        if he:
            human_cases.append({"case_id": case.get("id"), "case_name": case.get("name"), "human_eval": he})

    pub_results = []
    draft_results = []
    for case in cases:
        pub_results.append(await _run_pipeline_on_case(agent_config, published["id"], case))
        draft_results.append(await _run_pipeline_on_case(agent_config, draft["id"], case))

    published_text = _aggregate_text(pub_results)
    draft_text = _aggregate_text(draft_results)
    human = _aggregate_human(human_cases)

    return {
        "slug": slug,
        "published": {
            "pipeline_id": published["id"],
            "version": published.get("version"),
            "text": published_text,
        },
        "draft": {
            "pipeline_id": draft["id"],
            "version": draft.get("version"),
            "text": draft_text,
        },
        "human_baseline": human,
        "recommendation": _recommendation(published_text, draft_text, human),
        "dual_track_note": "文本轨对比 published vs draft；人评轨为 import 的专家评价基线（等权决策参考）",
    }
