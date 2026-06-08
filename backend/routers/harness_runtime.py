"""Harness TestCase 运行与模块 API 扩展。"""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from agents.graphs.lookbook_prompt_graph import run_prompt_agent
from data.services import AgentDefinitionService, HarnessTestCaseService
from database import get_db
from harness.module_registry import MODULE_REGISTRY, SELECTED_MODULE_IDS, get_selected_modules
from services.harness_testcase_runner import run_testcase_evaluation
from services.promptfoo_export import export_promptfoo_yaml, write_promptfoo_tests
from services.seed_admin_data import BUILTIN_AGENT_SLUG

router = APIRouter(prefix="/api/agent-runtime", tags=["agent-runtime-ext"])


def _agent_config_from_row(row: dict) -> dict:
    tool_ids = row.get("tool_ids_json") or row.get("tool_ids")
    if isinstance(tool_ids, str):
        tool_ids = json.loads(tool_ids)
    return {
        "id": row["id"],
        "slug": row.get("slug"),
        "pipeline_config_id": row.get("pipeline_config_id"),
        "tool_ids": tool_ids or [],
        "knowledge_tree_id": row.get("knowledge_tree_id"),
    }


@router.get("/modules")
def list_optimization_modules():
    return {
        "selected_ids": SELECTED_MODULE_IDS,
        "modules": get_selected_modules(),
        "registry": MODULE_REGISTRY,
    }


@router.post("/harness-testcases/{case_id}/run-prompts")
async def run_harness_testcase_prompts(case_id: str, db: Session = Depends(get_db)):
    svc = HarnessTestCaseService(db)
    case = svc.get(case_id)
    if not case:
        raise HTTPException(404, "TestCase 不存在")

    agent_row = None
    if case.get("agent_id"):
        agent_row = AgentDefinitionService(db).get(case["agent_id"])
    if not agent_row:
        rows = AgentDefinitionService(db).list_all()
        agent_row = next((r for r in rows if r.get("slug") == BUILTIN_AGENT_SLUG), None)
    if not agent_row:
        raise HTTPException(404, "Agent 不存在")

    clothing_ids = case.get("clothing_ids_json") or case.get("clothing_ids") or []
    if isinstance(clothing_ids, str):
        clothing_ids = json.loads(clothing_ids)
    business_context = case.get("business_context_json") or case.get("business_context") or {}
    if isinstance(business_context, str):
        business_context = json.loads(business_context)

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
        _agent_config_from_row(agent_row),
        session_id=f"harness-tc-{case_id}",
        user_id="harness",
        ref_type="harness_testcase",
        ref_id=case_id,
    )

    svc.update(case_id, {
        "prompts_json": result.get("prompts"),
        "last_run_id": result.get("run_id"),
        "run_meta_json": {
            "source": result.get("source"),
            "llm_error": result.get("llm_error"),
            "trace": result.get("trace"),
            "run_id": result.get("run_id"),
        },
        "module_snapshot_json": result.get("module_snapshot"),
        "status": "ready" if result.get("prompts") else "draft",
    })

    return {"case_id": case_id, "result": result, "run_id": result.get("run_id")}


@router.post("/harness-testcases/{case_id}/run-images")
async def run_harness_testcase_images(case_id: str, db: Session = Depends(get_db)):
    raise HTTPException(
        410,
        "Harness TestCase 联调生图已下线。请在用户平台 /studio 使用 Seedream 生图，"
        "并通过 Gallery 评价导入 TestCase。",
    )


@router.post("/harness-testcases/{case_id}/run-evaluation")
async def run_harness_testcase_evaluation(case_id: str, db: Session = Depends(get_db)):
    try:
        return await run_testcase_evaluation(db, case_id)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(500, str(e)) from e


@router.get("/promptfoo/tests.yaml", response_class=PlainTextResponse)
def promptfoo_tests_yaml(db: Session = Depends(get_db)):
    try:
        return export_promptfoo_yaml(db)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/promptfoo/sync")
def promptfoo_sync(db: Session = Depends(get_db)):
    try:
        return write_promptfoo_tests(db, active=True)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
