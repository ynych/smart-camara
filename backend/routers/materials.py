import os
import json
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Material
from tools.file_tool import FileTool
from tools.material_tool import MaterialTool
from services.thumbnail_service import rebuild_missing_thumbnails
from services.material_sync import backfill_material_columns, normalize_shoot_type, SHOOT_TYPES
from config import UPLOADS_DIR, CONTENT_DIR

router = APIRouter(prefix="/api/materials", tags=["素材管理"])


def _material_item(m: Material) -> dict:
    meta = {}
    if m.metadata_json:
        try:
            meta = json.loads(m.metadata_json)
        except (json.JSONDecodeError, TypeError):
            pass
    outfit_set = m.outfit_set or meta.get("outfit_set") or "未分组"
    shoot_type = normalize_shoot_type(m.sub_category or meta.get("sub_category"))
    return {
        "id": m.id,
        "name": m.name,
        "type": m.type,
        "category": m.category,
        "file_path": m.file_path,
        "thumbnail_path": m.thumbnail_path,
        "parent_dir": m.parent_dir or meta.get("parent_dir"),
        "outfit_set": outfit_set,
        "sub_category": shoot_type,
        "shoot_type": shoot_type,
        "sub_type": shoot_type,
        "metadata": meta,
    }


def _build_grouped(materials: list, sections: set | None = None) -> dict:
    """按分组组织素材；sections 为 None 时返回全部。"""
    want = sections or {"model", "clothing", "refs", "scenes"}
    model_cards = []
    clothing_sets_map = {}
    lookbook_refs = []
    scenes = []

    for m in materials:
        item = _material_item(m)
        if m.category == "model" and "model" in want:
            model_cards.append(item)
        elif m.category == "clothing" and "clothing" in want:
            outfit_name = item["outfit_set"] or "未分组"
            sub_cat = normalize_shoot_type(item["shoot_type"])
            if outfit_name not in clothing_sets_map:
                clothing_sets_map[outfit_name] = {
                    "name": outfit_name,
                    "items": [],
                    "sub_groups": {"人台图": [], "平铺图": [], "时尚拍摄": []},
                    "人台图": [],
                    "平铺图": [],
                    "时尚拍摄": [],
                }
            item["sub_type"] = sub_cat
            clothing_sets_map[outfit_name]["items"].append(item)
            clothing_sets_map[outfit_name]["sub_groups"].setdefault(sub_cat, []).append(item)
            clothing_sets_map[outfit_name].setdefault(sub_cat, []).append(item)
        elif m.category == "lookbook_ref" and "refs" in want:
            lookbook_refs.append(item)
        elif m.category in ("scene", "background") and "scenes" in want:
            scenes.append(item)

    result = {}
    if "model" in want:
        result["model_cards"] = model_cards
        result["models"] = model_cards
    if "clothing" in want:
        result["clothing_sets"] = list(clothing_sets_map.values())
    if "refs" in want:
        result["lookbook_refs"] = lookbook_refs
    if "scenes" in want:
        result["scenes"] = scenes
        result["backgrounds"] = scenes
    return result


@router.get("")
def list_materials(category: str = None, db: Session = Depends(get_db)):
    """获取素材列表"""
    query = db.query(Material)
    if category == "reference":
        category = "lookbook_ref"
    if category == "background":
        category = "scene"
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
                "thumbnail_path": m.thumbnail_path,
                "metadata": json.loads(m.metadata_json) if m.metadata_json else {},
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in materials
        ]
    }


@router.post("/upload")
def upload_material(
    files: list[UploadFile] = File(...),
    category: str = Form("clothing"),
    outfit_set: str = Form(None),
    shoot_type: str = Form(None),
    db: Session = Depends(get_db),
):
    """上传素材到 content/ 目录并写入数据库。"""
    results = []
    if category == "reference":
        category = "lookbook_ref"
    if category == "background":
        category = "scene"
    if category == "clothing" and not outfit_set:
        raise HTTPException(status_code=400, detail="上传服装素材请填写服装套装名称")

    for file in files:
        content = file.file.read()
        if not content:
            continue
        file_path = FileTool.save_content_material(
            content,
            file.filename,
            category=category,
            outfit_set=outfit_set,
            shoot_type=shoot_type,
        )
        shoot = normalize_shoot_type(shoot_type) if category == "clothing" else None
        meta = {"parent_dir": "服装素材/" + outfit_set if outfit_set else None}
        if category == "clothing":
            meta = {
                "parent_dir": f"服装素材/{outfit_set}",
                "outfit_set": outfit_set,
                "sub_category": shoot,
            }
        elif category == "model":
            meta = {"parent_dir": "模特卡"}
        elif category == "lookbook_ref":
            meta = {"parent_dir": "lookbook参考"}
        elif category == "scene":
            meta = {"parent_dir": "场景素材"}

        mid = MaterialTool.create(
            name=file.filename,
            type="upload",
            category=category,
            file_path=file_path,
            metadata=meta,
        )
        from services.thumbnail_service import ensure_material_thumbnail
        ensure_material_thumbnail(mid, file_path)
        results.append({
            "id": mid,
            "name": file.filename,
            "file_path": file_path,
            "outfit_set": outfit_set,
            "shoot_type": shoot,
        })

    backfill_material_columns(db)
    return {"message": f"成功上传 {len(results)} 个素材", "materials": results, "count": len(results)}


@router.delete("/{material_id}")
def delete_material(material_id: str, db: Session = Depends(get_db)):
    """删除素材"""
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="素材不存在")
    if material.file_path and os.path.exists(material.file_path):
        os.remove(material.file_path)
    if material.thumbnail_path and os.path.exists(material.thumbnail_path):
        os.remove(material.thumbnail_path)
    db.delete(material)
    db.commit()
    return {"message": "已删除"}


@router.get("/scan")
def scan_default_materials(db: Session = Depends(get_db)):
    """扫描CONTENT_DIR内容素材目录，将已有文件导入为素材"""
    if not os.path.exists(CONTENT_DIR):
        return {"message": "内容素材目录不存在", "imported": 0}

    imported = 0
    existing_paths = set()
    existing_materials = db.query(Material).all()
    for m in existing_materials:
        if m.file_path:
            existing_paths.add(m.file_path)

    # 支持的图片扩展名
    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}

    def is_image(filename):
        return os.path.splitext(filename)[1].lower() in IMAGE_EXTS

    # 1. 扫描 content/模特卡/
    model_dir = os.path.join(CONTENT_DIR, "模特卡")
    if os.path.isdir(model_dir):
        for filename in os.listdir(model_dir):
            file_path = os.path.join(model_dir, filename)
            if os.path.isfile(file_path) and is_image(filename) and file_path not in existing_paths:
                MaterialTool.create(
                    name=filename,
                    type="upload",
                    category="model",
                    file_path=file_path,
                    metadata={"parent_dir": "模特卡"},
                )
                imported += 1

    # 2. 扫描 content/服装素材/
    clothing_dir = os.path.join(CONTENT_DIR, "服装素材")
    if os.path.isdir(clothing_dir):
        for outfit_name in os.listdir(clothing_dir):
            outfit_path = os.path.join(clothing_dir, outfit_name)
            if not os.path.isdir(outfit_path):
                continue
            # 检查是否有子目录（子分类）
            has_sub_dirs = any(
                os.path.isdir(os.path.join(outfit_path, d))
                for d in os.listdir(outfit_path)
            )
            if has_sub_dirs:
                # content/服装素材/{outfit_name}/{sub_category}/files
                for sub_name in os.listdir(outfit_path):
                    sub_path = os.path.join(outfit_path, sub_name)
                    if not os.path.isdir(sub_path):
                        continue
                    for filename in os.listdir(sub_path):
                        file_path = os.path.join(sub_path, filename)
                        if os.path.isfile(file_path) and is_image(filename) and file_path not in existing_paths:
                            MaterialTool.create(
                                name=filename,
                                type="upload",
                                category="clothing",
                                file_path=file_path,
                                metadata={
                                    "parent_dir": f"服装素材/{outfit_name}",
                                    "outfit_set": outfit_name,
                                    "sub_category": sub_name,
                                },
                            )
                            imported += 1
            else:
                # content/服装素材/{outfit_name}/files (直接文件)
                for filename in os.listdir(outfit_path):
                    file_path = os.path.join(outfit_path, filename)
                    if os.path.isfile(file_path) and is_image(filename) and file_path not in existing_paths:
                        MaterialTool.create(
                            name=filename,
                            type="upload",
                            category="clothing",
                            file_path=file_path,
                            metadata={
                                "parent_dir": f"服装素材/{outfit_name}",
                                "outfit_set": outfit_name,
                                "sub_category": "时尚拍摄",
                            },
                        )
                        imported += 1

    # 3. 扫描参考图、场景图/背景图
    simple_dirs = [
        ("lookbook参考", "lookbook_ref"),
        ("场景素材", "scene"),
        ("场景图", "scene"),
        ("背景素材", "scene"),
        ("背景图", "scene"),
    ]
    for dirname, category in simple_dirs:
        target_dir = os.path.join(CONTENT_DIR, dirname)
        if os.path.isdir(target_dir):
            for filename in os.listdir(target_dir):
                file_path = os.path.join(target_dir, filename)
                if os.path.isfile(file_path) and is_image(filename) and file_path not in existing_paths:
                    MaterialTool.create(
                        name=filename,
                        type="upload",
                        category=category,
                        file_path=file_path,
                        metadata={"parent_dir": dirname},
                    )
                    imported += 1

    backfilled = backfill_material_columns(db)
    thumbs = rebuild_missing_thumbnails(db)
    return {
        "message": f"扫描完成，导入{imported}个素材",
        "imported": imported,
        "count": imported,
        "thumbnails": thumbs,
        "backfilled": backfilled,
    }


@router.post("/thumbnails/rebuild")
def rebuild_thumbnails(db: Session = Depends(get_db)):
    """为全部素材补全/更新缩略图。"""
    count = rebuild_missing_thumbnails(db)
    return {"message": f"已生成/更新 {count} 个缩略图", "count": count}


@router.get("/grouped")
def get_grouped_materials(
    sections: str = Query(
        None,
        description="按需加载：model,clothing,refs,scenes（逗号分隔）；不传则返回全部",
    ),
    outfit_set: str = Query(None, description="按服装套装筛选，如 连衣裙"),
    shoot_type: str = Query(None, description="按拍摄类型筛选：人台图/平铺图/时尚拍摄"),
    db: Session = Depends(get_db),
):
    """获取按分组组织的素材，支持分步懒加载与筛选。"""
    backfill_material_columns(db)
    query = db.query(Material)
    if outfit_set:
        query = query.filter(
            (Material.outfit_set == outfit_set) | (Material.metadata_json.contains(outfit_set))
        )
    if shoot_type:
        st = normalize_shoot_type(shoot_type)
        query = query.filter(
            (Material.sub_category == st) | (Material.metadata_json.contains(st))
        )
    materials = query.all()
    section_set = None
    if sections:
        section_set = {s.strip() for s in sections.split(",") if s.strip()}
    result = _build_grouped(materials, section_set)
    if "clothing" in (section_set or {"clothing"}):
        result["shoot_types"] = list(SHOOT_TYPES)
        result["outfit_sets"] = sorted({s["name"] for s in result.get("clothing_sets", [])})
    return result


@router.post("/check-conflict")
def check_conflict(data: dict):
    """检查服装搭配冲突"""
    items = data.get("items", [])
    conflicts = []

    # 收集所有服装的类型信息
    lower_items = []
    for item in items:
        name = item if isinstance(item, str) else item.get("name", "")
        lower_items.append(name.lower())

    # 检测多个下装
    bottom_keywords = ["裤子", "牛仔裤", "裙子", "短裤", "半裙", "长裤", "西裤", "休闲裤"]
    bottoms = []
    for name in lower_items:
        for kw in bottom_keywords:
            if kw in name:
                bottoms.append(name)
                break

    if len(bottoms) > 1:
        conflicts.append(f"检测到多个下装: {', '.join(bottoms)}")

    # 检测连体装+其他服装
    onesie_keywords = ["连衣裙", "连体裤", "连衣裤", " jumpsuit", "背带裤"]
    has_onesie = False
    other_clothing = []
    for name in lower_items:
        is_onesie = any(kw in name for kw in onesie_keywords)
        if is_onesie:
            has_onesie = True
        elif name:
            other_clothing.append(name)

    if has_onesie and other_clothing:
        conflicts.append(f"连体装与其他服装搭配冲突: 连体装 + {', '.join(other_clothing)}")

    return {
        "conflicts": conflicts,
        "has_conflict": len(conflicts) > 0,
    }
