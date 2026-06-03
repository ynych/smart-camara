import os
import httpx
from openai import AsyncOpenAI


class Image2Service:
    """OpenAI image2 API 封装服务"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.environ.get("OPENAI_API_KEY", "")
        )
        self.model = "gpt-image-1"

    def _map_size(self, size: str) -> str:
        """将业务尺寸映射为 API 尺寸"""
        size_map = {
            "1:1": "1024x1024",
            "3:4": "1024x1536",
            "9:16": "1024x1536",
        }
        return size_map.get(size, "1024x1024")

    async def generate_image(
        self, image_path: str, prompt: str, size: str, n: int, quality: str = "high"
    ) -> list[str]:
        """
        使用 OpenAI images.edit() 方法生成图片

        Args:
            image_path: 输入图片的本地路径
            prompt: 提示词
            size: 业务尺寸 (1:1, 3:4, 9:16)
            n: 生成数量
            quality: 图片质量

        Returns:
            生成的图片 URL 列表
        """
        api_size = self._map_size(size)

        with open(image_path, "rb") as image_file:
            response = await self.client.images.edit(
                model=self.model,
                image=image_file,
                prompt=prompt,
                size=api_size,
                n=n,
                quality=quality,
            )

        urls = []
        for item in response.data:
            urls.append(item.url)

        return urls

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

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(response.content)

        return save_path
