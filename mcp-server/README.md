# RCLL MCP Server

Standalone [MCP](https://modelcontextprotocol.io) server that exposes **RCLL** memory tools to any MCP-compatible client (Claude Code, OpenClaw, etc). RCLL is self-hosted, hierarchical **shared** memory for a *team* of AI agents — rooms for per-agent vs shared recall, L0–L3 depth, pgvector under the hood.

> RCLL — team memory for agent fleets. Built on Hindsight (github.com/vectorize-io/hindsight, MIT).

RCLL is a fork of [`vectorize-io/hindsight`](https://github.com/vectorize-io/hindsight) (MIT). It keeps Hindsight's storage engine and adds rooms — shared, isolated memory for a team of agents — plus a hierarchical depth model (L0–L3). The room/hall/layer taxonomy is prior art in the hierarchical-memory space; the implementation here is our own.

## Tools

| Tool | Description |
|------|-------------|
| `memory_retain` | Save memories with room/hall/layer classification |
| `memory_recall` | Scoped semantic search with room filtering |
| `memory_reflect` | Deep reasoning + synthesis over stored memories |
| `memory_compress` | Create closet summaries from accumulated facts |
| `memory_bridge` | Cross-bank tunnels between related memories |

## Quick Start

```bash
cd mcp-server
npm install
RCLL_URL=http://localhost:5100 node server.js
```

## Claude Code

Add to `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "rcll": {
      "command": "npx",
      "args": ["-y", "rcll-mcp"],
      "env": {
        "RCLL_URL": "http://localhost:5100",
        "RCLL_BANK": "my-agent-bank"
      }
    }
  }
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RCLL_URL` | `http://127.0.0.1:5100` | RCLL backend base URL |
| `RCLL_BANK` | `mempalace-main` | Default memory bank ID. The default keeps the pre-rebrand value on purpose, so an install that never set it stays on the same bank after upgrading. Set it explicitly. |

### Deprecated (still read, with a notice on stderr)

Installs created before the rebrand keep working — these are used only when the
`RCLL_*` equivalent is unset, and they will be dropped in a future major.

| Legacy variable | Replaced by |
|-----------------|-------------|
| `HINDSIGHT_URL` | `RCLL_URL` |
| `MEMPALACE_BANK` | `RCLL_BANK` |

## Memory Taxonomy

**Rooms** (topics): auth, pipeline, schema, infrastructure, ui, api, deployment, monitoring, agent, general

**Halls** (knowledge types — the `hall` field): fact, event, decision, preference, discovery, procedure, warning

**Layers** (depth):
- L0 — Surface / identity (always at hand)
- L1 — Critical (recalled by default)
- L2 — Session (default for new memories)
- L3 — Deepest burrow / archive (deep search only, compressed into closets)
