# Token 效率

MCP Server 无法决定 Client 注入多少工具 Schema；Client（包括 Yuki）仍负责按需选择工具。
服务器通过以下可验证策略降低开销：

- 只注册 8 个集中式工具，不按每个上游接口拆分。
- description 只有一句，参数语义放在 Field description。
- 搜索只给概要；详情使用批量 `get_songs` 或对应实体工具。
- 专辑/歌单默认不返回曲目，所有大列表分页。
- 歌词使用 offset/limit 分页。
- 返回 `structuredContent`；文本兼容内容仅为一句短摘要，不重复完整 JSON。
- Provider 原始 JSON 永不返回给 Client。

`tests/contract/test_token_efficiency.py` 记录并约束 8 个工具总 Schema、典型 search、song
detail、playlist page 与 lyrics page 的字符数。阈值是回归保护，不作为运行时代码中的固定
Token 预算。
