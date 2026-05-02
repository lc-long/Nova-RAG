# Nova-RAG 系统实现文档

## 概述

Nova-RAG 是一个企业级 RAG（Retrieval-Augmented Generation）知识库问答系统，基于 FastAPI + React + PostgreSQL/pgvector 构建。本文档对照 RAG 核心概念，说明系统的实现现状。

---

## 1. 文档解析 (Document Parsing)

**状态**: ✅ 已实现

支持的文档格式：
- **PDF**: PyMuPDF + pdfplumber 文本提取，表格识别
- **DOCX**: python-docx 段落解析
- **XLSX**: openpyxl 单元格提取
- **CSV**: Python csv 模块
- **PPTX**: python-pptx 幻灯片提取
- **Markdown**: 结构化标题分割
- **TXT**: 纯文本读取

**OCR 多模态解析**:
- 使用 Qwen-VL (DashScope) 视觉模型识别 PDF 中的图片/图表
- **持久化存储**: 图片文件存储在 `uploads/images/{doc_id}/` 目录，不再使用临时目录
- **独立索引**: ImageChunk 表存储图片元数据（路径、描述、页码、embedding）
- **图片检索**: 识别图片相关查询时，额外检索相关图片作为上下文
- **自适应策略**: 前 3 页必做 OCR + 含视觉指标的页面（少量文字、含 chart/figure/diagram 关键词）
- OCR 结果基于文件 MD5 哈希缓存，避免重复调用

**ImageChunk 表结构**:
- `id`: 图片 chunk ID
- `doc_id`: 所属文档 ID
- `page_num`: 页码
- `image_idx`: 图片索引
- `description`: Vision 模型生成的图片描述
- `image_path`: 图片文件路径
- `embedding`: 描述文本的向量嵌入

**位置**: `backend/src/core/chunker/pdf_parser.py`, `backend/src/core/ocr/__init__.py`, `backend/src/core/storage/vector_store.py`

---

## 2. 分块 (Chunking)

**状态**: ✅ 已实现

采用 **Parent-Child 分块策略**:

| 层级 | 大小 | 用途 |
|------|------|------|
| Parent Chunk | ~2000 字符 | 检索后返回给 LLM 的完整上下文 |
| Child Chunk | ~500 字符 | 用于嵌入和检索的小粒度单元 |

**特性**:
- **表格感知**: 大表格按行拆分为子表格，每个子表格保留表头
- **Markdown 感知**: 基于标题层级分割，保留 heading_path
- **段落保护**: 使用 `\x00P\x00` 哨兵标记保护段落边界

**位置**: `backend/src/core/chunker/parent_child.py`

---

## 3. 嵌入 (Embedding)

**状态**: ✅ 已实现

- **模型**: Aliyun DashScope text-embedding-v3
- **维度**: 1024
- **批量处理**: 每批 6 个文本，批间休眠 0.1s（避免限流）
- **最大文本长度**: 6000 字符

**位置**: `backend/src/core/embedder/aliyun_embedder.py`

---

## 4. 向量数据库 (Vector Database)

**状态**: ✅ 已实现

- **数据库**: PostgreSQL 16 + pgvector 扩展
- **距离度量**: cosine 距离
- **表结构**:
  - `document_chunks` 表存储文本 chunk 内容、embedding、metadata
  - `image_chunks` 表存储图片元数据、描述、embedding
- **端口**: 5433 (Docker 容器)

**位置**: `backend/src/core/storage/vector_store.py`

---

## 5. 混合检索 (Hybrid Search)

**状态**: ✅ 已实现

采用 **向量检索 + BM25 关键词检索 + 图片检索 + RRF 融合**:

```
用户查询
  ├── 向量检索 (pgvector, cosine距离) ─────────────────┐
  ├── BM25 检索 (jieba 分词, rank-bm25)                   │
  └── 图片检索 (图片描述 embedding) ← 仅图片相关查询       │
        │                                                │
        ▼                                                │
   RRF 融合 (Reciprocal Rank Fusion)                     │
        │                                                │
        ▼                                                │
   Cross-Encoder 重排序 ─────────────────────────────────┘
```

**图片查询识别**: 通过关键词匹配判断是否为图片查询，如"图片"、"图表"、"fig"、"image"、"照片"等

**RRF 公式**: `score = 1/(k + dense_rank) + 1/(k + sparse_rank)`
- k = 40 (可配置)
- 仅在一个通道出现的 chunk，另一通道 rank = 1000

**并行执行**: 向量检索和 BM25 检索通过 `asyncio.gather()` 并行执行

**位置**: `backend/src/core/retriever/hybrid_search.py`, `backend/src/core/retriever/bm25_index.py`

---

## 6. Rerank (重排序)

**状态**: ✅ 已实现

- **模型**: Aliyun DashScope gte-rerank (Cross-Encoder)
- **最低分数阈值**: 0.05 (跨语言场景需要较低阈值)
- **执行时机**: RRF 融合之后

**位置**: `backend/src/core/retriever/aliyun_reranker.py`

---

## 7. 查询扩展 (Query Expansion)

**状态**: ⚠️ 部分实现

**QueryRewriter** 提供两种扩展方式:

1. **LLM 扩展**: 调用 LLM 生成 3-5 个查询变体（含中英文翻译）
2. **模式扩展**: 基于预定义模式表的关键词替换

**当前模式表** (部分):
- "饼状图" → ["pie chart", "饼图", "Revenue Distribution"]
- "架构图" → ["architecture", "系统架构", "Technical Architecture"]
- "限制高度" → ["限高", "限制高"]

**局限**: 模式表是硬编码的，新领域需要手动添加

**位置**: `backend/src/core/retriever/query_rewriter.py`

---

## 8. 自查询 (Self-Query)

**状态**: ✅ 已实现

**功能**: 自动解析用户查询中的隐含条件，将自然语言转为结构化查询

**流程**:
1. LLM 解析用户查询，提取:
   - `semantic_query`: 核心语义问题
   - `doc_name`: 文档名称关键词
   - `page_range`: 页码范围
2. 根据 `doc_name` 模糊匹配文档 ID，缩小检索范围
3. 根据 `page_range` 过滤检索结果

**示例**:
- 用户: "nova tech文档中的架构图"
  → semantic: "架构图", doc_name: "nova tech"
- 用户: "第3页的图表是什么意思"
  → semantic: "图表是什么意思", page_range: [3, 3]

**位置**: `backend/src/core/retriever/self_query.py`

---

## 9. 提示压缩 (Prompt Compression)

**状态**: ✅ 已实现

**功能**: 从检索到的 chunk 中提取与查询相关的句子，减少无关内容

**流程**:
1. 将每个 chunk 拆分为句子
2. 基于关键词重叠为每个句子打分
3. 按分数排序，保留分数 > 0 的句子（最多保留 70%）
4. 按原始顺序重组，标记为 "[提取的相关内容]"

**关键词提取**: 中文按词（≥2字）、英文按词（≥3字），过滤停用词

**位置**: `backend/src/core/retriever/compressor.py`

---

## 10. RAG 提示工程 (RAG Prompt Engineering)

**状态**: ⚠️ 部分实现

**System Prompt 包含的指令**:
1. 严格基于上下文回答
2. 多场景分点列举
3. 条件调整规则（基础值 + 调整规则 = 最终结果）
4. 否定推理（未列出 = 不允许）
5. 版本对比（以最新版本为准）
6. 跨语言匹配（中英文对应关系）
7. 不猜测图表类型
8. 如实回答

**局限**: 未做 few-shot 示例、未做动态 prompt 模板

**位置**: `backend/src/core/llm/minimax.py` (`_build_prompt` 方法)

---

## 11. RAG 效果评估三维度

**状态**: ❌ 未实现

**需要实现的维度**:

### 检索质量
- Precision@k: 前 k 个结果中相关文档占比
- Recall@k: 前 k 个结果覆盖的相关文档比例
- MRR: 第一个相关结果的排名倒数
- NDCG: 考虑相关性等级和排名位置

### 生成质量
- CR (Context Relevance): 答案是否基于检索内容
- AR (Answer Relevance): 回答是否解决用户问题
- F (Faithfulness): 生成内容是否有幻觉

### 系统性能
- 延迟: 端到端响应时间
- 吞吐量: 并发请求数
- 错误率: 失败请求占比

---

## 12. Advanced RAG

**状态**: ❌ 未实现

**缺失的高级技术**:
- 迭代检索 (Iterative Retrieval): 根据初始结果重新检索
- 假设文档嵌入 (Hypothetical Document Embedding, HyDE)
- 自适应检索 (Adaptive Retrieval): 根据查询复杂度选择检索策略
- 链式推理 (Chain-of-Thought Retrieval)

---

## 13. Modular RAG

**状态**: ❌ 未实现

**当前管道是固定的**:
```
Query → SelfQuery → QueryExpansion → HybridSearch → RRF → Rerank → Compress → LLM
```

**理想的 Modular RAG 应该**:
- 每个模块可插拔、可替换
- 有统一的编排器 (Orchestrator) 负责调度
- 可以根据查询类型动态选择模块组合
- 支持 A/B 测试不同模块组合

---

## 14. 多数据库

**状态**: ❌ 未实现

当前只使用 PostgreSQL + pgvector 单一数据库。未实现:
- 多向量数据库联合检索
- 知识图谱数据库 (Neo4j)
- 关系型数据库 + 向量数据库混合查询

---

## 15. 数据清洗 (Data Cleaning)

**状态**: ⚠️ 部分实现

**当前清洗**:
- PDF 文本提取后去除多余空白
- 表格格式化为 Markdown
- OCR 文本合并到对应页面

**缺失**:
- 去重 (near-duplicate detection)
- 实体识别和标准化
- 元数据自动提取（作者、日期、标签）
- 质量评分和过滤

---

## 16. 预处理 (Preprocessing)

**状态**: ⚠️ 部分实现

**当前预处理**:
- 文本提取和格式化
- 分块和嵌入
- BM25 索引构建

**缺失**:
- 元数据提取和结构化
- 实体识别 (NER)
- 关系抽取
- 知识图谱构建

---

## 模块映射表

| Modular RAG 模块 | Nova-RAG 实现 | 状态 |
|------------------|---------------|------|
| Indexing (索引) | ParentChildChunker + AliyunEmbedder + pgvector | ✅ |
| Image Indexing (图片索引) | Qwen-VL + ImageChunk + image embedding | ✅ |
| Pre-Retrieval (检索前) | SelfQueryRetriever + QueryRewriter | ✅ |
| Retrieval (检索) | HybridRetriever (向量 + BM25 + 图片 + RRF) | ✅ |
| Post-Retrieval (检索后) | AliyunReranker + Compressor | ✅ |
| Generation (生成) | MinimaxClient + DeepSeekClient (fallback) | ✅ |
| Orchestrator (编排器) | 固定管道，无动态编排 | ❌ |

---

## 配置参数

所有 RAG 参数集中在 `backend/src/core/config.py`，通过 `backend/.env` 覆盖:

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `CHUNK_PARENT_SIZE` | 2000 | Parent chunk 大小 |
| `CHUNK_CHILD_SIZE` | 500 | Child chunk 大小 |
| `CHUNK_OVERLAP` | 100 | Chunk 重叠字符数 |
| `RRF_K` | 40 | RRF 融合常数 |
| `RERANK_MIN_SCORE` | 0.05 | Reranker 最低相关性阈值 |
| `RETRIEVER_TOP_K` | 8 | 最终返回 chunk 数 |
| `RECALL_MULTIPLIER` | 8 | 召回放大倍数 |
| `MAX_CONTEXT_TOKENS` | 6000 | 上下文 token 上限 |
| `DISTANCE_THRESHOLD` | 10.0 | 向量距离阈值 |
