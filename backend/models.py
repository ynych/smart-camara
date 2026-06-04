import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime
from database import Base

class Requirement(Base):
    __tablename__ = "requirements"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String(20), default="active")  # active/completed/archived
    source_image_path = Column(String(500))
    detected_features = Column(Text)  # JSON string
    selected_style = Column(String(36))
    user_edits = Column(Text)  # JSON string
    selected_materials = Column(Text)  # JSON: [{"id": "xxx", "category": "model"}, ...]
    reference_image_path = Column(String(500))
    prompt_overrides = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class StyleTemplate(Base):
    __tablename__ = "style_templates"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    preview_prompt = Column(Text)
    prompt_template = Column(Text, nullable=False)
    variables = Column(Text)  # JSON string
    angles = Column(Text, nullable=False)  # JSON string
    sort_order = Column(Integer, default=0)

class LookbookTask(Base):
    __tablename__ = "lookbook_tasks"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    requirement_id = Column(String(36))
    style_id = Column(String(36))
    status = Column(String(20), default="pending")  # pending/analyzing/generating/completed/failed
    progress = Column(Integer, default=0)
    quantity = Column(Integer, default=4)
    size = Column(String(20), default="3:4")
    selected_materials = Column(Text)  # JSON string
    acceptance_criteria = Column(Text)
    prompt_overrides = Column(Text)  # JSON string
    generated_images = Column(Text)  # JSON string
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

class Material(Base):
    __tablename__ = "materials"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255))
    type = Column(String(20))  # upload/generated/reference
    category = Column(String(50))  # clothing/model/scene
    file_path = Column(String(500))
    thumbnail_path = Column(String(500))
    metadata_json = Column(Text)  # JSON string (避免与SQLAlchemy metadata冲突)
    parent_dir = Column(String(255))
    sub_category = Column(String(50))
    outfit_set = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

class GeneratedImage(Base):
    __tablename__ = "generated_images"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36))
    file_path = Column(String(500))
    angle = Column(String(100))
    prompt = Column(Text)
    status = Column(String(20), default="pending")  # pending/approved/rejected
    feedback = Column(Text)
    acceptance_criteria = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime)

class PromptFeedback(Base):
    __tablename__ = "prompt_feedbacks"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36))
    image_id = Column(String(36))
    prompt_used = Column(Text)
    result = Column(String(20))
    feedback = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class ApiConfig(Base):
    __tablename__ = "api_configs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String(50), unique=True, nullable=False)
    api_key = Column(String(500), nullable=False)
    endpoint = Column(String(500))
    model = Column(String(100))
    is_active = Column(Integer, default=1)
