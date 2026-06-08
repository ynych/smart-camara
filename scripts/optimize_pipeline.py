#!/usr/bin/env python3
"""离线 Pipeline 优化：读失败 TestCase + 专家 note → 写 draft（不自动 publish）。

用法:
  cd smart-camara
  python scripts/optimize_pipeline.py [--slug lookbook_v1]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND)

_env = os.path.join(ROOT, ".env")
if os.path.exists(_env):
    from dotenv import load_dotenv
    load_dotenv(_env)


async def _suggest_templates(failures: list[dict], modules: dict) -> dict:
    from agents.prompt_agent import call_ark_chat, extract_responses_text
    from config import get_chat_api_config

    cfg = get_chat_api_config()
    endpoint = (cfg.get("endpoint") or "").strip()
    api_key = (cfg.get("api_key") or "").strip()
    if not endpoint or not api_key:
        print("未配置 VOLCANO_CHAT_ENDPOINT / VOLCANO_API_KEY，跳过 LLM 优化，仅克隆 draft")
        return modules

    notes = []
    for f in failures[:5]:
        ev = f.get("human_eval") or {}
        notes.append({
            "case": f.get("name"),
            "expert_note": ev.get("expert_note") or f.get("notes"),
            "issues": ev.get("issues"),
            "acceptance": f.get("acceptance_criteria"),
        })

    system = (
        "你是 Lookbook Pipeline 模板优化助手。根据专家反馈，仅调整 A1–A8 模块的 template 字段。"
        "输出 JSON：{\"modules\": {\"role\": {\"template\": \"...\"}, ...}}，不要改其他键。"
    )
    user = json.dumps({"failures": notes, "current_modules": {k: v.get("template") for k, v in modules.items()}}, ensure_ascii=False)
    body, _ = await call_ark_chat(
        api_key, endpoint,
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=2048,
        temperature=0.2,
    )
    if not body:
        return modules
    content = extract_responses_text(body)
    try:
        chunk = content[content.find("{") : content.rfind("}") + 1]
        parsed = json.loads(chunk)
        patches = parsed.get("modules") or {}
        out = dict(modules)
        for mid, patch in patches.items():
            if mid in out and isinstance(patch, dict):
                out[mid] = {**out[mid], **patch}
        return out
    except json.JSONDecodeError:
        print("LLM 返回非 JSON，保留原 modules")
        return modules


def main():
    parser = argparse.ArgumentParser(description="Propose Pipeline draft from failed TestCases")
    parser.add_argument("--slug", default="lookbook_v1")
    args = parser.parse_args()

    from database import SessionLocal
    from data.services import HarnessTestCaseService
    from services.pipeline_version import clone_to_draft, get_version_pair, update_draft_modules

    db = SessionLocal()
    try:
        tc_svc = HarnessTestCaseService(db)
        cases = tc_svc.list_all()
        parsed_failures = []
        for c in cases:
            he = c.get("human_eval_json")
            if isinstance(he, str):
                try:
                    he = json.loads(he)
                except json.JSONDecodeError:
                    he = {}
            row = {**c, "human_eval": he or {}}
            if row.get("status") == "failed" or row.get("pass_label") == 0 or row["human_eval"].get("overall") == "poor":
                parsed_failures.append(row)

        clone_to_draft(db, args.slug)
        pair = get_version_pair(db, args.slug)
        draft = pair.get("draft") or {}
        modules = draft.get("modules_json") or draft.get("modules") or {}
        if isinstance(modules, str):
            modules = json.loads(modules)

        if parsed_failures:
            modules = asyncio.run(_suggest_templates(parsed_failures, modules))
            update_draft_modules(db, args.slug, modules)
            print(f"已根据 {len(parsed_failures)} 条失败/差评样本更新 draft template")
        else:
            print("无失败 TestCase，已克隆 published → draft（未改 template）")

        pair = get_version_pair(db, args.slug)
        print(json.dumps({"draft_id": pair.get("draft", {}).get("id"), "slug": f"{args.slug}_draft"}, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
