import json
from database import SessionLocal
from models import Material

class MaterialTool:
    """素材管理工具"""

    @staticmethod
    def create(name: str, type: str, category: str, file_path: str, metadata: dict = None) -> str:
        """创建素材记录"""
        db = SessionLocal()
        try:
            material = Material(
                name=name,
                type=type,
                category=category,
                file_path=file_path,
                metadata_json=json.dumps(metadata, ensure_ascii=False) if metadata else None,
            )
            db.add(material)
            db.commit()
            db.refresh(material)
            return material.id
        finally:
            db.close()

    @staticmethod
    def get(material_id: str) -> dict:
        """获取素材"""
        db = SessionLocal()
        try:
            material = db.query(Material).filter(Material.id == material_id).first()
            if not material:
                return None
            return {
                "id": material.id,
                "name": material.name,
                "type": material.type,
                "category": material.category,
                "file_path": material.file_path,
                "metadata": json.loads(material.metadata_json) if material.metadata_json else {},
            }
        finally:
            db.close()
