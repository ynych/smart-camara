import json
from database import SessionLocal
from models import StyleTemplate

class PromptTool:
    """提示词管理工具"""

    @staticmethod
    def build_prompt(template_id: str, variables: dict, angle_desc: str = None) -> str:
        """根据模板和变量构建提示词"""
        db = SessionLocal()
        try:
            style = db.query(StyleTemplate).filter(StyleTemplate.id == template_id).first()
            if not style:
                return ""

            template = style.prompt_template
            # 替换变量
            for key, value in variables.items():
                template = template.replace(f"{{{key}}}", str(value))

            # 如果有角度描述，替换angle_desc
            if angle_desc:
                template = template.replace("{angle_desc}", angle_desc)

            return template
        finally:
            db.close()

    @staticmethod
    def get_style_variables(template_id: str) -> dict:
        """获取风格的默认变量"""
        db = SessionLocal()
        try:
            style = db.query(StyleTemplate).filter(StyleTemplate.id == template_id).first()
            if style and style.variables:
                return json.loads(style.variables)
            return {}
        finally:
            db.close()

    @staticmethod
    def get_style_angles(template_id: str) -> list:
        """获取风格的视角列表"""
        db = SessionLocal()
        try:
            style = db.query(StyleTemplate).filter(StyleTemplate.id == template_id).first()
            if style and style.angles:
                return json.loads(style.angles)
            return []
        finally:
            db.close()
