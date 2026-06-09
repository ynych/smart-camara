"""Workflow schema 校验单元测试。"""

import pytest

from domains.workflow.schema import validate_workflow_input, validate_workflow_output, WorkflowValidationError


def test_validate_input_ok():
    out = validate_workflow_input({
        "model_id": "m1",
        "clothing_ids": ["c1"],
        "quantity": 4,
        "size": "3:4",
    })
    assert out["quantity"] == 4


def test_validate_input_rejects_bad_quantity():
    with pytest.raises(WorkflowValidationError):
        validate_workflow_input({"model_id": "m", "clothing_ids": ["c"], "quantity": 99})


def test_validate_output_count():
    validate_workflow_output([{"prompt": "a"}, {"prompt": "b"}], 2)


def test_validate_output_rejects_empty_prompt():
    with pytest.raises(WorkflowValidationError):
        validate_workflow_output([{"prompt": ""}], 1)
