import json
from models import Material

SHOOT_TYPES = ("人台图", "平铺图", "时尚拍摄")


def normalize_shoot_type(value: str | None) -> str:
    if not value:
        return "未分类"
    v = value.strip()
    if v in SHOOT_TYPES:
        return v
    mapping = {
        "mannequin": "人台图",
        "flat_lay": "平铺图",
        "flat-lay": "平铺图",
        "fashion_shot": "时尚拍摄",
        "fashion-shot": "时尚拍摄",
    }
    return mapping.get(v, v)


def backfill_material_columns(db) -> int:
    """从 metadata_json 回填 outfit_set、sub_category（拍摄类型）列。"""
    updated = 0
    for m in db.query(Material).all():
        meta = {}
        if m.metadata_json:
            try:
                meta = json.loads(m.metadata_json)
            except (json.JSONDecodeError, TypeError):
                pass

        changed = False
        outfit = m.outfit_set or meta.get("outfit_set")
        shoot = m.sub_category or meta.get("sub_category")
        if outfit and m.outfit_set != outfit:
            m.outfit_set = outfit
            changed = True
        if shoot:
            shoot = normalize_shoot_type(shoot)
            if m.sub_category != shoot:
                m.sub_category = shoot
                changed = True
        if changed:
            updated += 1
    if updated:
        db.commit()
    return updated
