"""Agent 运行时 API（LangGraph，依赖数据层配置）。"""

import json
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agents.graphs.lookbook_prompt_graph import run_prompt_agent
from agents.prompt_agent import call_ark_chat, extract_responses_text
from config import get_chat_api_config
from data.services import AgentChatSessionService, AgentDefinitionService, AgentTestCaseService
from database import get_db
from services.golden.text_eval import run_golden_regression
from services.observability.run_ledger import agent_run, record_run
from services.seed_admin_data import BUILTIN_AGENT_SLUG

router = APIRouter(prefix="/api/agent-runtime", tags=["agent-runtime"])


def _agent_config_from_row(row: dict) -> dict:
    tool_ids = row.get("tool_ids_json") or row.get("tool_ids")
    if isinstance(tool_ids, str):
        try:
            tool_ids = json.loads(tool_ids)
        except json.JSONDecodeError:
            tool_ids = []
    return {
        "id": row["id"],
        "slug": row.get("slug"),
        "pipeline_config_id": row.get("pipeline_config_id"),
        "tool_ids": tool_ids or [],
        "knowledge_tree_id": row.get("knowledge_tree_id"),
        "role_prompt": row.get("role_prompt"),
    }


def _get_agent(db: Session, agent_id: str | None = None) -> dict:
    svc = AgentDefinitionService(db)
    if agent_id:
        row = svc.get(agent_id)
    else:
        rows = svc.list_all()
        row = next((r for r in rows if r.get("slug") == BUILTIN_AGENT_SLUG), rows[0] if rows else None)
    if not row:
        raise HTTPException(404, "Agent 不存在")
    return row


class InvokeBody(BaseModel):
    model_config = {"extra": "allow"}


@router.get("/agents/default")
def default_agent(db: Session = Depends(get_db)):
    return _get_agent(db)


@router.post("/agents/{agent_id}/invoke")
async def invoke_agent(agent_id: str, body: InvokeBody, db: Session = Depends(get_db)):
    row = _get_agent(db, agent_id)
    if row.get("status") != "published":
        raise HTTPException(400, "Agent 未发布")
    inputs = body.model_dump(exclude_none=True)
    session_id = inputs.pop("session_id", None) or inputs.pop("langfuse_session_id", None)
    result = await run_prompt_agent(
        inputs,
        _agent_config_from_row(row),
        session_id=session_id,
        user_id="admin-invoke",
        ref_type="agent_invoke",
        ref_id=agent_id,
    )
    return {
        "agent_id": agent_id,
        **result,
        "acceptance_criteria": inputs.get("acceptance_criteria"),
    }


@router.post("/agents/{agent_id}/test-cases/{case_id}/run")
async def run_test_case(agent_id: str, case_id: str, db: Session = Depends(get_db)):
    row = _get_agent(db, agent_id)
    case = AgentTestCaseService(db).get(case_id)
    if not case or case.get("agent_id") != agent_id:
        raise HTTPException(404, "TestCase 不存在")
    inputs = case.get("inputs_json") or case.get("inputs") or {}
    if isinstance(inputs, str):
        inputs = json.loads(inputs)
    result = await run_prompt_agent(
        inputs,
        _agent_config_from_row(row),
        ref_type="agent_testcase",
        ref_id=case_id,
    )
    return {"test_case": case, "result": result}


class ChatBody(BaseModel):
    message: str
    session_id: str | None = None


@router.post("/agents/{agent_id}/chat")
async def chat_agent(agent_id: str, body: ChatBody, db: Session = Depends(get_db)):
    row = _get_agent(db, agent_id)
    chat_svc = AgentChatSessionService(db)
    session = chat_svc.get(body.session_id) if body.session_id else None
    messages = []
    slots = {}
    if session:
        messages = session.get("messages_json") or session.get("messages") or []
        if isinstance(messages, str):
            messages = json.loads(messages)
        slots = session.get("slots_json") or session.get("slots") or {}
        if isinstance(slots, str):
            slots = json.loads(slots)

    chat_session_id = body.session_id or (session.get("id") if session else None)
    messages.append({"role": "user", "content": body.message})

    config = get_chat_api_config()
    endpoint = (config.get("endpoint") or "").strip()
    api_key = (config.get("api_key") or "").strip()
    if not endpoint or not api_key:
        raise HTTPException(400, "未配置对话模型")

    system = (row.get("role_prompt") or "") + (
        "\n你是 Lookbook 提示词 Agent 助手。帮助用户补全 model_id、clothing_ids、reference_id、"
        "size、quantity、business_context。回复简洁。若信息足够，在回复末尾输出 JSON 块 "
        '{"ready":true,"inputs":{...}}。'
    )
    llm_messages = [{"role": "system", "content": system}, *messages[-12:]]

    started = time.perf_counter()
    with agent_run(
        "chat",
        session_id=chat_session_id,
        user_id="admin-chat",
        agent_id=agent_id,
        ref_type="chat_session",
        ref_id=chat_session_id,
        input={"message": body.message},
    ) as run_ctx:
        body, err = await call_ark_chat(api_key, endpoint, llm_messages, max_tokens=1024, temperature=0.5)
        if not body:
            run_ctx["error"] = err or "对话失败"
            raise HTTPException(400, err or "对话失败")
        reply = extract_responses_text(body)
        run_ctx["output"] = {"reply": reply}
        run_ctx["steps"] = [{"step": "chat_reply", "model": endpoint[:32]}]

    messages.append({"role": "assistant", "content": reply})

    ready_inputs = None
    if '"ready"' in reply and "inputs" in reply:
        try:
            chunk = reply[reply.rfind("{") : reply.rfind("}") + 1]
            data = json.loads(chunk)
            if data.get("ready"):
                ready_inputs = data.get("inputs")
                slots = {**slots, **(ready_inputs or {})}
        except json.JSONDecodeError:
            pass

    run_id = run_ctx["run_id"]

    if body.session_id and session:
        chat_svc.update(body.session_id, {
            "messages_json": messages,
            "slots_json": slots,
            "last_run_id": run_id,
        })
        sid = body.session_id
    else:
        created = chat_svc.create({
            "agent_id": agent_id,
            "title": body.message[:40],
            "messages_json": messages,
            "slots_json": slots,
            "last_run_id": run_id,
        })
        sid = created["id"]

    invoke_result = None
    if ready_inputs and ready_inputs.get("model_id"):
        invoke_result = await run_prompt_agent(
            ready_inputs,
            _agent_config_from_row(row),
            session_id=sid,
            user_id="admin-chat",
            ref_type="chat_session",
            ref_id=sid,
        )

    return {
        "session_id": sid,
        "reply": reply,
        "slots": slots,
        "invoke_result": invoke_result,
        "run_id": run_id,
    }


@router.post("/golden/regression")
async def golden_regression(body: dict, db: Session = Depends(get_db)):
    started = time.perf_counter()
    try:
        result = await run_golden_regression(db, body)
        record_run(
            run_type="golden_regression",
            status="success",
            user_id="admin",
            ref_type="golden_regression",
            input=body,
            output=result,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        return result
    except ValueError as e:
        record_run(
            run_type="golden_regression",
            status="failed",
            user_id="admin",
            input=body,
            error_message=str(e),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        raise HTTPException(400, str(e)) from e
