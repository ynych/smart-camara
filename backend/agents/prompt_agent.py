import json
import os
import httpx
from config import get_chat_api_config

SHOOT_TYPES = ("人台图", "平铺图", "时尚拍摄")


class PromptAgent:
    """使用大模型生成 Lookbook 多角度提示词。"""

    name = "prompt"
    description = "根据素材与业务上下文生成生图提示词"

    async def generate_prompts(
        self,
        *,
        model_desc: str,
        clothing_desc: str,
        scene_desc: str,
        style_hint: str,
        size: str,
        quantity: int,
        angle_templates: list,
        business_context: dict,
        acceptance_criteria: str,
    ) -> list | None:
        config = get_chat_api_config()
        if not config.get("api_key") or not config.get("endpoint"):
            return None

        angles_text = "\n".join(
            f"- {t['name']}：{t['desc']}" for t in angle_templates[:quantity]
        )
        merchant = business_context.get("merchant_need", "")
        audience = business_context.get("target_audience", "")

        system = (
            "你是电商 Lookbook 摄影导演，负责为 AI 图生图模型编写中文提示词。"
            "输出必须是合法 JSON 数组，不要 markdown，不要额外说明。"
        )
        user = f"""请为以下拍摄任务生成 {quantity} 条差异化提示词。

【模特】{model_desc}
【服装】{clothing_desc}
【场景】{scene_desc}
【风格参考】{style_hint or "无"}
【输出比例】{size}
【商家需求】{merchant}
【目标用户】{audience}
【验收标准】{acceptance_criteria or "无"}

需要覆盖的角度（每条对应一个数组元素）：
{angles_text}

返回 JSON 数组，每个元素格式：
{{"angle_name":"角度名","angle_desc":"角度说明","prompt":"完整中文生图提示词"}}

要求：
1. prompt 为一段完整中文，适合 Seedream 图生图，强调服装版型颜色、光线、镜头与构图；
2. angle_name 必须与上面列表中的名称一致；
3. 各条 prompt 在视角与构图上明显区分。"""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config['api_key']}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": config["endpoint"],
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        "temperature": 0.7,
                        "max_tokens": 4096,
                    },
                )
            if response.status_code != 200:
                print(f"[PromptAgent] LLM 失败: {response.status_code} {response.text[:300]}")
                return None

            content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            prompts = self._parse_json_array(content)
            if not prompts:
                return None

            result = []
            for i, item in enumerate(prompts[:quantity]):
                if not isinstance(item, dict):
                    continue
                prompt = (item.get("prompt") or "").strip()
                if not prompt:
                    continue
                result.append({
                    "index": i,
                    "angle_name": item.get("angle_name") or angle_templates[i]["name"],
                    "angle_desc": item.get("angle_desc") or angle_templates[i]["desc"],
                    "prompt": prompt,
                    "editable": True,
                    "source": "llm",
                })
            return result if len(result) >= 1 else None
        except Exception as e:
            print(f"[PromptAgent] 异常: {e}")
            return None

    def _parse_json_array(self, content: str) -> list | None:
        if not content:
            return None
        text = content.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        try:
            data = json.loads(text.strip())
            return data if isinstance(data, list) else None
        except json.JSONDecodeError:
            return None
