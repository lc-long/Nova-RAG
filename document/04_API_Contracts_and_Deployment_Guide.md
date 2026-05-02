# API 契约与部署指南 (API Contracts & Deployment Guide)

## 1. 核心 API 契约 (Core API Contracts)

所有接口遵循 RESTful 风格，基础路径为 `/api/v1`。

### 1.1 文档管理
- **上传文档**: `POST /docs/upload`
  - **Payload**: `multipart/form-data` (file: File)
  - **Response**: `201 Created` { "doc_id": "uuid", "status": "processing" }
- **文档列表**: `GET /docs`
  - **Response**: `200 OK` [ { "id": "uuid", "name": "manual.pdf", "size": "2MB", "upload_at": "timestamp" } ]
- **删除文档**: `DELETE /docs/:id`

### 1.2 AI 智能对话 (核心)
- **发起对话**: `POST /chat/completions`
  - **Request Body**:
    ```json
    {
      "messages": [
        { "role": "user", "content": "公司报销标准是什么？" }
      ],
      "stream": true
    }
    ```
  - **Response (SSE)**: 
    - 数据格式: `data: {"content": "...", "references": [...]}`
    - **约束**: `references` 中严禁包含 `<cite>` 标签。引用的片段需包含 `source_doc` 和 `page_number`。

## 2. 内部服务间通信 (Go <-> Python)
- **协议**: HTTP/JSON (MVP 阶段不引入 gRPC 以简化部署)。
- **路径**: `POST http://localhost:5000/process_query`
- **逻辑**: Go 后端接收前端请求后，透传给 Python 服务进行向量检索与大模型调用。

## 3. 部署环境要求 (Environment Requirements)

### 3.1 基础环境
- **OS**: Windows 11 (PowerShell/Git Bash)
- **Backend**: Go 1.20+
- **Frontend**: Node.js 18+ & NPM/PNPM
- **AI Service**: Python 3.10+

### 3.2 关键依赖库
- **Go**: `github.com/gin-gonic/gin`, `gorm.io/gorm`, `gorm.io/driver/sqlite`
- **Python**: `langchain`, `langchain-community`, `chromadb`, `minimax-python-sdk`
- **Frontend**: `axios`, `react-markdown`, `lucide-react` (图标库)

## 4. 部署步骤 (Step-by-Step Deployment)

### Step 1: 环境配置
1. 创建 `.env` 文件，配置 `MINIMAX_API_KEY` 和 `MINIMAX_GROUP_ID`。
2. 配置 Python 虚拟环境: `python -m venv venv` 并在其中安装依赖。

### Step 2: 数据库初始化
- 系统启动时，Go 后端自动通过 GORM 创建 `lumina.db` (SQLite)。
- Python 服务启动时，自动在 `./vector_db` 目录下初始化 Chroma 向量库。

### Step 3: 启动流程 (Claude Code 需编写一键启动脚本)
1. 启动 Python 服务 (Port 5000)。
2. 启动 Go 后端 (Port 8080)。
3. 启动 React 开发服务器。

## 5. 故障排查与日志 (Troubleshooting)
- **CGO 问题**: 在 Windows 下编译 Go 时，若报错 `gcc not found`，需安装 Mingw-w64 并确保 `CGO_ENABLED=1`。
- **SSE 响应中断**: 检查 Nginx 或代理是否开启了 Buffer，确保流式数据不被拦截。
- **引用错误**: 若前端出现 `cite` 相关解析报错，立即检查 Python 端的 Prompt 模版，确保输出不含非法标签。