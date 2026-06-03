import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import engine, Base
from config import init_default_data, ASSETS_DIR
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
    init_default_data()
    yield

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

@app.get("/")
async def root():
    return {"message": "私人摄影团队 MVP API", "version": "1.0.0", "docs": "/docs"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
