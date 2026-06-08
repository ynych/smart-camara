import json
import os
from database import SessionLocal
from models import ApiConfig, StyleTemplate
import uuid

# 从环境变量读取配置，或使用占位符
DEFAULT_VOLCANO_CONFIG = {
    "provider": "volcano",
    "api_key": os.environ.get("VOLCANO_API_KEY", ""),
    "endpoint": os.environ.get("VOLCANO_ENDPOINT", ""),
    "model": os.environ.get("VOLCANO_MODEL", "seedream"),
    "is_active": 1,
}

# 文件存储根目录
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
UPLOADS_DIR = os.path.join(ASSETS_DIR, "uploads")
GENERATED_DIR = os.path.join(ASSETS_DIR, "generated")
THUMBS_DIR = os.path.join(ASSETS_DIR, "thumbs")

# 内容素材目录
CONTENT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content")

for d in [ASSETS_DIR, UPLOADS_DIR, GENERATED_DIR, THUMBS_DIR]:
    os.makedirs(d, exist_ok=True)

def get_chat_api_config():
    """文本大模型配置：env 优先，无效 ark- 时回退 DB；缺项从 DB / 生图 Key 补齐。"""
    chat_endpoint = (
        os.environ.get("VOLCANO_CHAT_ENDPOINT")
        or os.environ.get("VOLCANO_LLM_ENDPOINT")
        or ""
    ).strip()
    try:
        from agents.prompt_agent import validate_chat_endpoint_id
        if validate_chat_endpoint_id(chat_endpoint):
            chat_endpoint = ""
    except ImportError:
        pass
    chat_key = (
        os.environ.get("VOLCANO_CHAT_API_KEY")
        or os.environ.get("ARK_API_KEY")
        or ""
    ).strip()

    db = SessionLocal()
    try:
        chat_cfg = db.query(ApiConfig).filter(ApiConfig.provider == "volcano_chat").first()
        volcano_cfg = db.query(ApiConfig).filter(ApiConfig.provider == "volcano").first()
        if chat_cfg:
            if not chat_endpoint and chat_cfg.endpoint:
                chat_endpoint = chat_cfg.endpoint.strip()
            if not chat_key and chat_cfg.api_key:
                chat_key = chat_cfg.api_key.strip()
        if not chat_key:
            chat_key = (os.environ.get("VOLCANO_API_KEY") or "").strip()
        if not chat_key and volcano_cfg and volcano_cfg.api_key:
            chat_key = volcano_cfg.api_key.strip()
    finally:
        db.close()

    try:
        from agents.prompt_agent import validate_chat_endpoint_id
        if validate_chat_endpoint_id(chat_endpoint):
            chat_endpoint = ""
    except ImportError:
        pass

    if chat_endpoint and chat_key:
        return {
            "provider": "volcano_chat",
            "api_key": chat_key,
            "endpoint": chat_endpoint,
            "model": os.environ.get("VOLCANO_CHAT_MODEL", "doubao"),
        }
    return {"provider": "volcano_chat", "api_key": "", "endpoint": "", "model": ""}


def get_image_api_config():
    """获取当前激活的生图API配置"""
    db = SessionLocal()
    try:
        config = db.query(ApiConfig).filter(ApiConfig.is_active == 1).first()
        if config:
            return {
                "provider": config.provider,
                "api_key": config.api_key,
                "endpoint": config.endpoint,
                "model": config.model,
            }
        return DEFAULT_VOLCANO_CONFIG
    finally:
        db.close()

def init_default_data():
    """初始化默认数据（风格模板+API配置）"""
    db = SessionLocal()
    try:
        # 初始化API配置
        existing = db.query(ApiConfig).filter(ApiConfig.provider == "volcano").first()
        if not existing:
            config = ApiConfig(**DEFAULT_VOLCANO_CONFIG)
            db.add(config)

        chat_endpoint = (
            os.environ.get("VOLCANO_CHAT_ENDPOINT")
            or os.environ.get("VOLCANO_LLM_ENDPOINT")
            or ""
        ).strip()
        volcano_row = db.query(ApiConfig).filter(ApiConfig.provider == "volcano").first()
        chat_key = (
            os.environ.get("VOLCANO_CHAT_API_KEY")
            or os.environ.get("ARK_API_KEY")
            or os.environ.get("VOLCANO_API_KEY")
            or (volcano_row.api_key if volcano_row else "")
        ).strip()
        chat_existing = db.query(ApiConfig).filter(ApiConfig.provider == "volcano_chat").first()
        if chat_endpoint:
            from agents.prompt_agent import validate_chat_endpoint_id
            if validate_chat_endpoint_id(chat_endpoint):
                chat_endpoint = ""
        if not chat_existing and chat_endpoint and chat_key:
            db.add(ApiConfig(
                provider="volcano_chat",
                api_key=chat_key,
                endpoint=chat_endpoint,
                model=os.environ.get("VOLCANO_CHAT_MODEL", "doubao"),
                is_active=1,
            ))
        elif chat_existing:
            from agents.prompt_agent import validate_chat_endpoint_id
            if chat_existing.endpoint and validate_chat_endpoint_id(chat_existing.endpoint):
                chat_existing.endpoint = ""
            if chat_endpoint and chat_existing.endpoint != chat_endpoint:
                if not validate_chat_endpoint_id(chat_endpoint):
                    chat_existing.endpoint = chat_endpoint
            if chat_key and not chat_existing.api_key:
                chat_existing.api_key = chat_key
        elif chat_endpoint and volcano_row and volcano_row.api_key:
            db.add(ApiConfig(
                provider="volcano_chat",
                api_key=volcano_row.api_key,
                endpoint=chat_endpoint,
                model=os.environ.get("VOLCANO_CHAT_MODEL", "doubao"),
                is_active=1,
            ))

        # 初始化风格模板
        if db.query(StyleTemplate).count() == 0:
            styles = get_default_styles()
            for style in styles:
                db.add(StyleTemplate(**style))

        db.commit()
    finally:
        db.close()

def get_default_styles():
    """获取默认的3种Lookbook风格模板"""
    return [
        {
            "id": "street",
            "name": "街拍风格",
            "description": "城市街道、咖啡馆、公园等户外场景，适合种草图和社交媒体",
            "prompt_template": "一位{model_desc}模特，穿着{clothing_desc}，{scene_desc}，{angle_desc}，柔和自然光，专业补光，85mm镜头浅景深，高清8K细节丰富，专业电商摄影风格，时尚街拍",
            "variables": json.dumps({
                "model_desc": "优雅的亚洲女性",
                "clothing_desc": "白色简约连衣裙",
                "scene_desc": "走在城市街道上，午后阳光洒落",
                "angle_desc": "正面全身展示"
            }, ensure_ascii=False),
            "angles": json.dumps([
                {"name": "正面全身", "desc": "正面全身展示，展现服装整体效果"},
                {"name": "侧面展示", "desc": "侧面45度角，展示服装线条和剪裁"},
                {"name": "细节特写", "desc": "面料和工艺细节特写"},
                {"name": "搭配场景", "desc": "搭配包包和鞋子的街拍场景"}
            ], ensure_ascii=False),
            "sort_order": 0,
        },
        {
            "id": "studio",
            "name": "棚拍风格",
            "description": "纯白/灰色背景，专业灯光，适合商品主图和详情页",
            "prompt_template": "一位{model_desc}模特，穿着{clothing_desc}，{scene_desc}，{angle_desc}，专业摄影棚灯光，柔和均匀，高清8K细节丰富，商业电商摄影，干净简约风格",
            "variables": json.dumps({
                "model_desc": "优雅的亚洲女性",
                "clothing_desc": "白色简约连衣裙",
                "scene_desc": "站在纯白色背景前",
                "angle_desc": "正面全身展示"
            }, ensure_ascii=False),
            "angles": json.dumps([
                {"name": "正面全身", "desc": "正面全身展示，展现服装整体效果"},
                {"name": "侧面展示", "desc": "侧面45度角，展示服装轮廓"},
                {"name": "细节特写", "desc": "面料质地和工艺细节"},
                {"name": "背面展示", "desc": "背面设计展示"}
            ], ensure_ascii=False),
            "sort_order": 1,
        },
        {
            "id": "natural",
            "name": "自然风格",
            "description": "户外自然场景，花园、海边等，适合品牌形象和Lookbook画册",
            "prompt_template": "一位{model_desc}模特，穿着{clothing_desc}，{scene_desc}，{angle_desc}，自然柔和光线，温暖色调，85mm镜头浅景深，高清8K，品牌Lookbook画册风格，优雅自然",
            "variables": json.dumps({
                "model_desc": "优雅的亚洲女性",
                "clothing_desc": "白色简约连衣裙",
                "scene_desc": "站在花园中，阳光透过树叶洒落",
                "angle_desc": "正面全身展示"
            }, ensure_ascii=False),
            "angles": json.dumps([
                {"name": "正面全身", "desc": "正面全身展示，自然姿态"},
                {"name": "侧面展示", "desc": "侧面自然转身，展示服装动态"},
                {"name": "细节特写", "desc": "面料在自然光下的质感"},
                {"name": "场景融入", "desc": "人物与自然环境的和谐融合"}
            ], ensure_ascii=False),
            "sort_order": 2,
        },
    ]
