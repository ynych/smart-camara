"""用户域 U1–U5 中间态检查（TDD）。"""

from domains.checks.registry import run_suite
from domains.checks.user_journey import (
    check_u1_materials,
    check_u2_selection,
    check_u3_prompts,
    check_u4_generation,
    check_u5_evaluation,
)


def test_u1_passes_with_models_and_clothing():
    r = check_u1_materials({"materials_grouped": {"models": [1], "clothing_sets": [1]}})
    assert r.passed
    assert r.id == "U1_materials"


def test_u1_fails_when_empty():
    r = check_u1_materials({"materials_grouped": {}})
    assert not r.passed


def test_u3_requires_llm_source(user_ctx_minimal):
    r = check_u3_prompts(user_ctx_minimal)
    assert r.passed

    bad = {**user_ctx_minimal, "prompt_result": {"prompt_source": "harness", "prompts": []}}
    assert not check_u3_prompts(bad).passed


def test_user_journey_suite_ok(user_ctx_minimal):
    out = run_suite("user_journey", user_ctx_minimal)
    assert out["ok"]
    assert out["passed"] == 5


def test_u2_requires_clothing():
    assert not check_u2_selection({"selection": {"model_id": "m"}}).passed
    assert check_u2_selection({"selection": {"model_id": "m", "clothing_ids": ["c"]}}).passed


def test_u4_requires_images():
    assert not check_u4_generation({}).passed
    assert check_u4_generation({"generation_result": {"task_id": "t", "images": [{}]}}).passed


def test_u5_accepts_scores_without_overall():
    r = check_u5_evaluation({"evaluation": {"scores": {"质量": 4}}})
    assert r.passed
