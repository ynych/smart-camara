"""图片专家评价服务（AI 初评 + 持久化）。"""

import json
from datetime import datetime

from agents.prompt_agent import call_ark_chat, extract_responses_text
from config import get_chat_api_config
from database import SessionLocal
from models import GeneratedImage, ImageEvaluation, LookbookTask


def _parse_json(text: str | None, default=None):
    if not text:
        return default if default is not None else {}
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else {}


def evaluation_to_dict(ev: ImageEvaluation) -> dict:
    return {
        "id": ev.id,
        "image_id": ev.image_id,
        "task_id": ev.task_id,
        "reviewer_name": ev.reviewer_name,
        "overall": ev.overall,
        "scores": _parse_json(ev.scores_json, {}),
        "issues": _parse_json(ev.issues_json, []),
        "suggestions": _parse_json(ev.suggestions_json, []),
        "expert_note": ev.expert_note or "",
        "ai_draft": ev.ai_draft or "",
        "ai_vision_diff": ev.ai_vision_diff or "",
        "created_at": ev.created_at.isoformat() if ev.created_at else None,
        "updated_at": ev.updated_at.isoformat() if ev.updated_at else None,
    }


def get_evaluation(image_id: str) -> dict | None:
    db = SessionLocal()
    try:
        ev = (
            db.query(ImageEvaluation)
            .filter(ImageEvaluation.image_id == image_id)
            .order_by(ImageEvaluation.updated_at.desc())
            .first()
        )
        return evaluation_to_dict(ev) if ev else None
    finally:
        db.close()


def save_evaluation(image_id: str, data: dict) -> dict:
    db = SessionLocal()
    try:
        image = db.query(GeneratedImage).filter(GeneratedImage.id == image_id).first()
        if not image:
            raise ValueError("图片不存在")

        ev = (
            db.query(ImageEvaluation)
            .filter(ImageEvaluation.image_id == image_id)
            .order_by(ImageEvaluation.updated_at.desc())
            .first()
        )
        if not ev:
            ev = ImageEvaluation(image_id=image_id, task_id=image.task_id)
            db.add(ev)

        ev.reviewer_name = data.get("reviewer_name") or ev.reviewer_name or "专家"
        ev.overall = data.get("overall") or ev.overall
        if "scores" in data:
            ev.scores_json = json.dumps(data["scores"], ensure_ascii=False)
        if "issues" in data:
            ev.issues_json = json.dumps(data["issues"], ensure_ascii=False)
        if "suggestions" in data:
            ev.suggestions_json = json.dumps(data["suggestions"], ensure_ascii=False)
        if "expert_note" in data:
            ev.expert_note = data.get("expert_note") or ""
        if "ai_draft" in data:
            ev.ai_draft = data.get("ai_draft") or ""
        ev.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(ev)
        return evaluation_to_dict(ev)
    finally:
        db.close()


async def generate_ai_draft(image_id: str) -> dict:
    """基于 prompt 与验收标准生成 AI 初评（纯文本 LLM，MVP 不做视觉对比）。"""
    db = SessionLocal()
    try:
        image = db.query(GeneratedImage).filter(GeneratedImage.id == image_id).first()
        if not image:
            raise ValueError("图片不存在")
        task = db.query(LookbookTask).filter(LookbookTask.id == image.task_id).first()
        config = get_chat_api_config()
        endpoint = (config.get("endpoint") or "").strip()
        api_key = (config.get("api_key") or "").strip()
        if not endpoint or not api_key:
            raise ValueError("未配置对话模型，无法生成 AI 初评")

        system = (
            "你是电商 Lookbook 摄影总监，负责验收 AI 生成图的质量。"
            "仅根据提示词与验收标准做文本初评（你看不到实际图片）。"
            "输出合法 JSON，不要 markdown。"
        )
        user = f"""请对以下生成任务做专家初评：

【角度】{image.angle or "未知"}
【生图提示词】
{image.prompt or "无"}

【验收标准】
{image.acceptance_criteria or task.acceptance_criteria if task else "无"}

返回 JSON：
{{
  "overall": "good|fair|poor",
  "scores": {{"composition":1-5,"lighting":1-5,"color":1-5,"model_pose":1-5,"brand_fit":1-5}},
  "issues": ["问题1","问题2"],
  "suggestions": ["建议1","建议2"],
  "expert_note": "一段给运营/摄影师的可执行备注",
  "ai_draft": "200字以内总结"
}}"""

        body, err = await call_ark_chat(
            api_key, endpoint,
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=1200,
            temperature=0.3,
        )
        if not body:
            raise ValueError(err or "AI 初评失败")

        content = extract_responses_text(body)
        draft = _parse_ai_json(content)
        if not draft:
            raise ValueError("AI 返回无法解析为 JSON")

        saved = save_evaluation(image_id, {
            **draft,
            "reviewer_name": "AI 初评",
        })
        return saved
    finally:
        db.close()


def _parse_ai_json(content: str) -> dict | None:
    if not content:
        return None
    text = content.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    try:
        data = json.loads(text.strip())
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None
