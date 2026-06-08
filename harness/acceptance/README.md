# AI 验收 TestCase

规范文件：`ai-testcases.yaml`

## 快速执行（无需 Promptfoo）

```bash
# 1. 环境门禁
curl -s -X POST http://127.0.0.1:8155/api/config/test-chat | jq .

# 2. 核心：工作台提示词 LLM 轨（TC-U02）
curl -s -X POST http://127.0.0.1:8155/api/lookbook/generate-prompt \
  -H 'Content-Type: application/json' \
  -d @- <<'EOF' | jq '{prompt_source, llm_error, count: (.prompts|length), agent_slug}'
{
  "model_id": "8a2ef835-bf47-4616-891d-bb584cc5be63",
  "clothing_ids": ["8baf75e8-f41a-44b9-9fb5-ca40a90051e8"],
  "reference_id": "a93c7bf2-b47b-410a-8571-99b775e3df11",
  "quantity": 2,
  "size": "3:4",
  "business_context": {
    "merchant_need": "电商主图与详情页展示",
    "target_audience": "25-35 岁都市女性"
  }
}
EOF

# 3. Agent 契约（TC-A01）
AGENT=$(curl -s http://127.0.0.1:8155/api/agent-runtime/agents/default | jq -r .id)
curl -s -X POST "http://127.0.0.1:8155/api/agent-runtime/agents/$AGENT/invoke" \
  -H 'Content-Type: application/json' \
  -d '{"model_id":"8a2ef835-bf47-4616-891d-bb584cc5be63","clothing_ids":["8baf75e8-f41a-44b9-9fb5-ca40a90051e8"],"quantity":4,"size":"3:4"}' \
  | jq '{source, run_id, prompts: (.prompts|length)}'

# 4. 边界：Harness 不生图（G-BOUNDARY）
CASE=$(curl -s http://127.0.0.1:8155/api/admin/harness-testcases | jq -r '.[0].id')
curl -s -o /dev/null -w "%{http_code}\n" -X POST \
  "http://127.0.0.1:8155/api/agent-runtime/harness-testcases/$CASE/run-images"
# 期望 410
```

## Promptfoo 全量回归（TC-A04）

```bash
./start.sh restart
./scripts/run-promptfoo.sh
```

## Admin UI 手工验收

| 用例 | 路径 |
|------|------|
| TC-A02 | `/admin/harness/testcases` → 跑 Agent → 评价 |
| TC-A03 | `/admin/harness/versions` → Compare → Approve |
| TC-A05 | `/history` → 评价 → 导入 TestCase |
