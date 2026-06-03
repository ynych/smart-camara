import httpx
from config import get_image_api_config

class ImageTool:
    """生图API调用工具"""

    @staticmethod
    async def generate(prompt: str, image_urls: list = None) -> bytes:
        """调用火山引擎API生成图片，支持文生图和图生图

        Args:
            prompt: 提示词
            image_urls: 参考图URL列表，单图传["url"]，多图传["url1", "url2"]，不传则为文生图

        Returns:
            图片二进制内容
        """
        config = get_image_api_config()

        payload = {
            "model": config["endpoint"],
            "prompt": prompt,
            "size": "2048x2048",
            "response_format": "url",
            "watermark": False,
            "stream": False,
        }

        # 如果有参考图，添加image参数（支持单图和多图）
        if image_urls:
            if len(image_urls) == 1:
                payload["image"] = image_urls[0]
            else:
                payload["image"] = image_urls

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
                error = response.json().get("error", {}).get("message", "Unknown error")
                raise Exception(f"生图API调用失败: {error}")

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
                        "size": "2048x2048",
                        "response_format": "url",
                        "stream": False,
                    },
                )
                return {"success": response.status_code in [200, 400], "status_code": response.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}
