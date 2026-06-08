"""从 Harness TestCases / Golden Cases 导出 Promptfoo tests。"""

import json
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from data.services import AgentDefinitionService, GoldenEvalCaseService, HarnessTestCaseService
from services.seed_admin_data import BUILTIN_AGENT_SLUG

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPTFOO_TESTS_PATH = PROJECT_ROOT / "harness" / "promptfoo" / "tests.yaml"
PROMPTFOO_ACTIVE_PATH = PROJECT_ROOT / "harness" / "promptfoo" / "tests.yaml.active"


def _parse_json(value, default=None):
    if value is None:
        return default if default is not None else {}
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default if default is not None else {}
    return default if default is not None else {}


def _default_agent_id(db: Session) -> str:
    rows = AgentDefinitionService(db).list_all()
    agent = next((r for r in rows if r.get("slug") == BUILTIN_AGENT_SLUG), rows[0] if rows else None)
    if not agent:
        raise ValueError("无可用 Agent，请先 seed Admin 数据")
    return agent["id"]


def build_promptfoo_tests(db: Session, *, agent_id: str | None = None) -> list[dict]:
    aid = agent_id or _default_agent_id(db)
    tests: list[dict] = []

    for case in HarnessTestCaseService(db).list_all():
        bc = _parse_json(case.get("business_context_json") or case.get("business_context"), {})
        clothing = _parse_json(case.get("clothing_ids_json") or case.get("clothing_ids"), [])
        tests.append({
            "vars": {
                "name": case.get("name") or case.get("id"),
                "source": "harness_testcase",
                "case_id": case.get("id"),
                "agent_id": case.get("agent_id") or aid,
                "model_id": case.get("model_id") or "",
                "clothing_ids": clothing,
                "reference_id": case.get("reference_id") or "",
                "size": case.get("size") or "3:4",
                "quantity": case.get("quantity") or 4,
                "merchant_need": bc.get("merchant_need") or "",
                "target_audience": bc.get("target_audience") or "",
                "acceptance_criteria": case.get("acceptance_criteria") or "",
            },
        })

    for case in GoldenEvalCaseService(db).list_all():
        ctx = _parse_json(case.get("context_json") or case.get("context"), {})
        bc = ctx.get("business_context") if isinstance(ctx.get("business_context"), dict) else {}
        tests.append({
            "vars": {
                "name": case.get("name") or case.get("id"),
                "source": "golden_case",
                "case_id": case.get("id"),
                "agent_id": aid,
                "model_id": ctx.get("model_id") or "",
                "clothing_ids": ctx.get("clothing_ids") or [],
                "reference_id": ctx.get("reference_id") or "",
                "size": ctx.get("size") or "3:4",
                "quantity": ctx.get("quantity") or 4,
                "merchant_need": bc.get("merchant_need") or ctx.get("merchant_need") or "",
                "target_audience": bc.get("target_audience") or ctx.get("target_audience") or "",
                "acceptance_criteria": ctx.get("acceptance_criteria") or case.get("notes") or "",
            },
        })

    if not tests:
        tests.append({
            "vars": {
                "name": "default-4-shots",
                "source": "fallback",
                "agent_id": aid,
                "model_id": "",
                "clothing_ids": [],
                "reference_id": "",
                "size": "3:4",
                "quantity": 4,
                "merchant_need": "电商主图与详情页展示",
                "target_audience": "25-35 岁都市女性",
                "acceptance_criteria": "服装颜色准确，构图专业，光线自然",
            },
        })
    return tests


def export_promptfoo_yaml(db: Session, *, agent_id: str | None = None) -> str:
    tests = build_promptfoo_tests(db, agent_id=agent_id)
    header = (
        "# 由 API 自动生成：GET /api/agent-runtime/promptfoo/tests.yaml\n"
        "# 来源：Harness TestCases + Golden Cases\n\n"
    )
    return header + yaml.dump(tests, allow_unicode=True, default_flow_style=False, sort_keys=False)


def write_promptfoo_tests(db: Session, *, agent_id: str | None = None, active: bool = True) -> dict:
    tests = build_promptfoo_tests(db, agent_id=agent_id)
    content = export_promptfoo_yaml(db, agent_id=agent_id)
    PROMPTFOO_TESTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROMPTFOO_TESTS_PATH.write_text(content, encoding="utf-8")
    target = PROMPTFOO_ACTIVE_PATH if active else PROMPTFOO_TESTS_PATH
    if active:
        PROMPTFOO_ACTIVE_PATH.write_text(content, encoding="utf-8")
    return {
        "path": str(target),
        "tests_path": str(PROMPTFOO_TESTS_PATH),
        "count": len(tests),
    }
