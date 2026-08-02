# Backend - AI Research OS

FastAPI 后端服务，提供 REST API 与 LangGraph Agent 编排。

## 结构

```
app/
├── main.py           # 应用入口
├── config.py         # 配置
├── agents/           # Agent 实现
├── api/              # API 路由
├── database/         # 数据库层
├── tools/            # 工具 (论文检索等)
└── workflows/        # LangGraph 工作流
tests/                # 测试
```

## 本地开发

复用 Conda `base` 环境，不创建项目内 venv：

```bash
conda activate base
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 测试

```bash
pytest tests/ -v
```

## API

- `GET /health` — 健康检查
- `POST /api/v1/chat` — 科研对话
- `POST /api/v1/research/plan` — 生成研究计划
- `POST /api/v1/papers/search` — 论文搜索
- `POST /api/v1/papers/summarize` — 论文摘要
- `GET /api/v1/projects` — 项目列表
- `GET /api/v1/knowledge/graph` — 知识图谱
- `POST /api/v1/experiments/design` — 实验设计
- `POST /api/v1/experiments/code` — 代码生成
- `POST /api/v1/experiments/run` — 运行实验
- `GET /api/v1/experiments/mlflow` — MLflow 实验列表
- `POST /api/v1/scientist/run` — AI Scientist 全自动闭环
- `GET /api/v1/scientist/runs` — Scientist 运行历史
