# Roadmap

这些能力只记录路线，不在 0.1.0 中预建空接口。

## 0.2.0（已实现）

- 已实现 MCP Resources：`netease://song/{id}`、`album`、`artist`、`playlist`。

## 0.3.0（已实现）

- 已实现只读推荐、相似歌曲、新歌速递、排行榜和喜欢的歌曲分页读取。

## 0.4.0（已实现）

- 默认启用、可通过 `NETEASE_WRITE_OPERATIONS_ENABLED=false` 关闭的写操作模块：创建歌单、增删歌曲、点赞。
- 每次写调用还必须显式传入 `confirm=true`；真实账号测试只允许使用可恢复的目标。

## 0.5.0（当前开发版本）

- 服务容器通过 Docker Desktop 兼容 Windows 与 macOS，不要求宿主机处理 Python/路径差异；
  宿主机认证导入命令另需 Python/uv 访问系统密钥。
- 保持现有 15 个工具、4 个 Resource URI 和本地 Cookie 认证方式不变。
- 增加宿主机 `auth import-local` / `auth run-docker`：读取 Windows/macOS 桌面客户端登录态，
  经确认后仅注入当前 Docker 进程。
- 通过 `MusicCatalogBackend.supported_operations` 声明能力；未实现的能力返回
  `unsupported_operation`，不以空数据伪装成功。
- 统一歌曲、歌手、专辑、歌单和用户歌库模型；核心能力为搜索、歌曲、专辑、歌手、歌单和用户歌单。

## 1.0.0（已实现）

- MCP Python SDK v2 Adapter；保持 Domain、Service 与 Backend 不变，并增加完整兼容测试。
