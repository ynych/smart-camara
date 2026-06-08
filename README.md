# 私人摄影团队 MVP

电商 Lookbook 效果图生成平台：从本地素材选择模特/服装/参考图，生成验收标准与提示词，调用火山 Seedream 图生图，并在工作台完成合格验收。

## 快速开始

### 1. 环境要求

- Python 3.10+
- Node.js 18+
- 火山引擎 Ark API Key 与推理端点（Seedream）

### 2. 配置

```bash
cp .env.example .env
# 编辑 .env：
# - VOLCANO_API_KEY / VOLCANO_ENDPOINT：Seedream 生图
# - VOLCANO_CHAT_ENDPOINT：豆包等对话模型（提示词生成，与生在图 endpoint 不同）
```

### 3. 准备素材

将图片放入 `content/` 目录，结构见 [content/README.md](content/README.md)。

### 4. 启动

```bash
./start.sh          # 启动后端 8155 + 前端 8150
./start.sh status   # 查看状态
./start.sh stop     # 停止
```

- 前端：http://localhost:8150
- API 文档：http://localhost:8155/docs
- 独立验收页（可选）：`frontend/acceptance.html`（需本地打开或自行托管）

### 5. 使用流程

1. **素材管理** → 扫描 content 目录 / 上传素材  
2. **生图工作台** → 选模特、服装、参考图 → 生成提示词 → 生图 → 合格/不合格验收  
3. **我的相册** → 查看已完成任务  
4. **设置** → 配置并测试火山 API  

## 项目结构

```
backend/          # FastAPI、LookbookSkill、Seedream 生图
frontend/         # React + Ant Design 工作台
content/          # 本地素材库（扫描导入）
assets/           # 上传与生图输出
```

## 输出尺寸

工作台可选 `1:1`、`3:4`、`9:16`，会映射为 Seedream API 像素（如 3:4 → 1728x2304）。

## 开发

```bash
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8155

cd frontend && npm install && npm run dev
```

### 测试（TDD）

```bash
./scripts/run-tests.sh
```

域中间态检查：`POST /api/health/domain-checks`（见 [plan.md](plan.md) §〇·二）

Vite 已将 `/api`、`/assets`、`/content` 代理到后端。
