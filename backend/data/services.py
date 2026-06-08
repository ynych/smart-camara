"""各实体 CRUD Service（纯数据层）。"""

from data.crud import CrudService
from models import (
    AgentChatSession,
    AgentDefinition,
    AgentRun,
    AgentTestCase,
    GoldenEvalCase,
    GoldenEvalRun,
    HarnessTestCase,
    KnowledgeNode,
    KnowledgeTree,
    PipelineConfig,
    PromptAtomPack,
    ToolDefinition,
)


class AgentDefinitionService(CrudService[AgentDefinition]):
    model = AgentDefinition
    json_fields = ["tool_ids_json", "graph_config_json"]


class AgentTestCaseService(CrudService[AgentTestCase]):
    model = AgentTestCase
    json_fields = ["inputs_json", "expected_json"]

    def list_by_agent(self, agent_id: str):
        rows = (
            self.db.query(AgentTestCase)
            .filter(AgentTestCase.agent_id == agent_id)
            .order_by(AgentTestCase.sort_order.asc())
            .all()
        )
        return [self.serialize(r) for r in rows]


class KnowledgeTreeService(CrudService[KnowledgeTree]):
    model = KnowledgeTree


class KnowledgeNodeService(CrudService[KnowledgeNode]):
    model = KnowledgeNode
    json_fields = ["meta_json"]

    def list_by_tree(self, tree_id: str):
        rows = (
            self.db.query(KnowledgeNode)
            .filter(KnowledgeNode.tree_id == tree_id)
            .order_by(KnowledgeNode.sort_order.asc())
            .all()
        )
        return [self.serialize(r) for r in rows]

    def build_tree_index(self, tree_id: str) -> list[dict]:
        nodes = self.list_by_tree(tree_id)
        by_id = {n["id"]: {**n, "children": []} for n in nodes}
        roots = []
        for n in by_id.values():
            pid = n.get("parent_id")
            if pid and pid in by_id:
                by_id[pid]["children"].append(n)
            elif not pid:
                roots.append(n)
        return roots


class PromptAtomPackService(CrudService[PromptAtomPack]):
    model = PromptAtomPack
    json_fields = ["tags_json"]


class PipelineConfigService(CrudService[PipelineConfig]):
    model = PipelineConfig
    json_fields = ["module_order_json", "modules_json"]

    def get_published_by_slug(self, slug: str):
        row = (
            self.db.query(PipelineConfig)
            .filter(PipelineConfig.slug == slug, PipelineConfig.status == "published")
            .order_by(PipelineConfig.version.desc())
            .first()
        )
        return self.serialize(row) if row else None


class ToolDefinitionService(CrudService[ToolDefinition]):
    model = ToolDefinition
    json_fields = ["module_ids_json", "input_schema_json", "output_schema_json", "config_json"]


class GoldenEvalCaseService(CrudService[GoldenEvalCase]):
    model = GoldenEvalCase
    json_fields = ["context_json", "human_eval_json", "baseline_output_json"]


class GoldenEvalRunService(CrudService[GoldenEvalRun]):
    model = GoldenEvalRun
    json_fields = ["config_snapshot_json", "metrics_json", "case_results_json"]


class AgentChatSessionService(CrudService[AgentChatSession]):
    model = AgentChatSession
    json_fields = ["messages_json", "slots_json"]


class HarnessTestCaseService(CrudService[HarnessTestCase]):
    model = HarnessTestCase
    json_fields = [
        "clothing_ids_json", "business_context_json", "prompts_json", "images_json",
        "seedream_slots_json", "evaluation_json", "run_meta_json", "module_snapshot_json",
        "human_eval_json",
    ]


class AgentRunService(CrudService[AgentRun]):
    model = AgentRun
    json_fields = ["input_json", "output_json", "steps_json", "meta_json", "module_snapshot_json"]

    def list_recent(self, limit: int = 100, run_type: str | None = None):
        q = self.db.query(AgentRun).order_by(AgentRun.created_at.desc())
        if run_type:
            q = q.filter(AgentRun.run_type == run_type)
        return [self.serialize(r) for r in q.limit(limit).all()]
