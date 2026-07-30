# Yuki Integration

Yuki 可把本服务器作为普通 MCP Server 延迟加载。推荐 scope：`mcp.netease_music`，标签可使用
音乐、网易云、歌曲、歌手、专辑、歌单和歌词。

stdio 与 HTTP 完整示例见 README。`yuki` 配置仅由 Client 解释；Server 不读取专有字段，也不
调用 Yuki 的 QQ、表情、语音或自动化能力。
