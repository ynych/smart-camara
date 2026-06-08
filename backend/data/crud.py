"""数据层通用 CRUD（AI 无关）。"""

import json
from datetime import datetime
from typing import Any, Generic, Type, TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")


def parse_json_field(value: str | None, default=None):
    if not value:
        return default if default is not None else None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else None


def dump_json_field(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def row_to_dict(row, *, json_fields: list[str] | None = None) -> dict:
    json_fields = json_fields or []
    data = {}
    for col in row.__table__.columns:
        val = getattr(row, col.name)
        if col.name in json_fields:
            data[col.name.replace("_json", "") if col.name.endswith("_json") else col.name] = parse_json_field(val, {})
            if col.name.endswith("_json"):
                data[col.name] = val
            continue
        if isinstance(val, datetime):
            data[col.name] = val.isoformat()
        else:
            data[col.name] = val
    return data


class CrudService(Generic[T]):
    model: Type[T]
    json_fields: list[str] = []

    def __init__(self, db: Session):
        self.db = db

    def list_all(self, *, skip: int = 0, limit: int = 200, **filters):
        q = self.db.query(self.model)
        for key, val in filters.items():
            if val is not None and hasattr(self.model, key):
                q = q.filter(getattr(self.model, key) == val)
        rows = q.offset(skip).limit(limit).all()
        return [self.serialize(r) for r in rows]

    def get(self, item_id: str):
        row = self.db.query(self.model).filter(self.model.id == item_id).first()
        return self.serialize(row) if row else None

    def create(self, data: dict):
        payload = self._prepare_write(data)
        row = self.model(**payload)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self.serialize(row)

    def update(self, item_id: str, data: dict):
        row = self.db.query(self.model).filter(self.model.id == item_id).first()
        if not row:
            return None
        payload = self._prepare_write(data, partial=True)
        for k, v in payload.items():
            setattr(row, k, v)
        if hasattr(row, "updated_at"):
            row.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(row)
        return self.serialize(row)

    def delete(self, item_id: str) -> bool:
        row = self.db.query(self.model).filter(self.model.id == item_id).first()
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def serialize(self, row) -> dict | None:
        if not row:
            return None
        return row_to_dict(row, json_fields=self.json_fields)

    def _prepare_write(self, data: dict, partial: bool = False) -> dict:
        out = {}
        for col in self.model.__table__.columns:
            name = col.name
            if name in ("id", "created_at"):
                continue
            if name not in data and partial:
                continue
            if name.endswith("_json") and name.replace("_json", "") in data:
                out[name] = dump_json_field(data[name.replace("_json", "")])
            elif name in data:
                val = data[name]
                if name.endswith("_json") and isinstance(val, (dict, list)):
                    out[name] = dump_json_field(val)
                else:
                    out[name] = val
        return out
