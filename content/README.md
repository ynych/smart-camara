# 内容素材目录

将本地图片放入以下目录后，在 **素材管理** 页点击「扫描 content 目录」，或在生图工作台刷新素材即可使用。

## 目录结构

```
content/
├── model-cards/         # 模特参考图（每张一个文件）
├── clothing/
│   └── {套装名称}/      # 如「春季通勤」（套装名可保留中文）
│       ├── fashion-shot/  # 可选：时尚拍摄
│       ├── mannequin/     # 可选：人台图
│       ├── flat-lay/      # 可选：平铺图
│       └── *.jpg          # 或直接放在套装目录下
├── lookbook-refs/       # Lookbook 风格参考图
└── scenes/              # 场景/背景图（可选）
```

启动时会自动将旧的中文目录名迁移为上述英文名（见 `backend/services/content_path_migration.py`）。

## 格式要求

- 支持：`.jpg`、`.jpeg`、`.png`、`.webp`、`.bmp`、`.gif`
- 建议单张不超过 10MB，分辨率适中即可（生图 API 会自行处理）

## 首次使用

1. 按上方结构放入至少 1 张模特卡 + 1 套服装图
2. 启动服务：`./start.sh`
3. 打开 http://localhost:8150 → **素材管理** → **扫描 content 目录**
4. 进入 **生图工作台** 完成选图、提示词与验收
