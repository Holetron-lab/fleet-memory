# RCLL as a fork of Hindsight

RCLL is a fork of [vectorize-io/hindsight](https://github.com/vectorize-io/hindsight)
(MIT, Copyright (c) 2025 Vectorize AI). This file records what we changed, where
we branched from, and how to take the next upstream release — the three things
the repository could not answer before, and the reason updating had become
archaeology instead of a rebase.

## What was wrong

The code arrived here on 2026-06-27 as a **single commit of 1716 files and
558,283 lines**, with no upstream remote and no common ancestor. Five later
commits carried branding only. So `git log` could tell you that a rebrand
happened and nothing at all about the engine changes underneath it — and
`git merge upstream/main` was not merely painful, it was *impossible*: unrelated
histories.

## Where we actually branched

Not from a release tag. The snapshot was matched against upstream commit by
commit, minimising the number of differing files:

| candidate | files differing from our tree |
|---|---|
| `v0.5.0` (2026-04-08) | 146 |
| `7b2263ba` (2026-04-13) | 34 |
| **`d054b884` (2026-04-10)** | **32** |

**Base = `d054b884`, "fix: add PEP 561 py.typed marker to all Python packages (#973)",
2026-04-10** — twelve commits past `v0.5.0`, which is why an earlier reading of
the delta against `v0.5.0` looked like 146 changed files and 13,383 inserted
lines. Most of that was upstream's own work between the tag and our branch
point, not ours. **Our real patch is 32 files.**

## The series

`rcll/main` replays that patch as nine commits on top of `d054b884`:

| commit | what |
|---|---|
| `chore: drop committed session keys and .DS_Store` | two `.sesskey` files and a `.DS_Store` that upstream had committed |
| `ci: replace upstream release pipeline with npm Trusted Publishing` | our publish workflow; upstream's four release/test workflows removed |
| `ops: standalone compose and env template` | `docker-compose.rcll.yml`, `.env.example`, standalone entrypoint |
| **`feat(rooms)`** | per-agent rooms, halls, durability layers — ADR-145. The one thing in this repo that is ours and has no upstream counterpart |
| **`feat(closets)`** | compression of memories by room+hall — ADR-145 phase 3 |
| **`feat(tunnels)`** | cross-bank memory bridges — ADR-145 phase 4 |
| `fix(engine)` | sync migration URL fallback, protected tables, small engine fixes |
| `feat(mcp)` | the RCLL MCP server and `server.json` registry manifest |
| `brand` | `README.md`, `RCLL.md` |

### How the split was verified

The series was not hand-sorted. `/root/rcll-split.py` decomposes the
base→snapshot diff to **line granularity** — hunks are too coarse, because the
two largest are single appended blocks containing more than one feature — then
classifies every edit and materialises each stage by content.

Two checks, both mechanical:

* **Identity.** The tree at the last commit is byte-identical to the snapshot
  tree (`git diff --quiet <series-head> <snapshot-tree>`). A split that lost
  work could not pass this.
* **Each stage compiles.** Every intermediate commit is checked with
  `py_compile` across `hindsight_api/`. This caught a real bug in the splitter:
  a first version deleted base lines for not-yet-staged edits, which still
  satisfied the identity check — because the final stage enables every group —
  while corrupting all eight commits before it.

### Known imperfection, stated rather than hidden

Ten lines of tunnel code sit in the `feat(closets)` commit: one
`DELETE /tunnels/{id}` endpoint pair, plus the shared `_PROTECTED_TABLES` entry
that adds `"tunnels"` and `"closets"` on the same line. Rooms, closets and
tunnels are one ADR and genuinely share plumbing; this is where the automatic
boundary stops being sharp. Everything else separates cleanly (`rooms` contains
zero tunnel or closet lines; `tunnels` contains zero closet lines).

## Distance to upstream

As of 2026-08-23, upstream `main` is `3295716c` and the newest tag is `v0.9.1`
(2026-08-14). From our base that is **~1600 first-parent commits**, and the four
files our room/hall work touches most are also the four upstream rewrote most
(`memory_engine.py`, `http.py`, `orchestrator.py`, `retrieval.py`). Upstream has
**no room/hall/layer concept at all** — checked by grep against `main` — so
there is nothing to inherit and nothing to drop.

Our alembic line adds exactly one migration upstream does not have,
`aa1_add_room_hall_to_memory_units`. Production currently has **two alembic
heads** (`aa1_room_hall` and upstream's `h3i4j5k6l7m8`); any upgrade needs an
authored merge revision first.

## Taking the next upstream release

```
git fetch upstream --tags
git rebase --onto v0.9.1 d054b884 rcll/main    # nine commits, not one blob
```

Conflicts land inside the feature commit that owns them, which is the entire
point of the series.

**Do not run migrations as part of this.** On Ring 0 the memory schema
`hindsight_v2` lives *inside* the CRM database, so an upstream migration is DDL
against a combat master, and 16 of the ~50 new ones are destructive
(`drop_memory_units_access_count`, `drop_entity_memory_links`,
`split_history_into_own_tables`, …). `HINDSIGHT_API_RUN_MIGRATIONS_ON_STARTUP`
stays `false` there. Rehearse on a copy of the schema, never on the master.

## Remotes

```
origin    https://github.com/holetron-lab/rcll.git
upstream  https://github.com/vectorize-io/hindsight.git   (push URL deliberately
                                                           poisoned — nothing on
                                                           this box can push to
                                                           vectorize-io)
```

## What is deliberately NOT done here

`main` is untouched. Making `main` descend from upstream requires a force-push,
and this repository is one decision away from being made public with an already
published `server.json` — a rewritten history is a one-way door. The series
lives on its own branch; repointing `main` is the owner's call.
