# Nova-RAG

> 企业级 RAG 知识库问答系统 — V2.0

基于 MiniMax-M2.7 大模型、PostgreSQL + pgvector 向量数据库、Python FastAPI 统一架构的智能问答系统。

---

## 系统架构

```
┌──────────────┐      ┌─────────────────────────────────────┐
│   Frontend   │─────>│         Backend (Python/FastAPI)     │
│  React + TS  │ SSE  │  port 5000                          │
│  Tailwind    │<─────│  ├── API Routes: docs, chat, convs  │
│  Vite + Zustand │   │  ├── Core: chunker/embedder/retriever/llm/ocr │
└──────────────┘      │  └── Storage: PostgreSQL + pgvector   │
                      └──────────────┬──────────────────────┘
                                   │
                      ┌────────────┴──────────────────────┐
                      │  PostgreSQL + pgvector (port 5433)  │
                      │  Docker: pgvector/pgvector:pg16      │
                      └─────────────────────────────────────┘
                      ┌─────────────────────────────────────┐
                      │  External APIs                        │
                      │  ├── Aliyun DashScope (Embedding + Reranker) │
                      │  ├── MiniMax M2.7 (LLM + DeepSeek Fallback) │
                      │  └── Qwen-VL (OCR)                           │
                      └─────────────────────────────────────┘
```

---

## 快速启动

### 前置条件

- Python 3.12+（建议使用 `uv` 管理虚拟环境）
- PostgreSQL 16 + pgvector 扩展
- Node.js 18+（前端）

### 1. 配置环境变量

```bash
# backend/.env
MINIMAX_API_KEY=your_api_key_here
MINIMAX_GROUP_ID=your_group_id_here
DEEPSEEK_API_KEY=your_deepseek_key_here
ALIYUN_API_KEY=your_dashscope_key_here
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/novarag
HF_ENDPOINT=https://hf-mirror.com
```

### 2. 启动 PostgreSQL + pgvector

```bash
docker run -d --name nova-rag-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=novarag \
  -p 5433:5432 \
  pgvector/pgvector:pg16
```

### 3. 启动后端

```bash
cd backend
uv run uvicorn src.api.server:app --host 0.0.0.0 --port 5000
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

---

## 核心功能

| 功能 | 状态 | 说明 |
|------|------|------|
| **文档解析** | ✅ | PDF/DOCX/XLSX/CSV/PPTX/MD/TXT |
| **PDF 表格提取** | ✅ | pdfplumber + Markdown 格式 |
| **OCR 多模态** | ✅ | Qwen-VL + 自适应页面选择（最多15页） |
| **多格式索引** | ✅ | Text chunks + Image chunks 独立索引 |
| **Parent-Child 分块** | ✅ | Parent ~2000字符 / Child ~500字符 |
| **向量语义检索** | ✅ | pgvector 1024 维 cosine |
| **BM25 关键词检索** | ✅ | jieba 中文分词 |
| **RRF 混合检索** | ✅ | 向量 + BM25 + RRF 融合 (k=40) |
| **Reranker 精排** | ✅ | DashScope gte-rerank |
| **Self-Query 解析** | ✅ | LLM 解析 doc_name + page_range |
| **Query Rewriter** | ✅ | LLM扩展 + 语义缓存(512条) + PRF |
| **Prompt 压缩** | ✅ | jieba关键词 + 句子评分 (保留80%) |
| **SSE 流式回答** | ✅ | reasoning + answer 双轨 |
| **AI 思考过程** | ✅ | Thought Panel + Reasoning 折叠 |
| **幻觉防御** | ✅ | 严格上下文 + 低相关性过滤 |
| **参考来源标注** | ✅ | [N] 格式 + Source Modal |
| **多轮对话** | ✅ | 历史截断 + Token 管理 |
| **文档预览** | ✅ | PDF/DOCX/MD/CSV 全格式 |
| **@mention 文档** | ✅ | 指定文档范围检索 |
| **图片问答** | ✅ | 图片描述检索 + 多模态上下文 |
| **会话管理** | ✅ | CRUD + 持久化 + 自动标题 |
| **健康检查** | ✅ | /health 端点 |

---

## RAG 评估三维度

| 维度 | 指标 | 实现 |
|------|------|------|
| **检索质量** | Precision@8, Recall@8, MRR, NDCG | ✅ |
| **生成质量** | Context Relevance, Answer Relevance, Faithfulness | ✅ (LLM评分) |
| **系统性能** | Latency, Throughput, Error Rate | ✅ |

**最新测试结果**（10类复杂问题）：

```
Retrieval: Avg NDCG 0.412, Precision@8 82.5%
Generation: Avg CR 0.52, AR 0.76, F 0.48
System: Avg Latency 15.6s (MiniMax M2.7)
Overall Score: 0.469 / 1.0
```

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/api/v1/docs/upload` | 上传文档 |
| GET | `/api/v1/docs` | 文档列表 |
| GET | `/api/v1/docs/{id}/preview` | 文档预览 |
| GET | `/api/v1/docs/{id}/download` | 文档下载 |
| GET | `/api/v1/docs/{id}/images` | 图片列表 |
| GET | `/api/v1/docs/{id}/images/{idx}` | 获取图片 |
| DELETE | `/api/v1/docs/{id}` | 删除文档（含图片清理） |
| POST | `/api/v1/docs/batch-delete` | 批量删除 |
| POST | `/api/v1/chat/completions` | 流式问答 (SSE) |
| GET | `/api/v1/conversations` | 会话列表 |
| GET | `/api/v1/conversations/{id}` | 会话详情 |
| DELETE | `/api/v1/conversations/{id}` | 删除会话 |

---

## 目录结构

```
Nova-RAG/
├── backend/                    # Python FastAPI 后端
│   ├── src/
│   │   ├── api/
│   │   │   ├── routes/         # docs.py, chat.py, conversations.py
│   │   │   ├── database.py     # SQLAlchemy 连接
│   │   │   ├── models.py       # ORM 模型
│   │   │   ├── components.py    # 全局组件初始化
│   │   │   └── server.py       # FastAPI 入口
│   │   └── core/
│   │       ├── chunker/        # Parent-Child 分块
│   │       ├── embedder/       # Aliyun DashScope Embedding
│   │       ├── llm/            # MiniMax M2.7 + DeepSeek Fallback
│   │       ├── ocr/            # Qwen-VL 多模态
│   │       ├── retriever/      # Hybrid + Self-Query + Compressor
│   │       ├── storage/        # pgvector + Image chunks
│   │       └── config.py       # 集中配置
│   └── uploads/                # 上传文件 + 图片存储
├── frontend/                   # React + TypeScript 前端
│   └── src/
│       ├── components/         # ChatArea, Sidebar, DocumentPreviewer
│       ├── hooks/              # useChat, useDocuments, useConversations
│       ├── store/              # Zustand 全局状态
│       └── lib/                # API 客户端
├── tests/
│   ├── test_novatech.py       # 基础功能测试
│   └── test_rag_evaluation_full.py  # RAG 效果评估
├── document/
│   ├── RAG_IMPLEMENTATION.md   # RAG 实现文档
│   └── AGENTS.md               # 开发规范
└── README.md
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Tailwind CSS + Vite + Zustand |
| 后端 | Python 3.12 + FastAPI + Uvicorn |
| 向量数据库 | PostgreSQL 16 + pgvector |
| Embedding | Aliyun DashScope text-embedding-v3 (1024 维) |
| Reranker | Aliyun DashScope gte-rerank |
| LLM | MiniMax M2.7 + DeepSeek (fallback) |
| OCR | Qwen-VL (DashScope) |
| PDF 解析 | pdfplumber + PyMuPDF |
| BM25 | rank-bm25 + jieba |

---

## 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `CHUNK_PARENT_SIZE` | 2000 | Parent chunk 大小 |
| `CHUNK_CHILD_SIZE` | 500 | Child chunk 大小 |
| `RRF_K` | 40 | RRF 融合常数 |
| `RERANK_MIN_SCORE` | 0.5 | Reranker 最低阈值 |
| `RETRIEVER_TOP_K` | 8 | 最终返回 chunk 数 |
| `RECALL_MULTIPLIER` | 8 | 召回放大倍数 |
| `MAX_CONTEXT_TOKENS` | 6000 | 上下文 token 上限 |

---

## 文档导航

| 文档 | 说明 |
|------|------|
| [RAG 实现文档](document/RAG_IMPLEMENTATION.md) | 16个 RAG 概念的实现映射 |
| [开发规范](document/AGENTS.md) | Git 提交规范 + 技术栈 |
| [V1.0 复盘踩坑](docs/v1.0_POST_MORTEM.md) | V1.0 核心问题与解决方案 |
| [V2.0 路线图](docs/v2.0_ROADMAP.md) | 未来演进方向与改进计划 |