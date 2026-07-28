# GPT review package template

Every package sent to GPT follows this skeleton (authored fresh in GMR-001,
implementation criterion 1c). An omitted section is itself a review finding. Where this
template and the hash-pinned plan disagree, the plan wins.

## 1. Plan binding

- Quote the plan section header of the ticket under review (for example
  `## GMR-001 — Foundation: context system, toolchain, skeleton`).
- Paste `sha256(tickets/REBUILD_PLAN.md)`. It must equal the checker's pinned value —
  a mismatch means the package was built against bytes GPT never approved.

## 2. Revision binding (D-028a)

- Branch name.
- `git rev-parse HEAD` — verbatim output.
- The full diff under review, untruncated.

## 3. Regime

Name the review regime from the plan's per-object regime table.

- **Regime A:** evidence is pasted command output and observable repository state.
- **Regime B:** additionally include the CI run (URL and conclusion) on the reviewed
  branch and the merge-gate state.

## 4. Evidence, criterion by criterion

- Every implementation criterion of the pinned plan section, in order, each with its
  pasted command output. A criterion asserted without output is not met.
- Show every attempt, including failures. A negative demonstration must be red for the
  right reason: the rule-specific failure message, then the restore, then a final clean
  run.
- `python scripts/check_consistency.py` output, clean, at the head under review.

## 5. Closeout packages

A closeout package addresses the plan lifecycle's fixed closeout criteria **(a) through
(g), by name**:

- (a) the diff touches only the four closeout files, and all four are changed;
- (b) the completed record quotes the full implementation verdict verbatim in a fenced
  `VERDICT` block, plus the approved head SHA, the date, and the plan-section link-back;
- (c) `tickets/ACTIVE.md` points at the next ticket in the approved order, verified
  against the plan's order table;
- (d) `PROJECT_STATE.md` gains the templated completion line and keeps no stale status
  line for the completed ticket;
- (e) `CONTEXT_PACK.md` records the completion and agrees with the state file;
- (f) the prohibited-language check runs on the closeout diff excluding fenced `VERDICT`
  blocks, and is pasted clean;
- (g) the checker is clean, including its pointer-order and plan-hash rules.
