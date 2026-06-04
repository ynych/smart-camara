import json
import asyncio
from agents.base_agent import BaseAgent
from tools.prompt_tool import PromptTool
from tools.image_tool import ImageTool
from tools.file_tool import FileTool

class ImageSynthAgent(BaseAgent):
    """效果图合成Agent - 执行Lookbook生成"""
    name = "image_synth"
    description = "根据提示词生成Lookbook效果图"

    def __init__(self):
        super().__init__()
        self.prompt_tool = PromptTool()
        self.image_tool = ImageTool()
        self.file_tool = FileTool()

    async def generate_lookbook(self, task_id: str, features: dict, reference_images=None, progress_callback=None, quantity: int = 4, prompt_overrides=None, size: str = "3:4") -> list:
        """
        生成Lookbook（多张不同视角）

        Args:
            task_id: 任务ID
            features: 服装特征字典
            reference_images: 参考图URL列表（可选），用于图生图
            progress_callback: 进度回调函数 callback(progress_percent)
            quantity: 生成数量
            prompt_overrides: 用户自定义prompt列表（可选），如提供则直接使用

        Returns:
            生成的图片路径列表
        """
        # 如果有用户自定义prompt，直接使用
        if prompt_overrides and isinstance(prompt_overrides, list) and len(prompt_overrides) > 0:
            prompts = prompt_overrides
        else:
            # 使用内置角度模板构建prompt
            prompts = self._build_prompts_from_features(features, quantity)

        results = []
        total = len(prompts)

        for i, prompt_data in enumerate(prompts):
            # prompt_data可以是字符串或字典
            if isinstance(prompt_data, dict):
                prompt = prompt_data.get("prompt", "")
                angle_name = prompt_data.get("angle_name", f"视角{i+1}")
            else:
                prompt = str(prompt_data)
                angle_name = f"视角{i+1}"

            if not prompt:
                continue

            # 调用生图API（传入参考图进行图生图）
            image_content = await self.image_tool.generate(prompt, image_paths=reference_images, size=size)

            # 保存图片
            file_path = self.file_tool.save_generated(task_id, image_content, i)
            results.append({
                "angle": angle_name,
                "path": file_path,
                "status": "completed",
            })

            # 更新进度
            if progress_callback:
                progress = int((i + 1) / total * 100)
                await progress_callback(progress)

        return results

    def _build_prompts_from_features(self, features: dict, quantity: int) -> list:
        """从特征信息构建角度prompt列表（后备方案）"""
        base_variables = {
            "model_desc": features.get("model_description", "优雅的亚洲女性模特"),
            "clothing_desc": features.get("clothing_description", "时尚服装"),
            "scene_desc": features.get("scene_description", "室内摄影棚"),
        }

        angle_templates = [
            {"name": "正面全身", "desc": "正面全身展示，展现服装整体效果"},
            {"name": "侧面45度", "desc": "侧面45度角，展示服装线条和剪裁"},
            {"name": "背面展示", "desc": "背面设计展示，展示背部剪裁和细节"},
            {"name": "细节特写", "desc": "面料质地和工艺细节特写"},
            {"name": "动态抓拍", "desc": "自然行走中的动态抓拍，展现服装垂坠感"},
            {"name": "搭配场景", "desc": "搭配包包和鞋子的完整造型场景"},
            {"name": "坐姿展示", "desc": "坐姿展示，展现服装自然状态下的效果"},
            {"name": "半身特写", "desc": "上半身特写，展示领口和袖口设计"},
        ]

        selected = angle_templates[:quantity]
        prompts = []
        for template in selected:
            variables = base_variables.copy()
            variables["angle_desc"] = template["desc"]
            prompt = (
                f"一位{variables['model_desc']}模特，"
                f"穿着{variables['clothing_desc']}，"
                f"{variables['angle_desc']}，"
                f"{variables['scene_desc']}，"
                f"柔和自然光，专业补光，85mm镜头浅景深，"
                f"高清8K细节丰富，专业电商摄影风格，时尚Lookbook"
            )
            prompts.append({
                "prompt": prompt,
                "angle_name": template["name"],
            })
        return prompts
