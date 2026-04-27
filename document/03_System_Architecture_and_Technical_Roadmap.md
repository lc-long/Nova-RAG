# 系统架构与技术路线图 (System Architecture & Roadmap)

## 1. 逻辑架构 (Logical Architecture)
系统采用三层分层架构，确保职责单一，便于后续维护与扩展。

### 1.1 前端展现层 (Frontend - React)
- **核心框架**: React 18/19 + Vite + Tailwind CSS。
- **职责**: 
  - 构建高响应式的聊天交互界面。
  - 实现 Markdown 实时流式渲染（处理 SSE 数据流）。
  - 处理文件上传的前端校验与进度展示。
- **扩展性设计**: 预留多主题切换（Theme Context）与国际化（i18n）接口。

### 1.2 业务逻辑层 (Backend - Go/Gin)
- **核心框架**: Go 1.2x + Gin Framework + GORM。
- **职责**: 
  - **网关鉴权**: 负责用户登录、权限控制（MVP 阶段暂留空，预留 OAuth2 接口）。
  - **业务编排**: 管理文档上传记录、对话历史持久化。
  - **中转通信**: 作为前端与 AI 算法层之间的桥梁，分发检索请求。
- **数据库**: MVP 阶段使用 **SQLite**（单文件存储，部署简单）；V2 阶段平滑迁移至 **PostgreSQL**。

### 1.3 AI 数据层 (AI Service - Python/LangChain)
- **核心技术**: Python 3.10+ + LangChain + ChromaDB + Minimax API。
- **职责**: 
  - **文档处理**: PDF/Docx 解析、清洗及父子块切片逻辑。
  - **向量化与存储**: 调用 Embedding 模型将文本存入 Chroma 向量库。
  - **RAG 调度**: 执行语义检索，拼接 Context 提交给 Minimax m2.7 生成答案。

## 2. 核心数据流 (Data Flow)

### 2.1 文档入库流程
1. 用户通过前端上传文件 -> **Go 后端**接收。
2. **Go 后端**记录元数据并调用 **Python AI 层** 接口。
3. **Python 层** 进行父子切片 (Parent-Child Splitting) -> 向量化 -> 存入 **ChromaDB**。
4. 返回成功状态至前端。

### 2.2 问答对话流程 (RAG Loop)
1. 用户发起提问 -> **Go 后端** 转发至 **Python 层**。
2. **Python 层** 提取用户问题向量 -> 在 **ChromaDB** 检索最相关的 Child Chunks -> 关联获取对应的 Parent Chunks。
3. 构造 Prompt -> 调用 **Minimax m2.7**。
4. **Minimax** 返回流式结果 -> **Python 层** 通过 **SSE (Server-Sent Events)** 转发给 **Go 后端** -> **前端**。

## 3. 技术路线图 (Technical Roadmap)

### V1: MVP 阶段 (当前目标)
- [ ] 实现基础的 PDF/Markdown 解析入库。
- [ ] 实现基于父子检索的 RAG 问答闭环。
- [ ] 前端流式对话界面。
- [ ] 规范的 Git Commit 记录（强制要求 scope）。

### V2: 性能与稳定性增强 (后续扩展)
- [ ] **数据库升级**: 将 SQLite 迁移至 PostgreSQL，增加用户多租户隔离。
- [ ] **检索优化**: 引入 Rerank（重排序）机制，进一步提升问答精准度。
- [ ] **多模态扩展**: 支持文档内图片的 OCR 解析与多模态模型调用。

### V3: 企业级生态接入 (高级阶段)
- [ ] **大规模向量存储**: 引入 Milvus 或 Pinecone 向量数据库。
- [ ] **系统监控**: 集成 Prometheus/Grafana 监控 API 延迟与 Token 消耗。
- [ ] **外部插件**: 支持联网搜索、日历接入等 Tool Use 能力。

## 4. 关键技术约束 (Reminders for Claude Code)
- **隔离性**: Go 后端不应直接处理向量计算，所有 AI 逻辑必须限制在 Python 服务内。
- **无状态**: 后端服务尽量保持无状态，以便于后续容器化（Docker/K8s）部署。