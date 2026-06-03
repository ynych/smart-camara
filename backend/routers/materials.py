import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from sqlalchemy.orm import Session
from database import get_db
from models import Material
from tools.file_tool import FileTool
from tools.material_tool import MaterialTool
from config import UPLOADS_DIR

router = APIRouter(prefix="/api/materials", tags=["素材管理"])


@router.get("")
def list_materials(category: str = None, db: Session = Depends(get_db)):
    """获取素材列表"""
    query = db.query(Material)
    if category:
        query = query.filter(Material.category == category)
    materials = query.order_by(Material.created_at.desc()).all()
    return {
        "materials": [
            {
                "id": m.id,
                "name": m.name,
                "type": m.type,
                "category": m.category,
                "file_path": m.file_path,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in materials
        ]
    }


@router.post("/upload")
def upload_material(
    files: list[UploadFile] = File(...),
    category: str = Form("clothing"),
    name: str = Form(None),
    db: Session = Depends(get_db),
):
    """上传素材"""
    results = []
    for file in files:
        content = file.file.read()
        file_path = FileTool.save_upload(content, file.filename)
        mid = MaterialTool.create(
            name=name or file.filename,
            type="upload",
            category=category,
            file_path=file_path,
        )
        results.append({"id": mid, "name": file.filename, "file_path": file_path})
    return {"message": f"上传{len(results)}个素材", "materials": results}


@router.delete("/{material_id}")
def delete_material(material_id: str, db: Session = Depends(get_db)):
    """删除素材"""
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="素材不存在")
    if material.file_path and os.path.exists(material.file_path):
        os.remove(material.file_path)
    db.delete(material)
    db.commit()
    return {"message": "已删除"}


@router.get("/scan")
def scan_default_materials(db: Session = Depends(get_db)):
    """扫描默认素材目录，将已有文件导入为素材"""
    if not os.path.exists(UPLOADS_DIR):
        return {"message": "上传目录不存在", "imported": 0}

    imported = 0
    existing_paths = set()
    # 获取数据库中已有的素材路径
    existing_materials = db.query(Material).all()
    for m in existing_materials:
        if m.file_path:
            existing_paths.add(m.file_path)

    for filename in os.listdir(UPLOADS_DIR):
        file_path = os.path.join(UPLOADS_DIR, filename)
        if os.path.isfile(file_path) and file_path not in existing_paths:
            # 根据文件名推断分类
            category = "clothing"
            lower_name = filename.lower()
            if "model" in lower_name or "模特" in lower_name:
                category = "model"
            elif "scene" in lower_name or "场景" in lower_name:
                category = "scene"

            MaterialTool.create(
                name=filename,
                type="upload",
                category=category,
                file_path=file_path,
            )
            imported += 1

    return {"message": f"扫描完成，导入{imported}个素材", "imported": imported}
