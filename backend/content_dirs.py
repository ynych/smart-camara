"""Content 目录布局（磁盘上使用英文文件夹名）。"""

import os

DIR_MODEL_CARDS = "model-cards"
DIR_CLOTHING = "clothing"
DIR_LOOKBOOK_REFS = "lookbook-refs"
DIR_SCENES = "scenes"

# 顶层目录：旧中文名 -> 新英文名（扫描兼容 / 迁移）
LEGACY_TOP_DIR_MAP = {
    "模特卡": DIR_MODEL_CARDS,
    "服装素材": DIR_CLOTHING,
    "lookbook参考": DIR_LOOKBOOK_REFS,
    "场景素材": DIR_SCENES,
    "场景图": DIR_SCENES,
    "背景素材": DIR_SCENES,
    "背景图": DIR_SCENES,
}

SHOOT_DIR_BY_TYPE = {
    "人台图": "mannequin",
    "平铺图": "flat-lay",
    "时尚拍摄": "fashion-shot",
}
SHOOT_TYPE_BY_DIR = {v: k for k, v in SHOOT_DIR_BY_TYPE.items()}

# 路径片段替换（DB / 历史绝对路径归一化）
CONTENT_PATH_REWRITES = (
    ("模特卡/", f"{DIR_MODEL_CARDS}/"),
    ("模特卡", DIR_MODEL_CARDS),
    ("服装素材/", f"{DIR_CLOTHING}/"),
    ("lookbook参考/", f"{DIR_LOOKBOOK_REFS}/"),
    ("lookbook参考", DIR_LOOKBOOK_REFS),
    ("场景素材/", f"{DIR_SCENES}/"),
    ("场景素材", DIR_SCENES),
    ("/人台图/", "/mannequin/"),
    ("/平铺图/", "/flat-lay/"),
    ("/时尚拍摄/", "/fashion-shot/"),
    ("\\人台图\\", "\\mannequin\\"),
    ("\\平铺图\\", "\\flat-lay\\"),
    ("\\时尚拍摄\\", "\\fashion-shot\\"),
)

SCAN_SIMPLE_DIRS = (
    (DIR_LOOKBOOK_REFS, "lookbook_ref"),
    (DIR_SCENES, "scene"),
)


def rewrite_content_path(value: str | None) -> str | None:
    """将路径中的中文 content 片段替换为英文。"""
    if not value:
        return value
    out = value
    for old, new in CONTENT_PATH_REWRITES:
        out = out.replace(old, new)
    return out


def shoot_type_to_dir(shoot_type: str | None) -> str:
    """业务拍摄类型 -> 磁盘子目录名。"""
    if not shoot_type:
        return SHOOT_DIR_BY_TYPE["时尚拍摄"]
    v = shoot_type.strip()
    if v in SHOOT_DIR_BY_TYPE:
        return SHOOT_DIR_BY_TYPE[v]
    if v in SHOOT_TYPE_BY_DIR:
        return v
    aliases = {
        "mannequin": "mannequin",
        "flat_lay": "flat-lay",
        "flat-lay": "flat-lay",
        "fashion_shot": "fashion-shot",
        "fashion-shot": "fashion-shot",
    }
    return aliases.get(v, SHOOT_DIR_BY_TYPE["时尚拍摄"])


def shoot_type_from_dir(dirname: str) -> str:
    """磁盘子目录名 -> 业务拍摄类型（中文）。"""
    d = (dirname or "").strip()
    if d in SHOOT_TYPE_BY_DIR:
        return SHOOT_TYPE_BY_DIR[d]
    if d in SHOOT_DIR_BY_TYPE:
        return d
    from services.material_sync import normalize_shoot_type

    return normalize_shoot_type(d)


def parent_dir_for(category: str, outfit_set: str | None = None) -> str:
    if category == "model":
        return DIR_MODEL_CARDS
    if category == "clothing" and outfit_set:
        return f"{DIR_CLOTHING}/{outfit_set.strip()}"
    if category in ("lookbook_ref", "reference"):
        return DIR_LOOKBOOK_REFS
    if category in ("scene", "background"):
        return DIR_SCENES
    return ""


def resolve_top_dir(content_dir: str, canonical: str) -> str | None:
    """返回实际存在的顶层目录路径（优先英文，兼容旧中文）。"""
    primary = os.path.join(content_dir, canonical)
    if os.path.isdir(primary):
        return primary
    for legacy, mapped in LEGACY_TOP_DIR_MAP.items():
        if mapped == canonical:
            legacy_path = os.path.join(content_dir, legacy)
            if os.path.isdir(legacy_path):
                return legacy_path
    return None
