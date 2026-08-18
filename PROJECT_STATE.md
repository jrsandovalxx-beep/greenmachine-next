# PROJECT_STATE.md

Current state only. History and reasoning live in `DECISIONS.md`. Rewritten clean 2026-07-27
(D-028c) after the file accreted contradictions across five review rounds.

## Repository
- `greenmachine-next`: created, **private**, account on **GitHub Pro** (D-027).
- Branches: `main` (default), `staging`. Initial commit `3d5e4fde`.
- Protection live on both: PRs required (0 approving reviews - solo config, D-027),
  `enforce_admins` on, no force push, no deletion. All six destructive operations demonstrated
  rejected, force pushes from proven-divergent refs.
- Local clone: `Desktop\greenmachine-next`; working tree clean.

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
- **GMR-001: COMPLETE** - implementation APPROVED for SHA `3fc9f1e04d71cbd4ec464634d5598e16510a496d`
  (2026-07-27), merged to `staging` as `a3eb0ea26db6f4a1ac94cc7d6f75fe1a3afc9774`; closeout
  APPROVED WITH NOTES for `5e90e5967212b32a4620a5ca9742df28ac8e5742`. Records:
  `tickets/completed/GMR-001.md`.
- **GMR-002: COMPLETE** - implementation APPROVED WITH NOTES for SHA
  `3e01ad3e4b90326f478083e727f97f9b2fe71ca3` (2026-07-27), merged to `staging` as
  `adb5405d881a1d8ba0046469f51bcf1dac5cae4c`; closeout APPROVED WITH NOTES for
  `0612a39450b206e8a8f1019451a4349f94a5ce0c`. Records: `tickets/completed/GMR-002.md`.
- CI live and required on both branches: contexts `Format, lint, type check, test (Python 3.11)`
  and `Format, lint, type check, test (Python 3.12)`, strict off. Every review object from
  GMR-002's closeout onward is Regime B.
- **GMR-003: implementation COMPLETE** - APPROVED WITH NOTES for SHA
  `7d1a396ba8cefb451f080957eb94bbc5a9234cfd` (2026-07-31), merged to `staging` as
  `25a86b1ec3890c9c85db95b1691c2fd231755b7e`. The manifest's 138 rows landed with zero
  deviations, the one enumerated `pyproject.toml` block, the OQ-4 marker and the enumerated
  deletion of `tests/test_skeleton.py`. Record: `tickets/completed/GMR-003.md`. Its earlier stop
  (D-039) was against superseded plan v7, whose criterion 5 no zero-deviation transplant could
  satisfy; the approved v15 criteria are what it executed. The closeout PR is this ticket's
  second review object and its verdict lives in the review thread, not in this file.
- **GMR-003R: COMPLETE** — the plan-revision object of the GMR-003 sequence, seven files, no
  completed record, pointer untouched. Merged to `staging` as
  `21cd7d1e021dbde825900d5711bdc23f081a887c`: it committed the approved plan bytes, re-pinned
  the checker and landed manifest v3. The old backlogs are retired archive.
- **GMR-004: both submissions COMPLETE** — submission 1 APPROVED WITH NOTES for SHA
  `72a31e44bcd98b94c1256e82547ae6ab29395bda` (2026-08-03), merged to `staging` as
  `7329f02759b8ee4f8608fd5409ccfd23125ec933`; submission 2 APPROVED WITH NOTES at head of record
  `500613ec81dd972a3ad53d8f4ec618665ad90c5f`. The staging app is live at
  https://greenmachine.streamlit.app/ — **public**, by Product Owner choice, confirmed by
  signed-out check; the revisit trigger is the first ticket rendering real provider data
  (`docs/DEPLOYMENT.md`). Record: `tickets/completed/GMR-004.md`. This closeout PR is the ticket's
  third review object and its verdict lives in the review thread, not in this file.
- **GMR-005: COMPLETE** — implementation APPROVED WITH NOTES for SHA
  `4e6904184d02177bbf12fa5fc76f08a21f225d77` (2026-08-04), merged to `staging` as
  `4efffc0e816e2aac691d1437663ac3bcfe69785b`. The deselection ledger is at **zero** — no
  transplanted test is left disabled. Register row 1 replaced (state (b)); rows 2 and 5–6 removed
  (state (c)); `pyproject.toml`'s `addopts` carries no `--deselect`, restored byte-exactly to its
  pre-deselection form. `.streamlit/config.toml` added from the legacy tag blob, ruled in scope.
  Record: `tickets/completed/GMR-005.md`. This closeout PR is the ticket's second review object
  and its verdict lives in the review thread, not in this file. **With this ticket the bootstrap
  is complete**; the feature phase is planned as its own package, GPT-reviewed before any feature
  ticket starts.
- **Phase transition (2026-08-04): the feature phase is ACTIVE.** FEATURE_PHASE_PLAN v6
  committed and pinned by §GMF-000R; REBUILD_PLAN advanced to v16 (the §GMR-005 criterion-4
  correction and the version line — two lines, nothing else); decisions D-047..D-057 landed;
  first active ticket **GMF-001**.
- **GMF-001: implementation COMPLETE** — APPROVED WITH NOTES for SHA
  `aa962bab2faadf90d62ab990f614985ac4f29a52` (2026-08-10), merged to `staging` as
  `06013599435d4ef7c803357f5ae5c5aef5e495fb`. The input contract landed: `InputSnapshot`
  with three-way absence semantics enforced at construction — positive denominators on
  every aggregate, all three named windows mandatory with `metrics_for` total, usage
  share an observed `SnapshotField[UsageShare]`, source health carried per observation
  (the source table is identity and provenance only, and source-dependent absences name
  the source they implicate); the thirty-venue park reference with venue type (D-055);
  the pinned Savant snapshot (`2bbaee9d…`) committed with its full provenance record
  and joined by test (D-053/D-057). Three rejections and one Lead-held wrapper preceded
  approval — nine findings, all repaired at the approved head. Record:
  `tickets/completed/GMF-001.md`. This closeout PR is the ticket's second review object
  and its verdict lives in the review thread, not in this file.
- **GMF-002: implementation and deployed verification COMPLETE** — submission 1 APPROVED
  WITH NOTES for SHA `ef28d3219d773a487f633dd72a1982ea161a7972` (2026-08-11), merged to
  `staging` as `31f3cd53f6d2872b8b7619f5a3b13df5cb4240e6`; submission 2 (deployed
  verification) APPROVED WITH NOTES at head of record `31f3cd53…`, an observation object
  that merged nothing (§4d). **The grid is the first visible product surface**, live at
  https://greenmachine.streamlit.app/ and observed rendering there: five synthetic
  batters, user-controlled sorting/columns/density, numeric metric ordering, and the
  D-058 selection-driven detail mechanism driven by a real click. D-058..D-062 landed in
  the same commit as the pack-count move 57 → 62. **Recorded non-blocking product
  defect:** absent metric cells render on the deployed canvas as `None` rather than their
  three committed reasons, which survive visually only as distinct backgrounds; the
  reviewer ruled it a semantic/accessibility defect that does not falsify the GMF-002
  criterion, and authorized GMF-003's existing selection-driven detail *content* as the
  remedy vehicle — **changing the GMF-002 grid-cell representation itself is not
  authorized without plan-level authorization**. Record: `tickets/completed/GMF-002.md`,
  which carries both verdicts verbatim. This closeout PR is the ticket's third review
  object and its verdict lives in the review thread, not in this file.
- **GMF-003: implementation COMPLETE** — APPROVED WITH NOTES for SHA
  `161161457957ab7b178ba8ab802aa4e8ea5525a4` (2026-08-16), merged to `staging` as
  `dae0b42031d5d3c1d487fdb5972930f8ffd41c59`. The pitch-type metrics screen on the
  GMF-002 grid: seven metrics per qualifying pitch type against the named
  `SEASON_TO_DATE` window, the ≥15% usage threshold stated on screen with
  suppressed types named and counted, three-way absence carried to the surface,
  per-row provenance notes distinguishing sourced from derived values, and batter
  selection only by user action (`index=None` with an explicit invitation).
  **GMF-003 shipped the authorized additive remedy** for the GMF-002 `None`
  finding — absence reasons in words on its own surface and in the detail panel —
  while the component-level `None` rendering remains as recorded at GMF-002: the
  grid-cell representation is untouched in both directions. Record:
  `tickets/completed/GMF-003.md`. This closeout PR is the ticket's second review
  object and its verdict lives in the review thread, not in this file.

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
3. **GMR-001 COMPLETE** - both review objects verdicted (implementation `3fc9f1e0...`;
   closeout `5e90e596...`). Verdict-of-record hashes are certified by the reviewer before a
   completed record is built (GMN-000A `064fa760...`, GMR-001 `23109bb2...`) - the standing
   method after the GMN-000A transcription defect.
4. Feature phase planned after GMR-005.

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
