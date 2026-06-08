"""健康检查与域中间态检查 API。"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from domains.agent.pipeline_version import get_version_pair
from domains.checks.registry import run_suite, run_step_check
from services.seed_admin_data import BUILTIN_PIPELINE_SLUG

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health():
    return {"status": "healthy"}


@router.post("/domain-checks")
async def domain_checks(body: dict[str, Any] | None = None, db: Session = Depends(get_db)):
    """
    运行域中间态检查。
    body: { "suite": "user_journey|agent_flywheel|evolution_gates|full", "context": {...} }
    """
    body = body or {}
    suite = body.get("suite") or "full"
    ctx = dict(body.get("context") or {})

    if body.get("include_pipeline_pair"):
        ctx["pipeline_pair"] = get_version_pair(db, body.get("pipeline_slug") or BUILTIN_PIPELINE_SLUG)

    try:
        return run_suite(suite, ctx)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/domain-checks/{step_id}")
async def domain_check_step(step_id: str, db: Session = Depends(get_db)):
    """单步检查，如 U3_prompts、A2_run、GATE_signal。"""
    ctx: dict[str, Any] = {}
    try:
        result = run_step_check(step_id, ctx)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
