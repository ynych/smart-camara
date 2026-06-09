"""Workflow I/O schema 校验（W1）。"""

from __future__ import annotations

from typing import Any

VALID_SIZES = {"1:1", "3:4", "4:3", "16:9", "9:16"}
MAX_QUANTITY = 8
MAX_PROMPT_LEN = 4000


class WorkflowValidationError(ValueError):
    pass


def validate_workflow_input(data: dict[str, Any]) -> dict[str, Any]:
    model_id = (data.get("model_id") or "").strip()
    if not model_id:
        raise WorkflowValidationError("缺少 model_id")
    clothing_ids = data.get("clothing_ids") or []
    if not clothing_ids:
        raise WorkflowValidationError("缺少 clothing_ids")
    quantity = int(data.get("quantity") or 4)
    if quantity < 1 or quantity > MAX_QUANTITY:
        raise WorkflowValidationError(f"quantity 须在 1–{MAX_QUANTITY}")
    size = data.get("size") or "3:4"
    if size not in VALID_SIZES:
        raise WorkflowValidationError(f"不支持的 size: {size}")
    return {
        **data,
        "model_id": model_id,
        "clothing_ids": list(clothing_ids),
        "quantity": quantity,
        "size": size,
        "business_context": data.get("business_context") or {},
        "acceptance_criteria": data.get("acceptance_criteria") or "",
    }


def validate_workflow_output(prompts: list[Any], quantity: int) -> None:
    if len(prompts) < quantity:
        raise WorkflowValidationError(f"prompts 条数不足: {len(prompts)} < {quantity}")
    for i, p in enumerate(prompts[:quantity]):
        text = p.get("prompt") if isinstance(p, dict) else str(p)
        if not (text or "").strip():
            raise WorkflowValidationError(f"第 {i + 1} 条 prompt 为空")
        if len(text) > MAX_PROMPT_LEN:
            raise WorkflowValidationError(f"第 {i + 1} 条 prompt 超长")
