import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import engine, Base
from config import init_default_data, ASSETS_DIR, CONTENT_DIR
from routers.admin import (
    agents_router,
    chat_sessions_router,
    golden_cases_router,
    golden_runs_router,
    harness_testcases_router,
    agent_runs_router,
    knowledge_nodes_router,
    knowledge_trees_router,
    pipeline_configs_router,
    prompt_packs_router,
    testcases_router,
    tool_defs_router,
)
from routers import lookbook, config, materials, harness, agent_runtime, harness_runtime, pipeline_versions, health
from routers import generation_packs, workflow_admin

# 加载 .env 文件
from pathlib import Path
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库和默认数据"""
    Base.metadata.create_all(bind=engine)
    migrate_db()
    init_default_data()
    _backfill_materials()
    from services.seed_admin_data import seed_admin_data
    seed_admin_data()
    from services.seed_workflow_data import seed_workflow_data
    seed_workflow_data()
    yield

def _backfill_materials():
    from database import SessionLocal
    from services.material_sync import backfill_material_columns
    db = SessionLocal()
    try:
        backfill_material_columns(db)
    finally:
        db.close()


def migrate_db():
    """使用raw sqlite3为已有表添加新列（兼容已有数据库）"""
    import sqlite3
    from database import DB_PATH
    if not os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    migrations = [
        ("materials", "parent_dir", "VARCHAR(255)"),
        ("materials", "sub_category", "VARCHAR(50)"),
        ("materials", "outfit_set", "VARCHAR(255)"),
        ("lookbook_tasks", "quantity", "INTEGER DEFAULT 4"),
        ("lookbook_tasks", "size", "VARCHAR(20) DEFAULT '3:4'"),
        ("lookbook_tasks", "selected_materials", "TEXT"),
        ("lookbook_tasks", "acceptance_criteria", "TEXT"),
        ("lookbook_tasks", "prompt_overrides", "TEXT"),
        ("requirements", "reference_image_path", "VARCHAR(500)"),
        ("requirements", "prompt_overrides", "TEXT"),
        ("lookbook_tasks", "generation_round", "INTEGER DEFAULT 1"),
        ("generated_images", "generation_round", "INTEGER DEFAULT 1"),
        ("generated_images", "parent_image_id", "VARCHAR(36)"),
        ("generated_images", "prompt_modules_json", "TEXT"),
        ("agent_chat_sessions", "last_run_id", "VARCHAR(36)"),
        ("harness_test_cases", "last_run_id", "VARCHAR(36)"),
        ("harness_test_cases", "source_image_id", "VARCHAR(36)"),
        ("harness_test_cases", "source_evaluation_id", "VARCHAR(36)"),
        ("harness_test_cases", "human_eval_json", "TEXT"),
        ("prompt_run_records", "studio_task_id", "VARCHAR(36)"),
    ]
    for table, column, col_type in migrations:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        except sqlite3.OperationalError:
            pass  # 列已存在，忽略
    conn.commit()
    conn.close()
    # 补齐 ORM 新增表（如 lookbook_studio_tasks）
    from models import LookbookStudioTask  # noqa: F401
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="私人摄影团队 MVP",
    description="电商Lookbook效果图生成平台",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(lookbook.router)
app.include_router(config.router)
app.include_router(materials.router)
app.include_router(harness.router)
app.include_router(harness.eval_router)
app.include_router(harness.image_router)
app.include_router(agents_router)
app.include_router(testcases_router)
app.include_router(knowledge_trees_router)
app.include_router(knowledge_nodes_router)
app.include_router(prompt_packs_router)
app.include_router(pipeline_configs_router)
app.include_router(tool_defs_router)
app.include_router(golden_cases_router)
app.include_router(golden_runs_router)
app.include_router(chat_sessions_router)
app.include_router(harness_testcases_router)
app.include_router(agent_runs_router)
app.include_router(agent_runtime.router)
app.include_router(harness_runtime.router)
app.include_router(pipeline_versions.router)
app.include_router(health.router)
app.include_router(generation_packs.router)
app.include_router(workflow_admin.router)

# 静态文件
os.makedirs(ASSETS_DIR, exist_ok=True)
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# 内容素材静态文件
if os.path.exists(CONTENT_DIR):
    app.mount("/content", StaticFiles(directory=CONTENT_DIR), name="content")

@app.get("/")
async def root():
    return {"message": "私人摄影团队 MVP API", "version": "1.0.0", "docs": "/docs"}

@app.get("/health")
async def health_legacy():
    return {"status": "healthy"}
