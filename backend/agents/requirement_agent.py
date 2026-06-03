import json
from agents.base_agent import BaseAgent
from tools.prompt_tool import PromptTool

class RequirementAgent(BaseAgent):
    """需求理解Agent - 分析上传的服装照片特征"""
    name = "requirement"
    description = "分析服装照片，提取特征信息"

    def __init__(self):
        super().__init__()

    def analyze(self, source_image_path: str, user_description: str = "") -> dict:
        """
        分析服装特征（MVP简化版：基于用户描述+默认推断）

        在完整版中，这里会调用LLM的多模态能力来分析图片。
        MVP版本使用用户提供的描述或默认推断。
        """
        features = {
            "clothing_type": "连衣裙",
            "color": "白色",
            "style": "简约优雅",
            "material": "棉质/丝绸",
            "model_description": "优雅的亚洲女性模特",
            "clothing_description": user_description or "白色简约连衣裙",
            "target_audience": "25-35岁女性",
            "selling_points": ["显瘦", "舒适", "优雅"],
        }

        # 如果用户提供了描述，尝试从中提取信息
        if user_description:
            features["clothing_description"] = user_description

        return features
