# 精准溯源功能开发计划

## 一、功能目标

实现企业级 RAG 精准溯源能力，包括：
1. **引用置信度** - 每个引用显示相似度分数，颜色标记
2. **原文高亮** - 点击引用后在原文档中高亮对应位置
3. **溯源链路** - 展示 query → chunk → 父chunk → 原文 的完整链路
4. **引用评分** - 用户可标记引用"有帮助/无帮助"

## 二、后端改动

### 2.1 修改检索返回结构

**文件**: `backend/src/core/retriever/hybrid_search.py`

检索结果新增字段：
```python
{
    "index": 1,                    # 引用编号
    "doc_id": "doc_xxx",           # 文档ID
    "source_doc": "filename.pdf",  # 源文档名
    "page_number": 5,              # 页码（如果有）
    "content": "chunk text",       # chunk 内容
    "score": 0.85,                # 相似度分数 (0-1)
    "score_type": "combined",     # 分数类型：vector/bm25/combined
    "chunk_index": 12,             # chunk 在文档中的索引
    "parent_chunk_index": 2,       # 父chunk索引（用于溯源链路）
    "start_pos": 150,              # chunk在原文中的起始位置
    "end_pos": 450,                # chunk在原文中的结束位置
    "doc_name": "filename.pdf",     # 文档名
}
```

**改动点**：
- `_search_vectors()` 返回每个 chunk 的向量相似度分数
- `_search_bm25()` 返回每个 chunk 的 BM25 分数
- `search()` 方法合并分数时保留原始分数
- 在返回结果中增加 `start_pos`, `end_pos`, `chunk_index`, `parent_chunk_index`

### 2.2 添加引用评分 API

**文件**: `backend/src/api/routes/citations.py` (新文件)

**端点**:
- `POST /api/v1/citations/{citation_id}/feedback` - 提交反馈
  ```json
  {
    "helpful": true,
    "conversation_id": "conv_xxx",
    "query": "用户问题",
    "citation_id": 1,
    "doc_id": "doc_xxx",
    "content": "chunk内容"
  }
  ```

### 2.3 修改文档内容 API

**文件**: `backend/src/api/routes/docs.py`

**改动**: `GET /docs/{id}/content` 返回结果新增 `chunks` 数组：
```json
{
  "doc_id": "xxx",
  "name": "xxx.pdf",
  "chunks": [
    {
      "index": 0,
      "content": "...",
      "start_pos": 0,
      "end_pos": 200
    }
  ]
}
```

## 三、前端改动

### 3.1 类型定义更新

**文件**: `frontend/src/types/index.ts`

```typescript
export interface Reference {
  index: number
  doc_id: string
  source_doc?: string
  page_number?: number
  content: string
  score: number              // 新增
  score_type: string         // 新增
  chunk_index: number         // 新增
  parent_chunk_index: number  // 新增
  start_pos: number          // 新增
  end_pos: number            // 新增
}
```

### 3.2 SourceCard 组件升级

**文件**: `frontend/src/components/chat/SourceCard.tsx`

**改动**:
- 显示置信度分数（0-100%）
- 颜色编码：>=0.8 绿色，0.6-0.8 黄色，<0.6 红色
- 显示分数来源标签（向量/BM25/混合）

### 3.3 SourceModal 组件升级

**文件**: `frontend/src/components/chat/SourceModal.tsx`

**改动**:
- 添加置信度指示器（进度条+分数）
- 添加"跳转到原文"按钮
- 添加溯源链路面板（当前chunk → 父chunk → 原文）

### 3.4 DocumentPreviewer 高亮功能

**文件**: `frontend/src/components/DocumentPreviewer.tsx`

**改动**:
- 新增 `highlightRanges` prop
- 高亮指定位置文本（黄色背景）
- 支持多个高亮区域
- 高亮样式：`bg-yellow-200 dark:bg-yellow-900/50`

### 3.5 CitationBadge 组件升级

**文件**: `frontend/src/components/chat/CitationBadge.tsx`

**改动**:
- 添加置信度颜色底色
- Hover 显示分数预览

### 3.6 新增 CitationChainPanel 组件

**文件**: `frontend/src/components/chat/CitationChainPanel.tsx`

**功能**:
- 展示溯源链路：Query → Chunk → Parent Chunk → Original Text
- 可视化链路图
- 显示每个层级的关键信息

### 3.7 ChatArea 整合

**文件**: `frontend/src/components/ChatArea.tsx`

**改动**:
- 点击 SourceCard 时传递 highlightRanges 给 DocumentPreviewer
- 维护当前高亮引用状态

## 四、数据流

```
用户提问
    ↓
后端检索（带分数）
    ↓
返回 references（含 score, start_pos, end_pos）
    ↓
前端 SourceCard 显示置信度颜色
    ↓
用户点击引用
    ↓
SourceModal 显示详情 + 溯源链路
    ↓
点击"跳转到原文"
    ↓
DocumentPreviewer 高亮对应位置
```

## 五、置信度计算

```
最终置信度 = w_vector * vector_score + w_bm25 * bm25_score

其中：
- w_vector = 0.7（向量检索权重）
- w_bm25 = 0.3（关键词检索权重）
- vector_score: 0-1（余弦相似度）
- bm25_score: 归一化到 0-1
```

## 六、颜色规范

| 置信度 | 分数区间 | 颜色 |
|--------|---------|------|
| 高 | >= 0.8 | emerald (绿) |
| 中 | 0.6-0.8 | amber (黄) |
| 低 | < 0.6 | red (红) |

## 七、执行步骤

### Step 1: 后端 - 检索分数
1. 修改 `hybrid_search.py` 返回分数
2. 修改 `retriever/__init__.py` 传递分数
3. 修改 `chat/completions.py` 在 references 中包含分数
4. 测试检索返回分数

### Step 2: 后端 - 文档 chunk 映射
1. 修改 `routes/docs.py` 返回 chunks 数组
2. 确保 chunk 有 start_pos, end_pos

### Step 3: 后端 - 引用反馈 API
1. 创建 `routes/citations.py`
2. 实现反馈存储（可先存内存/文件）

### Step 4: 前端 - 类型和基础组件
1. 更新 `types/index.ts`
2. 更新 `SourceCard` 显示置信度
3. 更新 `CitationBadge` 颜色

### Step 5: 前端 - SourceModal 升级
1. 添加置信度指示器
2. 添加溯源链路面板
3. 添加"跳转到原文"按钮

### Step 6: 前端 - DocumentPreviewer 高亮
1. 添加 highlightRanges prop
2. 实现文本高亮逻辑
3. 整合到 ChatArea

### Step 7: 端到端测试
1. 启动服务
2. 上传文档
3. 提问验证
4. 检查所有功能

## 八、验收标准

1. ✅ 每个引用卡片显示置信度分数和颜色
2. ✅ 点击引用后文档预览器中高亮对应位置
3. ✅ SourceModal 显示溯源链路
4. ✅ 用户可标记引用有帮助/无帮助
5. ✅ 置信度分数与实际检索质量匹配
6. ✅ 亮/暗主题下颜色正确显示
