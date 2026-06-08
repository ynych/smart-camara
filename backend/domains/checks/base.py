"""域中间态检查 — 统一结果模型与运行器。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable, Protocol


class CheckDomain(str, Enum):
    USER = "user"
    AGENT = "agent"
    GATE = "gate"


@dataclass
class CheckResult:
    id: str
    domain: CheckDomain
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["domain"] = self.domain.value
        return d


class CheckFn(Protocol):
    def __call__(self, ctx: dict[str, Any]) -> CheckResult: ...


def run_checks(checks: list[CheckFn], ctx: dict[str, Any]) -> list[CheckResult]:
    return [fn(ctx) for fn in checks]


def summarize(results: list[CheckResult]) -> dict[str, Any]:
    passed = sum(1 for r in results if r.passed)
    by_domain: dict[str, list[CheckResult]] = {}
    for r in results:
        by_domain.setdefault(r.domain.value, []).append(r)
    return {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "ok": passed == len(results),
        "by_domain": {
            k: {"passed": sum(1 for x in v if x.passed), "total": len(v)}
            for k, v in by_domain.items()
        },
        "results": [r.to_dict() for r in results],
    }


def _result(
    check_id: str,
    domain: CheckDomain,
    passed: bool,
    message: str,
    **details: Any,
) -> CheckResult:
    return CheckResult(id=check_id, domain=domain, passed=passed, message=message, details=details)
