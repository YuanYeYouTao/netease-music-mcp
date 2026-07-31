# 认证

`AuthenticationProvider` 是唯一组装 Cookie 的组件。优先接受 `NETEASE_COOKIE`，并可追加
`MUSIC_U` 与 `__csrf` 拆分变量。组件的 `repr` 只显示状态和配置用户 ID。

认证状态模型包括 `anonymous`、`authenticated`、`expired` 和 `invalid`。项目不提供扫码 UI，
也不扫描浏览器 Cookie。Windows/macOS 桌面客户端可通过宿主机 `auth import-local` 读取本地
MMKV Cookie 归档，并兼容 CEF Chromium Cookie 数据库；读取加密 CEF Cookie 时，macOS 通过
Keychain、Windows 通过 DPAPI 解密。首次运行需要确认。
公开查询不强制登录；私人音乐库需要 Cookie，缺失或过期分别映射为明确的领域错误。

安全规则：

- 不记录 Cookie、完整 Header、认证响应或真实令牌。
- 不把 Cookie 放入领域模型、MCP 输出、异常或 SQLite。
- 私人缓存键以用户 ID 区分认证作用域，但不包含 Cookie。
- README 与测试仅使用明显的虚构值。
- 本地导入默认只把 Cookie 放入当前 Docker 子进程环境，不写入 `.env`、镜像或仓库。
- `auth` 导入命令必须在 Windows/macOS 宿主机运行（需要 Python/uv）；Linux 容器不读取宿主机
  Keychain 或 DPAPI。
- 非交互导入必须显式提供 `--yes`；未登录、找不到数据库或无法获得系统密钥时直接失败。
