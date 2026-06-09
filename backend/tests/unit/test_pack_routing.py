"""Pack 选包路由单元测试。"""

from domains.workflow.pack_routing import score_pack, select_pack


def test_score_pack_match_rules():
    pack = {
        "id": "p1",
        "slug": "ecom",
        "status": "published",
        "scenario_json": {"match_rules": {"channel": "ecommerce"}},
    }
    assert score_pack(pack, {"channel": "ecommerce"}) == 1
    assert score_pack(pack, {"channel": "other"}) == 0


def test_select_pack_uses_default_when_no_match():
    packs = [
        {"id": "default", "slug": "lookbook_default", "status": "published", "scenario_json": {}},
        {
            "id": "ecom",
            "slug": "ecom",
            "status": "published",
            "scenario_json": {"match_rules": {"channel": "ecommerce"}},
        },
    ]
    sel = select_pack(packs, business_context={"channel": "other"}, default_pack_id="default")
    assert sel["id"] == "default"


def test_select_pack_match_beats_default():
    packs = [
        {"id": "default", "slug": "lookbook_default", "status": "published", "scenario_json": {}},
        {
            "id": "ecom",
            "slug": "ecom",
            "status": "published",
            "scenario_json": {"match_rules": {"channel": "ecommerce"}},
        },
    ]
    sel = select_pack(packs, business_context={"channel": "ecommerce"}, default_pack_id="default")
    assert sel["id"] == "ecom"
