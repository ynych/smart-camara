import json
import asyncio
from database import SessionLocal
from models import Requirement, LookbookTask, StyleTemplate
from agents.requirement_agent import RequirementAgent
from agents.scene_design_agent import SceneDesignAgent
from agents.image_synth_agent import ImageSynthAgent
from tools.file_tool import FileTool

class LookbookSkill:
    """Lookbook生成Skill - 业务层核心"""

    def __init__(self):
        self.requirement_agent = RequirementAgent()
        self.scene_agent = SceneDesignAgent()
        self.synth_agent = ImageSynthAgent()
        self.file_tool = FileTool()

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

    async def generate(self, requirement_id: str, progress_callback=None) -> dict:
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

            results = await self.synth_agent.generate_lookbook(
                task_id=task_id,
                style_id=style_id,
                features=features,
                reference_images=reference_images if reference_images else None,
                progress_callback=update_progress,
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
