import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import engine, Base
from config import init_default_data, ASSETS_DIR, CONTENT_DIR
from routers import lookbook, config, materials

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
    yield

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
    ]
    for table, column, col_type in migrations:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        except sqlite3.OperationalError:
            pass  # 列已存在，忽略
    conn.commit()
    conn.close()

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
async def health():
    return {"status": "healthy"}
