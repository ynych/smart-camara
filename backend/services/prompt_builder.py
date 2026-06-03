class PromptBuilder:
    """提示词生成器 - 根据参数组合生成中文提示词"""

    def build_prompt(
        self,
        clothing_desc: str,
        model_gender: str,
        scene_type: str,
        size: str,
        extra_params: dict = None,
    ) -> str:
        """
        根据参数组合生成中文提示词

        Args:
            clothing_desc: 服装描述
            model_gender: 模特性别 (female/male)
            scene_type: 场景类型 (indoor/outdoor)
            size: 尺寸 (1:1/3:4/9:16)
            extra_params: 额外参数

        Returns:
            组合后的中文提示词
        """
        extra_params = extra_params or {}

        # 服装描述
        clothing_part = f"服装：{clothing_desc}"

        # 模特描述
        gender_map = {
            "female": "女性模特",
            "male": "男性模特",
        }
        model_desc = gender_map.get(model_gender, "模特")
        model_part = f"模特：{model_desc}，身材比例匀称，姿态自然优雅"

        # 场景描述
        scene_map = {
            "indoor": "室内场景，简洁干净的背景，柔和的灯光",
            "outdoor": "户外场景，自然光线，城市街拍风格",
        }
        scene_desc = scene_map.get(scene_type, "简洁干净的背景")
        scene_part = f"场景：{scene_desc}"

        # 风格要求
        style_part = "风格要求：电商产品展示风格，高清画质，色彩还原准确，光影自然"

        # 尺寸要求
        size_map = {
            "1:1": "正方形构图，适合商品主图展示",
            "3:4": "竖版构图，适合详情页展示",
            "9:16": "长竖版构图，适合移动端展示",
        }
        size_desc = size_map.get(size, "正方形构图")
        size_part = f"构图要求：{size_desc}"

        # 额外参数
        extra_part = ""
        if extra_params:
            extra_items = []
            if "style" in extra_params:
                extra_items.append(f"风格补充：{extra_params['style']}")
            if "pose" in extra_params:
                extra_items.append(f"姿势要求：{extra_params['pose']}")
            if "background" in extra_params:
                extra_items.append(f"背景补充：{extra_params['background']}")
            if "lighting" in extra_params:
                extra_items.append(f"灯光补充：{extra_params['lighting']}")
            if extra_items:
                extra_part = "；".join(extra_items)

        # 组合提示词
        parts = [clothing_part, model_part, scene_part, style_part, size_part]
        if extra_part:
            parts.append(extra_part)

        prompt = "。".join(parts) + "。"

        return prompt
