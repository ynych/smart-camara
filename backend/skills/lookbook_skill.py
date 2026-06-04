import json
import asyncio
from datetime import datetime
from database import SessionLocal
from models import Requirement, LookbookTask, StyleTemplate, GeneratedImage, PromptFeedback
from agents.requirement_agent import RequirementAgent
from agents.scene_design_agent import SceneDesignAgent
from agents.image_synth_agent import ImageSynthAgent
from tools.file_tool import FileTool
from tools.material_tool import MaterialTool
from tools.image_tool import ImageTool
from services.prompt_optimizer import PromptOptimizer

class LookbookSkill:
    """Lookbook生成Skill - 业务层核心"""

    def __init__(self):
        self.requirement_agent = RequirementAgent()
        self.scene_agent = SceneDesignAgent()
        self.synth_agent = ImageSynthAgent()
        self.file_tool = FileTool()
        self.image_tool = ImageTool()
        self.prompt_optimizer = PromptOptimizer()

    def create_requirement(self, source_image_path: str, user_description: str = "") -> dict:
        """创建需求（上传照片后调用）"""
        db = SessionLocal()
        try:
            req = Requirement(
                source_image_path=source_image_path,
                status="active",
            )
            db.add(req)
            db.commit()
            db.refresh(req)
            return {"id": req.id, "status": req.status}
        finally:
            db.close()

    def analyze_requirement(self, requirement_id: str, user_description: str = "") -> dict:
        """分析需求（AI识别服装特征）"""
        db = SessionLocal()
        try:
            req = db.query(Requirement).filter(Requirement.id == requirement_id).first()
            if not req:
                raise Exception("需求不存在")

            # 调用需求理解Agent分析
            features = self.requirement_agent.analyze(req.source_image_path, user_description)

            # 保存分析结果
            req.detected_features = json.dumps(features, ensure_ascii=False)
            req.status = "analyzed"
            db.commit()

            return features
        finally:
            db.close()

    def get_styles(self) -> list:
        """获取可用风格列表"""
        return self.scene_agent.get_styles()

    def select_style(self, requirement_id: str, style_id: str) -> bool:
        """选择风格"""
        db = SessionLocal()
        try:
            req = db.query(Requirement).filter(Requirement.id == requirement_id).first()
            if not req:
                raise Exception("需求不存在")
            req.selected_style = style_id
            db.commit()
            return True
        finally:
            db.close()

    def build_prompts(
        self,
        model_id: str,
        clothing_ids: list,
        reference_id: str = None,
        quantity: int = 4,
        size: str = "3:4",
        scene_id: str = None,
        business_context: dict = None,
        acceptance_criteria: str = "",
    ) -> list:
        """
        构建差异化角度的prompt列表

        Args:
            model_id: 模特素材ID
            clothing_ids: 服装素材ID列表
            reference_id: 参考图素材ID（可选）
            quantity: 生成数量

        Returns:
            [{"index": 0, "angle_name": "...", "angle_desc": "...", "prompt": "...", "editable": True}, ...]
        """
        # 获取模特信息
        model_info = MaterialTool.get(model_id) if model_id else None
        model_desc = "优雅的亚洲女性模特"
        if model_info:
            meta = model_info.get("metadata", {})
            model_desc = meta.get("description", model_info.get("name", model_desc))

        # 获取服装信息
        clothing_items = MaterialTool.get_by_ids(clothing_ids) if clothing_ids else []
        clothing_descs = []
        for item in clothing_items:
            meta = item.get("metadata", {})
            desc = meta.get("description", item.get("name", ""))
            clothing_descs.append(desc)
        clothing_desc = "、".join(clothing_descs) if clothing_descs else "时尚服装"

        # 获取参考图信息
        reference_info = MaterialTool.get(reference_id) if reference_id else None
        style_hint = ""
        if reference_info:
            style_hint = self._extract_style_from_filename(reference_info.get("name", ""))

        scene_info = MaterialTool.get(scene_id) if scene_id else None
        scene_desc = "电商Lookbook拍摄场景"
        if scene_info:
            scene_desc = scene_info.get("metadata", {}).get("description", scene_info.get("name", scene_desc))

        context_parts = []
        business_context = business_context or {}
        if business_context.get("merchant_need"):
            context_parts.append(f"商家需求：{business_context['merchant_need']}")
        if business_context.get("target_audience"):
            context_parts.append(f"目标用户画像：{business_context['target_audience']}")
        if acceptance_criteria:
            context_parts.append(f"验收标准：{acceptance_criteria}")
        context_hint = "；".join(context_parts)

        # 获取角度模板
        angle_templates = self._get_angle_templates(quantity)

        # 构建每个角度的prompt
        prompts = []
        for i, template in enumerate(angle_templates):
            prompt = self._compose_prompt(
                model_desc=model_desc,
                clothing_desc=clothing_desc,
                angle_name=template["name"],
                angle_desc=template["desc"],
                style_hint=style_hint,
                scene_desc=scene_desc,
                size=size,
                context_hint=context_hint,
            )
            prompt = self._apply_feedback_improvements(prompt)
            prompts.append({
                "index": i,
                "angle_name": template["name"],
                "angle_desc": template["desc"],
                "prompt": prompt,
                "editable": True,
            })

        return prompts

    def _get_angle_templates(self, quantity: int) -> list:
        """获取角度模板列表"""
        all_templates = [
            {"name": "正面全身", "desc": "正面全身展示，展现服装整体效果和版型"},
            {"name": "侧面45度", "desc": "侧面45度角，展示服装线条和剪裁细节"},
            {"name": "背面展示", "desc": "背面设计展示，展示背部剪裁和细节"},
            {"name": "细节特写", "desc": "面料质地和工艺细节特写，展示材质纹理"},
            {"name": "动态抓拍", "desc": "自然行走中的动态抓拍，展现服装的垂坠感和动态美"},
            {"name": "搭配场景", "desc": "搭配包包和鞋子的完整造型场景"},
            {"name": "坐姿展示", "desc": "坐姿展示，展现服装在自然状态下的效果"},
            {"name": "半身特写", "desc": "上半身特写，展示领口、袖口等上半部分设计"},
        ]
        return all_templates[:quantity]

    def _compose_prompt(
        self,
        model_desc: str,
        clothing_desc: str,
        angle_name: str,
        angle_desc: str,
        style_hint: str = "",
        scene_desc: str = "电商Lookbook拍摄场景",
        size: str = "3:4",
        context_hint: str = "",
    ) -> str:
        """组合生成prompt"""
        prompt = f"一位{model_desc}模特，穿着{clothing_desc}，{angle_desc}，"
        if style_hint:
            prompt += f"{style_hint}风格，"
        prompt += f"{scene_desc}，{self._size_hint(size)}，"
        if context_hint:
            prompt += f"{context_hint}，"
        prompt += "柔和自然光，专业补光，85mm镜头浅景深，高清细节丰富，专业电商摄影风格，时尚Lookbook，服装版型和颜色准确"
        return prompt

    def _size_hint(self, size: str) -> str:
        size_map = {
            "1:1": "正方形构图，主体居中，适合商品主图",
            "3:4": "竖版3:4构图，展示完整穿搭比例",
            "9:16": "移动端9:16长竖构图，人物全身清晰",
        }
        return size_map.get(size, "竖版3:4构图，展示完整穿搭比例")

    def build_acceptance_criteria(
        self,
        size: str = "3:4",
        quantity: int = 4,
        business_context: dict = None,
    ) -> str:
        """生成可编辑验收标准。"""
        business_context = business_context or {}
        criteria = [
            "模特身份、五官和体态与所选模特参考保持一致",
            "服装款式、颜色、版型和关键细节与所选服装素材一致",
            "场景氛围与所选参考图/场景图一致，背景不抢主体",
            f"输出为{size}比例，共{quantity}张，构图完整且无明显裁切",
            "图片清晰、光线自然、无明显肢体畸形、文字水印或商品变形",
        ]
        if business_context.get("merchant_need"):
            criteria.append(f"满足商家需求：{business_context['merchant_need']}")
        if business_context.get("target_audience"):
            criteria.append(f"贴合目标用户画像：{business_context['target_audience']}")
        return "\n".join(f"{i + 1}. {item}" for i, item in enumerate(criteria))

    def _recent_feedbacks(self, limit: int = 30) -> list:
        db = SessionLocal()
        try:
            rows = (
                db.query(PromptFeedback)
                .order_by(PromptFeedback.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {"result": r.result, "feedback": r.feedback, "prompt": r.prompt_used}
                for r in rows
            ]
        finally:
            db.close()

    def _apply_feedback_improvements(self, prompt: str) -> str:
        feedbacks = self._recent_feedbacks()
        return self.prompt_optimizer.suggest_improvements(prompt, feedbacks)

    def _extract_style_from_filename(self, filename: str) -> str:
        """从文件名中提取风格提示"""
        if not filename:
            return ""
        lower = filename.lower()
        style_map = {
            "street": "街拍",
            "studio": "棚拍",
            "natural": "自然",
            "minimal": "极简",
            "vintage": "复古",
            "luxury": "奢华",
        }
        for key, style in style_map.items():
            if key in lower:
                return style
        # 中文关键词
        cn_map = {"街拍": "街拍", "棚拍": "棚拍", "自然": "自然", "极简": "极简", "复古": "复古"}
        for key, style in cn_map.items():
            if key in lower:
                return style
        return ""

    async def generate(self, requirement_id: str, progress_callback=None, quantity: int = 4, reference_image_path: str = None) -> dict:
        """执行Lookbook生成"""
        db = SessionLocal()
        try:
            req = db.query(Requirement).filter(Requirement.id == requirement_id).first()
            if not req:
                raise Exception("需求不存在")

            features = json.loads(req.detected_features) if req.detected_features else {}
            style_id = req.selected_style

            # 收集参考图URL列表
            reference_images = []
            if req.source_image_path:
                reference_images.append(req.source_image_path)
            # reference_image_path 参数
            if reference_image_path and reference_image_path not in reference_images:
                reference_images.append(reference_image_path)
            # 从selected_materials中获取额外素材图
            if req.selected_materials:
                try:
                    selected = json.loads(req.selected_materials)
                    for item in selected:
                        if isinstance(item, dict) and item.get("file_path"):
                            fp = item["file_path"]
                            if fp not in reference_images:
                                reference_images.append(fp)
                except (json.JSONDecodeError, TypeError):
                    pass

            # 获取prompt_overrides
            prompt_overrides = None
            if req.prompt_overrides:
                try:
                    prompt_overrides = json.loads(req.prompt_overrides)
                except (json.JSONDecodeError, TypeError):
                    pass

            # 创建任务
            task = LookbookTask(
                requirement_id=requirement_id,
                style_id=style_id,
                status="generating",
                progress=0,
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            task_id = task.id

        finally:
            db.close()

        # 执行生成
        try:
            async def update_progress(progress):
                db2 = SessionLocal()
                try:
                    t = db2.query(LookbookTask).filter(LookbookTask.id == task_id).first()
                    if t:
                        t.progress = progress
                        db2.commit()
                finally:
                    db2.close()
                if progress_callback:
                    await progress_callback(progress)

            task_size = "3:4"
            if req.user_edits:
                try:
                    edits = json.loads(req.user_edits)
                    task_size = edits.get("size") or task_size
                except (json.JSONDecodeError, TypeError):
                    pass

            results = await self.synth_agent.generate_lookbook(
                task_id=task_id,
                features=features,
                reference_images=reference_images if reference_images else None,
                progress_callback=update_progress,
                quantity=quantity,
                prompt_overrides=prompt_overrides,
                size=task_size,
            )

            # 更新任务状态
            db = SessionLocal()
            try:
                task = db.query(LookbookTask).filter(LookbookTask.id == task_id).first()
                task.status = "completed"
                task.progress = 100
                task.generated_images = json.dumps(results, ensure_ascii=False)
                db.commit()
            finally:
                db.close()

            # 更新需求状态
            db = SessionLocal()
            try:
                req = db.query(Requirement).filter(Requirement.id == requirement_id).first()
                req.status = "completed"
                db.commit()
            finally:
                db.close()

            return {"task_id": task_id, "images": results}

        except Exception as e:
            # 更新任务失败状态
            db = SessionLocal()
            try:
                task = db.query(LookbookTask).filter(LookbookTask.id == task_id).first()
                if task:
                    task.status = "failed"
                    task.error_message = str(e)
                    db.commit()
            finally:
                db.close()
            raise

    async def generate_from_selection(self, data: dict, progress_callback=None) -> dict:
        """按工作台选择的素材执行 Seedream 5.x 图生图。"""
        model_id = data.get("model_id")
        clothing_ids = data.get("clothing_ids") or []
        reference_id = data.get("reference_id")
        scene_id = data.get("scene_id")
        size = data.get("size") or "3:4"
        prompts = data.get("prompts") or []
        quantity = int(data.get("quantity") or len(prompts) or 1)
        acceptance_criteria = data.get("acceptance_criteria") or ""
        business_context = data.get("business_context") or {}

        if not model_id:
            raise Exception("缺少模特素材")
        if not clothing_ids:
            raise Exception("缺少服装素材")
        if not prompts:
            prompts = self.build_prompts(
                model_id=model_id,
                clothing_ids=clothing_ids,
                reference_id=reference_id,
                quantity=quantity,
                size=size,
                scene_id=scene_id,
                business_context=business_context,
                acceptance_criteria=acceptance_criteria,
            )

        material_ids = [model_id, *clothing_ids]
        if reference_id:
            material_ids.append(reference_id)
        if scene_id:
            material_ids.append(scene_id)
        materials = MaterialTool.get_by_ids(material_ids)
        material_map = {m["id"]: m for m in materials}
        reference_images = []
        for mid in material_ids:
            item = material_map.get(mid)
            if item and item.get("file_path") and item["file_path"] not in reference_images:
                reference_images.append(item["file_path"])

        db = SessionLocal()
        try:
            req = Requirement(
                source_image_path=material_map.get(model_id, {}).get("file_path"),
                reference_image_path=material_map.get(reference_id, {}).get("file_path") if reference_id else None,
                selected_materials=json.dumps(
                    {
                        "model_id": model_id,
                        "clothing_ids": clothing_ids,
                        "reference_id": reference_id,
                        "scene_id": scene_id,
                        "business_context": business_context,
                    },
                    ensure_ascii=False,
                ),
                prompt_overrides=json.dumps(prompts, ensure_ascii=False),
                user_edits=json.dumps({"acceptance_criteria": acceptance_criteria, "size": size}, ensure_ascii=False),
                status="generating",
            )
            db.add(req)
            db.commit()
            db.refresh(req)

            task = LookbookTask(
                requirement_id=req.id,
                status="generating",
                progress=0,
                quantity=len(prompts),
                size=size,
                selected_materials=req.selected_materials,
                acceptance_criteria=acceptance_criteria,
                prompt_overrides=json.dumps(prompts, ensure_ascii=False),
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            task_id = task.id
        finally:
            db.close()

        results = []
        try:
            total = len(prompts)
            for i, prompt_data in enumerate(prompts):
                prompt = prompt_data.get("prompt", "") if isinstance(prompt_data, dict) else str(prompt_data)
                angle_name = prompt_data.get("angle_name", f"图片{i + 1}") if isinstance(prompt_data, dict) else f"图片{i + 1}"
                if not prompt:
                    continue
                image_content = await self.image_tool.generate(prompt, image_paths=reference_images, size=size)
                file_path = self.file_tool.save_generated(task_id, image_content, i)
                image_id = None
                db = SessionLocal()
                try:
                    image = GeneratedImage(
                        task_id=task_id,
                        file_path=file_path,
                        angle=angle_name,
                        prompt=prompt,
                        status="pending",
                        acceptance_criteria=acceptance_criteria,
                    )
                    db.add(image)
                    db.commit()
                    db.refresh(image)
                    image_id = image.id
                finally:
                    db.close()

                result = {
                    "id": image_id,
                    "angle": angle_name,
                    "path": file_path,
                    "prompt": prompt,
                    "status": "pending",
                    "feedback": None,
                }
                results.append(result)
                progress = int((i + 1) / total * 100)
                db = SessionLocal()
                try:
                    task = db.query(LookbookTask).filter(LookbookTask.id == task_id).first()
                    if task:
                        task.progress = progress
                        db.commit()
                finally:
                    db.close()
                if progress_callback:
                    await progress_callback(progress)

            db = SessionLocal()
            try:
                task = db.query(LookbookTask).filter(LookbookTask.id == task_id).first()
                req = db.query(Requirement).filter(Requirement.id == task.requirement_id).first() if task else None
                if task:
                    task.status = "completed"
                    task.progress = 100
                    task.generated_images = json.dumps(results, ensure_ascii=False)
                    task.completed_at = datetime.utcnow()
                if req:
                    req.status = "completed"
                    req.updated_at = datetime.utcnow()
                db.commit()
            finally:
                db.close()
            return {"task_id": task_id, "images": results}
        except Exception as e:
            db = SessionLocal()
            try:
                task = db.query(LookbookTask).filter(LookbookTask.id == task_id).first()
                if task:
                    task.status = "failed"
                    task.error_message = str(e)
                    db.commit()
            finally:
                db.close()
            raise

    def review_image(self, image_id: str, status: str, feedback: str = "") -> dict:
        """记录图片验收结果，并沉淀到提示词反馈。"""
        if status not in ("approved", "rejected"):
            raise Exception("验收状态必须是 approved 或 rejected")
        db = SessionLocal()
        try:
            image = db.query(GeneratedImage).filter(GeneratedImage.id == image_id).first()
            if not image:
                raise Exception("图片不存在")
            image.status = status
            image.feedback = feedback
            image.reviewed_at = datetime.utcnow()
            db.add(PromptFeedback(
                task_id=image.task_id,
                image_id=image.id,
                prompt_used=image.prompt or "",
                result=status,
                feedback=feedback,
            ))
            task = db.query(LookbookTask).filter(LookbookTask.id == image.task_id).first()
            db.commit()

            if task and task.generated_images:
                images = json.loads(task.generated_images)
                for item in images:
                    if item.get("id") == image.id:
                        item["status"] = status
                        item["feedback"] = feedback
                task.generated_images = json.dumps(images, ensure_ascii=False)
                db.commit()
            return {"image_id": image_id, "status": status, "feedback": feedback}
        finally:
            db.close()
