# Changelog

本项目遵循语义化版本。

## Unreleased

- 修复 Streamable HTTP 会话在初始化或工具发现后提前关闭共享上游 HTTP Client，导致后续工具
  调用返回 `Cannot send a request, as the client has been closed.` 的问题。

## 0.1.0 - 2026-07-30

- 提供 8 个只读、结构化 MCP 工具。
- 支持 stdio 与无状态 JSON Streamable HTTP。
- 增加网易云 Web Backend、Fake Backend、统一响应规范化和错误映射。
- 增加内存/SQLite 缓存、认证作用域隔离和确定性歌单统计。
- 增加 CLI、Docker、Compose、单元测试、MCP 合约与传输测试。
