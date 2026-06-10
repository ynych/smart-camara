"""ImageTool 路径解析。"""

from __future__ import annotations

import os

from config import CONTENT_DIR
from tools.image_tool import ImageTool


def test_resolve_mac_content_path_on_current_machine():
    rel = "lookbook-refs/sample-ref.jpg"
    target = os.path.join(CONTENT_DIR, rel)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "wb") as f:
        f.write(b"fake")

    mac_path = f"/Users/yyc/apps/smart-camara/content/{rel}"
    assert ImageTool.resolve_image_path(mac_path) == target
    assert ImageTool.normalize_storage_path(mac_path) == target


def test_resolve_relative_content_prefix():
    rel = "lookbook-refs/foo.jpg"
    normalized = ImageTool.normalize_storage_path(f"content/{rel}")
    assert normalized == os.path.join(CONTENT_DIR, rel)
