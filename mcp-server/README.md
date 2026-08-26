# RCLL MCP Server (`fleet-memory-mcp`)

Standalone [MCP](https://modelcontextprotocol.io) server that exposes **RCLL** memory tools to any MCP-compatible client (Claude Code, OpenClaw, etc). RCLL is self-hosted, hierarchical **shared** memory for a *team* of AI agents — topic-scoped rooms, L0–L3 depth, pgvector under the hood. The published artifact is named `fleet-memory`; RCLL is the product name.

> RCLL — team memory for agent fleets. Built on Hindsight (github.com/vectorize-io/hindsight, MIT).

Canonical repository: <https://godcrm.ai/git/holetron-lab/fleet-memory> — self-hosted, clonable
anonymously. <https://github.com/holetron-lab/fleet-memory> is a read-only mirror of it, and is
where issues and stars go.

RCLL is a fork of [`vectorize-io/hindsight`](https://github.com/vectorize-io/hindsight) (MIT). It keeps Hindsight's storage engine and adds rooms — topic scoping over one shared store, which is selectivity rather than isolation — plus a hierarchical depth model (L0–L3). The room/hall/layer taxonomy is prior art in the hierarchical-memory space; the implementation here is our own.

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
npx fleet-memory-mcp
```

`FLEET_URL` points at your own RCLL backend (default `http://127.0.0.1:5100`); this package is the
MCP client half and does not start a store for you. Standing one up is [the quickstart on
rcll.ai](https://rcll.ai/docs/quickstart/).

From a clone instead:

```bash
cd mcp-server
npm install
FLEET_URL=http://localhost:5100 node server.js
```

## Claude Code

Add to `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "rcll": {
      "command": "npx",
      "args": ["-y", "fleet-memory-mcp"],
      "env": {
        "FLEET_URL": "http://localhost:5100",
        "FLEET_BANK": "my-agent-bank"
      }
    }
  }
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLEET_URL` | `http://127.0.0.1:5100` | fleet-memory backend base URL |
| `FLEET_BANK` | `fleet-main` | Default memory bank ID. Set it explicitly. |

### Migrating from `hindsight-mempalace-mcp`

That package defaulted to bank `mempalace-main`. `fleet-memory-mcp` defaults to `fleet-main`,
so an install that never set the variable would open a different, empty bank — which
reads as "the update erased my memory". It does not: the old bank is still there.

Set `FLEET_BANK=mempalace-main` to keep reading it, or move the contents into a new
bank first. When `FLEET_BANK` and `MEMPALACE_BANK` are both unset, the server prints
which bank it defaulted to on stderr rather than picking one silently.

### Deprecated (still read, with a notice on stderr)

Installs created before the rebrand keep working — these are used only when the
`FLEET_*` equivalent is unset, and they will be dropped in a future major.

| Legacy variable | Replaced by |
|-----------------|-------------|
| `HINDSIGHT_URL` | `FLEET_URL` |
| `MEMPALACE_BANK` | `FLEET_BANK` |

## Memory Taxonomy

**Rooms** (topics): auth, pipeline, schema, infrastructure, ui, api, deployment, monitoring, agent, general

**Halls** (knowledge types — the `hall` field): fact, event, decision, preference, discovery, procedure, warning

**Layers** (depth):
- L0 — Surface / identity (always at hand)
- L1 — Critical (recalled by default)
- L2 — Session (default for new memories)
- L3 — Deepest burrow / archive (deep search only, compressed into closets)
