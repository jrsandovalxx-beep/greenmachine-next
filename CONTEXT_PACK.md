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

- Active ticket: **GMR-005** (per `tickets/ACTIVE.md` → REBUILD_PLAN §GMR-005).
- Decision count: **46** (D-001..D-046).
- Plan: REBUILD_PLAN v15, **APPROVED WITH NOTES 2026-07-28**, sha256
  `3daa28b952f3c78d80c2d01764f495e3866eb68e32d13de86ac6f7a67646d904` — the checker's pinned
  value.
- GMN-000A complete: APPROVED WITH NOTES for `3d5e4fde3d6065fad1078749c85eb61b96fde9de`.
- GMR-001 complete: implementation APPROVED for `3fc9f1e04d71cbd4ec464634d5598e16510a496d`,
  merged to `staging` (`a3eb0ea26db6f4a1ac94cc7d6f75fe1a3afc9774`); closeout approved
  `5e90e5967212b32a4620a5ca9742df28ac8e5742`.
- GMR-002 complete: implementation APPROVED WITH NOTES for
  `3e01ad3e4b90326f478083e727f97f9b2fe71ca3`, merged to `staging`
  (`adb5405d881a1d8ba0046469f51bcf1dac5cae4c`); closeout approved
  `0612a39450b206e8a8f1019451a4349f94a5ce0c`. CI live and required on both branches.
- GMR-003 implementation complete: APPROVED WITH NOTES for
  `7d1a396ba8cefb451f080957eb94bbc5a9234cfd`, merged to `staging`
  (`25a86b1ec3890c9c85db95b1691c2fd231755b7e`) - the manifest's 138 rows, entire.
- GMR-004 both submissions complete: S1 APPROVED WITH NOTES for
  `72a31e44bcd98b94c1256e82547ae6ab29395bda` (merged `7329f02759b8ee4f8608fd5409ccfd23125ec933`);
  S2 APPROVED WITH NOTES at head of record `500613ec81dd972a3ad53d8f4ec618665ad90c5f`. Staging app
  live and public: https://greenmachine.streamlit.app/

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
