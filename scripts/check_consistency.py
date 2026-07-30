#!/usr/bin/env python3
"""Repository consistency checker for greenmachine-next.

Adapted for the repository from the planning kit's checker (REBUILD_PLAN, GMR-001
scope item 3; rules re-pinned and rule 7 added by §GMR-003R per D-046 — the
repository checker implements rules 1-7 and nothing more):

1. freshness (ticket)     CONTEXT_PACK.md names the current active ticket.
2. freshness (count)      CONTEXT_PACK.md states the current decision count.
3. plan hash              sha256(tickets/REBUILD_PLAN.md) equals the pinned approved value.
4. pointer order          tickets/completed/ is exactly a prefix of the order table and
                          tickets/ACTIVE.md names the first ticket after that prefix.
5. banned phrases         the plan contains no retired-lifecycle phrase outside fenced
                          code blocks.
6. manifest partition     the PORT_MANIFEST owner partition sums 138 + 4 + 1 + 1 = 144,
                          no row unowned.
7. plan hash (pack)       the plan hash recorded in CONTEXT_PACK.md equals the pinned
                          approved value.

Why it exists is unchanged from the kit (D-016): a finding a script can catch must
never reach a reviewer. Run it before any package goes to GPT and paste the output.

Usage:  python scripts/check_consistency.py [repo_root]
Exit 0 = clean, 1 = failures found.
"""

from __future__ import annotations

import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()

# The sha256 GPT's plan approval names (v15, APPROVED WITH NOTES, 2026-07-28). Any edit
# to tickets/REBUILD_PLAN.md turns the plan-hash rule red; a plan revision is committed
# only with a reviewed PR that updates this pin alongside the plan bytes (plan lifecycle).
PINNED_PLAN_SHA256 = "3daa28b952f3c78d80c2d01764f495e3866eb68e32d13de86ac6f7a67646d904"

# The completed-order table (plan lifecycle, closeout criterion c). The set of files in
# tickets/completed/ must be exactly a prefix of this table.
ORDER = ("GMN-000A", "GMR-001", "GMR-002", "GMR-003", "GMR-004", "GMR-005")
SENTINEL = "NO ACTIVE TICKET — next phase pending planning"

# The seven retired-lifecycle phrases, fixed by the plan's BANNED-PHRASES block. Fenced
# code blocks are excluded from the scan so the plan can name what it bans.
BANNED_PHRASES = (
    "frozen first commit",
    "and the ticket freeze",
    "freezes the ticket's text",
    "APPROVAL RECORD",
    "its annex",
    "approval annex",
    "annex quoting",
)

# The manifest owner partition (PORT_MANIFEST v3; §GMR-003R, D-039/D-040).
EXPECTED_PARTITION = {
    "GMR-003": 138,
    "GMR-001": 4,
    "GMR-002": 1,
    "SUPERSEDED-000A": 1,
}

failures: list[str] = []
checks_run = 0


def read(rel: str) -> str:
    p = ROOT / rel
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def check(name: str, ok: bool, detail: str = "") -> None:
    global checks_run
    checks_run += 1
    if ok:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}" + (f" -- {detail}" if detail else ""))
        failures.append(name)


def active_pointer() -> str:
    """Return the ticket ID or sentinel that tickets/ACTIVE.md points at."""
    txt = read("tickets/ACTIVE.md")
    m = re.search(r"^Active:\s*(GM[NR]-\w+|NO ACTIVE TICKET.*?)\s*(?:per\b.*)?$", txt, re.M)
    return m.group(1).strip() if m else ""


def outside_fences(markdown: str) -> str:
    """Return the text with fenced code blocks removed."""
    return re.sub(r"```.*?```", "", markdown, flags=re.S)


print(f"Repository consistency check — {ROOT.name}\n")

# Rules 1 and 2 -- freshness: the hand-maintained pack must agree with the repository.
print("Freshness (CONTEXT_PACK.md)")
pack = read("CONTEXT_PACK.md")
pointer = active_pointer()
pack_ticket_m = re.search(r"Active ticket:\s*\*\*(.+?)\*\*", pack)
pack_ticket = pack_ticket_m.group(1).strip() if pack_ticket_m else ""
check(
    "freshness (ticket): CONTEXT_PACK.md names the current active ticket",
    bool(pack_ticket) and pack_ticket == pointer,
    f"CONTEXT_PACK.md names {pack_ticket!r} but tickets/ACTIVE.md points at {pointer!r}",
)

decisions = read("DECISIONS.md")
decision_ids = re.findall(r"^## (D-\d+)", decisions, re.M)
latest = len(decision_ids)
pack_count_m = re.search(r"Decision count:\s*\*\*(\d+)\*\*", pack)
pack_count = int(pack_count_m.group(1)) if pack_count_m else -1
check(
    "freshness (count): CONTEXT_PACK.md states the current decision count",
    pack_count == latest,
    f"CONTEXT_PACK.md states {pack_count} but DECISIONS.md holds {latest} decisions",
)

# Rule 3 -- plan hash: the hash-pinned plan file is the single frozen authority.
print("\nPlan hash (tickets/REBUILD_PLAN.md)")
plan_path = ROOT / "tickets" / "REBUILD_PLAN.md"
plan_sha = hashlib.sha256(plan_path.read_bytes()).hexdigest() if plan_path.exists() else "(missing)"
check(
    "plan hash: sha256(tickets/REBUILD_PLAN.md) equals the pinned approved value",
    plan_sha == PINNED_PLAN_SHA256,
    f"committed file is {plan_sha}; pinned approved value is {PINNED_PLAN_SHA256}",
)

# Rule 4 -- pointer order: completed/ is a prefix of the order table; ACTIVE.md names the
# first ticket after that prefix, or the sentinel when the table is exhausted.
print("\nPointer order (tickets/completed/ vs tickets/ACTIVE.md)")
completed_dir = ROOT / "tickets" / "completed"
completed = sorted(p.stem for p in completed_dir.glob("*.md")) if completed_dir.exists() else []
prefix = list(ORDER[: len(completed)])
off_table = sorted(set(completed) - set(ORDER))
check(
    "pointer order: tickets/completed/ is exactly a prefix of the order table",
    set(completed) == set(prefix) and not off_table,
    f"completed/ holds {completed}; the order-table prefix is {prefix}"
    + (f"; not on the table: {off_table}" if off_table else ""),
)
expected = ORDER[len(completed)] if len(completed) < len(ORDER) else SENTINEL
check(
    "pointer order: ACTIVE.md names the first ticket after the completed prefix",
    pointer == expected,
    f"ACTIVE.md names {pointer!r} but the order table expects {expected!r}",
)

# Rule 5 -- banned phrases: retired lifecycle vocabulary must not return to the plan.
print("\nBanned phrases (tickets/REBUILD_PLAN.md, outside fenced code blocks)")
plan_scannable = outside_fences(read("tickets/REBUILD_PLAN.md"))
hits = [phrase for phrase in BANNED_PHRASES if phrase in plan_scannable]
check(
    "banned phrases: no retired-lifecycle phrase outside fences",
    not hits,
    "banned phrase present outside fences: " + ", ".join(repr(h) for h in hits),
)

# Rule 6 -- manifest partition: every row owned, the owner counts exact.
print("\nManifest partition (docs/PORT_MANIFEST.md)")
manifest = read("docs/PORT_MANIFEST.md")
row_re = re.compile(r"^\|\s*\d+\s*\|\s*(\S+)\s*\|\s*`[^`]+`\s*\|\s*`[0-9a-f]{64}`\s*\|", re.M)
owners = Counter(row_re.findall(manifest))
unknown = {owner: n for owner, n in owners.items() if owner not in EXPECTED_PARTITION}
check(
    "manifest partition: owner partition sums 138 + 4 + 1 + 1 = 144, no row unowned",
    dict(owners) == EXPECTED_PARTITION and sum(owners.values()) == 144,
    f"owner counts are {dict(owners)}; the partition must be GMR-003=138 + GMR-001=4 "
    f"+ GMR-002=1 + SUPERSEDED-000A=1 = 144"
    + (f"; unrecognized owner(s): {unknown}" if unknown else ""),
)

# Rule 7 -- plan hash (pack): the freshness rules watch the active ticket and the decision
# count; neither notices a stale plan version. Rule 7 makes that drift mechanical
# (added by the §GMR-003R plan-revision PR; D-046 fixes the rule set at exactly 1-7).
# The match is anchored to the pack's Plan record -- the bullet beginning
# "- Plan: REBUILD_PLAN" -- not to the first hash-shaped string in the file, so an
# unrelated entry carrying the right value cannot mask a stale Plan record. A missing
# Plan record, or a Plan record without a hash, FAILS the rule rather than passing
# vacuously.
print("\nPlan hash recorded in CONTEXT_PACK.md (the Plan record)")
plan_entry_m = re.search(r"^- Plan: REBUILD_PLAN.*?(?=^- |\Z)", pack, re.M | re.S)
if plan_entry_m is None:
    pack_hash = "(no '- Plan: REBUILD_PLAN' record in CONTEXT_PACK.md)"
else:
    entry_hash_m = re.search(r"`([0-9a-f]{64})`", plan_entry_m.group(0))
    pack_hash = (
        entry_hash_m.group(1) if entry_hash_m else "(the Plan record contains no sha256)"
    )
check(
    "plan hash (pack): the pack's Plan record carries the pinned approved plan hash",
    pack_hash == PINNED_PLAN_SHA256,
    f"the Plan record in CONTEXT_PACK.md carries {pack_hash}; pinned approved value is "
    f"{PINNED_PLAN_SHA256}",
)

print(f"\n{checks_run} checks run, {len(failures)} failed")
if failures:
    print("\nFAILURES:")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print("Clean.")
