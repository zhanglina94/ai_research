# Database Layer

三层 Memory 系统的数据存储实现。

## 组件

| 模块 | 用途 | Memory 层 |
|------|------|-----------|
| `postgres.py` | 科研任务、项目、对话记录 | Working Memory |
| `redis_client.py` | 会话状态、短期缓存 | Short Memory |
| `milvus_client.py` | 论文向量检索 | Long Memory |
| `neo4j_client.py` | 知识图谱 (Paper/Method/Dataset) | Long Memory |

## 连接

配置见 `.env`，通过 `app.config.Settings` 读取。

## 初始化

应用启动时自动调用 `init_db()` 创建 PostgreSQL 表结构。
Milvus / Neo4j 在首次使用时懒加载连接。
