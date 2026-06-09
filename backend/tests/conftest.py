"""Pytest 公共 fixtures。"""

import os
import sys

import pytest

# 确保 backend 为 import 根
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)


@pytest.fixture
def user_ctx_minimal():
    return {
        "materials_grouped": {"models": [{"id": "m1"}], "clothing_sets": [{"name": "套装"}]},
        "selection": {"model_id": "m1", "clothing_ids": ["c1"]},
        "quantity": 2,
        "prompt_result": {
            "prompt_run_id": "run-1",
            "prompts": [{"prompt": "a"}, {"prompt": "b"}],
        },
        "generation_result": {"task_id": "t1", "images": [{"id": "i1"}]},
        "evaluation": {"overall": "good", "scores": {"构图": 5}},
    }


@pytest.fixture
def agent_ctx_minimal():
    return {
        "testcase": {
            "model_id": "m1",
            "acceptance_criteria": "服装颜色准确",
            "last_run_id": "run-1",
            "prompts_json": [{"prompt": "x"}],
            "run_meta_json": {"source": "llm", "run_id": "run-1"},
            "evaluation_json": {
                "text_judge": {"pass": True, "avg": 4.0},
                "human_eval": {"overall": "good"},
                "pass": True,
            },
        },
        "pipeline_pair": {
            "published": {"id": "pub-1", "status": "published", "version": 1},
            "draft": {"id": "drf-1", "status": "draft", "slug": "lookbook_v1_draft"},
        },
        "compare_result": {
            "published": {"text": {"case_count": 2, "pass_rate": 80, "avg_score": 4.0}},
            "draft": {"text": {"case_count": 2, "pass_rate": 90, "avg_score": 4.2}},
            "recommendation": "approve",
        },
        "user_consumed_pipeline_id": "pub-1",
    }
