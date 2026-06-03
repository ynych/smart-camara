from collections import Counter


class PromptOptimizer:
    """提示词优化器 - 分析反馈并建议改进"""

    def analyze_feedback(self, feedbacks: list) -> dict:
        """
        分析历史反馈，统计合格率，提取常见问题

        Args:
            feedbacks: 反馈列表，每个元素为包含 result 和 feedback 的字典

        Returns:
            分析结果字典
        """
        if not feedbacks:
            return {
                "total": 0,
                "approved": 0,
                "rejected": 0,
                "approval_rate": 0.0,
                "common_issues": [],
            }

        total = len(feedbacks)
        approved = sum(1 for f in feedbacks if f.get("result") == "approved")
        rejected = total - approved
        approval_rate = round(approved / total * 100, 1) if total > 0 else 0.0

        # 提取常见问题关键词
        issue_keywords = []
        for f in feedbacks:
            if f.get("result") == "rejected" and f.get("feedback"):
                issue_keywords.append(f["feedback"].strip())

        # 统计高频问题
        common_issues = []
        if issue_keywords:
            keyword_counter = Counter(issue_keywords)
            common_issues = [
                {"issue": keyword, "count": count}
                for keyword, count in keyword_counter.most_common(5)
            ]

        return {
            "total": total,
            "approved": approved,
            "rejected": rejected,
            "approval_rate": approval_rate,
            "common_issues": common_issues,
        }

    def suggest_improvements(self, prompt: str, feedbacks: list) -> str:
        """
        根据反馈建议提示词改进

        Args:
            prompt: 原始提示词
            feedbacks: 反馈列表

        Returns:
            改进后的提示词
        """
        if not feedbacks:
            return prompt

        analysis = self.analyze_feedback(feedbacks)

        # 如果合格率已经很高，不需要大改
        if analysis["approval_rate"] >= 80:
            return prompt

        improvements = []

        # 根据常见问题添加改进建议
        rejected_feedbacks = [
            f["feedback"]
            for f in feedbacks
            if f.get("result") == "rejected" and f.get("feedback")
        ]

        if not rejected_feedbacks:
            return prompt

        # 分析反馈中的关键词并生成改进
        all_feedback_text = " ".join(rejected_feedbacks)

        if "颜色" in all_feedback_text or "色彩" in all_feedback_text:
            improvements.append("确保服装颜色准确还原，色彩饱和度适中")

        if "光线" in all_feedback_text or "灯光" in all_feedback_text or "亮度" in all_feedback_text:
            improvements.append("优化光线效果，确保服装细节清晰可见")

        if "背景" in all_feedback_text:
            improvements.append("背景干净整洁，突出服装主体")

        if "模特" in all_feedback_text or "姿势" in all_feedback_text or "姿态" in all_feedback_text:
            improvements.append("模特姿态自然，展示服装的最佳效果")

        if "尺寸" in all_feedback_text or "比例" in all_feedback_text:
            improvements.append("注意画面比例，服装在画面中占比适中")

        if "模糊" in all_feedback_text or "清晰" in all_feedback_text:
            improvements.append("提高画面清晰度，确保服装纹理细节可见")

        if "褶皱" in all_feedback_text:
            improvements.append("注意服装褶皱的自然表现")

        if improvements:
            improvement_text = "改进要求：" + "；".join(improvements) + "。"
            # 将改进附加到原始提示词
            improved_prompt = prompt.rstrip("。") + "。" + improvement_text
            return improved_prompt

        return prompt
