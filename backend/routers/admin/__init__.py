"""Admin CRUD 路由汇总。"""

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from data.services import (
    AgentChatSessionService,
    AgentDefinitionService,
    AgentRunService,
    AgentTestCaseService,
    GoldenEvalCaseService,
    GoldenEvalRunService,
    HarnessTestCaseService,
    KnowledgeNodeService,
    KnowledgeTreeService,
    PipelineConfigService,
    PromptAtomPackService,
    ToolDefinitionService,
)
from database import get_db
from routers.admin.crud_factory import make_crud_router


def _testcase_routes(router, svc_dep):
    @router.get("/by-agent/{agent_id}")
    def list_by_agent(agent_id: str, db: Session = Depends(get_db)):
        return {"items": AgentTestCaseService(db).list_by_agent(agent_id)}


def _knowledge_node_routes(router, svc_dep):
    @router.get("/tree/{tree_id}/flat")
    def list_flat(tree_id: str, db: Session = Depends(get_db)):
        return {"items": KnowledgeNodeService(db).list_by_tree(tree_id)}

    @router.get("/tree/{tree_id}/index")
    def tree_index(tree_id: str, db: Session = Depends(get_db)):
        return {"tree": KnowledgeNodeService(db).build_tree_index(tree_id)}


def _pipeline_routes(router, svc_dep):
    @router.get("/slug/{slug}/published")
    def published(slug: str, db: Session = Depends(get_db)):
        item = PipelineConfigService(db).get_published_by_slug(slug)
        if not item:
            raise HTTPException(404, "无已发布配置")
        return item


agents_router = make_crud_router("/api/admin/agents", "admin-agents", AgentDefinitionService)
testcases_router = make_crud_router(
    "/api/admin/test-cases", "admin-testcases", AgentTestCaseService, extra_routes=_testcase_routes,
)
knowledge_trees_router = make_crud_router("/api/admin/knowledge-trees", "admin-knowledge-trees", KnowledgeTreeService)
knowledge_nodes_router = make_crud_router(
    "/api/admin/knowledge-nodes", "admin-knowledge-nodes", KnowledgeNodeService, extra_routes=_knowledge_node_routes,
)
prompt_packs_router = make_crud_router("/api/admin/prompt-packs", "admin-prompt-packs", PromptAtomPackService)
pipeline_configs_router = make_crud_router(
    "/api/admin/pipeline-configs", "admin-pipeline-configs", PipelineConfigService, extra_routes=_pipeline_routes,
)
tool_defs_router = make_crud_router("/api/admin/tool-definitions", "admin-tool-definitions", ToolDefinitionService)
golden_runs_router = make_crud_router(
    "/api/admin/golden-runs", "admin-golden-runs", GoldenEvalRunService, allow_create=True,
)
chat_sessions_router = make_crud_router("/api/admin/chat-sessions", "admin-chat-sessions", AgentChatSessionService)


def _harness_import_routes(router, svc_dep):
    from fastapi import Depends, HTTPException
    from sqlalchemy.orm import Session
    from database import get_db
    from services.harness.import_case import import_from_evaluation

    @router.post("/import-from-evaluation/{image_id}")
    def import_eval(image_id: str, db: Session = Depends(get_db)):
        try:
            return import_from_evaluation(db, image_id)
        except ValueError as e:
            raise HTTPException(400, str(e)) from e


harness_testcases_router = make_crud_router(
    "/api/admin/harness-testcases", "admin-harness-testcases", HarnessTestCaseService,
    extra_routes=_harness_import_routes,
)
agent_runs_router = make_crud_router(
    "/api/admin/agent-runs", "admin-agent-runs", AgentRunService, allow_create=False,
)


def _golden_import_routes(router, svc_dep):
    from fastapi import Depends
    from sqlalchemy.orm import Session
    from database import get_db
    from services.golden.import_case import import_from_evaluation

    @router.post("/import-from-evaluation/{image_id}")
    def import_eval(image_id: str, db: Session = Depends(get_db)):
        try:
            return import_from_evaluation(db, image_id)
        except ValueError as e:
            from fastapi import HTTPException
            raise HTTPException(400, str(e))


golden_cases_router = make_crud_router(
    "/api/admin/golden-cases", "admin-golden-cases", GoldenEvalCaseService, extra_routes=_golden_import_routes,
)
