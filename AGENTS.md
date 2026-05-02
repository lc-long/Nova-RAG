# AGENTS.md

## 项目概览

Nova-RAG 是企业级 RAG 知识库问答系统，基于 **FastAPI (Python) + React + PostgreSQL/pgvector**。

## 目录结构

```
Nova-RAG/
├── backend/               # Python 后端，入口: src/api/server.py
│   ├── src/api/           # 路由 (docs/chat/conversations)、数据库、模型
│   ├── src/core/          # chunker/embedder/llm/ocr/retriever/storage
│   └── uploads/           # 上传文件暂存
├── frontend/              # React 18 + TypeScript + Vite + Tailwind
├── tests/                 # 集成测试脚本 (不是 backend/tests/)
└── docker-compose.yml     # PostgreSQL 配置
```

## 启动命令

### PostgreSQL
```bash
# Docker 单容器 (port 5433)
docker run -d --name pgvector -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=novarag -p 5433:5432 pgvector/pgvector:pg16

# 或使用 docker-compose
docker compose up -d
```

### 后端
```bash
cd backend
uv run uvicorn src.api.server:app --host 0.0.0.0 --port 5000
```

### 前端
```bash
cd frontend
npm install
npm run dev
```

## 环境变量 (backend/.env)

```env
MINIMAX_API_KEY=
MINIMAX_GROUP_ID=
ALIYUN_API_KEY=
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/novarag
HF_ENDPOINT=https://hf-mirror.com
```

## 关键架构

- **后端端口**: 5000，入口 `src/api/server.py`
- **数据库端口**: 5433 (pgvector/pg16)
- **向量维度**: 1024 (Aliyun DashScope text-embedding-v3)
- **混合检索**: pgvector 向量检索 + BM25 (jieba 分词) + RRF 融合
- **外部 API**: MiniMax M2.7 (LLM), Aliyun DashScope (Embedding/Reranker), Qwen-VL (OCR)

**注意点**: `server.py` 在启动时通过 `load_dotenv()` 加载 .env，并强制设置 `HF_ENDPOINT`。如需修改 HF 镜像地址，修改 .env 中的 `HF_ENDPOINT` 即可覆盖。

## RAG 调参

所有 RAG 核心参数集中在 `backend/src/core/config.py`，通过 `backend/.env` 覆盖。

关键参数及默认值：
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `CHUNK_PARENT_SIZE` | 2000 | 父chunk大小 |
| `CHUNK_CHILD_SIZE` | 500 | 子chunk大小 |
| `CHUNK_OVERLAP` | 100 | chunk重叠字符数 |
| `RRF_K` | 40 | RRF融合常数 (越小越重视高排名) |
| `RERANK_MIN_SCORE` | 0.05 | Reranker最低相关性阈值 |
| `RETRIEVER_TOP_K` | 8 | 最终返回chunk数 |
| `RECALL_MULTIPLIER` | 8 | 召回放大倍数 |
| `MAX_CONTEXT_TOKENS` | 6000 | 上下文token上限 |
| `EMBED_MODEL` | text-embedding-v3 | 嵌入模型 |
| `RERANK_MODEL` | gte-rerank | 重排序模型 |

Query改写扩展模式支持外部JSON文件，通过 `QUERY_PATTERNS_FILE` 指定路径。

## 测试

```bash
cd tests && python test_novatech.py
```
依赖后端运行在 `http://localhost:5000`。

## 自测要求

每次 commit 前必须完成以下检查：

### 1. Backend 代码改动
```bash
cd backend && uv run python -c "from src.api.server import app; print('OK')"
```

### 2. 前端代码改动
```bash
cd frontend && npm run build 2>&1 | tail -5
```

### 3. RAG 相关改动（如涉及检索/生成/LLM）
必须运行 `tests/test_rag_evaluation_full.py` 验证：
```bash
cd backend && uv run python ../tests/test_rag_evaluation_full.py 2>&1 | tail -20
```

### 4. 配置参数改动
将参数写入 `backend/.env.example` 作为默认值参考。

## Git 提交规范

遵循 Angular 规范：`type(scope): description`

- type: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`
- scope: `ui`, `api`, `rag`, `db`, `config`
- 提交语言：英文
- 禁止：`fix bug`, `update code` 等模糊 message
- **勤提交**：每完成一个独立功能或修复就立即提交，不要积攒大量改动后一次性提交。按功能拆分提交，每个 commit 应该是一个可独立理解的变更单元。

详见 `document/02_Engineering_Standards_and_Coding_Protocols.md`

## 技术栈

- Python 3.12+ (使用 `uv` 管理)
- React 18 + TypeScript + Tailwind CSS + Vite
- FastAPI + Uvicorn
- PostgreSQL 16 + pgvector