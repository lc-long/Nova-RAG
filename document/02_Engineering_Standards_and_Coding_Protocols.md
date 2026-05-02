# 工程规范与代码协议 (Engineering Standards & Coding Protocols)

## 1. 总体开发原则
- **模块化优先**: 严禁编写“巨型文件”。每个文件的逻辑代码建议控制在 200 行以内，核心业务逻辑必须从 Controller/Handler 层抽离至 Service 层。
- **高内聚低耦合**: 前端 UI 与业务逻辑分离，后端业务逻辑与 AI 检索算法分离。
- **防御式编程**: 对所有外部输入（尤其是 AI 返回的非结构化数据）进行严格校验和异常处理。

## 2. 版本控制规范 (Git Standards)
- **提交语言**: 必须使用规范的 **英文 (Normative English)**。
- **提交格式**: 必须严格遵循 Angular 规范，格式为 `type(scope): description`。
  - **type**:
    - `feat`: 新功能 (New feature)
    - `fix`: 修复 Bug (Bug fix)
    - `docs`: 文档变更 (Documentation only)
    - `style`: 代码格式调整 (Formatting, missing semi-colons, etc)
    - `refactor`: 重构 (Code change that neither fixes a bug nor adds a feature)
    - `perf`: 性能优化 (Performance improvement)
  - **scope**: 必须明确指出本次提交影响的系统模块。可选范围包括但不限于：
    - `ui` (前端 React 组件/样式)
    - `api` (Go 后端接口/路由)
    - `rag` (Python 检索核心/大模型交互)
    - `db` (数据库结构/查询逻辑)
    - `config` (环境变量/构建配置)
- **正确示例**: 
  - `feat(rag): implement parent-child chunking logic in python retriever`
  - `fix(ui): resolve streaming output lag in chat component`
  - `refactor(api): extract user authentication logic to middleware`
- **严禁**: 拒绝使用模糊不清的 commit message，如 `fix bug` 或 `update code`。

## 3. 环境变量与配置管理
- **环境隔离**: 区分 `development` 和 `production` 环境。敏感信息（API Keys, Database Credentials）严禁硬编码在代码中，必须通过 `.env` 文件读取。
- **Windows 环境兼容性**:
  - 后端 Go 项目在 Windows 11 环境下编译时，需注意 CGO 依赖。若涉及 SQLite 或特定加密库，需指引用户检查 `CGO_ENABLED=1` 及 GCC 环境配置。
  - 使用 `PowerShell` 或 `Git Bash` 运行脚本，路径处理需考虑跨平台兼容性。

## 4. 技术栈特定红线
### 4.1 前端 (React/Node.js)
- **模块规范**: 严禁在 `package.json` 中盲目添加 `"type": "module"`。若项目中包含传统的 `webpack.config.js` 或使用 `require` 的配置文件，必须保持 CommonJS 兼容性，避免引起构建冲突。
- **渲染限制**: 在处理 AI 返回的 Markdown 字符串时，**严禁使用 `<cite>` 标签或类似的自定义引用块语法**。引用信息应通过普通的 UI 组件（如：带有链接的数字角标或底部的引用列表卡片）实现。

### 4.2 后端 (Go/Gin)
- **依赖管理**: 使用 `go mod` 进行依赖管理。
- **并发处理**: 充分利用 Go 的 Goroutine 处理文档解析等耗时任务，但必须通过 Context 进行生命周期控制，防止内存泄漏。

### 4.3 AI 数据层 (Python/LangChain)
- **类型提示**: 所有 Python 函数必须包含 Type Hints，提高代码自解释性。
- **日志记录**: 必须记录原始的 Prompt 和 LLM 的 Raw Response，便于后续针对 Minimax m2.7 进行提示词调优。

## 5. 代码质量检查 (Linting)
- Claude Code 在提交代码前，应自检代码风格是否符合主流规范（如：Prettier for React, Gofmt for Go, Black for Python）。
- 关键逻辑必须包含基本的单元测试。

## 6. 协作声明
- **严禁 Cite 引用**: 再次强调，无论是脚本注释还是输出给前端的内容，严禁出现 `cite` 关键字触发的特殊格式，以避免解析错误。