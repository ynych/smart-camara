import base64
import os
import httpx
from config import get_image_api_config, CONTENT_DIR, ASSETS_DIR
from content_dirs import rewrite_content_path

class ImageTool:
    """生图API调用工具 - 支持文生图和图生图（含多图融合）"""

    # 业务比例 -> Seedream 2K 推荐像素（见火山文档附表）
    SIZE_MAP = {
        "1:1": "2048x2048",
        "3:4": "1728x2304",
        "9:16": "1440x2560",
        "4:3": "2304x1728",
        "16:9": "2560x1440",
    }

    @staticmethod
    def resolve_api_size(size: str = "3:4") -> str:
        """将业务尺寸（1:1、3:4 等）转为 API size 字符串。"""
        if not size:
            return ImageTool.SIZE_MAP["3:4"]
        normalized = size.strip()
        if "x" in normalized and normalized[0].isdigit():
            return normalized
        return ImageTool.SIZE_MAP.get(normalized, ImageTool.SIZE_MAP["3:4"])

    @staticmethod
    def normalize_storage_path(path: str | None) -> str | None:
        """将跨机器/历史绝对路径归一化为当前环境的 content 或 assets 路径。"""
        if not path:
            return path
        normalized = path.replace("\\", "/").strip()
        if "/content/" in normalized:
            suffix = rewrite_content_path(normalized.split("/content/", 1)[1])
            return os.path.join(CONTENT_DIR, suffix)
        if "/assets/" in normalized:
            suffix = normalized.split("/assets/", 1)[1]
            return os.path.join(ASSETS_DIR, suffix)
        rel = normalized.lstrip("/")
        if rel.startswith("content/"):
            suffix = rewrite_content_path(rel[len("content/"):])
            return os.path.join(CONTENT_DIR, suffix)
        if rel.startswith("assets/"):
            return os.path.join(ASSETS_DIR, rel[len("assets/"):])
        return path

    @staticmethod
    def resolve_image_path(image_path: str) -> str | None:
        """解析素材/生成图路径（支持绝对路径、content 相对路径）。"""
        if not image_path:
            return None
        raw = ImageTool.normalize_storage_path(image_path.strip()) or ""
        if os.path.isfile(raw):
            return raw
        candidates = [
            os.path.join(CONTENT_DIR, raw),
            os.path.join(ASSETS_DIR, raw),
        ]
        if not os.path.isabs(raw):
            repo_root = os.path.dirname(CONTENT_DIR)
            candidates.append(os.path.join(repo_root, raw.lstrip("/")))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    @staticmethod
    def _image_to_base64(image_path: str) -> str:
        """将本地图片文件转为Base64编码（带data URI前缀）"""
        resolved = ImageTool.resolve_image_path(image_path)
        if not resolved:
            return None
        image_path = resolved

        # 获取文件扩展名确定MIME类型
        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
            ".gif": "image/gif",
        }
        mime_type = mime_map.get(ext, "image/png")

        with open(image_path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")

        return f"data:{mime_type};base64,{b64_data}"

    @staticmethod
    def _url_to_base64(url: str) -> str:
        """将URL图片转为Base64编码（带data URI前缀）"""
        if not url:
            return None
        # 如果已经是base64格式，直接返回
        if url.startswith("data:"):
            return url
        # 如果是本地路径，用文件转base64
        if url.startswith("/") or url.startswith("./") or not url.startswith("http"):
            return ImageTool._image_to_base64(url)
        # http(s) URL 原样传给 API
        return url

    @staticmethod
    async def generate(prompt: str, image_paths: list = None, size: str = "3:4") -> bytes:
        """调用火山引擎Seedream API生成图片，支持文生图和图生图

        Args:
            prompt: 提示词
            image_paths: 参考图路径列表（本地路径或URL），单图传["path"]，多图传["path1", "path2"]
                        本地路径会自动转为Base64编码
                        不传则为文生图
            size: 业务尺寸 1:1 / 3:4 / 9:16，或 API 像素串如 1728x2304

        Returns:
            图片二进制内容
        """
        config = get_image_api_config()
        api_size = ImageTool.resolve_api_size(size)

        payload = {
            "model": config["endpoint"],
            "prompt": prompt,
            "size": api_size,
            "response_format": "url",
            "watermark": False,
            "stream": False,
            "sequential_image_generation": "disabled",
        }

        # 如果有参考图，转为Base64后添加image参数
        if image_paths:
            b64_images = []
            skipped = []
            for path in image_paths:
                b64 = ImageTool._url_to_base64(path)
                if b64:
                    b64_images.append(b64)
                else:
                    skipped.append(path)
            if skipped:
                print(f"[ImageTool] 跳过无法读取的参考图: {skipped[:3]}")

            if b64_images:
                if len(b64_images) == 1:
                    payload["image"] = b64_images[0]
                else:
                    payload["image"] = b64_images

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                "https://ark.cn-beijing.volces.com/api/v3/images/generations",
                headers={
                    "Authorization": f"Bearer {config['api_key']}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

            if response.status_code != 200:
                error_detail = response.text[:500]
                try:
                    error_json = response.json()
                    error_detail = error_json.get("error", {}).get("message", error_detail)
                except Exception:
                    pass
                raise Exception(f"生图API调用失败({response.status_code}): {error_detail}")

            result = response.json()
            image_url = result["data"][0]["url"]

            # 下载图片
            img_response = await client.get(image_url)
            if img_response.status_code != 200:
                raise Exception("下载生成的图片失败")

            return img_response.content

    @staticmethod
    async def test_connection() -> dict:
        """测试API连接"""
        try:
            config = get_image_api_config()
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://ark.cn-beijing.volces.com/api/v3/images/generations",
                    headers={
                        "Authorization": f"Bearer {config['api_key']}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": config["endpoint"],
                        "prompt": "test",
                        "size": ImageTool.resolve_api_size("3:4"),
                        "response_format": "url",
                        "stream": False,
                    },
                )
                return {"success": response.status_code in [200, 400], "status_code": response.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}
