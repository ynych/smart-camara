import os
import uuid
import shutil
from config import UPLOADS_DIR, GENERATED_DIR, CONTENT_DIR

class FileTool:
    """文件存储工具"""

    @staticmethod
    def _safe_filename(name: str) -> str:
        base = os.path.basename(name or "image.jpg")
        return base.replace("..", "").strip() or "image.jpg"

    @staticmethod
    def save_content_material(
        file_content: bytes,
        original_filename: str,
        category: str,
        outfit_set: str = None,
        shoot_type: str = None,
    ) -> str:
        """保存到 content/ 目录结构，与扫描导入一致。"""
        filename = FileTool._safe_filename(original_filename)
        if category == "model":
            target_dir = os.path.join(CONTENT_DIR, "模特卡")
            parent_dir = "模特卡"
            outfit = None
            shoot = None
        elif category == "clothing":
            outfit = (outfit_set or "未分组").strip()
            shoot = (shoot_type or "时尚拍摄").strip()
            target_dir = os.path.join(CONTENT_DIR, "服装素材", outfit, shoot)
            parent_dir = f"服装素材/{outfit}"
        elif category in ("lookbook_ref", "reference"):
            target_dir = os.path.join(CONTENT_DIR, "lookbook参考")
            parent_dir = "lookbook参考"
            outfit = None
            shoot = None
        elif category in ("scene", "background"):
            target_dir = os.path.join(CONTENT_DIR, "场景素材")
            parent_dir = "场景素材"
            outfit = None
            shoot = None
        else:
            return FileTool.save_upload(file_content, original_filename)

        os.makedirs(target_dir, exist_ok=True)
        file_path = os.path.join(target_dir, filename)
        if os.path.exists(file_path):
            stem, ext = os.path.splitext(filename)
            file_path = os.path.join(target_dir, f"{stem}_{uuid.uuid4().hex[:6]}{ext}")
        with open(file_path, "wb") as f:
            f.write(file_content)
        return file_path

    @staticmethod
    def save_upload(file_content: bytes, original_filename: str = None) -> str:
        """保存用户上传的文件，返回文件路径"""
        ext = os.path.splitext(original_filename)[1] if original_filename else ".jpg"
        if not ext:
            ext = ".jpg"
        filename = f"{uuid.uuid4().hex[:12]}{ext}"
        file_path = os.path.join(UPLOADS_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(file_content)
        return file_path

    @staticmethod
    def save_generated(task_id: str, image_content: bytes, index: int) -> str:
        """保存AI生成的图片，返回文件路径"""
        task_dir = os.path.join(GENERATED_DIR, task_id)
        os.makedirs(task_dir, exist_ok=True)
        file_path = os.path.join(task_dir, f"image_{index + 1}.png")
        with open(file_path, "wb") as f:
            f.write(image_content)
        return file_path

    @staticmethod
    def get_generated_dir(task_id: str) -> str:
        """获取任务生成图片的目录"""
        return os.path.join(GENERATED_DIR, task_id)

    @staticmethod
    def delete_file(file_path: str):
        """删除文件"""
        if os.path.exists(file_path):
            os.remove(file_path)

    @staticmethod
    def file_exists(file_path: str) -> bool:
        """检查文件是否存在"""
        return os.path.exists(file_path)
