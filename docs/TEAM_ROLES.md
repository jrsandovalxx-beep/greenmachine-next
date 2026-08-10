# Team roles and review lifecycle

Authored fresh in GMR-001 to agree with the hash-pinned `tickets/REBUILD_PLAN.md`
(implementation criterion 1c). Where this file and the plan disagree, the plan wins and
this file is defective.

## Roles

| Role | Primary responsibility | Must not do |
|---|---|---|
| Product Owner | Priorities, final product and model decisions, staging acceptance, production approval | Routine Git or engineering work |
| Claude Lead | Lead engineering: plan sections, acceptance criteria, architecture, sequencing, pointer moves | Approve its own work for production, or override a GPT rejection |
| GPT | Independent review and release approval of the actual branch, diff, and evidence | Define the tickets it later reviews, or approve without real evidence |
| Claude Code Fable | Complex implementation and repository operations | Final production approval, or baseball rule invention |
| Claude Code Sonnet | Routine implementation within an approved plan section | Architecture changes |
| Claude Research | External evidence and cited briefs | Code or pushes |
| Grok | Baseball rulings (D-023 locked set) | Git, deployment, engineering |

Separation of duties: the role that defines a ticket never approves it, and the builder
never substitutes self-review for GPT's independent approval (D-011).

## Two PRs per ticket (plan lifecycle)

- **Implementation PR** — the work. Its package binds to the plan: it quotes the plan
  section header and pastes `sha256(tickets/REBUILD_PLAN.md)`, which must equal the
  checker's pinned value. Reviewed against the section's implementation criteria.
  Merges into `staging` only after GPT approval of the head SHA.
- **Closeout PR** — touches only the four closeout files (completed record, pointer,
  state, pack) and is reviewed against the lifecycle's fixed closeout criteria (a)-(g).
  The completed record quotes the implementation verdict verbatim in a fenced `VERDICT`
  block.

A ticket is COMPLETE when both verdicts exist.

## Review regimes (D-018, D-028a)

- **Regime A — pre-CI.** Evidence is pasted command output and observable repository
  state. Every package carries revision binding (D-028a): branch name,
  `git rev-parse HEAD` verbatim, and the full diff under review.
- **Regime B — post-CI.** Everything Regime A carries, plus the CI run on the reviewed
  branch and the merge-gate state.

The regime follows the infrastructure state at submission time, fixed in advance per
review object:

| Review object | Regime |
|---|---|
| GMR-001 implementation PR | A |
| GMR-001 closeout PR | A |
| GMR-002 implementation PR | A (the last Regime A object) |
| GMR-002 closeout PR | B |
| GMR-003 implementation + closeout PRs | B |
| GMR-004 submissions 1, 2 + closeout PR | B |
| GMR-005 implementation + closeout PRs | B |
| FEATURE_PHASE_PLAN document review | document object — reviewed as pasted bytes, no PR |
| FEATURE_PHASE_PLAN revision r1 — document review | document object — reviewed as pasted bytes, no PR |
| FEATURE_PHASE_PLAN revision r1 — commit PR (no completed record) | B |
| §GMF-000R plan-commit PR (no completed record) | B |
| GMF-001 implementation + closeout PRs | B |
| GMF-002 submission 1, deployed verification, closeout | B |
| GMF-003 implementation + closeout PRs | B |
| GMF-004 implementation + closeout PRs | B |
| GMF-005 submission 1, deployed verification, closeout | B |
| GMF-006 submission 1, deployed verification, closeout | B |

The feature phase comprises **19 review objects** in total (FEATURE_PHASE_PLAN §4c: the
plan document, revision r1's document review and commit, §GMF-000R, and the six GMF
tickets at 2 + 3 + 2 + 2 + 3 + 3). Deployed
verification follows the GMR-004 two-submission pattern with **no D-018-style
exception**: submission 1 merges only after its own approval, and submission 2 merges
nothing (FEATURE_PHASE_PLAN §4d).

## GPT's rejection and the overrule process (D-020)

A GPT rejection blocks the merge until the blocker is fixed **or** the Product Owner
overrules it in writing. An overrule is a written entry appended to `DECISIONS.md` that
quotes the objection verbatim, states the reason, the date, and the release it applies
to. Never silent, never verbal, never retroactive. Claude Lead cannot override a
rejection — only the Product Owner can, and only in writing.

Stated honestly: this is an advisory rejection with an audit trail, not an absolute
veto. The protection is the permanent record that someone chose to ship over the
objection, and why.
