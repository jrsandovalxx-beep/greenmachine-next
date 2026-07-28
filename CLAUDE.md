# CLAUDE.md — greenmachine-next builder rules

Authored fresh in GMR-001 to agree with the hash-pinned plan (implementation
criterion 1c). Where this file and `tickets/REBUILD_PLAN.md` disagree, the plan wins
and this file is defective.

## The ticket is the plan

- The hash-pinned `tickets/REBUILD_PLAN.md` section named by `tickets/ACTIVE.md` is the
  **sole ticket text**. No other document defines scope or criteria.
- **No work without `tickets/ACTIVE.md` naming the ticket.** When the pointer shows the
  sentinel (`NO ACTIVE TICKET — next phase pending planning`), nothing is in build.
- Plan changes are made only by committing a GPT-reviewed revised plan together with the
  checker's new pinned hash, in a dedicated PR. Never edit the plan on a work branch:
  the checker's plan-hash rule turns red on any byte change.

## Product identity

- GreenMachine is an MLB home-run evaluation and research platform (D-001, narrowed by
  D-017). The score is a tally of criteria met and thresholds passed (D-015/D-017).
- No odds, no probabilities, no stakes, no picks, no automated selection, no outcome
  language. Evidence confidence is a separate axis, never fused into the score (D-014).

## Work rules

- Read `CLAUDE.md`, `PROJECT_STATE.md`, `DECISIONS.md`, `CONTEXT_PACK.md`,
  `tickets/ACTIVE.md`, then the pinned plan section it names, before any work.
- Branch from updated `staging`; PRs target `staging`; `main` is production, untouched.
- Never push directly to `main` or `staging`; never force-push; never `git add -A`.
- Transplanted bytes come from tag blobs (`git cat-file blob legacy-v0.2^{commit}:<path>`),
  never from a working tree. Every transplanted file carries provenance: legacy path,
  blob sha256 at the tag, resulting sha256 (D-013, D-028d).
- **Stop-and-return rule: any byte deviation not enumerated in the active plan section is
  returned to Claude Lead. There are no builder judgment calls on deviations.**
- Run `python scripts/check_consistency.py` before submitting any package and paste its
  output. A finding a script can catch must never reach a reviewer (D-016).
- Two PRs per ticket — implementation, then closeout (plan lifecycle). Merges happen only
  after GPT approves the head SHA; production merges additionally require the Product
  Owner and `docs/PRODUCTION_MERGE_CHECKLIST.md`.

## Loop

ORIENT -> INSPECT -> PLAN -> IMPLEMENT -> TEST -> VERIFY -> RECORD -> PUSH -> REPORT -> STOP.

Stop after the ticket. The next ticket starts only when Claude Lead moves the pointer.
