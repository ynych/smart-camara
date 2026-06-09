import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime
from database import Base

class Requirement(Base):
    __tablename__ = "requirements"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String(20), default="active")  # active/completed/archived
    source_image_path = Column(String(500))
    detected_features = Column(Text)  # JSON string
    selected_style = Column(String(36))
    user_edits = Column(Text)  # JSON string
    selected_materials = Column(Text)  # JSON: [{"id": "xxx", "category": "model"}, ...]
    reference_image_path = Column(String(500))
    prompt_overrides = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class StyleTemplate(Base):
    __tablename__ = "style_templates"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    preview_prompt = Column(Text)
    prompt_template = Column(Text, nullable=False)
    variables = Column(Text)  # JSON string
    angles = Column(Text, nullable=False)  # JSON string
    sort_order = Column(Integer, default=0)

class LookbookTask(Base):
    __tablename__ = "lookbook_tasks"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    requirement_id = Column(String(36))
    style_id = Column(String(36))
    status = Column(String(20), default="pending")  # pending/analyzing/generating/completed/failed
    progress = Column(Integer, default=0)
    quantity = Column(Integer, default=4)
    size = Column(String(20), default="3:4")
    selected_materials = Column(Text)  # JSON string
    acceptance_criteria = Column(Text)
    prompt_overrides = Column(Text)  # JSON string
    generated_images = Column(Text)  # JSON string
    generation_round = Column(Integer, default=1)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

class Material(Base):
    __tablename__ = "materials"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255))
    type = Column(String(20))  # upload/generated/reference
    category = Column(String(50))  # clothing/model/scene
    file_path = Column(String(500))
    thumbnail_path = Column(String(500))
    metadata_json = Column(Text)  # JSON string (避免与SQLAlchemy metadata冲突)
    parent_dir = Column(String(255))
    sub_category = Column(String(50))
    outfit_set = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

class GeneratedImage(Base):
    __tablename__ = "generated_images"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36))
    file_path = Column(String(500))
    angle = Column(String(100))
    prompt = Column(Text)
    status = Column(String(20), default="pending")  # pending/approved/rejected
    feedback = Column(Text)
    acceptance_criteria = Column(Text)
    generation_round = Column(Integer, default=1)
    parent_image_id = Column(String(36))
    prompt_modules_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime)

class ImageEvaluation(Base):
    __tablename__ = "image_evaluations"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    image_id = Column(String(36), nullable=False, index=True)
    task_id = Column(String(36))
    reviewer_name = Column(String(100), default="专家")
    overall = Column(String(20))
    scores_json = Column(Text)
    issues_json = Column(Text)
    suggestions_json = Column(Text)
    expert_note = Column(Text)
    ai_draft = Column(Text)
    ai_vision_diff = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PromptModuleRun(Base):
    __tablename__ = "prompt_module_runs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    image_id = Column(String(36))
    task_id = Column(String(36))
    pipeline_id = Column(String(50))
    module_id = Column(String(50))
    input_json = Column(Text)
    output_text = Column(Text)
    tool_traces_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class PromptFeedback(Base):
    __tablename__ = "prompt_feedbacks"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36))
    image_id = Column(String(36))
    prompt_used = Column(Text)
    result = Column(String(20))
    feedback = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class ApiConfig(Base):
    __tablename__ = "api_configs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String(50), unique=True, nullable=False)
    api_key = Column(String(500), nullable=False)
    endpoint = Column(String(500))
    model = Column(String(100))
    is_active = Column(Integer, default=1)


# ---------- Admin / Agent 数据层（AI 无关） ----------


class AgentDefinition(Base):
    __tablename__ = "agent_definitions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String(100), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    role_prompt = Column(Text)
    pipeline_config_id = Column(String(36))
    tool_ids_json = Column(Text)  # JSON array of tool definition ids
    knowledge_tree_id = Column(String(36))
    graph_config_json = Column(Text)
    status = Column(String(20), default="published")  # draft / published
    is_builtin = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentTestCase(Base):
    __tablename__ = "agent_test_cases"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(36), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    inputs_json = Column(Text, nullable=False)
    expected_json = Column(Text)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KnowledgeTree(Base):
    __tablename__ = "knowledge_trees"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String(100), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    root_node_id = Column(String(36))
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tree_id = Column(String(36), nullable=False, index=True)
    parent_id = Column(String(36))
    title = Column(String(500), nullable=False)
    summary = Column(Text)
    content = Column(Text)
    source_type = Column(String(50))  # manual / evaluation / prompt / import
    source_ref = Column(String(100))
    sort_order = Column(Integer, default=0)
    meta_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PromptAtomPack(Base):
    __tablename__ = "prompt_atom_packs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    domain = Column(String(100), default="lookbook")
    module_id = Column(String(50))
    name = Column(String(200), nullable=False)
    template = Column(Text, nullable=False)
    tags_json = Column(Text)
    status = Column(String(20), default="draft")  # draft / published
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PipelineConfig(Base):
    __tablename__ = "pipeline_configs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String(100), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    module_order_json = Column(Text)
    modules_json = Column(Text)
    status = Column(String(20), default="draft")
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ToolDefinition(Base):
    __tablename__ = "tool_definitions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String(100), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    handler_key = Column(String(100), nullable=False)
    module_ids_json = Column(Text)
    input_schema_json = Column(Text)
    output_schema_json = Column(Text)
    config_json = Column(Text)
    status = Column(String(20), default="published")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GoldenEvalCase(Base):
    __tablename__ = "golden_eval_cases"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    source_type = Column(String(50))  # evaluation / testcase / manual
    source_ref = Column(String(100))
    context_json = Column(Text, nullable=False)
    human_eval_json = Column(Text)
    baseline_output_json = Column(Text)
    pass_label = Column(Integer)  # 1 pass 0 fail null unknown
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GoldenEvalRun(Base):
    __tablename__ = "golden_eval_runs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200))
    target_type = Column(String(50))  # agent / pipeline / tool / prompt_pack
    target_ref = Column(String(100))
    config_snapshot_json = Column(Text)
    metrics_json = Column(Text)
    case_results_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentChatSession(Base):
    __tablename__ = "agent_chat_sessions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(36), nullable=False, index=True)
    title = Column(String(200))
    messages_json = Column(Text)
    slots_json = Column(Text)
    last_run_id = Column(String(36))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HarnessTestCase(Base):
    """Harness TestCase：输入 → prompts → 文本/人评聚合（生图在用户平台）。"""
    __tablename__ = "harness_test_cases"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    status = Column(String(20), default="draft")  # draft / ready / passed / failed
    agent_id = Column(String(36))
    model_id = Column(String(36))
    clothing_ids_json = Column(Text)
    reference_id = Column(String(36))
    scene_id = Column(String(36))
    business_context_json = Column(Text)
    size = Column(String(20), default="3:4")
    quantity = Column(Integer, default=4)
    acceptance_criteria = Column(Text)
    prompts_json = Column(Text)
    images_json = Column(Text)
    seedream_slots_json = Column(Text)
    evaluation_json = Column(Text)
    pass_label = Column(Integer)
    last_run_id = Column(String(36))
    run_meta_json = Column(Text)
    module_snapshot_json = Column(Text)
    source_image_id = Column(String(36))
    source_evaluation_id = Column(String(36))
    human_eval_json = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentRun(Base):
    """Agent / Harness 本地运行账本。"""
    __tablename__ = "agent_runs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_type = Column(String(50), nullable=False, index=True)
    session_id = Column(String(100), index=True)
    user_id = Column(String(50), default="admin")
    agent_id = Column(String(36), index=True)
    ref_type = Column(String(50))
    ref_id = Column(String(36), index=True)
    status = Column(String(20), default="running")
    input_json = Column(Text)
    output_json = Column(Text)
    steps_json = Column(Text)
    meta_json = Column(Text)
    module_snapshot_json = Column(Text)
    error_message = Column(Text)
    duration_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PromptGenerationPack(Base):
    """提示词生成包 — 场景 × 需求 × 优化技术。"""
    __tablename__ = "prompt_generation_packs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String(100), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    scenario_json = Column(Text)
    user_needs_json = Column(Text)
    techniques_json = Column(Text)
    harness_pipeline_slug = Column(String(100), default="lookbook_v1")
    status = Column(String(20), default="draft")  # draft / published / archived
    version = Column(Integer, default=1)
    parent_id = Column(String(36))
    skill_version_id = Column(String(100))
    published_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkflowDefinition(Base):
    """生产 Workflow 定义（Admin 编辑，publish 后 pin）。"""
    __tablename__ = "workflow_definitions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    steps_json = Column(Text)
    graph_ref = Column(String(100))
    status = Column(String(20), default="published")
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProductionManifest(Base):
    """生产 manifest — pin workflow / pack / skill 版本。"""
    __tablename__ = "production_manifests"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String(100), unique=True, nullable=False)
    workflow_id = Column(String(100), nullable=False)
    default_pack_id = Column(String(36))
    default_pack_slug = Column(String(100))
    pack_version_pin_json = Column(Text)
    skill_version_id = Column(String(100))
    fallback_skill_version_id = Column(String(100))
    harness_pipeline_slug = Column(String(100))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PromptRunRecord(Base):
    """U3 预览 / Admin dry-run 的 prompt 运行记录（不可变）。"""
    __tablename__ = "prompt_run_records"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pack_id = Column(String(36), index=True)
    pack_version = Column(Integer)
    inputs_json = Column(Text)
    prompts_json = Column(Text)
    acceptance_criteria = Column(Text)
    source = Column(String(50))  # user_preview / admin_dry_run / testcase
    workflow_version = Column(String(100))
    agent_run_id = Column(String(36))
    studio_task_id = Column(String(36), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class LookbookStudioTask(Base):
    """用户工作台生图任务（选片 → 提示词 → 生图）。"""
    __tablename__ = "lookbook_studio_tasks"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200))
    status = Column(String(20), default="draft")  # draft | prompts_ready | generating | completed | failed
    model_id = Column(String(36))
    model_name = Column(String(200))
    clothing_ids_json = Column(Text)
    reference_id = Column(String(36))
    scene_id = Column(String(36))
    size = Column(String(20), default="3:4")
    quantity = Column(Integer, default=4)
    business_context_json = Column(Text)
    acceptance_criteria = Column(Text)
    prompts_json = Column(Text)
    prompt_run_id = Column(String(36))
    lookbook_task_id = Column(String(36))
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
