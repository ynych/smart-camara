"""Harness 调试与评价 API。"""

import json

from fastapi import APIRouter, HTTPException

from harness.engine import get_pipeline_config, run_module, run_pipeline
from harness.tools import list_tools, run_tool
from services.evaluation_service import generate_ai_draft, get_evaluation, save_evaluation
from services.harness_service import build_context_from_image
from services.regen_service import optimize_prompt_for_image, regenerate_image

router = APIRouter(prefix="/api/harness", tags=["harness"])


@router.get("/tools")
def get_tools():
    return {"tools": list_tools()}


@router.post("/tools/{tool_id}/run")
def debug_tool(tool_id: str, data: dict):
    try:
        return run_tool(tool_id, data.get("context") or data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pipeline")
def get_pipeline(pipeline_id: str = "lookbook_v1"):
    try:
        return get_pipeline_config(pipeline_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/pipeline/run")
def debug_pipeline(data: dict):
    try:
        ctx_data = data.get("context") or {}
        from harness.context import HarnessContext

        ctx = HarnessContext.from_dict(ctx_data)
        enabled = data.get("enabled_modules")
        include_regen = bool(data.get("include_regen"))
        return run_pipeline(ctx, enabled_modules=enabled, include_regen=include_regen)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pipeline/module/{module_id}/run")
def debug_module(module_id: str, data: dict):
    try:
        from harness.context import HarnessContext

        ctx = HarnessContext.from_dict(data.get("context") or {})
        return run_module(module_id, ctx)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/context/{image_id}")
def get_image_context(image_id: str):
    try:
        ctx = build_context_from_image(image_id)
        return {"context": ctx.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


eval_router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])


@eval_router.get("/{image_id}")
def read_evaluation(image_id: str):
    ev = get_evaluation(image_id)
    return {"evaluation": ev}


@eval_router.post("/{image_id}")
def write_evaluation(image_id: str, data: dict):
    try:
        return save_evaluation(image_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@eval_router.post("/{image_id}/ai-draft")
async def ai_draft_evaluation(image_id: str):
    try:
        return await generate_ai_draft(image_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


image_router = APIRouter(prefix="/api/images", tags=["images"])


@image_router.post("/{image_id}/optimize-prompt")
async def optimize_prompt(image_id: str, data: dict = None):
    data = data or {}
    try:
        return await optimize_prompt_for_image(
            image_id,
            confirmed_prompt=data.get("confirmed_prompt"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@image_router.post("/{image_id}/regenerate")
async def regen_image(image_id: str, data: dict):
    prompt = (data or {}).get("prompt", "")
    try:
        return await regenerate_image(image_id, prompt)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
