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
│  Vite        │      │  ├── Core: chunker/embedder/retriever/llm/ocr │
└──────────────┘      │  └── Storage: PostgreSQL + pgvector  │
                      └──────────────┬──────────────────────┘
                                     │
                      ┌──────────────┴──────────────────────┐
                      │  PostgreSQL + pgvector (port 5433)    │
                      │  Docker: pgvector/pgvector:pg16       │
                      └─────────────────────────────────────┘
                      ┌─────────────────────────────────────┐
                      │  External APIs                        │
                      │  ├── Aliyun DashScope (Embedding + Reranker) │
                      │  ├── MiniMax M2.7 (LLM + Query Rewrite)     │
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
ALIYUN_API_KEY=your_dashscope_key_here
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/novarag
HF_ENDPOINT=https://hf-mirror.com
```

### 2. 启动 PostgreSQL + pgvector

```bash
docker run -d --name pgvector \
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
| 文档上传 / 入库 | ✅ | PDF/DOCX/XLSX/CSV/PPTX/MD/TXT |
| PDF 表格提取 | ✅ | pdfplumber + Markdown 格式 |
| OCR 图片识别 | ✅ | Qwen-VL + 页面截图回退 |
| 向量语义检索 | ✅ | pgvector 1024 维 |
| BM25 关键词检索 | ✅ | jieba 中文分词 |
| RRF 混合检索 | ✅ | 向量 + BM25 + RRF 融合 |
| Reranker 精排 | ✅ | DashScope gte-rerank |
| Query Rewriter | ✅ | LLM 扩展 + 短查询跳过 |
| SSE 流式回答 | ✅ | 双轨制：reasoning + answer |
| AI 思考过程展示 | ✅ | Thought Panel + Reasoning 折叠 |
| 幻觉防御 | ✅ | 严格上下文 + 低相关性过滤 |
| 参考来源标注 | ✅ | [N] 格式 + Source Modal |
| 多轮对话 | ✅ | 历史截断 + Token 管理 |
| 文档预览 | ✅ | PDF/DOCX/MD/CSV 全格式 |
| @mention 文档 | ✅ | 指定文档范围检索 |
| 会话管理 | ✅ | CRUD + 持久化 + 自动标题 |
| 健康检查 | ✅ | /health 端点 |

---

## 测试结果

| 指标 | 结果 |
|------|------|
| 准确率 | **90.9%** |
| 幻觉率 | **0%** |
| 平均响应 | **11-16 秒** |
| 测试文档 | NovaTech Documentation (英文，13 页) |

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/api/v1/docs/upload` | 上传文档 |
| GET | `/api/v1/docs` | 文档列表 |
| GET | `/api/v1/docs/{id}/preview` | 文档预览 |
| GET | `/api/v1/docs/{id}/download` | 文档下载 |
| DELETE | `/api/v1/docs/{id}` | 删除文档 |
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
│   │   ├── api/               # API 路由、数据库、模型
│   │   │   ├── routes/        # docs.py, chat.py, conversations.py
│   │   │   ├── database.py    # SQLAlchemy 连接
│   │   │   ├── models.py      # ORM 模型
│   │   │   ├── components.py  # 全局组件初始化
│   │   │   └── server.py      # FastAPI 入口
│   │   └── core/
│   │       ├── chunker/       # 文档解析 (PDF/DOCX/XLSX/PPTX)
│   │       ├── embedder/      # Aliyun DashScope Embedding
│   │       ├── llm/           # MiniMax M2.7 客户端
│   │       ├── ocr/           # Qwen-VL OCR 处理
│   │       ├── retriever/     # Hybrid Retriever + Reranker
│   │       └── storage/       # pgvector 存储
│   └── uploads/               # 上传文件暂存
├── frontend/                   # React + TypeScript 前端
│   └── src/
│       ├── components/         # ChatArea, Sidebar, DocumentPreviewer
│       ├── config.ts           # API 配置
│       └── App.tsx             # 全局状态
├── tests/                      # 测试脚本
├── docs/                       # 项目文档
└── README.md
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Tailwind CSS + Vite |
| 后端 | Python 3.12 + FastAPI + Uvicorn |
| 向量数据库 | PostgreSQL 16 + pgvector |
| Embedding | Aliyun DashScope text-embedding-v3 (1024 维) |
| Reranker | Aliyun DashScope gte-rerank |
| LLM | MiniMax M2.7 |
| OCR | Qwen-VL (DashScope) |
| PDF 解析 | pdfplumber + PyMuPDF |
| BM25 | rank-bm25 + jieba |

---

## 文档导航

| 文档 | 说明 |
|------|------|
| [V1.0 复盘踩坑](docs/v1.0_POST_MORTEM.md) | V1.0 核心问题与解决方案 |
| [V2.0 路线图](docs/v2.0_ROADMAP.md) | 未来演进方向与改进计划 |
| [项目评估报告](docs/PROJECT_EVALUATION.md) | 当前状态评估与优化建议 |
