# PROJECT_STATE.md

Current state only. History and reasoning live in `DECISIONS.md`. Rewritten clean 2026-07-27
(D-028c) after the file accreted contradictions across five review rounds.

## Repository
- `greenmachine-next`: created, **private**, account on **GitHub Pro** (D-027).
- Branches: `main` (default), `staging`. Initial commit `3d5e4fde`.
- Protection live on both: PRs required (0 approving reviews - solo config, D-027),
  `enforce_admins` on, no force push, no deletion. All six destructive operations demonstrated
  rejected, force pushes from proven-divergent refs.
- Local clone: `Desktop\greenmachine-next`, clean, tracking origin.

## Legacy
- `greenmachine-dashboard`: frozen at tag `legacy-v0.2` = commit `57cd833d`. Read-only reference.
- The tag is **annotated**: resolve with `git rev-parse legacy-v0.2^{commit}` (D-028d).
- Full salvage inventory exists at the tag: 778 tracked files categorized PORT 141 / REFERENCE 104
  / EXTRACT 3 / REJECT 530, complete reject log, secret scan clean (D-029).
- At the tag: no betting-signal fields on the contract; full suite 3,800 passed / 0 failed;
  CI green (D-029).

## Ticket status
- **GMN-000A: COMPLETE and APPROVED WITH NOTES** for SHA
  `3d5e4fde3d6065fad1078749c85eb61b96fde9de` (disclosed in GPT's plan-v4 review after the
  supplement was reviewed). Both judgment calls confirmed. The base gate for GMR-001 is cleared;
  the full verdict text goes into the GMN-000A completed record during GMR-001.
- **The plan is `tickets/REBUILD_PLAN.md` v7 (GMR-001..004, D-030): APPROVED WITH NOTES
  2026-07-28** for sha256 `f9c9089f036011678ba1c5d71bace3d1ea2895524e68a9777df8042085397443`.
  The old backlogs are retired archive.
- **GMR-001: IN BUILD** (Fable) against the approved plan. Submission requires the committed
  plan and the checker's pin to equal the approved hash.

## Specialist work
- **GB-001/GB-002 (Grok): complete.** Twelve locked decisions (D-023), sample floors and rulings
  confirmed (D-025, D-026).
- **GR-001 (Research): complete.** IAA official endpoint located (requires the `bat-tracking/`
  path segment - the spike used the wrong path); bat-tracking boundary is 2023-07-14 with columns
  present-but-empty earlier (values become None, no schema-drift failure); no published rate
  limits on Savant or the MLB Stats API - proposed policy pending; weather via Open-Meteo (free,
  CC-BY 4.0, archivable) with Visual Crossing as paid fallback; park factors have no working CSV
  export (JSON-in-HTML interface risk); MLBAM terms are individual, non-commercial, non-bulk.
- **GMS-001 (salvage audit): complete** (D-029).

## Sequencing
1. GMN-000A review CLOSED: APPROVED WITH NOTES for `3d5e4fde…` after the evidence supplement.
2. Plans v1-v6 REJECTED (9+7+7+8+7+7 findings, D-031..D-036). **Plan v7 APPROVED WITH NOTES
   2026-07-28**, the approval naming sha256 `f9c9089f0360…085397443`. Approval note, binding:
   the checker spec's "exactly these five" precedes six enumerated rules; the verdict rules the
   executable meaning unambiguous - **six rules, all six implemented, all six negatively
   demonstrated**. The approved bytes are hash-pinned and are not edited to fix the wording;
   the note travels with the verdict.
3. **GMR-001 is in build** (Fable, per §GMR-001). The GMN-000A verdict text for criterion 1b
   was re-emitted verbatim by GPT in the approval round and ships in the build package.
4. Feature phase planned after GMR-004.

## Open Product Owner decisions
- From GR-001: IAA source of record (official leaderboard vs event-derived, with the
  competitive-swings filter caveat); weather provider confirmation (Open-Meteo proposed); MLBAM
  terms tolerance; roof-status handling; park-factors approach given no CSV endpoint.
- Deferred pending a season of side-specific data (D-026): pitch-mix numeric bands;
  pitcher-vulnerability numeric thresholds.
- Legacy Q11-Q16 (production model configuration: max_points, bucket thresholds) remain open.
- Production deployment URL. (Staging host: Streamlit Community Cloud, D-024.)

## Team
- Claude Lead: tickets, architecture, sequencing (D-011).
- GPT: independent reviewer; a rejection is overridable only by written Product Owner ruling
  (D-020, reaffirmed D-028b).
- Claude Code Fable: complex builder. Sonnet: routine builder. Claude Research: evidence.
  Grok: baseball rulings.

## Last full context audit
- This rewrite, 2026-07-27.
