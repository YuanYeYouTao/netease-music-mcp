# 认证

`AuthenticationProvider` 是唯一组装 Cookie 的组件。优先接受 `NETEASE_COOKIE`，并可追加
`MUSIC_U` 与 `__csrf` 拆分变量。组件的 `repr` 只显示状态和配置用户 ID。

认证状态模型包括 `anonymous`、`authenticated`、`expired` 和 `invalid`。0.1.0 不提供扫码 UI、
浏览器自动化或自动 Cookie 读取。公开查询不强制登录；私人音乐库需要 Cookie，缺失或过期
分别映射为明确的领域错误。

安全规则：

- 不记录 Cookie、完整 Header、认证响应或真实令牌。
- 不把 Cookie 放入领域模型、MCP 输出、异常或 SQLite。
- 私人缓存键以用户 ID 区分认证作用域，但不包含 Cookie。
- README 与测试仅使用明显的虚构值。
