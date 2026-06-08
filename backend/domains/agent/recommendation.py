"""Agent 域 — 双轨发布建议（纯函数，可单测）。"""

from __future__ import annotations


def recommend_publish(
    published_text: dict,
    draft_text: dict,
    human: dict,
    *,
    avg_slack: float = 0.2,
    pass_rate_drop_threshold: float = 10.0,
    min_good_rate: float = 50.0,
) -> str:
    """
    返回 approve | hold | reject。
    文本轨：draft pass_rate/avg 不低于 published（avg 允许 slack）。
    人评轨：good_rate 低于 min_good_rate 则 hold。
    """
    if not draft_text.get("case_count"):
        return "hold"
    pub_rate = float(published_text.get("pass_rate") or 0)
    draft_rate = float(draft_text.get("pass_rate") or 0)
    pub_avg = float(published_text.get("avg_score") or 0)
    draft_avg = float(draft_text.get("avg_score") or 0)
    text_ok = draft_rate >= pub_rate and draft_avg >= pub_avg - avg_slack
    if human.get("case_count"):
        good_rate = human.get("good_rate")
        if good_rate is not None and float(good_rate) < min_good_rate:
            return "hold"
    if text_ok:
        return "approve"
    if draft_rate < pub_rate - pass_rate_drop_threshold:
        return "reject"
    return "hold"
