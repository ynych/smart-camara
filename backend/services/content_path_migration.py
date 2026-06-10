"""Content 目录英文化：磁盘重命名 + SQLite 路径回填。"""

from __future__ import annotations

import json
import os
import sqlite3

from content_dirs import (
    DIR_CLOTHING,
    LEGACY_TOP_DIR_MAP,
    SHOOT_DIR_BY_TYPE,
    rewrite_content_path,
)
from config import CONTENT_DIR
from database import DB_PATH


def _rewrite(value: str | None) -> str | None:
    return rewrite_content_path(value)


def migrate_content_filesystem(content_dir: str | None = None) -> list[str]:
    """将遗留中文 content 子目录重命名为英文（幂等）。"""
    root = content_dir or CONTENT_DIR
    if not os.path.isdir(root):
        return []

    actions: list[str] = []
    for legacy, canonical in LEGACY_TOP_DIR_MAP.items():
        if legacy == canonical:
            continue
        src = os.path.join(root, legacy)
        dst = os.path.join(root, canonical)
        if os.path.isdir(src):
            if not os.path.exists(dst):
                os.rename(src, dst)
                actions.append(f"{legacy} -> {canonical}")
            elif legacy != canonical:
                # 英文目录已存在：合并文件后删除旧目录
                for name in os.listdir(src):
                    s = os.path.join(src, name)
                    d = os.path.join(dst, name)
                    if os.path.isdir(s) and not os.path.exists(d):
                        os.rename(s, d)
                    elif os.path.isfile(s) and not os.path.exists(d):
                        os.rename(s, d)
                if not os.listdir(src):
                    os.rmdir(src)
                    actions.append(f"merged {legacy} into {canonical}")

    clothing = os.path.join(root, DIR_CLOTHING)
    if os.path.isdir(clothing):
        for outfit in os.listdir(clothing):
            outfit_path = os.path.join(clothing, outfit)
            if not os.path.isdir(outfit_path):
                continue
            for legacy_shoot, shoot_dir in SHOOT_DIR_BY_TYPE.items():
                src = os.path.join(outfit_path, legacy_shoot)
                dst = os.path.join(outfit_path, shoot_dir)
                if os.path.isdir(src) and not os.path.exists(dst):
                    os.rename(src, dst)
                    actions.append(f"{outfit}/{legacy_shoot} -> {shoot_dir}")

    return actions


def migrate_content_paths_in_db(db_path: str | None = None) -> int:
    """更新 materials / requirements 等表中的 content 路径。"""
    path = db_path or DB_PATH
    if not os.path.exists(path):
        return 0

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    updated = 0

    def touch(row_id: str, **fields):
        nonlocal updated
        sets = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(
            f"UPDATE materials SET {sets} WHERE id = ?",
            (*fields.values(), row_id),
        )
        updated += 1

    for row in conn.execute("SELECT id, file_path, thumbnail_path, parent_dir, metadata_json FROM materials"):
        changes = {}
        for col in ("file_path", "thumbnail_path", "parent_dir"):
            new_val = _rewrite(row[col])
            if new_val != row[col] and new_val is not None:
                changes[col] = new_val
        meta_raw = row["metadata_json"]
        if meta_raw:
            try:
                meta = json.loads(meta_raw)
            except (json.JSONDecodeError, TypeError):
                meta = None
            if isinstance(meta, dict):
                meta_changed = False
                if "parent_dir" in meta:
                    new_pd = _rewrite(meta.get("parent_dir"))
                    if new_pd != meta.get("parent_dir"):
                        meta["parent_dir"] = new_pd
                        meta_changed = True
                if meta_changed:
                    changes["metadata_json"] = json.dumps(meta, ensure_ascii=False)
        if changes:
            touch(row["id"], **changes)

    for row in conn.execute("SELECT id, reference_image_path FROM requirements WHERE reference_image_path IS NOT NULL"):
        new_path = _rewrite(row["reference_image_path"])
        if new_path != row["reference_image_path"]:
            conn.execute(
                "UPDATE requirements SET reference_image_path = ? WHERE id = ?",
                (new_path, row["id"]),
            )
            updated += 1

    conn.commit()
    conn.close()
    return updated


def run_content_path_migration() -> dict:
    """启动时执行：先磁盘、后数据库。"""
    fs_actions = migrate_content_filesystem()
    db_rows = migrate_content_paths_in_db()
    return {"filesystem": fs_actions, "db_rows_updated": db_rows}
