# Agents

LangGraph Agent 模块，每个 Agent 负责科研流程中的一个环节。

## Agent 列表

| Agent | 文件 | 职责 | Phase |
|-------|------|------|-------|
| Planner | `planner.py` | 研究规划、任务拆解 | 1 |
| Literature | `literature.py` | 论文搜索、摘要、知识抽取 | 1 |
| Knowledge Graph | `knowledge_graph.py` | Paper/Method/Dataset/Model/Citation 图谱 | 2 |
| Experiment | `experiment.py` | 实验设计、Baseline、Ablation | 2 |
| Coding | `coding.py` | 代码生成、项目脚手架 | 2 |
| Reviewer | `reviewer.py` | 论文审稿模拟 | 2 |

## 工作流

| 工作流 | 文件 | 说明 |
|--------|------|------|
| Research Chat | `workflows/research_graph.py` | 对话路由 (Planner/Literature/General) |
| AI Scientist Loop | `workflows/scientist_loop.py` | Idea→Experiment→Code→Run→Analyze→Paper |

## 使用

```python
from app.agents.experiment import ExperimentAgent
from app.workflows.scientist_loop import run_scientist_loop

agent = ExperimentAgent()
spec = await agent.design_experiment("efficient transformers")

result = await run_scientist_loop("novel attention mechanism for long context")
```
