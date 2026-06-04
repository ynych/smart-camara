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

    @staticmethod
    def get_by_ids(ids: list) -> list:
        """批量获取素材"""
        if not ids:
            return []
        db = SessionLocal()
        try:
            materials = db.query(Material).filter(Material.id.in_(ids)).all()
            return [
                {
                    "id": m.id,
                    "name": m.name,
                    "type": m.type,
                    "category": m.category,
                    "file_path": m.file_path,
                    "metadata": json.loads(m.metadata_json) if m.metadata_json else {},
                }
                for m in materials
            ]
        finally:
            db.close()
