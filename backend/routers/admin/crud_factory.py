"""Admin 数据层 CRUD 路由工厂。"""

from typing import Callable

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db


def make_crud_router(
    prefix: str,
    tag: str,
    service_factory: Callable,
    *,
    allow_create: bool = True,
    extra_routes: Callable[[APIRouter, Callable], None] | None = None,
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])

    class ItemBody(BaseModel):
        model_config = {"extra": "allow"}

    def svc(db: Session = Depends(get_db)):
        return service_factory(db)

    @router.get("")
    def list_items(service=Depends(svc)):
        return {"items": service.list_all()}

    @router.get("/{item_id}")
    def get_item(item_id: str, service=Depends(svc)):
        item = service.get(item_id)
        if not item:
            raise HTTPException(404, "记录不存在")
        return item

    if allow_create:

        @router.post("")
        def create_item(body: ItemBody, service=Depends(svc)):
            return service.create(body.model_dump(exclude_none=True))

        @router.put("/{item_id}")
        def update_item(item_id: str, body: ItemBody, service=Depends(svc)):
            item = service.update(item_id, body.model_dump(exclude_none=True))
            if not item:
                raise HTTPException(404, "记录不存在")
            return item

        @router.delete("/{item_id}")
        def delete_item(item_id: str, service=Depends(svc)):
            if not service.delete(item_id):
                raise HTTPException(404, "记录不存在")
            return {"ok": True}

    if extra_routes:
        extra_routes(router, svc)

    return router
