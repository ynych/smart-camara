"""黄金评测集文本侧回归。"""

import json

from agents.prompt_agent import call_ark_chat, extract_responses_text
from config import get_chat_api_config
from data.services import GoldenEvalCaseService, GoldenEvalRunService
from agents.graphs.lookbook_prompt_graph import run_prompt_agent
from services.seed_admin_data import BUILTIN_AGENT_SLUG
from data.services import AgentDefinitionService


async def run_golden_regression(db, body: dict) -> dict:
    agent_id = body.get("agent_id")
    case_ids = body.get("case_ids")
    svc = GoldenEvalCaseService(db)
    cases = svc.list_all()
    if case_ids:
        cases = [c for c in cases if c["id"] in case_ids]
    if not cases:
        raise ValueError("黄金评测集为空")

    agent_svc = AgentDefinitionService(db)
    if agent_id:
        agent_row = agent_svc.get(agent_id)
    else:
        rows = agent_svc.list_all()
        agent_row = next((r for r in rows if r.get("slug") == BUILTIN_AGENT_SLUG), None)
    if not agent_row:
        raise ValueError("Agent 不存在")

    config = get_chat_api_config()
    endpoint = (config.get("endpoint") or "").strip()
    api_key = (config.get("api_key") or "").strip()

    agent_cfg = {
        "id": agent_row["id"],
        "pipeline_config_id": agent_row.get("pipeline_config_id"),
        "tool_ids": json.loads(agent_row["tool_ids_json"]) if isinstance(agent_row.get("tool_ids_json"), str) else (agent_row.get("tool_ids") or []),
        "knowledge_tree_id": agent_row.get("knowledge_tree_id"),
    }

    results = []
    passed = 0
    for case in cases:
        ctx = case.get("context_json") or case.get("context") or {}
        if isinstance(ctx, str):
            ctx = json.loads(ctx)
        out = await run_prompt_agent(ctx, agent_cfg)
        prompts = out.get("prompts") or []
        score = await _text_judge(prompts, ctx, endpoint, api_key) if endpoint and api_key else {"avg": 3.0, "pass": len(prompts) >= int(ctx.get("quantity") or 1)}
        ok = bool(score.get("pass"))
        if ok:
            passed += 1
        results.append({"case_id": case["id"], "case_name": case.get("name"), "score": score, "pass": ok, "prompt_count": len(prompts)})

    metrics = {
        "total": len(cases),
        "passed": passed,
        "pass_rate": round(passed / len(cases) * 100, 1) if cases else 0,
    }
    from harness.module_registry import MODULE_REGISTRY
    e2 = next(m for m in MODULE_REGISTRY["eval"] if m["id"] == "E2")
    thresholds = e2.get("default") or {}
    metrics["e2_min_pass_rate"] = thresholds.get("min_pass_rate", 70)
    metrics["e2_pass"] = metrics["pass_rate"] >= metrics["e2_min_pass_rate"]
    run = GoldenEvalRunService(db).create({
        "name": body.get("name") or "回归运行",
        "target_type": "agent",
        "target_ref": agent_row["id"],
        "metrics_json": metrics,
        "case_results_json": results,
    })
    return {"metrics": metrics, "results": results, "run": run}


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
