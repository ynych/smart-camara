import json
import os
import base64
import httpx
from agents.base_agent import BaseAgent
from tools.prompt_tool import PromptTool
from config import get_image_api_config


class RequirementAgent(BaseAgent):
    """需求理解Agent - 分析上传的服装照片特征"""

    name = "requirement"
    description = "分析服装照片，提取特征信息"

    def __init__(self):
        super().__init__()

    def analyze(self, source_image_path: str, user_description: str = "") -> dict:
        """
        分析服装特征

        如果有图片且API可用，通过LLM多模态能力分析图片。
        否则基于用户描述推断。
        """
        # 尝试通过AI分析图片
        if source_image_path and os.path.exists(source_image_path):
            try:
                ai_features = self._analyze_with_ai(source_image_path)
                if ai_features:
                    # 如果用户有额外描述，补充到结果中
                    if user_description:
                        ai_features["clothing_description"] = user_description
                    return ai_features
            except Exception as e:
                print(f"[RequirementAgent] AI分析失败: {e}，使用默认推断")

        # 回退到基于描述的推断
        return self._analyze_from_description(user_description)

    def _analyze_with_ai(self, image_path: str) -> dict:
        """通过火山引擎LLM多模态API分析图片"""
        config = get_image_api_config()
        if not config.get("api_key"):
            return None

        # 将图片转为base64
        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
        mime_type = mime_map.get(ext, "image/png")

        with open(image_path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")

        analysis_prompt = """请分析这张服装/模特照片，提取以下信息，以JSON格式返回：
{
    "clothing_type": "服装类型（如连衣裙、T恤、西装、半身裙等）",
    "color": "主要颜色",
    "style": "风格（如简约、优雅、休闲、运动、商务等）",
    "material": "材质（如棉质、丝绸、牛仔、针织等）",
    "model_description": "模特描述（性别、年龄感、气质等）",
    "clothing_description": "服装整体描述（一句话概括）",
    "target_audience": "目标受众（年龄段、性别等）",
    "selling_points": ["卖点1", "卖点2", "卖点3"]
}

注意：只返回JSON，不要其他文字。"""

        # 使用火山引擎的对话API进行图片分析
        # 尝试使用视觉理解模型
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(self._call_vision_api(
                    config["api_key"],
                    analysis_prompt,
                    f"data:{mime_type};base64,{b64_data}"
                ))
            finally:
                loop.close()

            if result:
                return result
        except Exception as e:
            print(f"[RequirementAgent] 视觉API调用失败: {e}")

        return None

    async def _call_vision_api(self, api_key: str, prompt: str, image_b64: str) -> dict:
        """调用火山引擎视觉理解API"""
        # 使用豆包大模型的视觉理解能力
        # endpoint使用同一个ark key，但model需要是视觉理解模型
        # MVP: 使用通用endpoint尝试调用
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": os.environ.get("VISION_MODEL", ""),  # 需要配置视觉理解模型endpoint
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": image_b64}
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                    "max_tokens": 1000,
                },
            )

            if response.status_code != 200:
                return None

            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            # 解析JSON响应
            try:
                # 提取JSON部分（可能包含markdown代码块）
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                features = json.loads(content.strip())
                # 验证必要字段
                required_fields = ["clothing_type", "color", "style", "clothing_description"]
                if all(f in features for f in required_fields):
                    return features
            except (json.JSONDecodeError, IndexError):
                pass

            return None

    def _analyze_from_description(self, user_description: str) -> dict:
        """基于用户描述推断特征（回退方案）"""
        desc = user_description or ""

        # 简单关键词匹配
        clothing_type = "服装"
        color = "多色"
        style = "时尚"

        type_keywords = {
            "连衣裙": "连衣裙", "裙": "裙子", "裤": "裤子", "上衣": "上衣",
            "T恤": "T恤", "衬衫": "衬衫", "外套": "外套", "西装": "西装",
            "卫衣": "卫衣", "毛衣": "毛衣", "针织": "针织衫", "大衣": "大衣",
        }
        color_keywords = {
            "白": "白色", "黑": "黑色", "红": "红色", "蓝": "蓝色",
            "绿": "绿色", "灰": "灰色", "粉": "粉色", "黄": "黄色",
        }
        style_keywords = {
            "简约": "简约", "优雅": "优雅", "休闲": "休闲", "运动": "运动",
            "商务": "商务", "甜美": "甜美", "酷": "酷飒", "复古": "复古",
        }

        for kw, val in type_keywords.items():
            if kw in desc:
                clothing_type = val
                break

        for kw, val in color_keywords.items():
            if kw in desc:
                color = val
                break

        for kw, val in style_keywords.items():
            if kw in desc:
                style = val
                break

        return {
            "clothing_type": clothing_type,
            "color": color,
            "style": style,
            "material": "未知材质",
            "model_description": "模特",
            "clothing_description": desc or f"{color}{clothing_type}",
            "target_audience": "通用",
            "selling_points": [],
        }
