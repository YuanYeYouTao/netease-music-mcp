# Changelog

本项目遵循语义化版本。

## Unreleased

- 开始 0.3.0：增加只读推荐、相似歌曲、新歌速递和排行榜工具，并支持分页读取喜欢的歌曲。
- 增加 song、album、artist 和 playlist 四类只读 MCP Resource URI 模板。
- 兼容私人歌单中的空描述/空曲目字段，并在上游忽略 limit 时保持本地分页边界。
- 搜索切换至网页端当前使用的 Cloud Search 接口，并修复网易云对非浏览器 User-Agent 返回 HTTP 200 但结果完全无关的问题；同时升级缓存指纹，自动隔离此前写入的错误搜索缓存。
- 修复 Streamable HTTP 会话在初始化或工具发现后提前关闭共享上游 HTTP Client，导致后续工具
  调用返回 `Cannot send a request, as the client has been closed.` 的问题。

## 0.1.0 - 2026-07-30

- 提供 8 个只读、结构化 MCP 工具。
- 支持 stdio 与无状态 JSON Streamable HTTP。
- 增加网易云 Web Backend、Fake Backend、统一响应规范化和错误映射。
- 增加内存/SQLite 缓存、认证作用域隔离和确定性歌单统计。
- 增加 CLI、Docker、Compose、单元测试、MCP 合约与传输测试。
