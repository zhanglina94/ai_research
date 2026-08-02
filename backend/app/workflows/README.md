# Workflows

LangGraph 工作流编排。

## Research Chat (`research_graph.py`)

根据用户意图路由到 Planner / Literature / General Agent。

## AI Scientist Loop (`scientist_loop.py`)

Phase 3 全自动科研闭环：

```
Idea → Experiment Design → Code Generation → Run → Analyze → Paper Draft
```

### 调用

```python
from app.workflows.scientist_loop import run_scientist_loop

result = await run_scientist_loop("efficient long-context attention")
print(result["paper_draft"])
```

### API

```bash
POST /api/v1/scientist/run
{"idea": "novel sparse attention for LLM inference"}
```
