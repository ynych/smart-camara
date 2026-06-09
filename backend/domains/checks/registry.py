"""域检查注册表 — 按场景运行检查套件。"""

from __future__ import annotations

from typing import Any

from domains.checks.agent_flywheel import AGENT_FLYWHEEL_CHECKS
from domains.checks.base import CheckResult, run_checks, summarize
from domains.checks.evolution_gates import EVOLUTION_GATE_CHECKS
from domains.checks.pack_workflow import PACK_WORKFLOW_CHECKS
from domains.checks.user_journey import USER_JOURNEY_CHECKS

SUITES = {
    "user_journey": USER_JOURNEY_CHECKS,
    "agent_flywheel": AGENT_FLYWHEEL_CHECKS,
    "evolution_gates": EVOLUTION_GATE_CHECKS,
    "pack_workflow": PACK_WORKFLOW_CHECKS,
    "full": USER_JOURNEY_CHECKS + AGENT_FLYWHEEL_CHECKS + EVOLUTION_GATE_CHECKS + PACK_WORKFLOW_CHECKS,
}


def run_suite(name: str, ctx: dict[str, Any]) -> dict[str, Any]:
    checks = SUITES.get(name)
    if not checks:
        raise ValueError(f"未知检查套件: {name}，可选 {list(SUITES)}")
    results = run_checks(checks, ctx)
    out = summarize(results)
    out["suite"] = name
    return out


def run_step_check(step_id: str, ctx: dict[str, Any]) -> CheckResult:
    mapping = {fn(ctx).id: fn for fn in SUITES["full"]}
    # rebuild by stable id
    for suite in SUITES.values():
        for fn in suite:
            r = fn(ctx)
            if r.id == step_id:
                return r
    raise ValueError(f"未知步骤检查: {step_id}")
