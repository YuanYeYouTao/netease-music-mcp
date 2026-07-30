# 传输

## stdio

```bash
uv run netease-music-mcp serve --transport stdio
```

stdio 的 stdout 只用于 MCP 帧；诊断信息由 SDK 写入 stderr。

## Streamable HTTP

```bash
uv run netease-music-mcp serve --transport streamable-http \
  --host 127.0.0.1 --port 8766 --path /mcp
```

HTTP 模式使用 `stateless_http=true`、`json_response=true`。未提供已被替代的独立 SSE 主模式；
SDK 为协议兼容使用的流式能力仍保留。默认只监听回环地址；暴露到网络前应由反向代理提供 TLS、
访问控制与速率限制。
