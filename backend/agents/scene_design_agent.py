import json
from database import SessionLocal
from models import StyleTemplate
from agents.base_agent import BaseAgent

class SceneDesignAgent(BaseAgent):
    """场景设计Agent - 推荐适合的Lookbook风格"""
    name = "scene_design"
    description = "根据服装特征推荐Lookbook风格"

    def get_styles(self) -> list:
        """获取所有可用风格"""
        db = SessionLocal()
        try:
            styles = db.query(StyleTemplate).order_by(StyleTemplate.sort_order).all()
            return [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "angles": json.loads(s.angles) if s.angles else [],
                    "variables": json.loads(s.variables) if s.variables else {},
                }
                for s in styles
            ]
        finally:
            db.close()

    def recommend(self, features: dict) -> list:
        """根据服装特征推荐风格（MVP: 返回所有风格）"""
        return self.get_styles()
