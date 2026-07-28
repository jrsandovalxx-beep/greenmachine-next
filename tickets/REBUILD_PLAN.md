# REBUILD_PLAN v7 — GMR-001 … GMR-004

Authorized by D-030; revised per D-031..D-036 (45 findings across six reviews, all accepted).
v5 **removed** the freeze/annex machinery of v2-v4 rather than patching it again: the plan file
itself, hash-pinned, is the single frozen authority. v6-v7 harden that mechanism's edges:
version-proof binding, an explicit pointer base case, per-object review regimes, the exact
banned-phrase list, and a negative demonstration for every checker rule.
Four tickets. Every scope line traces to verified evidence: the GMN-000A repository (D-027), the
GMS-001 blob-sourced inventory (D-029), and `docs/PORT_MANIFEST.md` — the 141-file transplant
universe extracted verbatim from the audit.

**Gate before anything starts:** GMR-001 does not begin until GMN-000A holds an **APPROVED**
verdict naming its SHA. A plan approval does not cure an unapproved base (GPT finding 9).

**Source of truth for every transplant:** tag `legacy-v0.2`, resolved as
`git rev-parse legacy-v0.2^{commit}` (annotated tag, D-028d). Expected:
`57cd833d742272b0af8f35801dfa7dfb9534c3e0`. Mismatch → stop and report.

## Standing rules — all tickets

- Branch from updated `staging`; PR targets `staging`; `main` untouched.
- Revision binding in every package (D-028a): branch, `git rev-parse HEAD` verbatim, full diff.
- Provenance for every transplanted file: legacy path, blob sha256 at the tag, resulting sha256,
  source archive attached. Hashes from git blobs, never a working tree.
- Byte-identical means byte-identical. **Permitted deviations are enumerated per ticket, in
  advance. Any deviation not on the list: stop and return to Claude Lead.** "Near-zero" is not a
  number and appears nowhere in this plan (GPT finding 6).
- Merges into `staging` happen **only after GPT approval** of the ticket head — the sole
  exception remains GMR-004 submission 2 (D-018). Demonstration PRs are closed unmerged.

## Ticket lifecycle — the plan is the freeze

The v2-v4 freeze-and-annex ritual is gone (plan-v4 findings 1, 2, 3, 5). What replaces it has
three moving parts:

**1. The plan file is the frozen authority.** GMR-001 commits this file byte-identical to the
version GPT approved, and the repository checker embeds its sha256 — any later edit turns the
checker red. There is no per-ticket freeze commit, because there is nothing left to freeze: the
ticket text a builder executes IS the committed, hash-pinned, independently approved plan
section. `tickets/ACTIVE.md` becomes a two-line **pointer** ("Active: GMR-00N per
REBUILD_PLAN §GMR-00N" or the sentinel `NO ACTIVE TICKET — next phase pending planning`) with no
freeze semantics. Plan changes are made only by committing a revised plan **after** it has been
GPT-reviewed, together with the checker's new hash, in a dedicated PR.

**2. Two PRs per ticket, two distinct review objects** (plan-v4 finding 3):
- **Implementation PR** — the work. Its package binds to the plan: it quotes the section header
  and pastes `sha256(tickets/REBUILD_PLAN.md)`, which must equal the checker's pinned value.
  Reviewed against the ticket's **implementation criteria** (the numbered lists below). Merges
  after approval.
- **Closeout PR** — reviewed against the fixed **closeout criteria** (next paragraph). A ticket
  is COMPLETE when both verdicts exist.

**Review regime follows the infrastructure state at submission time, not the ticket label**
(plan-v6 finding 4). The regime of every review object, fixed in advance:

| Review object | Regime | Why |
|---|---|---|
| GMR-001 implementation PR | A | no CI exists yet |
| GMR-001 closeout PR | A | CI still absent — GMR-002 creates it |
| GMR-002 implementation PR | A | the PR that creates CI; the **last Regime A object** |
| GMR-002 closeout PR | B | CI exists once the implementation PR merges |
| GMR-003 implementation + closeout PRs | B | |
| GMR-004 submissions 1, 2 + closeout PR | B | |

A Regime B package includes the CI run on the reviewed branch and the merge-gate state; a
ticket's two PRs may therefore sit in different regimes, and GMR-002's do.

**3. Closeout, with an exact permitted delta** (plan-v4 findings 4, 8). A closeout PR may touch
only:
- `tickets/completed/GMR-00N.md` — new file: the implementation verdict **as issued**, the
  approved head SHA, the date, and a link-back "ticket text: REBUILD_PLAN §GMR-00N @ <plan
  sha256>". No ticket-text copy — the plan is pinned, so a copy is duplication, not evidence.
- `tickets/ACTIVE.md` — pointer swap to the next ticket or the sentinel.
- `PROJECT_STATE.md` — append one templated completion line; amend status lines that name this
  ticket. Nothing else in the file.
- `CONTEXT_PACK.md` — same templated scope.
Closeout criteria, fixed for every ticket (plan-v5 findings 3, 5, 7 — "may touch only" limits
the file set; these require the updates to actually occur and be correct):
(a) the diff touches only the four files above, **and all four are changed**;
(b) the completed record quotes the **full implementation verdict text verbatim** inside a fenced
    block labeled `VERDICT` (label-only is not a record; APPROVED WITH NOTES without its notes
    loses the notes), plus the approved head SHA, the date, and the plan-section link-back;
(c) `tickets/ACTIVE.md` points to the **next ticket in the approved order** —
    GMN-000A → GMR-001 → GMR-002 → GMR-003 → GMR-004 → sentinel — verified against this table,
    not against the context pack (the table begins at GMN-000A because its completed record is
    the first file in `tickets/completed/`; plan-v6 finding 3);
(d) `PROJECT_STATE.md` gains the templated completion line naming the approved implementation
    SHA, and **no stale status line for the completed ticket remains**;
(e) `CONTEXT_PACK.md` records the completion and agrees with the state file;
(f) the prohibited-language check runs on the closeout diff **excluding fenced `VERDICT`
    blocks** — a verdict legitimately discusses the banned vocabulary while evaluating it — and
    is pasted clean;
(g) the checker is clean, including its pointer-order and plan-hash rules.
**The closeout PR's own approval lives in the review thread, like every PR approval.** The
repository records each ticket's implementation verdict; it does not attempt to contain the
approval of its own final commit — that regress is acknowledged and accepted, not papered over
(plan-v4 finding 5).
---

## GMR-001 — Foundation: context system, toolchain, skeleton

**Builder:** Fable · **Regime:** A (revision binding per D-028a applies in full)

### Scope
1. **Context system:** `CLAUDE.md`, `PROJECT_STATE.md`, `DECISIONS.md` (D-001..D-036),
   `CONTEXT_PACK.md` (hand-maintained), `tickets/ACTIVE.md` (the two-line pointer to GMR-001),
   `tickets/REBUILD_PLAN.md`, `tickets/completed/GMN-000A.md`, `docs/TEAM_ROLES.md`,
   `docs/GPT_REVIEW_PACKAGE_TEMPLATE.md`, `docs/PRODUCTION_MERGE_CHECKLIST.md`.
2. **`docs/PORT_MANIFEST.md`** — committed verbatim from the kit, frozen here so GMR-003's
   universe predates GMR-003 (GPT finding 3).
3. **`scripts/check_consistency.py`** — the repository-adapted checker (source: the kit's
   script; adapted paths). Its repository rules, exactly these five — criterion 3c demonstrates
   each one failing:
   - **Freshness (ticket):** `CONTEXT_PACK.md` names the current active ticket.
   - **Freshness (count):** `CONTEXT_PACK.md` states the current decision count.
   - **Plan hash:** the pinned `REBUILD_PLAN.md` sha256 matches the committed file.
   - **Pointer order** (plan-v5 finding 5; base case plan-v6 finding 3): the completed order
     table is **GMN-000A → GMR-001 → GMR-002 → GMR-003 → GMR-004**. The set of files in
     `tickets/completed/` must be exactly a prefix of that table; `ACTIVE.md` must name the
     first ticket after the prefix, or the sentinel when the table is exhausted; any file in
     `completed/` not on the table is a failure. Base case, explicit: at GMR-001's own commit,
     `completed/` holds exactly `GMN-000A.md`, so the expected pointer is GMR-001. The pointer
     is checked against this table, never against the context pack.
   - **Banned phrases** (plan-v6 finding 7 — the list is fixed here, not chosen by the
     builder): the plan file must not contain, **outside fenced code blocks**, any of the seven
     retired-lifecycle phrases below. Fenced code blocks are excluded from the scan so this
     list can name what it bans — the same exclusion the closeout language check applies to
     `VERDICT` blocks.

     ```BANNED-PHRASES
     frozen first commit
     and the ticket freeze
     freezes the ticket's text
     APPROVAL RECORD
     its annex
     approval annex
     annex quoting
     ```
   - **Manifest partition:** the `PORT_MANIFEST.md` owner partition sums 135 + 4 + 1 + 1 = 141,
     no row unowned. (Arithmetic on the committed manifest — the five rules above plus this one
     are the checker's full repository rule set.)
4. **Toolchain transplanted from the tag:** `pyproject.toml`, `Makefile`,
   `.pre-commit-config.yaml`, `requirements.txt`. Enumerated deviations with their **exact
   resulting values** (plan-v4 finding 7 — categories are not deviations; results are):
   - `pyproject.toml` `version = "0.3.0"` (name stays `greenmachine`);
   - `pyproject.toml` ruff specifier becomes exactly `ruff>=0.6,<0.16` — 0.16.x is the version
     whose behavior change caused the recorded green-local/red-CI split, so the ceiling **excludes
     it**; v5's `<0.17` bound permitted the exact version it claimed to exclude (plan-v5
     finding 2);
   - `requirements.txt` retains `-e .` per D-030.
   Any other byte difference from the tag blobs: stop and return to Claude Lead.
5. **Skeleton:** `src/greenmachine/` with `common/`, `domain/`, `evaluation/`, `config/`,
   `scoring/` — `__init__.py` only. One placeholder test importing each subpackage (pytest must
   collect ≥1 or GMR-002's pipeline dies on exit code 5).

### Implementation criteria
1. **Plan binding, version-proof:** the committed `tickets/REBUILD_PLAN.md` is byte-identical
   to the plan bytes GPT approved — **the approval verdict names the sha256 it applies to**, and
   that value is both the checker's pinned hash and the pasted `sha256sum` of the committed
   file. No version numeral appears in this criterion by design: v6 named a specific superseded
   revision here and thereby ordered the builder to commit rejected bytes (plan-v6 finding 1) —
   a numeral goes stale every revision round; the verdict-named hash cannot. `tickets/ACTIVE.md`
   is the two-line pointer to GMR-001.
1b. **The GMN-000A completed record meets the record standard retroactively** (plan-v6
   finding 5): `tickets/completed/GMN-000A.md` quotes GPT's GMN-000A verdict **verbatim as
   issued** inside a fenced `VERDICT` block — the APPROVED WITH NOTES label, every note, the
   point-in-time protection limitation — plus the reviewed SHA
   `3d5e4fde3d6065fad1078749c85eb61b96fde9de`, the verdict date, and the line-back "ticket
   text: pre-plan bootstrap (D-027); reviewed under Regime A per D-028a". The verbatim text
   ships in the build package; a summary, paraphrase, or label-only record is a criterion
   failure.
1c. **The governance documents agree with this plan** (plan-v6 finding 6), verified clause by
   clause in the implementation diff — these documents assemble future review packages, so
   doc-vs-plan drift is a separation-of-duties defect:
   - `docs/TEAM_ROLES.md` states the two-PR-per-ticket lifecycle, the per-object regime table,
     Regime A and B definitions (D-018, D-028a), and D-020's overrule process (written Product
     Owner entry in `DECISIONS.md`, objection preserved verbatim).
   - `docs/GPT_REVIEW_PACKAGE_TEMPLATE.md` requires plan binding (section header +
     `sha256(tickets/REBUILD_PLAN.md)`), revision binding (branch, `git rev-parse HEAD`
     verbatim, full diff), and — for closeout packages — the closeout criteria (a)–(g) by name.
   - `docs/PRODUCTION_MERGE_CHECKLIST.md` includes the ancestry check
     (`git merge-base --is-ancestor <approved-SHA> <branch>`) and re-capture of branch
     protection before any production merge (protection evidence is point-in-time).
   - `CLAUDE.md` directs builders: the pinned plan section is the sole ticket text; no work
     without `ACTIVE.md` naming the ticket; stop-and-return on any unenumerated deviation.
   These documents are **authored fresh in this ticket to satisfy exactly these clauses** — no
   kit template is ported, so no stale template can compete with the pinned plan. A governance
   document contradicting the plan is a criterion failure regardless of the checker's result.
2. Provenance table for the four toolchain files; resulting bytes differ from the tag blobs
   exactly and only by the enumerated values above.
3. `DECISIONS.md` D-001..D-036, no gaps or duplicates; no document directs starting a dead
   ticket ID.
3b. **Manifest grounded against the repository** (plan-v2 UNVERIFIABLE 1): every PORT_MANIFEST
   row re-verified in the legacy clone — `git cat-file blob legacy-v0.2^{commit}:<path> |
   sha256sum` — script attached, `141/141 OK` summary pasted. The manifest's partition sums
   (135 + 4 + 1 + 1 = 141) verified by the checker.
3c. **Every checker rule demonstrated failing, red for the right reason** (D-012; plan-v2
   finding 5; plan-v6 finding 2): in an uncommitted working tree, one deliberate break per
   rule; checker run; the nonzero exit **and the rule-specific message** pasted; restore; one
   final clean run pasted. The six demonstrations:
   (i) `CONTEXT_PACK.md` names a wrong active ticket → freshness (ticket) fails, named;
   (ii) `CONTEXT_PACK.md` states a wrong decision count → freshness (count) fails, named;
   (iii) one byte changed in `tickets/REBUILD_PLAN.md` → the plan-hash rule fails, citing the
   pinned value;
   (iv) `ACTIVE.md` pointed at GMR-002 while `completed/` holds only `GMN-000A.md` → the
   pointer-order rule names GMR-001 as expected (this exercises the base case);
   (v) a phrase from the BANNED-PHRASES block inserted into the plan copy **outside any fenced
   block** → the banned-phrase rule names the phrase;
   (vi) one manifest row's owner edited → the partition rule reports the broken
   135 + 4 + 1 + 1 sum.
   A demonstration that fails for any reason other than the rule under test does not count.
   A checker that has only ever passed is not a guard (D-012). The plan hash is the only freeze
   mechanism this plan has — its failure path is demonstrated, not trusted.
4. **Every transplanted toolchain file exercised** (GPT finding 4):
   `pip install -e ".[dev]"` from a fresh clone; **`make check` runs and passes** (exercises the
   Makefile and each gate it wraps); **`pre-commit install && pre-commit run --all-files`
   passes**; **`pip install -r requirements.txt` succeeds in a second fresh venv**. All output
   pasted.
5. Placeholder test passes; `mypy --strict src/` and `ruff check .` pass.
6. `scripts/check_consistency.py` runs clean; output pasted. Its pinned plan hash equals the
   committed plan's sha256.
6b. **`PROJECT_STATE.md` is accurate at commit time** (plan-v4 finding 6): it records GMN-000A as
   APPROVED WITH NOTES for SHA `3d5e4fde…` — the actual current state — and every status line is
   checked against reality in the review package, line by line. Committing a known-stale state
   file as the repository's first truth is a criterion failure.
7. No absolute path, home-dir reference, or credential (grep pasted).
8. PR into `staging`; revision binding stated. (Closeout is the second PR, reviewed against the
   lifecycle's closeout criteria.)

---

## GMR-002 — CI: transplant the workflow, prove every gate can fail

**Builder:** Fable · **Regime:** A for the implementation PR — it creates the CI its successors
require, and is the **last Regime A review object**. The closeout PR follows the CI-creating
merge and is therefore **Regime B** — CI run on the closeout branch and merge-gate state
included — like every review object after it (plan-v6 finding 4; the lifecycle's regime table).

### Scope
Transplant `.github/workflows/ci.yml` from the tag. Wire branch protection to require the check
on both branches.

### The demonstration protocol (GPT finding 2)
Negative tests run on a **separate throwaway demonstration PR** (`demo/gmr-002-gates`) that is
**closed unmerged** after the evidence is captured — scratch commits never enter `staging` and
never need approval. The real GMR-002 implementation PR contains **the workflow, nothing else**
(closeout is its own PR per the lifecycle); it stays green and merges only after GPT approval. What is demonstrated is **merge state**, never a merge.

### Implementation criteria
1. Plan binding (lifecycle): section header quoted; plan sha256 pasted, equal to the checker's
   pinned value; `ACTIVE.md` points at GMR-002.
2. Provenance for `ci.yml`; deviations: none — resulting hash equals the manifest hash.
3. Green run on the real PR (URL + summary pasted).
4. **Four negative tests, one per gate** (GPT finding 5), each on the demonstration PR, each
   shown red then green after revert: a broken test; a lint violation; a type error; **a
   formatting violation** (a file `ruff format --check` rejects). Every attempt shown.
5. While the demonstration PR is red, GitHub reports it **blocked from merging** (merge-state
   output pasted); after revert, mergeable. The demonstration PR is then closed unmerged, its
   branch deleted; `git ls-remote` shows it gone.
6. **Protection regression check** (plan-v3 finding 2): after wiring the CI requirement,
   re-capture the full protection configuration on both branches via `gh api` and diff it against
   the GMN-000A-approved configuration. **The only permitted delta is the added required status
   check** — the diff is pasted and shows nothing else changed (PRs required, enforce_admins,
   force-push and deletion rejection all intact). Then one live re-test per branch: a direct push
   is rejected (output pasted). Mutating a guardrail re-proves it.
7. Wall-clock under 10 minutes, recorded.
8. Checker clean; revision binding. (Closeout is the second PR.)

---

## GMR-003 — Core transplant: the manifest, entire, one ticket

**Builder:** Fable · **Regime:** B

### Why one ticket
The audit proved the five-way split could not complete (`evaluation/` required by three,
`conftest.py` by all); the surface passes together at the tag (3,800/0), so it moves together.
GPT accepted this structure; the fixes below repair the verification boundary it rejected.

### Scope — the manifest's 135 `GMR-003`-owned rows, plus enumerated new files
The manifest is partitioned by owner (plan-v2 finding 2): 1 row superseded by GMN-000A's authored
`.gitignore`, 4 owned by GMR-001 (toolchain, enumerated deviations), 1 by GMR-002 (`ci.yml`),
**135 by this ticket** — including the real `__init__.py` files, which replace the GMR-001
skeleton's empty placeholders by design. The partition sums to 141 and the checker verifies it.

**New files created by this ticket's implementation PR, complete list** (plan-v2 finding 3 —
scope is manifest rows *plus exactly this*): `tests/fixtures/README_VALIDATION_ARTIFACTS.md`
(the OQ-4 marker as its own file, so no fixture byte changes). Nothing else — the completed
record, state, pack, and pointer changes belong to the closeout PR, per the lifecycle.

### Implementation criteria
1. Plan binding (lifecycle): section header quoted; plan sha256 pasted, equal to the checker's
   pinned value; `ACTIVE.md` points at GMR-003.
2. Tag verification: `git rev-parse legacy-v0.2^{commit}` = `57cd833d…`, pasted.
3. **Manifest-complete provenance:** the provenance table has **exactly 135 rows** — every
   `GMR-003`-owned manifest row, in manifest order — legacy path, manifest blob sha256, retrieved
   blob sha256 (must equal the manifest's), resulting sha256 (must also equal it: zero
   deviations). A script diffs the table's path+hash set against the manifest's `GMR-003` rows;
   its empty diff is pasted. The other six rows are accounted for by their owning tickets and the
   checker's partition test — no row of the 141 is unowned.
4. **Deviations: zero, for this ticket's rows.** Identical layout, no import rewrites. If any
   file genuinely requires deviation, stop and return to Claude Lead — that is a plan defect,
   not a builder judgment call. (The enumerated-deviation rows belong to GMR-001 and are checked
   there.)
5. **Node-ID equivalence, not counts** (GPT findings 3 and 6): `pytest --collect-only -q` run on
   the tag restricted to manifest test paths, and in the new repository; both **full node-ID
   lists** attached; their diff is **empty**. Then the run: pass/skip pattern identical to the
   tag's for those nodes. No "explained differences" escape hatch — a non-empty diff fails the
   ticket.
6. Full suite green in CI on the PR (URL pasted).
7. **All eight architecture guard modules demonstrated live, red for the RIGHT reason**
   (plan-v2 finding 6; plan-v3 finding 4): config, deployment-contract, determinism, evaluation,
   exception-handling, golden, import, and scoring boundaries (`static_analysis.py` is a shared
   helper, exercised through the eight). For each module, one deliberate violation of its
   namesake boundary → red → revert → green, on the demonstration-PR pattern (closed unmerged).
   **The pasted failure must include the failing test node ID from the module under
   demonstration** (`tests/architecture/test_X.py::test_...` in the pytest output) — a red caused
   only by ruff, mypy, or another suite does not count, even if the PR is red. Accepted scope,
   stated openly: one demonstration proves the module fires on its namesake boundary; it does not
   prove every rule inside the module. The tag-green suite plus one live firing per module is the
   bootstrap bar; per-rule demonstrations are not required.
8. `mypy --strict src/` green.
9. `tests/fixtures/README_VALIDATION_ARTIFACTS.md` present with the OQ-4 statement — fixture
   files themselves untouched (byte-identical to manifest); synthetic YAML header intact (OQ-2).
10. **Prohibited-language check, precisely defined** (plan-v3 finding 3): the transplanted 135
    files are byte-pinned by criterion 3, so searching them is meaningless and legitimate domain
    artifacts (`domain/outcome.py`, `test_outcome_record.py`, `outcome_record.json` — a domain
    type, permitted under D-017) are not violations. The check therefore runs over **only the
    files this implementation PR ADDS or MODIFIES outside the manifest** (the enumerated new file),
    with this pattern list: `likely`, `chance`, `probability`, `odds`,
    `expected value`, `projected to`, `due for`, `best bet`, `bet siz`, `bankroll`,
    `today's plays`, `unit recommendation` — each hit listed with a disposition. The file set and
    pattern list are fixed here, not chosen by the builder.
11. Checker clean; revision binding; source archive attached for GPT. (Closeout is the second
    PR.)

---

## GMR-004 — Shell and staging deploy

**Builder:** Fable · **Regime:** B · **Two submissions, then the standard closeout PR** (the
lifecycle's two-PR structure, with review split in two for the implementation): submission 1
(shell + requirements + deployment config) is reviewed before merge; submission 2 (redeploy +
rollback evidence) is produced after merge, before any production merge; the closeout PR follows
submission 2's approval, per the universal lifecycle, its completed record quoting both
submissions' verdicts. Rollback runs **before** closeout, so the tree-equality check is never polluted by
closeout files.

### Commit and environment resolution, defined in advance (plan-v2 finding 7)
`streamlit_app.py` resolves its displayed commit in this order — **git first, so a stale
environment variable can never mask a live checkout:**
1. `git rev-parse --short HEAD` when a git repository is present — including detached HEAD,
   which is a valid state with a valid SHA and must display it;
2. else `GM_COMMIT`, displayed with an explicit provenance marker — `abc1234 (env)` — so a
   reader can see the value came from configuration, not the checkout;
3. otherwise the literal `unknown`. Never a crash.
Where the env route is the only option (if Community Cloud exposes no git metadata),
`docs/DEPLOYMENT.md` must make updating `GM_COMMIT` a step of the deploy procedure itself, and
the redeploy test (criterion 6) proves the procedure updates it — the marker and the SHA must
both change. Staleness there is a documented procedural risk owned by the deploy runbook, not a
claim that it cannot happen.

Environment label: config value `staging` / `production`, explicit `local` fallback when unset.
Version: package metadata with explicit `unknown` fallback.

### Scope
1. `streamlit_app.py`: name, environment, version, commit per the resolution rules. No product
   screens; no odds/probability/outcome language (D-015/D-017).
2. `requirements.txt` finalized per D-030; contract test updated; supersession recorded — with
   completion evidence (plan-v3 finding 6): the final file's full content pasted; every runtime
   dependency listed with its version bound (an unbounded one fails the criterion); the changed
   contract test named by node ID; **the old contract shown failing against the new file, then
   the updated contract passing** — proof the contract actually changed, not a narrative; and the
   committed `DECISIONS.md` supersession section quoted from the repository.
3. Community Cloud staging app tracking `staging` (D-024); `docs/DEPLOYMENT.md` with redeploy
   and rollback procedures.

### Implementation criteria — submission 1
1. Plan binding (lifecycle): section header quoted; plan sha256 pasted; `ACTIVE.md` points at
   GMR-004.
2. App renders all four fields locally.
3. **Resolution tests, every route exercised locally and unconditionally** (plan-v2 finding 7;
   plan-v3 finding 5):
   a. environment unset → `local`; set to `staging` → `staging`; **set to `production` →
      `production`** (all three values, not two);
   b. package not installed (fresh venv, no `-e .`) → version `unknown`;
   c. no `.git`, no `GM_COMMIT` → commit `unknown`;
   d. **no `.git`, `GM_COMMIT=deadbee` → displays `deadbee (env)` with the provenance marker** —
      tested here, not left conditional on what Community Cloud happens to expose;
   e. detached HEAD → the correct SHA, not `unknown`;
   f. git present AND `GM_COMMIT` set to a different value → the **git** SHA wins (precedence
      proven, not asserted).
4. **Requirements contract evidence** (plan-v5 finding 4 — scope prose is not a criterion;
   this is): the final `requirements.txt` pasted in full; every runtime dependency listed with
   its version bound, an unbounded one failing the criterion; the changed contract test named by
   node ID; the **old contract shown failing** against the new file, then the updated contract
   passing; the committed D-030 supersession section quoted from the repository.
5. D-015/D-017 grep clean; CI green on the PR; checker clean; revision binding.

### Implementation criteria — submission 2 (post-merge, pre-production)
6. Deployed staging URL renders environment **`staging`** and the SHA of
   `git rev-parse --short staging`. If Community Cloud does not expose git metadata, report the
   observed behavior and configure the `GM_COMMIT` route instead — what may not happen is a
   silent wrong SHA.
7. **Redeploy test:** merge a trivial visible change (post-approval); deployed app shows it and
   the new SHA.
8. **Rollback, defined objectively** (GPT finding 8): rollback is a `git revert` PR into
   `staging` (protected branch — history moves forward). Success means all three, shown:
   (a) `git rev-parse staging^{tree}` **equals the prior commit's tree hash** — content
   identity, not narrative; (b) the deployed app displays the **new revert commit's SHA**;
   (c) the visible marker from criterion 7 is gone. `docs/DEPLOYMENT.md` states exactly this
   procedure and was followed verbatim; any improvised step is a documentation defect.
9. No secret, private path, or traceback in the deployed page.

### Closeout PR (after submission 2 approval)
10. The universal closeout PR per the lifecycle, its completed record quoting **both**
   submissions' verdicts and SHAs; `ACTIVE.md` gets the sentinel. Reviewed against the fixed
   closeout criteria.

---

## After GMR-004
Bootstrap complete. Claude Lead plans the feature phase (screens; the ingestion decision OQ-3;
the confidence surface and legibility guards from D-030's deferred register) as its own small
package, GPT-reviewed before any feature ticket starts.
