# CONTEXT_PACK.md

Hand-maintained orientation for builders. The authoritative state is `PROJECT_STATE.md`; the
authoritative history is `DECISIONS.md`; the authoritative ticket text is the hash-pinned
`tickets/REBUILD_PLAN.md`. If this file disagrees with any of them, this file is wrong — the
repository checker's freshness gate fails on a wrong active ticket or decision count here.

## Project

GreenMachine Next — clean rebuild of an MLB home-run research dashboard. The score is a tally
of criteria met and thresholds passed (D-015/D-017): no odds, no probabilities, no stakes, no
automated selection. Evidence confidence is displayed alongside, never fused into the score
(D-014).

## Current status

- Active ticket: **GMR-002** (per `tickets/ACTIVE.md` → REBUILD_PLAN §GMR-002).
- Decision count: **36** (D-001..D-036).
- Plan: REBUILD_PLAN v7, **APPROVED WITH NOTES 2026-07-28**, sha256
  `f9c9089f036011678ba1c5d71bace3d1ea2895524e68a9777df8042085397443` — the checker's pinned
  value.
- GMN-000A complete: APPROVED WITH NOTES for `3d5e4fde3d6065fad1078749c85eb61b96fde9de`.
- GMR-001 complete: implementation APPROVED for `3fc9f1e04d71cbd4ec464634d5598e16510a496d`,
  merged to `staging` (merge commit `a3eb0ea26db6f4a1ac94cc7d6f75fe1a3afc9774`); record:
  `tickets/completed/GMR-001.md`.

## Read first

1. `CLAUDE.md`
2. `PROJECT_STATE.md`
3. `DECISIONS.md`
4. `tickets/ACTIVE.md`, then the pinned plan section it names
5. `docs/TEAM_ROLES.md` and `docs/PORT_MANIFEST.md`

## Team

- Claude Lead: tickets, architecture, sequencing (D-011). Never approves its own work.
- GPT: independent reviewer and release approver. A rejection is overridable only by a written
  Product Owner ruling in `DECISIONS.md` (D-020, reaffirmed D-028b).
- Claude Code Fable: complex builder. Sonnet: routine builder. Claude Research: evidence.
  Grok: baseball rulings (D-023 locked set).

## Legacy source

Tag `legacy-v0.2` = `57cd833d742272b0af8f35801dfa7dfb9534c3e0`, resolved with
`git rev-parse legacy-v0.2^{commit}` (annotated tag, D-028d). Every transplanted byte comes
from tag blobs (`git cat-file`), never a working tree.
