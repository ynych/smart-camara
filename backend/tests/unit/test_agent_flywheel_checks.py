"""Agent 域飞轮 A1–A6 中间态检查（TDD）。"""

from domains.checks.agent_flywheel import check_a2_run, check_a4_propose, check_a6_publish
from domains.checks.registry import run_suite


def test_a2_run_passes(agent_ctx_minimal):
    r = check_a2_run(agent_ctx_minimal)
    assert r.passed
    assert r.details["source"] == "llm"


def test_a4_requires_draft(agent_ctx_minimal):
    assert check_a4_propose(agent_ctx_minimal).passed
    no_draft = {**agent_ctx_minimal, "pipeline_pair": {"published": {}, "draft": None}}
    assert not check_a4_propose(no_draft).passed


def test_a6_user_must_not_consume_draft(agent_ctx_minimal):
    assert check_a6_publish(agent_ctx_minimal).passed
    leaked = {
        **agent_ctx_minimal,
        "user_consumed_pipeline_id": "drf-1",
    }
    assert not check_gate_approval_leaked(leaked).passed


def check_gate_approval_leaked(ctx):
    from domains.checks.evolution_gates import check_gate_approval
    return check_gate_approval(ctx)


def test_agent_flywheel_suite(agent_ctx_minimal):
    out = run_suite("agent_flywheel", agent_ctx_minimal)
    assert out["passed"] >= 5
    assert out["by_domain"]["agent"]["passed"] >= 5
