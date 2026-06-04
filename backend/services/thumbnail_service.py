import hashlib
import os
from config import THUMBS_DIR

try:
    from PIL import Image
except ImportError:
    Image = None

THUMB_MAX_EDGE = 320
THUMB_QUALITY = 82


def _thumb_filename(file_path: str) -> str:
    digest = hashlib.sha256(os.path.abspath(file_path).encode("utf-8")).hexdigest()[:20]
    return f"{digest}.jpg"


def ensure_thumbnail(file_path: str, force: bool = False) -> str | None:
    """为本地图片生成缩略图，返回缩略图绝对路径。"""
    if not file_path or not os.path.isfile(file_path):
        return None
    if Image is None:
        return None

    os.makedirs(THUMBS_DIR, exist_ok=True)
    thumb_name = _thumb_filename(file_path)
    thumb_path = os.path.join(THUMBS_DIR, thumb_name)

    if not force and os.path.exists(thumb_path):
        src_mtime = os.path.getmtime(file_path)
        if os.path.getmtime(thumb_path) >= src_mtime:
            return thumb_path

    try:
        with Image.open(file_path) as img:
            img = img.convert("RGB")
            img.thumbnail((THUMB_MAX_EDGE, THUMB_MAX_EDGE), Image.Resampling.LANCZOS)
            img.save(thumb_path, "JPEG", quality=THUMB_QUALITY, optimize=True)
        return thumb_path
    except Exception as e:
        print(f"[ThumbnailService] 生成失败 {file_path}: {e}")
        return None


def ensure_material_thumbnail(material_id: str, file_path: str, force: bool = False) -> str | None:
    """生成缩略图并写回 materials.thumbnail_path。"""
    thumb_path = ensure_thumbnail(file_path, force=force)
    if not thumb_path:
        return None

    from database import SessionLocal
    from models import Material

    db = SessionLocal()
    try:
        material = db.query(Material).filter(Material.id == material_id).first()
        if material:
            material.thumbnail_path = thumb_path
            db.commit()
        return thumb_path
    finally:
        db.close()


def rebuild_missing_thumbnails(db) -> int:
    """为缺少缩略图的素材批量生成。"""
    from models import Material

    count = 0
    materials = db.query(Material).all()
    for m in materials:
        if not m.file_path or not os.path.isfile(m.file_path):
            continue
        if m.thumbnail_path and os.path.isfile(m.thumbnail_path):
            src_mtime = os.path.getmtime(m.file_path)
            if os.path.getmtime(m.thumbnail_path) >= src_mtime:
                continue
        if ensure_material_thumbnail(m.id, m.file_path, force=True):
            count += 1
    return count
