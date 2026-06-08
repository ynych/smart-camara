"""进化三道门 + 发布建议（TDD）。"""

from domains.agent.recommendation import recommend_publish
from domains.checks.evolution_gates import (
    check_gate_approval,
    check_gate_granularity,
    check_gate_signal,
)
from domains.checks.registry import run_suite


def test_recommend_approve_when_draft_better():
    pub = {"case_count": 2, "pass_rate": 70, "avg_score": 3.5}
    drf = {"case_count": 2, "pass_rate": 85, "avg_score": 4.0}
    assert recommend_publish(pub, drf, {}) == "approve"


def test_recommend_reject_when_draft_much_worse():
    pub = {"case_count": 2, "pass_rate": 80, "avg_score": 4.0}
    drf = {"case_count": 2, "pass_rate": 60, "avg_score": 3.0}
    assert recommend_publish(pub, drf, {}) == "reject"


def test_recommend_hold_when_low_human_good_rate():
    pub = {"case_count": 2, "pass_rate": 70, "avg_score": 3.5}
    drf = {"case_count": 2, "pass_rate": 80, "avg_score": 4.0}
    human = {"case_count": 3, "good_rate": 30}
    assert recommend_publish(pub, drf, human) == "hold"


def test_gate_signal_with_human(agent_ctx_minimal):
    r = check_gate_signal(agent_ctx_minimal)
    assert r.passed


def test_gate_granularity_rejects_unknown_module():
    r = check_gate_granularity({"module_patches": {"role": {"template": "x"}}})
    assert r.passed
    bad = check_gate_granularity({"module_patches": {"whole_prompt_blackbox": "x"}})
    assert not bad.passed


def test_gate_approval_blocks_draft_leak(agent_ctx_minimal):
    assert check_gate_approval(agent_ctx_minimal).passed
    leaked = {**agent_ctx_minimal, "user_consumed_pipeline_id": "drf-1"}
    assert not check_gate_approval(leaked).passed


def test_evolution_gates_suite(agent_ctx_minimal):
    ctx = {**agent_ctx_minimal, "module_patches": {"subject": {"template": "新模板"}}}
    out = run_suite("evolution_gates", ctx)
    assert out["by_domain"]["gate"]["passed"] == 3
