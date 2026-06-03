import os
import uuid
import shutil
from config import UPLOADS_DIR, GENERATED_DIR

class FileTool:
    """文件存储工具"""

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
