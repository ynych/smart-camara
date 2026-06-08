"""Harness 引擎单元测试（TDD）。"""

from harness.context import HarnessContext
from harness.engine import run_module, run_pipeline
from harness.defaults import PIPELINE_LOOKBOOK_V1


def test_run_module_role():
    ctx = HarnessContext(model_desc="测试模特", clothing_desc="连衣裙")
    out = run_module("role", ctx)
    assert "测试模特" in out["text"]
    assert out["module_id"] == "role"


def test_run_pipeline_assembles_prompt():
    ctx = HarnessContext(
        model_desc="模特A",
        clothing_desc="服装B",
        scene_desc="棚拍",
        size="3:4",
        goal_text="电商展示",
        constraint_text="颜色准确",
    )
    result = run_pipeline(ctx, include_regen=False)
    assert result["prompt"]
    assert len(result["modules"]) >= 5
    assert result["pipeline_id"] == PIPELINE_LOOKBOOK_V1["id"]


def test_regen_skipped_without_feedback():
    ctx = HarnessContext(model_desc="模特")
    result = run_pipeline(ctx, include_regen=True)
    module_ids = [m["module_id"] for m in result["modules"]]
    assert "regen" not in module_ids
