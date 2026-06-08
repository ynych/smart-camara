"""LangGraph：Lookbook 提示词 Agent 运行时。"""

import json
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from agents.prompt_agent import PromptAgent
from data.services import PipelineConfigService
from harness.context import HarnessContext
from harness.defaults import PIPELINE_LOOKBOOK_V1
from harness.engine import run_pipeline
from harness.tools import run_tool
from services.knowledge.pageindex_retriever import retrieve_knowledge_snippets


class PromptAgentState(TypedDict, total=False):
    inputs: dict
    agent_config: dict
    tool_outputs: dict
    knowledge_snippets: list
    pipeline_result: dict
    prompts: list
    source: str
    llm_error: str | None
    trace: list


def _load_pipeline(pipeline_config_id: str | None, db=None) -> dict:
    if pipeline_config_id and db:
        from database import SessionLocal

        session = db if db else SessionLocal()
        own_session = db is None
        try:
            row = PipelineConfigService(session).get(pipeline_config_id)
            if row and row.get("modules_json"):
                modules = json.loads(row["modules_json"]) if isinstance(row["modules_json"], str) else row["modules_json"]
                order = row.get("module_order_json") or row.get("module_order")
                if isinstance(order, str):
                    order = json.loads(order)
                return {
                    "id": row.get("slug") or "db_pipeline",
                    "name": row.get("name"),
                    "module_order": order or list(modules.keys()),
                    "modules": modules,
                }
        finally:
            if own_session:
                session.close()
    return PIPELINE_LOOKBOOK_V1


async def node_parse_input(state: PromptAgentState) -> PromptAgentState:
    inputs = state.get("inputs") or {}
    trace = list(state.get("trace") or [])
    trace.append({"step": "parse_input", "ok": bool(inputs.get("model_id"))})
    return {**state, "trace": trace}


async def node_run_tools(state: PromptAgentState) -> PromptAgentState:
    inputs = state.get("inputs") or {}
    agent = state.get("agent_config") or {}
    tool_outputs = {}
    trace = list(state.get("trace") or [])
    tool_slugs = agent.get("tool_ids") or []
    ctx = {**inputs}

    from database import SessionLocal
    from data.services import ToolDefinitionService

    db = SessionLocal()
    try:
        tool_svc = ToolDefinitionService(db)
        for tid in tool_slugs:
            tdef = tool_svc.get(tid)
            if not tdef:
                continue
            handler_key = tdef.get("handler_key")
            if not handler_key:
                continue
            try:
                out = run_tool(handler_key, ctx)
                tool_outputs[handler_key] = out.get("output") or {}
                ctx.update(out.get("output") or {})
                trace.append({"step": f"tool:{handler_key}", "ok": True})
            except Exception as e:
                trace.append({"step": f"tool:{handler_key}", "ok": False, "error": str(e)})
    finally:
        db.close()

    return {**state, "tool_outputs": tool_outputs, "trace": trace}


async def node_retrieve_knowledge(state: PromptAgentState) -> PromptAgentState:
    agent = state.get("agent_config") or {}
    inputs = state.get("inputs") or {}
    tree_id = agent.get("knowledge_tree_id")
    trace = list(state.get("trace") or [])
    snippets = []
    if tree_id:
        query_parts = [
            inputs.get("business_context", {}).get("merchant_need", ""),
            inputs.get("business_context", {}).get("target_audience", ""),
            inputs.get("acceptance_criteria", ""),
        ]
        query = " ".join(p for p in query_parts if p) or "Lookbook 生图规范"
        snippets = await retrieve_knowledge_snippets(tree_id, query)
        trace.append({"step": "retrieve_knowledge", "nodes": len(snippets)})
    else:
        trace.append({"step": "retrieve_knowledge", "skipped": True})
    return {**state, "knowledge_snippets": snippets, "trace": trace}


async def node_assemble_pipeline(state: PromptAgentState) -> PromptAgentState:
    inputs = state.get("inputs") or {}
    agent = state.get("agent_config") or {}
    trace = list(state.get("trace") or [])

    hctx = HarnessContext.from_dict({
        **inputs,
        **(state.get("tool_outputs") or {}),
        "goal_text": (inputs.get("business_context") or {}).get("merchant_need") or "电商 Lookbook 展示",
        "constraint_text": inputs.get("acceptance_criteria") or "",
    })
    if state.get("knowledge_snippets"):
        extra = "\n".join(s["content"] for s in state["knowledge_snippets"] if s.get("content"))
        if extra:
            hctx.constraint_text = (hctx.constraint_text + "\n知识检索：" + extra).strip()

    from database import SessionLocal

    db = SessionLocal()
    try:
        pipeline = _load_pipeline(agent.get("pipeline_config_id"), db)
        result = run_pipeline(hctx, pipeline=pipeline, include_regen=False)
    finally:
        db.close()

    trace.append({"step": "assemble_pipeline", "modules": len(result.get("modules") or [])})
    return {**state, "pipeline_result": result, "trace": trace}


async def node_llm_generate(state: PromptAgentState) -> PromptAgentState:
    inputs = state.get("inputs") or {}
    trace = list(state.get("trace") or [])
    quantity = int(inputs.get("quantity") or 4)
    size = inputs.get("size") or "3:4"
    business_context = inputs.get("business_context") or {}
    acceptance = inputs.get("acceptance_criteria") or ""

    tool_out = state.get("tool_outputs") or {}
    model_desc = tool_out.get("describe_material", {}).get("model_desc") or inputs.get("model_desc") or "模特"
    clothing_desc = tool_out.get("describe_clothing", {}).get("clothing_desc") or inputs.get("clothing_desc") or "服装"
    scene_bundle = tool_out.get("extract_reference_style") or {}
    scene_desc = scene_bundle.get("scene_desc") or inputs.get("scene_desc") or "场景"
    style_hint = scene_bundle.get("style_hint") or inputs.get("style_hint") or ""

    from skills.lookbook_skill import LookbookSkill

    skill = LookbookSkill()
    angle_templates = skill._get_angle_templates(quantity)

    agent = PromptAgent()
    llm_prompts, llm_error = await agent.generate_prompts(
        model_desc=model_desc,
        clothing_desc=clothing_desc,
        scene_desc=scene_desc,
        style_hint=style_hint,
        size=size,
        quantity=quantity,
        angle_templates=angle_templates,
        business_context=business_context,
        acceptance_criteria=acceptance,
    )

    if llm_prompts:
        for p in llm_prompts:
            p["prompt_modules"] = state.get("pipeline_result", {}).get("modules")
            p["source"] = "llm"
        trace.append({"step": "llm_generate", "source": "llm", "count": len(llm_prompts)})
        return {
            **state,
            "prompts": llm_prompts,
            "source": "llm",
            "llm_error": None,
            "trace": trace,
        }

    # fallback harness per angle
    pipeline = state.get("pipeline_result") or {}
    base_prompt = pipeline.get("prompt") or ""
    prompts = []
    for i, template in enumerate(angle_templates[:quantity]):
        prompts.append({
            "index": i,
            "angle_name": template["name"],
            "angle_desc": template["desc"],
            "prompt": base_prompt,
            "editable": True,
            "source": "harness",
            "prompt_modules": pipeline.get("modules"),
        })
    trace.append({"step": "llm_generate", "source": "harness", "llm_error": llm_error})
    return {
        **state,
        "prompts": prompts,
        "source": "harness",
        "llm_error": llm_error,
        "trace": trace,
    }


async def node_format_output(state: PromptAgentState) -> PromptAgentState:
    return state


def build_lookbook_prompt_graph():
    g = StateGraph(PromptAgentState)
    g.add_node("parse_input", node_parse_input)
    g.add_node("run_tools", node_run_tools)
    g.add_node("retrieve_knowledge", node_retrieve_knowledge)
    g.add_node("assemble_pipeline", node_assemble_pipeline)
    g.add_node("llm_generate", node_llm_generate)
    g.add_node("format_output", node_format_output)

    g.set_entry_point("parse_input")
    g.add_edge("parse_input", "run_tools")
    g.add_edge("run_tools", "retrieve_knowledge")
    g.add_edge("retrieve_knowledge", "assemble_pipeline")
    g.add_edge("assemble_pipeline", "llm_generate")
    g.add_edge("llm_generate", "format_output")
    g.add_edge("format_output", END)
    return g.compile()


_graph = None


def get_lookbook_prompt_graph():
    global _graph
    if _graph is None:
        _graph = build_lookbook_prompt_graph()
    return _graph


async def run_prompt_agent(
    inputs: dict,
    agent_config: dict,
    *,
    session_id: str | None = None,
    user_id: str = "workbench",
    ref_type: str | None = None,
    ref_id: str | None = None,
) -> dict[str, Any]:
    from harness.module_registry import get_selected_modules
    from services.observability.run_ledger import agent_run

    graph = get_lookbook_prompt_graph()
    modules = get_selected_modules()
    with agent_run(
        "generate_prompt",
        session_id=session_id,
        user_id=user_id,
        agent_id=agent_config.get("id"),
        ref_type=ref_type,
        ref_id=ref_id,
        input=inputs,
        metadata={"slug": agent_config.get("slug"), "module_snapshot": modules},
    ) as run_ctx:
        result = await graph.ainvoke({
            "inputs": inputs,
            "agent_config": agent_config,
            "trace": [],
        })
        out = {
            "prompts": result.get("prompts") or [],
            "source": result.get("source"),
            "llm_error": result.get("llm_error"),
            "trace": result.get("trace") or [],
            "knowledge_snippets": result.get("knowledge_snippets") or [],
            "pipeline_result": result.get("pipeline_result"),
            "run_id": run_ctx["run_id"],
            "session_id": run_ctx["session_id"],
            "agent_slug": agent_config.get("slug"),
            "module_snapshot": modules,
        }
        run_ctx["steps"] = out["trace"]
        run_ctx["output"] = out
        run_ctx["module_snapshot"] = modules
        return out
