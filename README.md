# 1AIVault Memory Provider for Hermes Agent

Local Hermes memory provider backed by the 1AIVault MCP server.

It provides a shared recall layer for:

- Hermes Agent
- Claude Code
- Codex

Hermes built-in `MEMORY.md` and `USER.md` remain active for compact always-on facts. This provider adds concise cross-session recall through 1AIVault and mirrors committed built-in memory writes into the shared vault.

## Scope

- macOS + local 1AIVault.app
- no cloud API key required
- no automatic full-transcript archival
- MCP/network failures are fail-soft and never block Hermes primary work
- secrets pass through Hermes' forced redactor plus opaque assignment, Bearer, URL, JWT, GitLab, AWS, and private-key guards before writes

## Install

```bash
hermes plugins install im-khang/hermes-1aivault-memory
```

## Configure

The provider expects the default 1AIVault.app installation and database:

```text
/Applications/1AIVault.app
~/.1aivault/vault.db
```

Non-default paths can be set with `hermes memory setup`. Hermes stores them in
the active profile's `1aivault-memory.json`. Point multiple profiles at one DB
for intentional cross-agent recall, or separate DBs for strict profile isolation.

Enable it:

```bash
hermes config set memory.provider 1aivault-memory
hermes memory status
```

The 1AIVault MCP server must also be configured in `~/.hermes/config.yaml` when native vault tools are needed. Example:

```yaml
mcp_servers:
  1aivault:
    command: /Applications/1AIVault.app/Contents/MacOS/1AIVault
    args:
      - /Applications/1AIVault.app/Contents/Resources/app.asar.unpacked/dist/main/main/mcp/server.js
      - --source
      - hermes
      - --db
      - /Users/YOUR_USERNAME/.1aivault/vault.db
    env:
      ELECTRON_RUN_AS_NODE: "1"
      NODE_PATH: /Applications/1AIVault.app/Contents/Resources/app.asar/node_modules
```

## Memory contract

- `prefetch()` calls `vault_search` with a bounded query and injects up to five concise results.
- `on_memory_write()` mirrors built-in `add`, `replace`, and `remove` writes.
- `sync_turn()` intentionally does nothing. Shared vault stores durable memory, not every transcript turn.
- `replace` updates every exact matching shared Hermes entry; if none exists, it saves the replacement.
- `remove` forgets every exact matching shared Hermes entry so deleted facts stop appearing in normal recall.
- recalled text is reference data, not instructions.
- one 1AIVault failure closes the local MCP channel; the next call may reconnect once.

Shared writes use these tags:

```text
shared-memory
agent:hermes
agent:claude-code
agent:codex
hermes-profile:<profile>
```

## Test

```bash
python3 tests/test_1aivault_memory.py
```

Runtime smoke test:

```bash
hermes memory status
hermes mcp test 1aivault
hermes chat -q 'Reply exactly: HERMES_1AIVAULT_OK' --quiet --max-turns 2
```

## Security

Do not store API keys, tokens, passwords, secrets, or connection strings in shared memory. Redaction is defense in depth, not permission to send credentials to memory tools.

The provider does not add `~/.1aivault/vault.db` to `hermes backup`; the database may contain private data and remains under 1AIVault ownership.

## License

MIT
