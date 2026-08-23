# RCLL

**Self-hosted shared memory for a _team_ of AI agents. Storage + structure in one system.**

> RCLL — team memory for agent fleets. Built on Hindsight (github.com/vectorize-io/hindsight, MIT).

RCLL is a fork of [`vectorize-io/hindsight`](https://github.com/vectorize-io/hindsight) (MIT). It keeps Hindsight's storage engine and adds **rooms** — shared, isolated memory across a team of agents — plus a hierarchical depth model (L0–L3). The room/hall/layer taxonomy is prior art in the hierarchical-memory space; the implementation here is our own.

RCLL is `recall` with the vowels dropped — the one operation every agent in the fleet performs before it does anything else. The tool is literally called `memory_recall`; the product is named after the call.

---

## How it works

```
┌──────────────────────────────────────────────────────┐
│                         RCLL                         │
│                                                      │
│  ┌─── Room: auth ───┐  ┌─── Room: pipeline ──┐       │
│  │ Hall: facts      │  │ Hall: decisions     │       │
│  │ Hall: procedures │  │ Hall: events        │       │
│  │ Hall: warnings   │  │ Hall: facts         │       │
│  │                  │  │                     │       │
│  │  L0 ████ always  │  │  L0 ████ always     │       │
│  │  L1 ███░ warm    │  │  L1 ███░ warm       │       │
│  │  L2 ██░░ cold    │  │  L2 ██░░ cold       │       │
│  │  L3 █░░░ archive │  │  L3 █░░░ archive    │       │
│  └──────────────────┘  └─────────────────────┘       │
│           │                      │                   │
│           └──── Tunnel ──────────┘                   │
│                (cross-bank bridge)                   │
│                                                      │
│  Closets: compressed summaries + source pointers     │
└──────────────────────┬───────────────────────────────┘
                       │
              Hindsight vector store
              (embeddings + semantic search)
```

**Rooms** — topic isolation. Auth, pipeline, infrastructure, schema — each topic in its own room. An agent searching for auth facts won't wade through 500 deploy memories.

**Halls** — knowledge typing within a room. Fact, event, decision, procedure, warning. The system knows *what* it's looking at before reading — like `Content-Type` for memory.

**Layers L0–L3** — four priority tiers. L0 (core) is always loaded. L3 (archive) is deep-search only. Same idea as CPU cache hierarchy: L1 is fast and small, RAM is slow but holds everything.

**Closets** — AI-compressed summaries with source pointers. Deduplication at the knowledge level: 10 related facts → 1 paragraph + references.

**Tunnels** — cross-bank bridges between agents. Agent A discovers an insight — Agent B sees it through a tunnel without data duplication.

## Comparison

| | [Hindsight](https://github.com/vectorize-io/hindsight) (upstream) | **RCLL** |
|---|---|---|
| **What it is** | Long-term memory store | Storage + taxonomy hybrid |
| **Storage** | Vector store + embeddings | Vector store + embeddings |
| **Memory structure** | Flat (all memories equal) | Rooms → Halls → Layers + embeddings |
| **Retrieval** | Semantic search | Room-scoped semantic search |
| **Classification** | None | Keyword-based, <1ms, zero LLM cost |
| **Priority tiers** | All memories equal | L0–L3 (implemented) |
| **Compression** | None | Closets with source pointers |
| **Multi-agent** | Shared bank | Tunnels (cross-bank bridges) |
| **MCP integration** | API only | **5 tools via MCP protocol** |
| **Setup** | Docker | Docker (drop-in upgrade) |

## Quick start

```bash
git clone https://github.com/holetron-lab/rcll.git
cd rcll
cp .env.example .env
# edit .env with your config
docker compose -f docker-compose.rcll.yml up -d
```

API available at `http://localhost:5100`. Drop-in replacement for vanilla Hindsight — same API, same clients, new brain.

### Embeddings

Ships with `BAAI/bge-small-en-v1.5` (384-dim) — fast, CPU-friendly, baked into the image so first run needs no network download. It's **English-optimized**; recall quality on other languages degrades.

For multilingual memory (e.g. RU, multi-script), point it at a multilingual model:

```bash
HINDSIGHT_API_EMBEDDINGS_LOCAL_MODEL=BAAI/bge-m3   # 1024-dim, multilingual
```

Dimension is detected automatically. ⚠️ Switching models changes the vector dimension — do it on an **empty** memory store, or wipe + re-embed, since existing vectors can't be mixed across dimensions.

## MCP Server

The `mcp-server/` directory contains a standalone [MCP](https://modelcontextprotocol.io) server. Any MCP-compatible client (Claude Code, OpenClaw, Cursor, etc.) connects and gets structured long-term memory.

### Tools

| Tool | Description |
|------|-------------|
| `memory_retain` | Save a memory with automatic room/hall classification |
| `memory_recall` | Scoped semantic search with room/hall/layer filters |
| `memory_reflect` | Deep reasoning — synthesize facts, find patterns, answer with citations |
| `memory_compress` | Create closet summaries from accumulated facts |
| `memory_bridge` | Cross-bank tunnels between related memories |

### Setup

```bash
cd mcp-server
npm install
RCLL_URL=http://localhost:5100 node server.js
```

### Claude Code config

Add to `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "rcll": {
      "command": "node",
      "args": ["/path/to/mcp-server/server.js"],
      "env": {
        "RCLL_URL": "http://localhost:5100",
        "RCLL_BANK": "my-agent-bank"
      }
    }
  }
}
```

Upgrading from the old package name? `HINDSIGHT_URL` and the legacy bank variable are still read
as a fallback, so an existing config keeps working — it just prints a deprecation notice on start.

See [`mcp-server/README.md`](./mcp-server/README.md) for full docs and environment variables.

## API changes from upstream

The base `/retain` and `/recall` endpoints are fully backward-compatible. New parameters are optional.

### New parameters

| Endpoint | Parameter | Type | Description |
|----------|-----------|------|-------------|
| `/retain` | `room` | string | Topic room (auto-classified if omitted) |
| `/retain` | `hall` | string | Knowledge type (auto-classified if omitted) |
| `/retain` | `layer` | int | Priority 0-3 (default: 2) |
| `/recall` | `room` | string | Filter recall to a specific room |
| `/recall` | `hall` | string | Filter recall to a specific hall |
| `/recall` | `max_layer` | int | Maximum layer depth to search |

### New endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/bridge` | Create a cross-bank memory bridge |
| GET | `/tunnels` | List existing tunnels |
| POST | `/tunnels` | Create a tunnel between banks |
| GET | `/closets` | List compressed memory summaries |
| POST | `/closets` | Compress L3 memories into a closet |

## Room/Hall taxonomy

### Rooms (topics)

`auth` · `pipeline` · `infrastructure` · `deployment` · `schema` · `api` · `ui` · `tax` · `hr` · `legal` · `compliance` · `monitoring` · `agent` · `general`

### Halls (knowledge types)

`warning` · `decision` · `procedure` · `event` · `preference` · `discovery` · `fact`

### Layers

| Layer | Name | Behavior |
|-------|------|----------|
| **L0** | Critical | Always recalled |
| **L1** | Important | Recalled by default |
| **L2** | Normal | Standard (default for new memories) |
| **L3** | Archive | Deep search only, compressed into closets |

## Auto-classification

RCLL includes a keyword-based classifier (`room_hall_classifier.py`) that assigns room and hall automatically when not provided. No LLM call — classification is instant and free.

Extensible: add keywords to `ROOM_KEYWORDS` / `HALL_KEYWORDS` dictionaries.

## Examples

### Store a memory

```bash
curl -X POST http://localhost:5100/retain \
  -H "Content-Type: application/json" \
  -d '{
    "bank": "project-alpha",
    "text": "Never restart PROD PM2 without confirming DEV works first.",
    "room": "deployment",
    "hall": "warning",
    "layer": 0
  }'
```

### Scoped recall

```bash
curl -X POST http://localhost:5100/recall \
  -H "Content-Type: application/json" \
  -d '{
    "bank": "project-alpha",
    "query": "deployment safety rules",
    "room": "deployment",
    "hall": "warning",
    "max_layer": 1
  }'
```

### Cross-bank bridge

```bash
curl -X POST http://localhost:5100/bridge \
  -H "Content-Type: application/json" \
  -d '{
    "source_bank": "project-alpha",
    "target_bank": "project-beta",
    "room": "infrastructure",
    "hall": "procedure"
  }'
```

## What we changed

A taxonomy layer over Hindsight's vector store, plus a standalone MCP server.

Key additions:
- `room_hall_classifier.py` — keyword-based taxonomy engine (new)
- `aa1_add_room_hall_to_memory_units.py` — DB migration: flat → hierarchical, adds room/hall + `layer` column (new)
- `mcp-server/` — standalone MCP server with 5 tools (new)
- Storage layer — room/hall/layer metadata on every write
- Retrieval — room-scoped search with hall filtering
- Compression — closet generation with source linking
- Tunnels — cross-bank memory sharing protocol

Full architectural spec: [RCLL.md](./RCLL.md)

## Upstream compatibility

This fork tracks `vectorize-io/hindsight` as upstream. To pull updates:

```bash
git remote add upstream https://github.com/vectorize-io/hindsight.git
git fetch upstream
git merge upstream/main
```

All changes are additive — existing Hindsight behavior is preserved.

## Credits

- [**Hindsight**](https://github.com/vectorize-io/hindsight) by vectorize-io — the memory storage engine
- [Holetron](https://github.com/holetron-lab) — fork maintainers, MCP server, integration

## License

MIT — same as upstream Hindsight. See [LICENSE](./LICENSE).
