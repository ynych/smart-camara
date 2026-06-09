"""PromptGenerationPack 选包路由（P1）。"""

from __future__ import annotations

import json
from typing import Any


def _get_nested(obj: dict, path: str) -> Any:
    parts = path.replace("business_context.", "").split(".")
    cur: Any = obj
    for p in parts:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
    return cur


def score_pack(pack: dict[str, Any], business_context: dict[str, Any]) -> int:
    scenario = pack.get("scenario") or pack.get("scenario_json") or {}
    if isinstance(scenario, str):
        scenario = json.loads(scenario)
    rules = scenario.get("match_rules") or {}
    if not rules:
        return 0
    score = 0
    for path, expected in rules.items():
        actual = _get_nested(business_context, path)
        if actual == expected:
            score += 1
    return score



def select_pack(
    packs: list[dict[str, Any]],
    *,
    business_context: dict[str, Any],
    default_pack_id: str | None = None,
    pack_version_pin: dict[str, int] | None = None,
) -> dict[str, Any] | None:
    if not packs:
        return None
    published = [p for p in packs if p.get("status") == "published"]
    if not published:
        return None

    pin = pack_version_pin or {}
    if pin:
        pinned_versions = []
        for p in published:
            slug = p.get("slug")
            if slug and slug in pin:
                if int(p.get("version") or 0) == int(pin[slug]):
                    pinned_versions.append(p)
        if pinned_versions:
            published = pinned_versions

    best_score = -1
    best: dict[str, Any] | None = None
    for pack in published:
        s = score_pack(pack, business_context)
        if s > best_score:
            best_score = s
            best = pack
    if best_score > 0 and best:
        return best

    if default_pack_id:
        fallback = next((p for p in published if p.get("id") == default_pack_id), None)
        if fallback:
            return fallback

    fallback = next((p for p in published if p.get("slug") == "lookbook_default"), None)
    return fallback or published[0]
