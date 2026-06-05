from fastapi import APIRouter, HTTPException
from database import SessionLocal
from models import ApiConfig
from tools.image_tool import ImageTool

router = APIRouter(prefix="/api/config", tags=["配置"])

@router.get("")
def get_config():
    """获取所有API配置"""
    db = SessionLocal()
    try:
        configs = db.query(ApiConfig).all()
        return {
            "configs": [
                {
                    "id": c.id,
                    "provider": c.provider,
                    "endpoint": c.endpoint,
                    "model": c.model,
                    "is_active": c.is_active,
                    "api_key_masked": c.api_key[:8] + "****" if c.api_key else "",
                }
                for c in configs
            ]
        }
    finally:
        db.close()

@router.put("")
def update_config(data: dict):
    """更新API配置"""
    db = SessionLocal()
    try:
        provider = data.get("provider")
        if not provider:
            raise HTTPException(status_code=400, detail="缺少provider")

        config = db.query(ApiConfig).filter(ApiConfig.provider == provider).first()
        if not config:
            config = ApiConfig(provider=provider)
            db.add(config)

        if data.get("api_key"):
            config.api_key = data["api_key"]
        if "endpoint" in data:
            config.endpoint = data["endpoint"]
        if "model" in data:
            config.model = data["model"]
        if "is_active" in data:
            config.is_active = 1 if data["is_active"] else 0

        db.commit()
        return {"message": "配置已更新"}
    finally:
        db.close()

@router.post("/test")
async def test_config():
    """测试API连接"""
    result = await ImageTool.test_connection()
    return result


@router.post("/test-chat")
async def test_chat_config():
    """测试对话模型（提示词 LLM）配置"""
    from agents.prompt_agent import probe_chat_config
    return await probe_chat_config()
