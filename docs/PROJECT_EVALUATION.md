# Nova-RAG 项目评估报告

**评估时间**: 2026-05-01
**评估版本**: V2.0 (Post-OCR)

---

## 一、整体架构

```
Frontend (React + TS) ──SSE──> Backend (Python FastAPI :5000)
                                    ├── PostgreSQL + pgvector (向量存储)
                                    ├── DashScope (Embedding + Reranking + OCR)
                                    ├── rank-bm25 + jieba (BM25)
                                    └── MiniMax M2.7 (LLM)
```

## 二、核心功能清单

### 已完成功能

| 功能 | 状态 | 说明 |
|------|------|------|
| PDF 解析 | ✅ | pdfplumber + PyMuPDF 双引擎 |
| 表格提取 | ✅ | 表格 → Markdown，原子 chunk |
| OCR 识别 | ✅ | Qwen-VL + 页面截图回退 |
| 多格式支持 | ✅ | PDF/DOCX/XLSX/CSV/PPTX/MD/TXT |
| 向量检索 | ✅ | pgvector 1024 维 |
| BM25 检索 | ✅ | jieba 分词 + 文本归一化 |
| RRF 融合 | ✅ | rank-based，k=60 |
| Reranker | ✅ | DashScope gte-rerank，阈值 0.3 |
| Query Rewriter | ✅ | LLM 扩展 + 短查询跳过 + 缓存 |
| 多轮对话 | ✅ | 前端发送 10 轮历史 + 后端截断 |
| PDF 预览 | ✅ | pdfjs-dist Canvas 渲染 |
| DOCX 预览 | ✅ | mammoth.js 转 HTML |
| @mention 文档 | ✅ | 指定文档范围检索 |
| 引用交互 | ✅ | [N] 标注 + Source Modal |
| 思考过程 | ✅ | Thought Panel + Reasoning 折叠 |

### 测试结果

| 指标 | 结果 |
|------|------|
| 准确率 | **90.9%** |
| 幻觉率 | **0%** |
| 平均响应 | **11-16 秒** |
| 测试文档 | NovaTech Documentation (英文，13 页) |

## 三、关键代码文件

### 后端核心

| 文件 | 职责 |
|------|------|
| `backend/src/api/routes/docs.py` | 文档上传、预览、下载、删除 |
| `backend/src/api/routes/chat.py` | 聊天接口、SSE 流式输出 |
| `backend/src/core/chunker/pdf_parser.py` | PDF 解析、表格提取、图片提取 |
| `backend/src/core/chunker/parent_child.py` | Parent-Child 双层分块 |
| `backend/src/core/retriever/hybrid_search.py` | Hybrid Retriever (向量+BM25+RRF) |
| `backend/src/core/retriever/query_rewriter.py` | 查询改写 |
| `backend/src/core/retriever/aliyun_reranker.py` | Reranker |
| `backend/src/core/ocr/__init__.py` | OCR 处理 |
| `backend/src/core/llm/minimax.py` | MiniMax LLM 调用 |
| `backend/src/core/storage/vector_store.py` | pgvector 存储 |

### 前端核心

| 文件 | 职责 |
|------|------|
| `frontend/src/App.tsx` | 全局状态、布局 |
| `frontend/src/components/Sidebar.tsx` | 文档列表、会话列表 |
| `frontend/src/components/ChatArea.tsx` | 聊天界面、SSE 渲染 |
| `frontend/src/components/DocumentPreviewer.tsx` | 文档预览 |

## 四、已解决问题

| 问题 | 解决方案 |
|------|----------|
| Go-Python 双服务架构 | 统一为 Python 单体 |
| ChromaDB 不稳定 | 迁移到 pgvector |
| PDF 表格碎片化 | 表格预拆分 + Markdown |
| 无 OCR 支持 | Qwen-VL + 页面截图 |
| 检索精度低 | Hybrid + RRF + Reranker |
| 多轮对话断裂 | 前端发送历史 + 后端截断 |
| PDF 预览白屏 | pdfjs-dist Canvas 渲染 |
| IDM 下载劫持 | XMLHttpRequest + Blob URL |
| 中文文件名编码 | urllib.parse.quote |
| 同步阻塞 | 全面异步化 (httpx + asyncio) |
| Token 估算不准 | 中文 1.5 token/字 + 英文 0.25 token/字符 |
| OCR 结果错位 | 插入到对应页面 chunk |
| OCR 无缓存 | 基于文件 MD5 缓存 |
| 数据库连接池重复 | 统一 engine/session |
| README 过时 | 更新为当前架构 |

## 五、待优化问题

### P0 (高优先级)

| 问题 | 建议 | 状态 |
|------|------|------|
| 同步阻塞 | 异步化所有外部 API 调用 | ✅ 已完成 |
| 数据库连接池重复 | 统一 engine/session | ✅ 已完成 |
| Token 估算不准 | 使用 tiktoken 或调整系数 | ✅ 已完成 |

### P1 (中优先级)

| 问题 | 建议 | 状态 |
|------|------|------|
| OCR 结果位置错位 | 插入到对应页面 chunk | ✅ 已完成 |
| OCR 无缓存 | 基于文件 hash 缓存 | ✅ 已完成 |
| 缺少单元测试 | pytest 覆盖核心逻辑 | ⏳ 待优化 |
| README 过时 | 更新为当前架构 | ✅ 已完成 |

### P2 (低优先级)

| 问题 | 建议 | 状态 |
|------|------|------|
| 向量索引优化 | 添加 HNSW/IVFFlat | ⏳ 待优化 |
| 前端环境变量化 | VITE_API_BASE_URL | ✅ 已完成 |
| 添加 /health 端点 | 健康检查 | ✅ 已完成 |
| Redis 缓存 | 查询结果缓存 | ⏳ 待优化 |
| SSE 错误事件 | 错误事件类型 | ✅ 已完成 |

## 六、环境变量配置

```env
# .env 文件位置: backend/.env

# Aliyun DashScope (Embedding + Reranker + OCR)
ALIYUN_API_KEY=sk-xxx

# MiniMax (LLM)
MINIMAX_API_KEY=sk-xxx
MINIMAX_GROUP_ID=xxx

# Database
DATABASE_URL=postgresql://...

# HuggingFace Mirror
HF_ENDPOINT=https://hf-mirror.com
```

## 七、启动命令

```bash
# 后端
cd backend
python -m uvicorn src.api.server:app --host 0.0.0.0 --port 5000

# 前端
cd frontend
npm run dev
```

## 八、测试命令

```bash
# RAG 测试
cd tests
python rag_test.py <doc_id>

# NovaTech 文档测试
python test_novatech.py
```
