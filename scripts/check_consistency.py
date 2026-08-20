#!/usr/bin/env python3
"""Repository consistency checker for greenmachine-next.

Adapted for the repository from the planning kit's checker (REBUILD_PLAN, GMR-001
scope item 3; rules re-pinned and rule 7 added by §GMR-003R per D-046; extended to
the two-plan form by §GMF-000R per FEATURE_PHASE_PLAN §5/§5a — ten rules, and
nothing more):

1.  freshness (ticket)      CONTEXT_PACK.md names the current active ticket.
2.  freshness (count)       CONTEXT_PACK.md states the current decision count.
3a. rebuild-plan hash       sha256(tickets/REBUILD_PLAN.md) equals its pin.
3b. feature-plan hash       sha256(tickets/FEATURE_PHASE_PLAN.md) equals its pin.
4.  pointer order           tickets/completed/ is exactly a prefix of the order table
                            and tickets/ACTIVE.md names the first ticket after that
                            prefix (two checks).
5.  banned phrases          neither plan contains a retired-lifecycle phrase outside
                            fenced code blocks (extended across both plans; still one
                            rule).
6.  manifest partition      the PORT_MANIFEST owner partition sums 138 + 4 + 1 + 1
                            = 144, no row unowned.
7a. bootstrap pack record   the pack's "Plan (bootstrap, historical)" record carries
                            the pinned REBUILD_PLAN hash AND a version label equal to
                            that plan's own title version.
7b. feature pack record     the pack's "Plan (active, feature phase)" record carries
                            the pinned FEATURE_PHASE_PLAN hash AND a version label
                            equal to that plan's own title version.

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

# Two plans, two independently checked pins (FEATURE_PHASE_PLAN §5). Any later change
# to either plan turns its rule red; a plan revision is committed only with a reviewed
# PR that updates the pin alongside the plan bytes (plan lifecycle).
# REBUILD_PLAN v16 = v15 + the §GMF-000R two-line revision (version line, GMR-005
# criterion-4 correction); the bootstrap's completed records keep their v15 link-backs.
PINNED_REBUILD_PLAN_SHA256 = "c41b6abd5fbe64c0e9b468bea0c9a2ddb5f1b646780c017655f0295aa0b82ca2"
# FEATURE_PHASE_PLAN v6, APPROVED — the bytes committed unaltered by §GMF-000R.
PINNED_FEATURE_PLAN_SHA256 = "87f76fade5fc33faa3c29d6d65dc57eece2150ce1c5857a1cc1b707e5802d2e5"

# The completed-order table (FEATURE_PHASE_PLAN §4a — the complete combined sequence,
# authoritative there). The set of files in tickets/completed/ must be exactly a prefix
# of this table.
ORDER = (
    "GMN-000A",
    "GMR-001",
    "GMR-002",
    "GMR-003",
    "GMR-004",
    "GMR-005",
    "GMF-001",
    "GMF-002",
    "GMF-003",
    "GMF-004",
    "GMF-005",
    "GMF-006",
    "GMF-007",
    "GMF-008",
    "GMF-009",
)
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
    m = re.search(r"^Active:\s*(GM[NRF]-\w+|NO ACTIVE TICKET.*?)\s*(?:per\b.*)?$", txt, re.M)
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

# Rules 3a and 3b -- plan hashes: each hash-pinned plan file is a frozen authority,
# each guarded by its own pin (FEATURE_PHASE_PLAN §5: a single constant cannot guard
# two files).
print("\nPlan hashes (tickets/REBUILD_PLAN.md, tickets/FEATURE_PHASE_PLAN.md)")
rebuild_path = ROOT / "tickets" / "REBUILD_PLAN.md"
rebuild_sha = (
    hashlib.sha256(rebuild_path.read_bytes()).hexdigest() if rebuild_path.exists() else "(missing)"
)
check(
    "rebuild-plan hash: sha256(tickets/REBUILD_PLAN.md) equals its pinned value",
    rebuild_sha == PINNED_REBUILD_PLAN_SHA256,
    f"committed file is {rebuild_sha}; pinned value is {PINNED_REBUILD_PLAN_SHA256}",
)
feature_path = ROOT / "tickets" / "FEATURE_PHASE_PLAN.md"
feature_sha = (
    hashlib.sha256(feature_path.read_bytes()).hexdigest() if feature_path.exists() else "(missing)"
)
check(
    "feature-plan hash: sha256(tickets/FEATURE_PHASE_PLAN.md) equals its pinned value",
    feature_sha == PINNED_FEATURE_PLAN_SHA256,
    f"committed file is {feature_sha}; pinned value is {PINNED_FEATURE_PLAN_SHA256}",
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

# Rule 5 -- banned phrases: retired lifecycle vocabulary must not return to either
# plan. Extended across both plans by §GMF-000R (FEATURE_PHASE_PLAN §5): the hash
# rules protect today's approved bytes, but this rule exists precisely to survive
# tomorrow's authorized re-pins. One rule, both files.
print("\nBanned phrases (both plans, outside fenced code blocks)")
phrase_hits: list[str] = []
for plan_rel in ("tickets/REBUILD_PLAN.md", "tickets/FEATURE_PHASE_PLAN.md"):
    scannable = outside_fences(read(plan_rel))
    phrase_hits += [f"{plan_rel}: {p!r}" for p in BANNED_PHRASES if p in scannable]
check(
    "banned phrases: no retired-lifecycle phrase outside fences in either plan",
    not phrase_hits,
    "banned phrase present outside fences: " + ", ".join(phrase_hits),
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

# Rules 7a and 7b -- the two pack plan records (FEATURE_PHASE_PLAN §5a). Each rule
# anchors to its own complete record -- not to the first hash-shaped string in the
# file -- so an unrelated entry carrying the right value cannot mask a stale record
# (the rule-7 hardening, inherited by both). A missing record, or a record without a
# hash, FAILS the rule rather than passing vacuously. Each rule additionally binds
# the version label inside the record to the version string in that plan's own title
# line, so a revision that updates a plan's title without its record, or a record
# without its title, turns the checker red instead of shipping a record that misnames
# its own authority (the self-reference trap, closed mechanically).


def plan_title_version(rel: str) -> str:
    """Return the vN version string from a plan's title line."""
    m = re.search(r"^# \S+ (v\d+)\b", read(rel), re.M)
    return m.group(1) if m else "(no version in title)"


def pack_record_check(
    label: str,
    anchor: str,
    plan_rel: str,
    plan_name: str,
    pinned: str,
) -> None:
    entry_m = re.search(anchor, pack, re.M | re.S)
    if entry_m is None:
        check(
            f"{label}: the pack record exists and carries the pinned hash",
            False,
            f"no record matching {anchor!r} in CONTEXT_PACK.md",
        )
        return
    entry = entry_m.group(0)
    hash_m = re.search(r"`([0-9a-f]{64})`", entry)
    record_hash = hash_m.group(1) if hash_m else "(the record contains no sha256)"
    label_m = re.search(re.escape(plan_name) + r" (v\d+)\b", entry)
    record_version = label_m.group(1) if label_m else "(no version label in record)"
    title_version = plan_title_version(plan_rel)
    check(
        f"{label}: the record carries the pinned hash and its version label equals "
        f"the plan title's version",
        record_hash == pinned and record_version == title_version,
        f"record hash {record_hash} vs pin {pinned}; record label {record_version} vs "
        f"{plan_rel} title {title_version}",
    )


print("\nPack plan records (CONTEXT_PACK.md: bootstrap-historical and active-feature)")
pack_record_check(
    "bootstrap pack record",
    r"^- Plan \(bootstrap, historical\): REBUILD_PLAN.*?(?=^- |\Z)",
    "tickets/REBUILD_PLAN.md",
    "REBUILD_PLAN",
    PINNED_REBUILD_PLAN_SHA256,
)
pack_record_check(
    "feature pack record",
    r"^- Plan \(active, feature phase\): FEATURE_PHASE_PLAN.*?(?=^- |\Z)",
    "tickets/FEATURE_PHASE_PLAN.md",
    "FEATURE_PHASE_PLAN",
    PINNED_FEATURE_PLAN_SHA256,
)

print(f"\n{checks_run} checks run, {len(failures)} failed")
if failures:
    print("\nFAILURES:")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print("Clean.")
