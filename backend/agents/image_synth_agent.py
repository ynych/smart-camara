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

    async def generate_lookbook(self, task_id: str, style_id: str, features: dict, reference_images=None, progress_callback=None) -> list:
        """
        生成Lookbook（4张不同视角）

        Args:
            task_id: 任务ID
            style_id: 风格模板ID
            features: 服装特征字典
            reference_images: 参考图URL列表（可选），用于图生图
            progress_callback: 进度回调函数 callback(progress_percent)

        Returns:
            生成的图片路径列表
        """
        # 获取风格的视角列表
        angles = self.prompt_tool.get_style_angles(style_id)
        if not angles:
            raise Exception("未找到风格的视角配置")

        # 构建基础变量
        base_variables = {
            "model_desc": features.get("model_description", "优雅的亚洲女性模特"),
            "clothing_desc": features.get("clothing_description", "时尚服装"),
        }

        # 获取风格默认变量中的场景描述
        style_vars = self.prompt_tool.get_style_variables(style_id)
        base_variables["scene_desc"] = style_vars.get("scene_desc", "室内摄影棚")

        results = []
        total = len(angles)

        for i, angle in enumerate(angles):
            # 构建该视角的提示词
            variables = base_variables.copy()
            variables["angle_desc"] = angle.get("desc", angle.get("name", ""))

            prompt = self.prompt_tool.build_prompt(style_id, variables)
            if not prompt:
                raise Exception(f"构建提示词失败: {style_id}")

            # 调用生图API（传入参考图进行图生图）
            image_content = await self.image_tool.generate(prompt, image_urls=reference_images)

            # 保存图片
            file_path = self.file_tool.save_generated(task_id, image_content, i)
            results.append({
                "angle": angle.get("name", f"视角{i+1}"),
                "path": file_path,
                "status": "completed",
            })

            # 更新进度
            if progress_callback:
                progress = int((i + 1) / total * 100)
                await progress_callback(progress)

        return results
