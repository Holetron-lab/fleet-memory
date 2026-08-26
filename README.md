# RCLL

**Self-hosted shared memory for a _team_ of AI agents. Storage + structure in one system.**

> RCLL — team memory for agent fleets. Built on Hindsight (github.com/vectorize-io/hindsight, MIT).

> [!IMPORTANT]
> **You are looking at a read-only mirror.** The canonical repository is
> [`godcrm.ai/git/holetron-lab/fleet-memory`](https://godcrm.ai/git/holetron-lab/fleet-memory) —
> self-hosted, public, clonable anonymously with no account anywhere in the chain. Everything
> here is pushed out from there, so **a merge performed on GitHub is overwritten by the next
> sync**, usually within the hour. Issues and stars belong here and are read. A pull request is
> welcome here as well — it gets merged on the canonical side and arrives back here on the next
> sync.

RCLL is a fork of [`vectorize-io/hindsight`](https://github.com/vectorize-io/hindsight) (MIT). It keeps Hindsight's storage engine and adds **rooms** — topic scoping over one shared store, which is selectivity rather than isolation — plus a hierarchical depth model (L0–L3). The room/hall/layer taxonomy is prior art in the hierarchical-memory space; the implementation here is our own.

RCLL is `recall` with the vowels dropped — the one operation every agent in the fleet performs before it does anything else. The tool is literally called `memory_recall`; the product is named after the call.

**Its one structural property worth remembering: the read path never invokes a language model.** A recall costs CPU and zero model tokens — see [architecture](https://rcll.ai/docs/architecture/).

### Status

The source is public and MIT. **There is no packaged release yet:** `fleet-memory-mcp` is not published on npm and no container image is pushed. Running RCLL today means building from this tree, which the quick start below does. Don't quote an install command as working until [rcll.ai](https://rcll.ai/) shows one.

| | |
|---|---|
| Site, measured numbers | [rcll.ai](https://rcll.ai/) · [benchmarks](https://rcll.ai/docs/benchmarks/) |
| Written for an AI agent, not a human | [rcll.ai/agents.md](https://rcll.ai/agents.md) |
| Where we branched from upstream, and how to take the next release | [FORK.md](./FORK.md) |
| Architecture spec | [RCLL.md](./RCLL.md) |

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

## What this fork adds

This is a list of **our additions relative to our branch point** ([`d054b884`](https://github.com/vectorize-io/hindsight/commit/d054b884), April 2026) — not a claim about what upstream Hindsight does today. Upstream has shipped roughly 1,700 commits and four minor releases since we branched; assume anything below has an upstream answer we have not evaluated, and read [FORK.md](./FORK.md) before treating this as a comparison.

| Added here | What it is |
|---|---|
| **Rooms** | Topic scoping on every write and every read — selectivity, not isolation |
| **Halls** | Knowledge typing within a room (fact, event, decision, procedure, warning) |
| **Layers L0–L3** | Durability tiers; L0 always recalled, L3 deep-search only |
| **Classification** | Keyword-based, sub-millisecond, **no LLM call** — the taxonomy costs zero tokens |
| **Closets** | Compressed summaries by room + hall, with pointers back to sources |
| **Tunnels** | Cross-bank bridges |
| **MCP server** | Standalone server exposing 5 tools over MCP |

Everything is additive: the upstream `/retain` and `/recall` contracts as of our branch point still work unchanged, and every new parameter is optional.

## Measured

Retrieval quality, our own models on the public LoCoMo dataset, using a third-party harness rather than one we wrote. Full method, the arms that lost, and the caveats: [rcll.ai/docs/benchmarks/](https://rcll.ai/docs/benchmarks/).

| Configuration | nDCG@10 | vs BM25 |
|---|---|---|
| BM25 | 0.3885 | baseline |
| vector | 0.4244 | +0.036 |
| hybrid fusion | 0.4722 | +0.084 |
| **hybrid fusion + reranker** (default) | **0.5862** | **+0.198** |

**This is retrieval quality, not answer accuracy.** It is not comparable to figures of the form "77% on LoCoMo", which measure a reader and a judge on top of a store. We publish no accuracy number because we have not run a reader and a judge.

Two results that go against us are on the benchmarks page rather than left out: on multi-hop questions our default fusion is **worse** than vector-plus-reranker, and on single-hop BM25 alone beats dense retrieval.

Latency on CPU with no GPU: ~0.29 s for search, ~3.0 s including the cross-encoder reranker. The reranker is 85% of the time and the single largest quality gain we can measure.

## Quick start

```bash
git clone https://github.com/holetron-lab/fleet-memory.git
cd rcll
cp .env.example .env
# edit .env with your config
docker compose -f docker-compose.rcll.yml up -d
```

This **builds the image from this tree** — there is no published image to pull, so the first run compiles and is not fast. The API then listens on `http://localhost:5100`.

Clients written against upstream Hindsight's API as of our branch point keep working — the added parameters are optional. It is *not* a drop-in for current upstream Hindsight, which is several releases ahead of this fork.

### Embeddings

Ships with `BAAI/bge-small-en-v1.5` (384-dim) — fast, CPU-friendly, baked into the image so first run needs no network download. It's **English-optimized**; recall quality on other languages degrades.

For multilingual memory (e.g. RU, multi-script), point it at a multilingual model:

```bash
HINDSIGHT_API_EMBEDDINGS_LOCAL_MODEL=BAAI/bge-m3   # 1024-dim, multilingual
```

Dimension is detected automatically. ⚠️ Switching models changes the vector dimension — do it on an **empty** memory store, or wipe + re-embed, since existing vectors can't be mixed across dimensions.

### Running without an LLM key

`LLM_PROVIDER=none` is a supported configuration, and it is a smaller product rather than the same one for free: retain drops to chunk mode — chunks stored and embedded whole, with **no fact extraction, no entity resolution, no causal links**, and consolidation and reflection off. You get a hybrid vector-and-lexical chunk store. Reading is unaffected, because reading never calls a model anyway. Choose this deliberately, or point extraction at a local model — don't arrive here by leaving a field blank.

## MCP Server

The `mcp-server/` directory contains a standalone [MCP](https://modelcontextprotocol.io) server over stdio.

**What is actually verified**, as of 2026-08-24, against a live backend: protocol version
`2025-06-18`; `initialize`, `tools/list` and `tools/call` all round-trip; `memory_recall`
returns real results. That is a protocol-level check run directly over stdio — not a
client-by-client compatibility matrix.

Any client that speaks MCP over stdio should therefore work, but we have not sat in front
of each one. Listed below is the config we run ourselves (Claude Code) and no others. If
you get it working with a different client, a PR to this section is the useful kind.

### Tools

| Tool | Description |
|------|-------------|
| `memory_retain` | Save a memory with automatic room/hall classification |
| `memory_recall` | Scoped semantic search with room/hall/layer filters |
| `memory_reflect` | Deep reasoning — synthesize facts, find patterns, answer with citations |
| `memory_compress` | Create closet summaries from accumulated facts |
| `memory_bridge` | Cross-bank tunnels between related memories |

`memory_recall` is the only one of the five that never calls a model. `memory_reflect` is an agentic loop with repeated LLM calls — if you expose this server to anything untrusted, expose `memory_recall` alone.

One thing worth knowing before you budget context: the backend treats `limit` on recall as
a retrieval hint, not a result cap — it returns everything inside its own token budget,
around 110 facts. The MCP layer enforces your `limit` on the way out, so a `limit: 2` recall
costs about 1 KB instead of 43 KB. Recall spends no model call; it does spend context.

### Setup

```bash
cd mcp-server
npm install
FLEET_URL=http://localhost:5100 node server.js
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
        "FLEET_URL": "http://localhost:5100",
        "FLEET_BANK": "my-agent-bank"
      }
    }
  }
}
```

Upgrading from the old package name? `HINDSIGHT_URL` and the legacy bank variable are still read
as a fallback, so an existing config keeps working — it just prints a deprecation notice on start.

See [`mcp-server/README.md`](./mcp-server/README.md) for full docs and environment variables.

## API changes from upstream

The base `/retain` and `/recall` endpoints are backward-compatible with upstream as of our branch point. New parameters are optional.

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
    "text": "Never restart PROD without confirming staging works first.",
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

## Known limits

Honest list, kept here rather than only on the site:

- **You cannot export your memory yet.** The upstream `export` command emits a bank *template* — config, mental models, directives — and none of your stored content. A full dump that carries rooms, halls, layers and the link graph is the top item on our list, because it is the one thing that should not be missing from a store you self-host.
- **No accuracy benchmark.** Retrieval quality is measured and published; a reader-and-judge run is not.
- **Adversarial / unanswerable questions** — where the right answer is "I don't know" — are not covered by the retrieval metric we report, and that is the category most likely to embarrass us.
- **Switching `MEMORY_MODE` later does not migrate what you already stored.** Pick before you accumulate.

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

Full architectural spec: [RCLL.md](./RCLL.md). Commit-by-commit account of the fork: [FORK.md](./FORK.md).

## Upstream

This fork branches from [`d054b884`](https://github.com/vectorize-io/hindsight/commit/d054b884) and its changes are a readable series on top of that commit, so taking a new upstream release is a rebase rather than an excavation:

```bash
git remote add upstream https://github.com/vectorize-io/hindsight.git
git fetch upstream --tags
git rebase --onto <upstream-tag> d054b884 main
```

Expect real conflicts: the rooms work touches the same engine files upstream has rewritten most. [FORK.md](./FORK.md) lists which ones and why.

## Credits

- [**Hindsight**](https://github.com/vectorize-io/hindsight) by vectorize-io — the memory storage engine
- [Holetron](https://github.com/holetron-lab) — fork maintainers, MCP server, integration

## License

MIT — same as upstream Hindsight. See [LICENSE](./LICENSE).
