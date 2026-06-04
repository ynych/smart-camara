import os
import base64
import httpx
from openai import AsyncOpenAI


class Image2Service:
    """OpenAI image2 API 封装服务"""

    def __init__(self):
        self.client = None
        self.model = "gpt-image-1"

    def _client(self) -> AsyncOpenAI:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("缺少 OPENAI_API_KEY，无法调用 image2 生图")
        if self.client is None:
            self.client = AsyncOpenAI(api_key=api_key)
        return self.client

    def _map_size(self, size: str) -> str:
        """将业务尺寸映射为 API 尺寸"""
        size_map = {
            "1:1": "1024x1024",
            "3:4": "1024x1536",
            "9:16": "1024x1536",
        }
        return size_map.get(size, "1024x1024")

    async def generate_image(
        self, image_path=None, prompt: str = "", size: str = "3:4", n: int = 1, quality: str = "high"
    ) -> list[dict]:
        """
        使用 OpenAI images.edit() 方法生成图片

        Args:
            image_path: 输入图片的本地路径，支持字符串或路径列表
            prompt: 提示词
            size: 业务尺寸 (1:1, 3:4, 9:16)
            n: 生成数量
            quality: 图片质量

        Returns:
            生成结果列表，元素包含 url 或 b64_json
        """
        api_size = self._map_size(size)
        image_paths = []
        if isinstance(image_path, str) and image_path:
            image_paths = [image_path]
        elif isinstance(image_path, list):
            image_paths = [p for p in image_path if p]

        opened_files = []
        try:
            if image_paths:
                for path in image_paths:
                    if os.path.exists(path):
                        opened_files.append(open(path, "rb"))
                if not opened_files:
                    raise FileNotFoundError("没有可用的参考图片")
                response = await self._client().images.edit(
                    model=self.model,
                    image=opened_files if len(opened_files) > 1 else opened_files[0],
                    prompt=prompt,
                    size=api_size,
                    n=n,
                    quality=quality,
                )
            else:
                response = await self._client().images.generate(
                    model=self.model,
                    prompt=prompt,
                    size=api_size,
                    n=n,
                    quality=quality,
                )
        finally:
            for f in opened_files:
                f.close()

        results = []
        for item in response.data:
            results.append({
                "url": getattr(item, "url", None),
                "b64_json": getattr(item, "b64_json", None),
            })

        return results

    async def generate_image_bytes(
        self, image_paths: list[str], prompt: str, size: str, quality: str = "high"
    ) -> bytes:
        """生成单张图片并返回二进制内容。"""
        results = await self.generate_image(
            image_path=image_paths,
            prompt=prompt,
            size=size,
            n=1,
            quality=quality,
        )
        if not results:
            raise RuntimeError("image2 没有返回图片")
        first = results[0]
        if first.get("b64_json"):
            return base64.b64decode(first["b64_json"])
        if first.get("url"):
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.get(first["url"])
                response.raise_for_status()
                return response.content
        raise RuntimeError("image2 返回结果缺少 url 或 b64_json")

    async def download_image(self, url: str, save_path: str) -> str:
        """
        下载图片到本地

        Args:
            url: 图片 URL
            save_path: 保存路径

        Returns:
            本地文件路径
        """
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(url)
            response.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(response.content)

        return save_path
