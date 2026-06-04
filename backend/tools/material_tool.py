import json
import os
from database import SessionLocal
from models import Material
from services.thumbnail_service import ensure_material_thumbnail

class MaterialTool:
    """素材管理工具"""

    @staticmethod
    def create(name: str, type: str, category: str, file_path: str, metadata: dict = None) -> str:
        """创建素材记录"""
        db = SessionLocal()
        try:
            meta = metadata or {}
            material = Material(
                name=name,
                type=type,
                category=category,
                file_path=file_path,
                parent_dir=meta.get("parent_dir"),
                sub_category=meta.get("sub_category"),
                outfit_set=meta.get("outfit_set"),
                metadata_json=json.dumps(meta, ensure_ascii=False) if meta else None,
            )
            db.add(material)
            db.commit()
            db.refresh(material)
            material_id = material.id
        finally:
            db.close()

        if file_path and os.path.isfile(file_path):
            ensure_material_thumbnail(material_id, file_path)
        return material_id

    @staticmethod
    def get(material_id: str) -> dict:
        """获取素材"""
        db = SessionLocal()
        try:
            material = db.query(Material).filter(Material.id == material_id).first()
            if not material:
                return None
            return MaterialTool._to_dict(material)
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
            return [MaterialTool._to_dict(m) for m in materials]
        finally:
            db.close()

    @staticmethod
    def _to_dict(material: Material) -> dict:
        meta = json.loads(material.metadata_json) if material.metadata_json else {}
        return {
            "id": material.id,
            "name": material.name,
            "type": material.type,
            "category": material.category,
            "file_path": material.file_path,
            "thumbnail_path": material.thumbnail_path,
            "parent_dir": material.parent_dir or meta.get("parent_dir"),
            "sub_category": material.sub_category or meta.get("sub_category"),
            "outfit_set": material.outfit_set or meta.get("outfit_set"),
            "sub_category": material.sub_category or meta.get("sub_category"),
            "shoot_type": material.sub_category or meta.get("sub_category"),
            "metadata": meta,
        }
