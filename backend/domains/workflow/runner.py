"""Production Workflow Runner — U3 dry-run / 内部步骤编排。"""

from __future__ import annotations

import json
from typing import Any

from database import SessionLocal
from data.services import AgentDefinitionService
from domains.workflow.defaults import LOOKBOOK_PROD_V1
from domains.workflow.manifest import ensure_manifest, get_manifest
from domains.workflow.pack_merge import format_acceptance_from_pack, pack_to_overlay
from domains.workflow.pack_routing import select_pack
from domains.workflow.pack_service import list_published_packs
from domains.workflow.records import create_prompt_run_record
from domains.workflow.schema import validate_workflow_input, validate_workflow_output
from services.seed_admin_data import BUILTIN_AGENT_SLUG


async def run_workflow_preview(
    data: dict[str, Any],
    *,
    source: str = "user_preview",
    session_id: str | None = None,
    user_id: str = "workbench",
    include_user_trace: bool = False,
    studio_task_id: str | None = None,
) -> dict[str, Any]:
    """步骤 ①–⑤：校验 → 选包 → LangGraph → 校验输出 → 落 prompt_run_record。"""
    from agents.graphs.lookbook_prompt_graph import run_prompt_agent
    from skills.lookbook_skill import LookbookSkill

    skill = LookbookSkill()
    validated = validate_workflow_input(data)
    workflow_version = data.get("workflow_version") or LOOKBOOK_PROD_V1["workflow_id"]

    db = SessionLocal()
    try:
        manifest = get_manifest(db) or ensure_manifest(db)
        packs = list_published_packs(db)
        pack = select_pack(
            packs,
            business_context=validated.get("business_context") or {},
            default_pack_id=manifest.get("default_pack_id"),
            pack_version_pin=manifest.get("pack_version_pin_json") or {},
        )
        overlay = pack_to_overlay(pack) if pack else {}
        techniques = overlay.get("techniques") or {}

        criteria = validated.get("acceptance_criteria") or skill.build_acceptance_criteria(
            size=validated["size"],
            quantity=validated["quantity"],
            business_context=validated.get("business_context") or {},
        )
        criteria = format_acceptance_from_pack(
            techniques,
            size=validated["size"],
            quantity=validated["quantity"],
            constraint_text=criteria,
            base=criteria,
        )

        agent_svc = AgentDefinitionService(db)
        rows = agent_svc.list_all()
        agent_row = next((r for r in rows if r.get("slug") == BUILTIN_AGENT_SLUG), rows[0] if rows else None)
        if not agent_row:
            prompts, prompt_source, llm_error = await skill.build_prompts_async(
                validated["model_id"],
                validated["clothing_ids"],
                validated.get("reference_id"),
                validated["quantity"],
                size=validated["size"],
                scene_id=validated.get("scene_id"),
                business_context=validated.get("business_context") or {},
                acceptance_criteria=criteria,
            )
            if prompts:
                validate_workflow_output(
                    prompts if isinstance(prompts[0], dict) else [{"prompt": p} for p in prompts],
                    validated["quantity"],
                )
            record = create_prompt_run_record(
                db,
                pack_id=overlay.get("pack_id"),
                pack_version=overlay.get("pack_version"),
                inputs=validated,
                prompts=prompts,
                acceptance_criteria=criteria,
                source=source,
                workflow_version=workflow_version,
                studio_task_id=studio_task_id,
            )
            db.commit()
            out = {
                "prompts": prompts,
                "acceptance_criteria": criteria,
                "prompt_source": prompt_source,
                "prompt_run_id": record["id"],
                "pack_id": overlay.get("pack_id"),
                "pack_version": overlay.get("pack_version"),
                "workflow_version": workflow_version,
                "llm_error": llm_error,
            }
            if not include_user_trace:
                out.pop("llm_error", None)
            return out

        tool_ids = agent_row.get("tool_ids_json")
        if isinstance(tool_ids, str):
            tool_ids = json.loads(tool_ids)
        agent_config = {
            "id": agent_row.get("id"),
            "slug": agent_row.get("slug"),
            "pipeline_config_id": agent_row.get("pipeline_config_id"),
            "tool_ids": tool_ids or [],
            "knowledge_tree_id": agent_row.get("knowledge_tree_id"),
        }
        inputs = {
            **validated,
            "acceptance_criteria": criteria,
            "pack_overlay": overlay,
        }
        result = await run_prompt_agent(
            inputs,
            agent_config,
            session_id=session_id or data.get("session_id"),
            user_id=user_id,
            ref_type=source,
        )
        prompts = result.get("prompts") or []
        validate_workflow_output(prompts, validated["quantity"])

        record = create_prompt_run_record(
            db,
            pack_id=overlay.get("pack_id"),
            pack_version=overlay.get("pack_version"),
            inputs=validated,
            prompts=prompts,
            acceptance_criteria=criteria,
            source=source,
            workflow_version=workflow_version,
            agent_run_id=result.get("run_id"),
            studio_task_id=studio_task_id,
        )
        db.commit()

        out = {
            "prompts": prompts,
            "acceptance_criteria": criteria,
            "prompt_source": result.get("source"),
            "prompt_run_id": record["id"],
            "pack_id": overlay.get("pack_id"),
            "pack_version": overlay.get("pack_version"),
            "workflow_version": workflow_version,
            "agent_slug": agent_row.get("slug"),
            "agent_id": agent_row.get("id"),
            "run_id": result.get("run_id"),
        }
        if include_user_trace:
            out["llm_error"] = result.get("llm_error")
            out["trace"] = result.get("trace")
            out["session_id"] = result.get("session_id")
        return out
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
