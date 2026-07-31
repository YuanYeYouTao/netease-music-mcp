# Changelog

本项目遵循语义化版本。

## Unreleased

- 开始 1.0.0：升级至 MCP Python SDK v2，保持 Domain、Service、Backend、15 个工具和 4 个 Resource 不变；补充 stdio/Streamable HTTP 现代与 legacy 客户端兼容测试。
- 修复写操作成功后同进程读取歌单、用户库或喜欢状态命中旧缓存的问题；写入成功后清理共享缓存并支持立即回读。
- 开始 0.5.0：补充 backend 能力声明，未支持的工具操作返回 `unsupported_operation`；保持 15 个工具、
  4 个 Resource、统一领域模型和本地 Cookie 认证不变。
- Docker Compose 镜像版本更新为 0.5.0，Windows 与 macOS 通过 Docker Desktop 使用同一运行方式。
- 增加宿主机本地认证导入命令；经确认后从 Windows/macOS 网易云桌面客户端读取 Cookie，
  仅注入当前 Docker 子进程，不持久化凭据。

- 开始 0.4.0：增加默认启用、可通过 `NETEASE_WRITE_OPERATIONS_ENABLED=false` 关闭的创建歌单、增删曲目和点赞工具。
- 写调用必须显式传入 `confirm=true`；不提供删除歌单接口，便于可恢复的真实账号测试。
- 修复创建歌单请求缺少 `os=pc` Cookie 且将 `privacy` 发送为字符串，导致上游返回 403 `illegal request`。
- 修复点赞请求缺少 `os=pc` 与 `appver=2.9.7` Cookie，导致上游返回 `-460` 风控错误。
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
