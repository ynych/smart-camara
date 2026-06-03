#!/usr/bin/env python3
"""测试火山引擎图片生成功能"""
import os
import uuid
import httpx
import asyncio

# 火山引擎 API 配置（从环境变量读取）
API_KEY = os.environ.get("VOLCANO_API_KEY", "")
ENDPOINT = os.environ.get("VOLCANO_ENDPOINT", "")

async def generate_image(prompt: str, category: str = "model"):
    """使用火山引擎生成图片"""
    
    print(f"正在生成 {category} 图片...")
    print(f"提示词: {prompt}")
    
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                "https://ark.cn-beijing.volces.com/api/v3/images/generations",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": ENDPOINT,
                    "prompt": prompt,
                    "size": "2048x2048",
                    "response_format": "url",
                    "watermark": False,
                    "stream": False,
                },
            )

            if response.status_code != 200:
                print(f"API调用失败: {response.status_code}")
                print(f"响应: {response.text}")
                return None

            result = response.json()
            image_url = result["data"][0]["url"]
            print(f"图片生成成功: {image_url}")

            # 下载图片
            img_response = await client.get(image_url)
            if img_response.status_code != 200:
                print("下载图片失败")
                return None

            # 保存图片
            file_id = str(uuid.uuid4())[:8]
            save_dir = os.path.join("/sessions/6a1e0eff2eaefdd5db2039dc/workspace/backend/uploads", category)
            os.makedirs(save_dir, exist_ok=True)
            file_path = os.path.join(save_dir, f"{file_id}.png")

            with open(file_path, "wb") as f:
                f.write(img_response.content)

            print(f"图片已保存: {file_path}")
            return file_path

    except httpx.TimeoutException:
        print("请求超时")
        return None
    except Exception as e:
        print(f"生成失败: {str(e)}")
        return None


async def main():
    """生成测试素材"""
    
    # 生成模特素材
    model_prompts = [
        "一位优雅的亚洲女性时尚模特，穿着简约白色连衣裙，站在摄影棚内，柔和的自然光，专业时尚摄影风格，高清画质",
        "一位年轻亚洲男性模特，穿着休闲西装，现代简约风格，专业摄影棚拍摄，柔和光线，高清画质",
    ]
    
    # 生成场景素材
    scene_prompts = [
        "现代简约风格的室内摄影棚，白色背景墙，专业摄影灯光设备，干净明亮的空间，适合服装拍摄",
        "户外自然场景，城市街道背景，柔和的午后阳光，适合时尚街拍风格",
    ]
    
    print("=" * 50)
    print("开始生成模特素材")
    print("=" * 50)
    for i, prompt in enumerate(model_prompts, 1):
        print(f"\n--- 模特 {i}/{len(model_prompts)} ---")
        await generate_image(prompt, "model")
        await asyncio.sleep(1)  # 避免请求过快
    
    print("\n" + "=" * 50)
    print("开始生成场景素材")
    print("=" * 50)
    for i, prompt in enumerate(scene_prompts, 1):
        print(f"\n--- 场景 {i}/{len(scene_prompts)} ---")
        await generate_image(prompt, "scene")
        await asyncio.sleep(1)
    
    print("\n" + "=" * 50)
    print("所有素材生成完成！")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
