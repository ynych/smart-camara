import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class HarnessContext:
    """Harness 动态参数上下文。"""

    task_id: str = ""
    image_id: str = ""
    size: str = "3:4"
    quantity: int = 4
    model_id: str = ""
    clothing_ids: list = field(default_factory=list)
    reference_id: str = ""
    scene_id: str = ""
    model_desc: str = "优雅的亚洲女性模特"
    clothing_desc: str = "时尚服装"
    scene_desc: str = "电商Lookbook拍摄场景"
    style_hint: str = ""
    goal_text: str = ""
    constraint_text: str = ""
    angle_name: str = ""
    angle_desc: str = ""
    fusion_text: str = ""
    seedream_image_slots: list = field(default_factory=list)
    materials: dict = field(default_factory=dict)
    evaluation: dict = field(default_factory=dict)
    previous_prompt: str = ""
    regen_text: str = ""
    business_context: dict = field(default_factory=dict)
    tool_outputs: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "image_id": self.image_id,
            "size": self.size,
            "model_id": self.model_id,
            "clothing_ids": self.clothing_ids,
            "reference_id": self.reference_id,
            "scene_id": self.scene_id,
            "model_desc": self.model_desc,
            "clothing_desc": self.clothing_desc,
            "scene_desc": self.scene_desc,
            "style_hint": self.style_hint,
            "goal_text": self.goal_text,
            "constraint_text": self.constraint_text,
            "angle_name": self.angle_name,
            "angle_desc": self.angle_desc,
            "fusion_text": self.fusion_text,
            "seedream_image_slots": self.seedream_image_slots,
            "materials": self.materials,
            "evaluation": self.evaluation,
            "previous_prompt": self.previous_prompt,
            "regen_text": self.regen_text,
            "business_context": self.business_context,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HarnessContext":
        allowed = cls.__dataclass_fields__.keys()
        kwargs = {k: v for k, v in (data or {}).items() if k in allowed and k != "tool_outputs"}
        return cls(**kwargs)

    def render_vars(self) -> dict[str, Any]:
        from harness.defaults import SIZE_HINTS

        return {
            **self.to_dict(),
            "size_hint": SIZE_HINTS.get(self.size, SIZE_HINTS["3:4"]),
            **self.tool_outputs,
        }
