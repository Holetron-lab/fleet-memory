#!/usr/bin/env python3
"""Split the RCLL snapshot into a reviewable patch series on top of upstream.

The repository was imported as ONE commit of 558k lines, so git does not know
which of our changes is which. This rebuilds the same tree as a sequence of
commits whose boundaries mean something, by classifying every EDIT of the
base..ours diff into a named group and materialising the tree stage by stage.

Model. A diff hunk is too coarse a unit here: the two largest hunks in the
snapshot are single appended blocks that contain two different features each
(rooms and tunnels share one ADR, so they also share a banner comment). So the
diff is decomposed to line granularity instead — every maximal run of
deletions/insertions becomes one independently selectable `Edit`, and long pure
insertions are cut again at top-level `def`/banner boundaries so a feature can
be lifted out of an appended block.

Stages are then built by content, not by patch application: stage k writes
base + (every edit belonging to groups 1..k, in original file order). Nothing
depends on fuzzy context matching, and an edit that no rule claims lands in an
explicit residue group rather than being dropped.

The correctness condition is not "the split looks right" — it is that the tree
after the last stage is byte-identical to the tree we started from. That check
cannot be satisfied by losing work.

    python3 .rcll-split.py plan            # classification only, changes nothing
    python3 .rcll-split.py stage <group>   # write stage content into the worktree
    python3 .rcll-split.py order           # groups that actually have content
    python3 .rcll-split.py desc <group>
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

BASE = Path("/tmp/bestbase.txt").read_text().strip()
OURS = Path("/tmp/ourtree.txt").read_text().strip()

# Whole-file groups, matched in order. A file listed here contributes entirely
# to that group; only files NOT listed here get per-edit classification.
FILE_GROUPS: list[tuple[str, re.Pattern]] = [
    ("secrets", re.compile(r"(^|/)\.sesskey$|(^|/)\.DS_Store$")),
    ("mcp", re.compile(r"^mcp-server/|^server\.json$")),
    ("ci", re.compile(r"^\.github/workflows/|^\.gitignore$")),
    ("ops", re.compile(r"^docker-compose\.rcll\.yml$|^docker/|^\.env\.example$")),
    ("brand", re.compile(r"^README\.md$|^RCLL\.md$")),
    ("rooms", re.compile(r"room_hall_classifier\.py$|aa1_add_room_hall")),
]

# Per-edit rules for the engine files that carry more than one feature.
# "ADR-145" is deliberately NOT a room signal: that ADR covers rooms AND
# tunnels, so matching it would drag the tunnel block into the rooms commit
# purely because its banner cites the document.
RE_TUNNEL = re.compile(r"tunnel", re.I)
RE_CLOSET = re.compile(r"closet", re.I)
RE_ROOM = re.compile(r"\broom\b|\bhall\b|\blayer\b", re.I)

# Boundaries a long pure insertion may be cut at, so one appended block can
# contribute to two features without either commit carrying the other's code.
RE_BLOCK_START = re.compile(r"^\s*(async\s+def |def |class |# =====|# -----)")

ORDER = ["secrets", "ci", "ops", "rooms", "closets", "tunnels", "engine-misc", "mcp", "brand", "residue"]

DESCRIPTIONS = {
    "secrets": "chore: drop committed session keys and .DS_Store from the tree",
    "ci": "ci: replace upstream release pipeline with npm Trusted Publishing",
    "ops": "ops: standalone compose and env template for the RCLL distribution",
    "rooms": "feat(rooms): per-agent rooms, halls and durability layers (ADR-145)",
    "closets": "feat(closets): compress memories by room+hall into closets (ADR-145 ph.3)",
    "tunnels": "feat(tunnels): cross-bank memory bridges (ADR-145 phase 4)",
    "engine-misc": "fix(engine): sync migration URL and assorted engine fixes",
    "mcp": "feat(mcp): RCLL MCP server and MCP-registry manifest",
    "brand": "brand: Hindsight-MemPalace -> RCLL",
    "residue": "chore: remaining snapshot delta not attributable to a named change",
}


@dataclass
class Edit:
    old_start: int          # index into base lines where this edit begins
    old_end: int            # exclusive
    new: list[str]          # replacement lines
    group: str = "residue"


@dataclass
class FileDelta:
    path: str
    whole_group: str | None = None       # set for whole-file groups
    base_lines: list[str] = field(default_factory=list)
    edits: list[Edit] = field(default_factory=list)
    binary: bool = False


def _run(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


def changed_files() -> list[tuple[str, str]]:
    out = _run(["git", "diff", "--name-status", BASE, OURS])
    rows = []
    for line in out.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        rows.append((parts[0][0], parts[-1]))
    return rows


def blob(tree: str, path: str) -> list[str] | None:
    r = subprocess.run(["git", "show", f"{tree}:{path}"], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return r.stdout.splitlines(keepends=True)


def file_group(path: str) -> str | None:
    for name, rx in FILE_GROUPS:
        if rx.search(path):
            return name
    return None


def edits_from_diff(path: str) -> tuple[list[str], list[Edit]]:
    """Decompose base->ours for one file into line-granular edits."""
    diff = _run(["git", "diff", "-U0", BASE, OURS, "--", path])
    base_lines = blob(BASE, path) or []
    edits: list[Edit] = []
    cur_old = 0
    pending_del = 0
    pending_new: list[str] = []
    start = 0
    hdr = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

    def flush():
        nonlocal pending_del, pending_new, start
        if pending_del or pending_new:
            edits.append(Edit(start, start + pending_del, pending_new))
        pending_del, pending_new, = 0, []

    lines = diff.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        m = hdr.match(lines[i])
        if m:
            flush()
            old_start = int(m.group(1))
            old_count = int(m.group(2) or 1)
            # -U0: a pure insertion reports the line BEFORE the insertion point
            start = old_start if old_count else old_start
            start = start - 1 if old_count else start
            cur_old = start
            i += 1
            body_del: list[str] = []
            body_add: list[str] = []
            while i < len(lines) and not lines[i].startswith("@@"):
                if lines[i].startswith("-"):
                    body_del.append(lines[i][1:])
                elif lines[i].startswith("+"):
                    body_add.append(lines[i][1:])
                i += 1
            edits.append(Edit(cur_old, cur_old + len(body_del), body_add))
            pending_del, pending_new = 0, []
            continue
        i += 1
    flush()
    return base_lines, edits


def subsplit(e: Edit) -> list[Edit]:
    """Cut a long pure insertion at block boundaries so features can separate."""
    if e.old_end != e.old_start or len(e.new) < 40:
        return [e]
    chunks: list[list[str]] = []
    cur: list[str] = []
    for line in e.new:
        if cur and RE_BLOCK_START.match(line) and len(cur) > 1:
            chunks.append(cur)
            cur = [line]
        else:
            cur.append(line)
    if cur:
        chunks.append(cur)
    if len(chunks) < 2:
        return [e]
    return [Edit(e.old_start, e.old_end, c) for c in chunks]


def classify(new: list[str], old: list[str]) -> str:
    body = "".join(new) + "".join(old)
    c = len(RE_CLOSET.findall(body))
    t = len(RE_TUNNEL.findall(body))
    r = len(RE_ROOM.findall(body))
    # Precedence, not dominance, for the two features BUILT ON rooms: a closet
    # is keyed by room+hall and a tunnel carries them across banks, so their
    # code necessarily says "room". Ranking by mention count would scatter one
    # feature across two commits depending on how chatty each block happened
    # to be — which is how closets first came out split down the middle.
    if c:
        return "closets"
    if t:
        return "tunnels"
    if r:
        return "rooms"
    return "engine-misc"


def build() -> list[FileDelta]:
    out: list[FileDelta] = []
    for status, path in changed_files():
        g = file_group(path)
        fd = FileDelta(path=path, whole_group=g)
        if g is not None:
            out.append(fd)
            continue
        base_lines = blob(BASE, path)
        ours_lines = blob(OURS, path)
        if base_lines is None or ours_lines is None:
            fd.whole_group = "residue"
            out.append(fd)
            continue
        bl, edits = edits_from_diff(path)
        fd.base_lines = bl
        split: list[Edit] = []
        for e in edits:
            for s in subsplit(e):
                s.group = classify(s.new, bl[s.old_start : s.old_end])
                split.append(s)
        fd.edits = split
        out.append(fd)
    return out


def render(fd: FileDelta, groups: set[str]) -> str:
    """base + every edit whose group is enabled, in original file order."""
    out: list[str] = []
    pos = 0
    for e in sorted(fd.edits, key=lambda x: (x.old_start, x.old_end)):
        if e.old_start < pos:          # sub-split siblings share an anchor
            if e.group in groups:
                out.extend(e.new)
            continue
        out.extend(fd.base_lines[pos : e.old_start])
        if e.group in groups:
            out.extend(e.new)
        else:
            # Not yet staged: keep what upstream had. Skipping the range would
            # silently delete base lines in every intermediate stage and still
            # pass the final identity check, because the last stage enables
            # every group — the check would be satisfied by a broken series.
            out.extend(fd.base_lines[e.old_start : e.old_end])
        pos = e.old_end
    out.extend(fd.base_lines[pos:])
    return "".join(out)


def write_stage(deltas: list[FileDelta], upto: list[str]) -> None:
    enabled = set(upto)
    for fd in deltas:
        p = Path(fd.path)
        if fd.whole_group is not None:
            if fd.whole_group not in enabled:
                continue
            ours = blob(OURS, fd.path)
            if ours is None:                     # deleted by us
                if p.exists():
                    p.unlink()
                continue
            p.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "checkout", OURS, "--", fd.path], check=True)
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(render(fd, enabled))


def main() -> int:
    deltas = build()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "plan"

    if cmd == "plan":
        print(f"base {BASE[:9]}  ours {OURS[:9]}")
        tally: dict[str, list[str]] = {g: [] for g in ORDER}
        for fd in deltas:
            if fd.whole_group is not None:
                tally[fd.whole_group].append(f"    whole   {fd.path}")
                continue
            per: dict[str, int] = {}
            for e in fd.edits:
                per[e.group] = per.get(e.group, 0) + 1
            for g, n in per.items():
                tally[g].append(f"    {n:3d}ed  {fd.path}")
        for g in ORDER:
            if not tally[g]:
                continue
            print(f"\n[{g}] — {DESCRIPTIONS[g]}")
            for line in sorted(tally[g]):
                print(line)
        tot = sum(len(fd.edits) for fd in deltas)
        print(f"\ntotal line-granular edits: {tot}")
        return 0

    if cmd == "order":
        have = set()
        for fd in deltas:
            have.add(fd.whole_group) if fd.whole_group else have.update(e.group for e in fd.edits)
        print(" ".join(g for g in ORDER if g in have))
        return 0

    if cmd == "desc":
        print(DESCRIPTIONS[sys.argv[2]])
        return 0

    if cmd == "stage":
        upto = sys.argv[2].split(",")
        write_stage(deltas, upto)
        return 0

    raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    sys.exit(main())
