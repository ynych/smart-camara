"""PageIndex 风格知识检索（无向量库，树索引 + LLM 推理选节点）。"""

import json

from agents.prompt_agent import call_ark_chat, extract_responses_text
from config import get_chat_api_config
from data.services import KnowledgeNodeService


def _build_tree_outline(nodes: list[dict]) -> str:
    lines = []
    for n in nodes:
        indent = "  " * (n.get("_depth", 0))
        lines.append(f"{indent}- [{n['id']}] {n.get('title', '')}: {(n.get('summary') or '')[:120]}")
    return "\n".join(lines)


def _flatten_with_depth(tree: list[dict], depth: int = 0) -> list[dict]:
    out = []
    for node in tree:
        out.append({**node, "_depth": depth, "children": None})
        out.extend(_flatten_with_depth(node.get("children") or [], depth + 1))
    return out


async def retrieve_knowledge_snippets(tree_id: str, query: str, *, max_nodes: int = 3) -> list[dict]:
    svc = KnowledgeNodeService.__new__(KnowledgeNodeService)
    from database import SessionLocal

    db = SessionLocal()
    try:
        svc.db = db
        index = svc.build_tree_index(tree_id)
        flat = _flatten_with_depth(index)
        if not flat:
            return []
        outline = _build_tree_outline(flat)
        config = get_chat_api_config()
        endpoint = (config.get("endpoint") or "").strip()
        api_key = (config.get("api_key") or "").strip()
        if not endpoint or not api_key:
            return [{"node_id": flat[0]["id"], "title": flat[0]["title"], "content": flat[0].get("content") or ""}][:1]

        system = "你是知识库导航助手。根据目录树推理应读取哪些节点，输出 JSON 数组 node_ids，不要 markdown。"
        user = f"""查询：{query}

知识树目录：
{outline}

返回格式：{{"node_ids":["id1","id2"]}}，最多 {max_nodes} 个。"""

        body, err = await call_ark_chat(
            api_key, endpoint,
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=256,
            temperature=0,
        )
        node_ids = []
        if body:
            content = extract_responses_text(body)
            try:
                text = content.strip()
                if "```" in text:
                    text = text.split("```")[1].split("```")[0]
                data = json.loads(text)
                node_ids = data.get("node_ids") or []
            except json.JSONDecodeError:
                node_ids = []
        if not node_ids and flat:
            node_ids = [flat[0]["id"]]

        by_id = {n["id"]: n for n in flat}
        snippets = []
        for nid in node_ids[:max_nodes]:
            n = by_id.get(nid)
            if n and (n.get("content") or n.get("summary")):
                snippets.append({
                    "node_id": nid,
                    "title": n.get("title"),
                    "content": n.get("content") or n.get("summary"),
                })
        return snippets
    finally:
        db.close()
