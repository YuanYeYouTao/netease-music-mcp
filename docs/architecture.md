# 架构

依赖方向固定为：

```text
MCP Transport → MCP Tool Adapter → Application Service
                                      ↓
                                  Domain Models
                                      ↑
                Cache ← MusicCatalogBackend → NetEase HTTP Client
```

- MCP Adapter：唯一理解 FastMCP 生命周期、stdio 和 Streamable HTTP 的适配层。
- Tool：只声明紧凑 Schema、接收参数、调用 `MusicApplication` 并返回领域模型。
- Application Service：执行分页/批量上限验证、缓存策略、认证作用域和确定性统计。
- Domain：严格、冻结的 Pydantic v2 模型、枚举、ID、分页和异常；不依赖 MCP、HTTP、环境变量
  或数据库。
- Backend：`MusicCatalogBackend` 隔离提供方。`NeteaseWebBackend` 将统一分页转换为上游参数；
  `FakeMusicCatalogBackend` 使默认测试完全离线。
- Client/Normalizer：共享 `httpx.AsyncClient` 管理连接、Cookie、超时和重试；Provider Model
  验证响应后，由 Normalizer 生成领域模型。
- Cache：只保存规范化领域 JSON；键包含 Backend、操作、规范化参数、认证作用域、模型版本和
  非敏感配置指纹。

只有 `mcp_adapter.py`、`server.py` 和 `tools/*` 允许导入 `mcp`。更换 MCP SDK v2 时，领域、
Backend 与 Service 不需要重写。

关闭顺序由 FastMCP lifespan 保证：先关闭共享 HTTP client，再关闭 cache（SQLite 连接）。

## 固定边界及来源

| 边界 | 值 | 来源 |
| --- | --- | --- |
| Python | `>=3.12` | 产品技术基线 |
| MCP SDK | `>=1.28.1,<2` | 0.1.0 兼容目标 |
| Tool 数量 | 8 | 0.1.0 产品范围 |
| ID 公共类型 | 十进制字符串 | 跨 Client 数字精度要求；上游 ID 语义 |
| page | `>=1` | 统一一基分页模型 |
| port | `1..65535` | TCP 协议 |
| 搜索 type | `1/10/100/1000` | 当前网易云 Web 搜索接口 |
| 历史 type | `1/0` | 当前网易云 Web 播放记录接口 |
| HTTP 404/429/5xx | not_found/rate_limited/upstream_unavailable | HTTP 协议语义 |
| 分页、批量、超时、重试、TTL 上限 | Settings 值 | 运维配置，不在业务代码重复 |
| SQLite 主键 | SHA-256 cache key | 缓存唯一性要求 |
