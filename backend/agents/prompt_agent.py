import json
import os
import httpx
from config import get_chat_api_config

CHAT_COMPLETIONS_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"


def _parse_ark_error(response: httpx.Response, model_id: str = "") -> str:
    try:
        body = response.json()
        err = body.get("error") or {}
        code = err.get("code") or str(response.status_code)
        msg = err.get("message") or response.text[:300]
        param = err.get("param") or ""
    except Exception:
        code = str(response.status_code)
        msg = response.text[:200]
        param = ""

    if "does not support this api" in msg.lower() or (
        param == "model" and "seedream" in msg.lower()
    ):
        return (
            "当前 VOLCANO_CHAT_ENDPOINT 指向的是 Seedream 生图接入点，不能用于对话。"
            "请在火山方舟「在线推理」新建豆包对话接入点（ep- 开头），写入 .env 后重启。"
        )
    if code == "ModelNotOpen":
        return (
            f"模型未开通：{model_id or '未知'}。请在火山方舟控制台 → 模型广场开通该豆包对话模型，"
            "或创建推理接入点(ep-) 并只填 ep ID。"
        )
    if code in ("InvalidEndpointOrModel.NotFound", "ModelNotFound"):
        if model_id.startswith("ark-"):
            return (
                f"应用/接入点 {model_id[:28]}… 无法被当前 API Key 访问（不存在、未发布或跨项目）。"
                "请打开火山方舟控制台，在「与 API Key 相同项目」下创建豆包对话推理接入点，"
                "复制 ep- 开头的 ID 到 VOLCANO_CHAT_ENDPOINT（不要用生图 ep、不要用其他账号的 ark ID）。"
            )
        return (
            f"接入点无效或无权访问：{msg[:120]}。"
            "请确认 VOLCANO_CHAT_ENDPOINT 与 VOLCANO_API_KEY 属于同一火山方舟项目。"
        )
    if code == "InvalidParameter":
        if param and param != "request":
            return f"对话 API 参数错误 ({param})：{msg[:140]}"
        return f"对话 API 参数错误：{msg[:160]}"
    return f"对话 API 失败 [{code}]：{msg[:160]}"


def _fallback_model_ids(primary: str) -> list[str]:
    """按优先级去重后的 model/endpoint 尝试列表。"""
    seen = set()
    ordered: list[str] = []

    def add(m: str):
        m = (m or "").strip()
        if not m or m in seen:
            return
        seen.add(m)
        ordered.append(m)

    add(primary)
    add(os.environ.get("VOLCANO_CHAT_MODEL", ""))
    for part in os.environ.get("VOLCANO_CHAT_FALLBACK_MODELS", "").split(","):
        add(part.strip())
    return ordered


async def _chat_completion(
    client: httpx.AsyncClient,
    api_key: str,
    model: str,
    messages: list,
    *,
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> httpx.Response:
    return await client.post(
        CHAT_COMPLETIONS_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
    )


async def call_ark_chat(
    api_key: str,
    model: str,
    messages: list,
    *,
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> tuple[httpx.Response | None, str | None]:
    """
    仅使用标准 /chat/completions（OpenAI 兼容）。
    对多个 model/endpoint 依次尝试，返回首个 200 响应或最后一次失败原因。
    """
    errors: list[str] = []
    async with httpx.AsyncClient(timeout=90.0) as client:
        for mid in _fallback_model_ids(model):
            response = await _chat_completion(
                client, api_key, mid, messages,
                max_tokens=max_tokens, temperature=temperature,
            )
            if response.status_code == 200:
                return response, None
            err = _parse_ark_error(response, mid)
            errors.append(f"[{mid[:24]}…] {err}" if len(mid) > 24 else f"[{mid}] {err}")
            print(f"[PromptAgent] 尝试 {mid[:40]} 失败: {err}")

    summary = errors[0] if len(errors) == 1 else "；".join(errors[:2])
    if len(errors) > 2:
        summary += f"（另 {len(errors) - 2} 次失败）"
    return None, summary


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
    ) -> tuple[list | None, str | None]:
        config = get_chat_api_config()
        endpoint = (config.get("endpoint") or "").strip()
        api_key = (config.get("api_key") or "").strip()
        if not endpoint or not api_key:
            return None, (
                "未配置对话模型：请在 .env 设置 VOLCANO_CHAT_ENDPOINT（推荐 ep- 对话接入点），"
                "并确保 VOLCANO_API_KEY 有效。"
            )

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

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        try:
            response, err = await call_ark_chat(
                api_key, endpoint, messages, max_tokens=4096, temperature=0.7,
            )
            if not response:
                return None, err

            content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            prompts = self._parse_json_array(content)
            if not prompts:
                return None, "大模型返回内容无法解析为 JSON 提示词数组，请重试或检查模型输出格式。"

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
            if len(result) < 1:
                return None, "大模型未返回有效提示词条目。"
            return result, None
        except Exception as e:
            print(f"[PromptAgent] 异常: {e}")
            return None, f"对话模型请求异常: {e}"

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


async def probe_chat_config() -> dict:
    """供设置页/诊断：检测对话配置是否可用。"""
    config = get_chat_api_config()
    endpoint = (config.get("endpoint") or "").strip()
    api_key = (config.get("api_key") or "").strip()
    if not endpoint:
        return {"configured": False, "success": False, "error": "未配置 VOLCANO_CHAT_ENDPOINT"}
    if not api_key:
        return {"configured": False, "success": False, "error": "未配置 API Key（VOLCANO_API_KEY）"}

    response, err = await call_ark_chat(
        api_key, endpoint,
        [{"role": "user", "content": "回复OK"}],
        max_tokens=8,
        temperature=0,
    )
    if response:
        return {
            "configured": True,
            "success": True,
            "endpoint": endpoint[:32] + ("…" if len(endpoint) > 32 else ""),
            "api_mode": "chat/completions",
        }
    return {
        "configured": True,
        "success": False,
        "endpoint": endpoint[:32] + ("…" if len(endpoint) > 32 else ""),
        "api_mode": "chat/completions",
        "error": err,
    }
