# REBUILD_PLAN v15 — GMR-001 … GMR-005

Authorized by D-030; revised per D-031..D-046. v8 existed because GMR-003's builder stopped:
criterion 5 assumed test node IDs are a function of the test files, and they are a function of
the whole repository tree — and in one case of the absolute checkout path. No zero-deviation
transplant could satisfy it. The diagnostic that replaced it is recorded in D-039; GMR-001 and
GMR-002 are COMPLETE and are unchanged by this revision. v9 repaired seven v8 blockers (D-040).
**v10** repairs seven more (D-041), every one a propagation failure from adding GMR-005 without
sweeping the places ticket order and counts appear: GMR-004's closeout still named the sentinel,
its deselect arithmetic misstated the count (narrative), the changed pointer-order guard was
not demonstrated, the regime table in the governance document and a stale sequencing line were
left outside the revision PR's delta, the manifest still credited GMR-001 with a 144-row
verification, GMR-005 could retire a node by deleting live coverage, and the GMR-003 narrative
still carried v8's counts. **v11** repairs five more (D-042): two v10 edits that silently
no-oped and were reported as applied — GMR-005's coverage-protection criteria and a superseded
approval reference — plus a stale decision range, and the finding that matters most: v10
*described* a plan-internal-consistency checker in its decision register but never **required**
it in §GMR-003R, so a builder could have satisfied every criterion while omitting the mechanism
the plan claimed as its defence. Rules 8-12 are now specified in the plan and each is
demonstrated failing. **v12** repairs three more (D-043): that opening range was itself
stale — the defect the new rule exists to catch, in the plan's first line, because my rule matched
only ranges beginning `D-001` and this one begins `D-031`; §GMR-003R now specifies **rule 13**
for decision-range currency over **any** range; criterion 6's tenth demonstration required a
result to be simultaneously red and clean, and is restructured as a separate **exemption control**
with its expected plan-hash red stated explicitly; and `PROJECT_STATE.md` still said this PR
contains six files. **v13** repairs three more (D-044), every one found by comparing the plan's
specification against the delivered checker source rather than against its description: rule 9 was
implemented in one direction only, so an orphan ticket section carrying executable criteria could
have sat outside the approved order undetected; rule 13's historical exemption used a 300-character
window where the plan fixes 500, a false-positive in a guard built to avoid false positives; and
the introduction to the rule list contradicted the list. **Rule 14** now checks the rule list
against itself. **v14** answers three v13 findings (D-045) that share one root: the reviewer
inserted evasions (narrative examples, quoted only) — a rephrased pointer instruction, a
restated remaining-entry sentence, a duplicated rule heading — and my guards stayed green. Regex over prose can always be rephrased
around (narrative); the fix is not another spelling. **The two prose-dependent claims are now declared in
structured fields** (`**Closeout pointer:**` per ticket, and a deselection ledger table), the
fields are what a builder executes, and prose about them is explicitly narrative. Where a prose
net remains it is written to **over-trigger and demand an explicit marker**, because a guard that
under-triggers is silent and a guard that over-triggers is merely annoying. **v15** acts on a
Product Owner ruling (D-046): the plan-internal-consistency rules are **removed from the
repository checker's scope**. Five reviews running, the findings were about those rules and not
about the transplant they were meant to protect. They caught Claude Lead's authoring errors, not
builder errors, and a text checker cannot be proven complete against paraphrase — so the plan now
requires only rules 1-7, and the consistency rules survive as a Lead-side authoring tool claimed
as nothing more.
v5 **removed** the freeze/annex machinery of v2-v4 rather than patching it again: the plan file
itself, hash-pinned, is the single frozen authority. v6-v7 harden that mechanism's edges:
version-proof binding, an explicit pointer base case, per-object review regimes, the exact
banned-phrase list, and a negative demonstration for every checker rule.
Five tickets, plus one dedicated plan-revision PR (§GMR-003R) that commits these bytes before
GMR-003 resumes. §GMR-003R is **not** a ticket: it produces no completed record and does not move
`ACTIVE.md`, which stays on GMR-003 throughout. Every scope line traces to verified evidence: the GMN-000A repository (D-027),
the GMS-001 blob-sourced inventory (D-029), and `docs/PORT_MANIFEST.md` — the transplant
universe extracted verbatim from the audit, **144 rows as of v3** (D-039, D-040).

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
| GMR-005 implementation + closeout PRs | B | |

A Regime B package includes the CI run on the reviewed branch and the merge-gate state; a
ticket's two PRs may therefore sit in different regimes, and GMR-002's do.

**Closeout pointers are declared, not narrated** (plan-v13 finding 1). Every ticket section
carries exactly one line of the form `**Closeout pointer:** <GMR-00N|SENTINEL>`. **That field is
the instruction a builder executes**; prose elsewhere describing pointer behaviour is narrative
and non-operative, and may not be relied on. The declarations must match the order table exactly,
which rule 8 now checks against the field rather than against a sentence form — an evasion like
"points to the sentinel" changes no field and therefore changes no instruction.

**The deselection ledger** (plan-v13 finding 2), the single authority for how many nodes are
deselected at each stage. Prose counts are narrative; this table is operative:

| Stage | Deselected | Set |
|---|---:|---|
| GMR-003 commits the register | 6 | the six register nodes |
| after GMR-004 removes its two | 4 | rows 1-2 and 5-6 of the register |
| after GMR-005 retires the rest | 0 | none |

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
    GMN-000A → GMR-001 → GMR-002 → GMR-003 → GMR-004 → GMR-005 → sentinel — verified against this table,
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
**Closeout pointer:** GMR-002

### Scope
1. **Context system:** `CLAUDE.md`, `PROJECT_STATE.md`, `DECISIONS.md` (D-001..D-036 —
   historical: the range GMR-001 committed and verified; superseded by §GMR-003R),
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
     first ticket after the prefix, or the sentinel when the table is exhausted (narrative:
     this describes the checker rule, it is not this ticket's pointer instruction); any file in
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
     no row unowned. *(Historical: these were the constants GMR-001 committed and verified;
     §GMR-003R supersedes them with 138 + 4 + 1 + 1 = 144. §GMR-001's text is preserved unchanged
     as the instruction under which a completed, approved ticket ran.)* (Arithmetic on the committed manifest — the five rules above plus this one
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
3. `DECISIONS.md` D-001..D-036 (historical: the range this completed ticket committed and
   verified; superseded by §GMR-003R), no gaps or duplicates; no document directs starting a dead
   ticket ID.
3b. **Manifest grounded against the repository** (plan-v2 UNVERIFIABLE 1): every PORT_MANIFEST
   row re-verified in the legacy clone — `git cat-file blob legacy-v0.2^{commit}:<path> |
   sha256sum` — script attached, `141/141 OK` summary pasted. The manifest's partition sums
   (135 + 4 + 1 + 1 = 141 — historical, the partition GMR-001 committed and verified;
   superseded by §GMR-003R) verified by the checker.
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
**Closeout pointer:** GMR-003

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
**Closeout pointer:** GMR-004

### Why one ticket
The audit proved the five-way split could not complete (`evaluation/` required by three,
`conftest.py` by all); the surface passes together at the tag (3,800/0), so it moves together.
GPT accepted this structure; the fixes below repair the verification boundary it rejected.

### What v8 changed, and why (D-039)
The transplant is unchanged. Three verification defects are repaired, each grounded in a
measurement the builder produced before anything was committed:

1. **Node IDs are tree-dependent.** Four modules parametrize over files discovered at collection
   time (`sorted(root.rglob("*.py"))` and similar), so their IDs move with tree size; pytest's
   duplicate-id disambiguation renumbers even shared files; and one static case in
   `tests/unit/config/test_versioning.py` renders a checkout-absolute path into its ID, which
   cannot match across any two machines. Measured: 2,885 tag nodes vs 2,620 new, 267 tag-only
   (all in those four modules), 2 new-only. **Function inventories, however, are identical:
   1,191 both sides, sha256 `200bb976c671a0f7a6e5ffa31bdb3417ff8b83f444ac2366a3654f6bc5795f1f`,
   equal per module.** Criterion 5 is rebuilt on that fact.
2. **Three documents were miscategorized.** Five transplanted tests read `docs/GLOSSARY.md`,
   `docs/adr/0008-golden-testing-strategy.md` and `docs/STREAMLIT_PROTOTYPE.md` and assert
   against their content. A document a
   ported test asserts against is a **dependency of that test**, not reference material.
   Measured: with the first two present the affected modules go 4 failed + 17 skipped → 37
   passed and the suite's skip set becomes byte-identical to the tag's (4 platform skips both
   sides); with the third present the deployment-documentation contract test passes, keeping that
   architecture guard live.
   PORT_MANIFEST v3 adds them as rows 142-144, owner GMR-003; partition 138 + 4 + 1 + 1 = 144.
   Node-ID collection is unperturbed by them (`.py`-only scans; re-collection produced a
   zero-diff 2,620-line list).
3. **Six tests read files the rebuild does not have and, in four cases, will never have.**
   They are transplanted byte-identical as content but cannot execute here. They are deselected
   by an **exact, enumerated list fixed in this plan**, each with a recorded disposition and
   owning ticket. Deselection is not a builder judgment.

### Scope — the manifest's 138 `GMR-003`-owned rows, plus these exact changes
The manifest is partitioned by owner: 1 row superseded by GMN-000A's authored `.gitignore`,
4 owned by GMR-001, 1 by GMR-002, **138 by this ticket** — including the real `__init__.py`
files, which replace the GMR-001 skeleton's empty placeholders by design, and the three documents
added in v3. The partition sums to 144 and the checker verifies it.

**New file created by this ticket, complete list:** `tests/fixtures/README_VALIDATION_ARTIFACTS.md`
(the OQ-4 marker as its own file, so no fixture byte changes).

**Deletion, enumerated:** `tests/test_skeleton.py` — GMR-001's placeholder, whose stated purpose
was to keep pytest from exit code 5 until the real suite arrived. The real suite arrives here, and
the file is discovered by `test_golden_boundaries.py`'s scan of `tests/`, producing a spurious
node. Deleting it is in scope; nothing else is deleted.

**Enumerated deviation to a GMR-001-owned file:** `pyproject.toml`'s existing
`[tool.pytest.ini_options]` table — the last table in the file — is **replaced in full** by the
table below. Every existing key **and its comment block** is preserved verbatim; the only change
is the six `--deselect` arguments appended to the end of the existing `addopts` string. v8
specified "one added block", which would have produced either a duplicate table (invalid TOML) or
a silent deletion of `minversion`, `testpaths`, `--strict-markers`, `--strict-config`, `-ra` and
the fixed Hypothesis seed (plan-v8 finding 1). The complete resulting table, exactly:

```toml
[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests"]
# --hypothesis-seed=20260724 is the GM-008 fixed property-test seed (ADR-0008):
# Hypothesis's supported pytest seed mechanism, configured explicitly here —
# never derived from a date, a clock, or an environment variable. A developer
# overrides it deliberately on the command line (a later --hypothesis-seed
# wins), e.g. --hypothesis-seed=12345 or --hypothesis-seed=random.
addopts = "-ra --strict-markers --strict-config --hypothesis-seed=20260724 --deselect tests/architecture/test_deployment_contract.py::test_requirements_txt_sits_beside_the_entrypoint --deselect tests/architecture/test_deployment_contract.py::test_the_release_archive_ships_requirements_under_the_outer_directory --deselect \"tests/unit/config/test_nonproduction_config_location.py::test_no_consumer_still_references_the_retired_fixture_path[streamlit_app.py]\" --deselect \"tests/unit/config/test_nonproduction_config_location.py::test_every_consumer_uses_the_canonical_path[streamlit_app.py]\" --deselect \"tests/unit/config/test_nonproduction_config_location.py::test_no_consumer_still_references_the_retired_fixture_path[generate_gm041_sample_evaluation.py]\" --deselect \"tests/unit/config/test_nonproduction_config_location.py::test_every_consumer_uses_the_canonical_path[generate_gm041_sample_evaluation.py]\""
```

**Before editing, verify the pre-edit table byte-for-byte** against the committed
`git show origin/staging:pyproject.toml` — header through the `addopts` line, **522 bytes**
including the five comment lines (narrative: a TOML comment count, not a deselection count).
If the committed bytes differ from the block above in any way
other than the appended deselects, **stop and return to Claude Lead**: the resulting content is
fixed by this plan and cannot be reconciled by a builder (narrative). The first two deselects are
function-level (those tests take no parameters); the last four are bracketed exact IDs, because
their functions have other parameters that must keep running. No other change to
`pyproject.toml`.

### The deselection register — six nodes, each with an owning review object
| # | Node | Absent dependency | Owner and disposition |
|---|---|---|---|
| 1 | `test_deployment_contract.py::test_requirements_txt_sits_beside_the_entrypoint` | `streamlit_app.py`, `.streamlit/config.toml`, and an **evidence bundle** | **GMR-005.** One assertion needs an evidence directory that OQ-7 keeps in the frozen legacy repository, so the legacy test cannot pass here as written; GMR-005 splits, replaces or removes it under its own criteria. |
| 2 | `test_deployment_contract.py::test_the_release_archive_ships_requirements_under_the_outer_directory` | `scripts/build_release_archive.py` | **GMR-005.** The rebuild has no release-archive mechanism; the legacy archiver is the mechanism at the centre of the D-013 duplicate-tree incident and is not transplanted to satisfy a test. |
| 3-4 | `test_nonproduction_config_location.py::{test_no_consumer_still_references_the_retired_fixture_path,test_every_consumer_uses_the_canonical_path}[streamlit_app.py]` | `streamlit_app.py` | **GMR-004**, criterion 4b — re-enabled and proven green by node ID. |
| 5-6 | the same two functions, `[generate_gm041_sample_evaluation.py]` | `scripts/generate_gm041_sample_evaluation.py` | **GMR-005.** D-029 rules the synthetic demo generator never-port, never-execute; the parameter is permanently inapplicable and GMR-005 retires it explicitly. |

**Every node has a named review object with fixed criteria — none is assigned to an undefined
future phase** (plan-v8 finding 6). v8's third deployment-contract deselection is gone: porting
`docs/STREAMLIT_PROTOTYPE.md` (manifest row 144) makes
`test_deployment_documentation_names_the_entrypoint_and_requirements` pass — measured,
content-only assertions — so the module keeps **six live tests** and criterion 7 demonstrates it
like every other guard, with no exception clause (plan-v8 finding 5).

### Implementation criteria
1. Plan binding (lifecycle): section header quoted; plan sha256 pasted, equal to the checker's
   pinned value; `ACTIVE.md` points at GMR-003.
2. Tag verification: `git rev-parse legacy-v0.2^{commit}` = `57cd833d…`, pasted.
3. **Manifest-complete provenance:** the provenance table has **exactly 138 rows** — every
   `GMR-003`-owned manifest row, in manifest order — legacy path, manifest blob sha256, retrieved
   blob sha256 (must equal the manifest's), resulting sha256 (must also equal it: zero
   deviations). A script diffs the table's path+hash set against the manifest's `GMR-003` rows;
   its empty diff is pasted. The other six rows are accounted for by their owning tickets and the
   checker's partition test — no row of the 144 is unowned.
4. **Deviations: zero, for this ticket's 138 rows.** Identical layout, no import rewrites. The
   single `pyproject.toml` block above is the ticket's only deviation and its resulting content is
   fixed by this plan. Anything else: stop and return to Claude Lead.
5. **Test-surface equivalence, by module class** (v8; refined in v9 per plan-v8 finding 7).
   Collection runs on both sides with the **pre-deviation options**, so the two sides are
   compared under identical settings and `--strict-markers` is not silently dropped:
   `pytest -o addopts="-ra --strict-markers --strict-config --hypothesis-seed=20260724" --collect-only -q`
   (`-o addopts=` replaces the ini value entirely, so the committed deselects do not apply to the
   comparison — proven in the diagnostic).
   a. **Class B1 — tree-scanning modules, enumerated:**
      `tests/architecture/test_determinism_boundaries.py`,
      `tests/architecture/test_golden_boundaries.py`,
      `tests/architecture/test_exception_handling.py`. Their parameters are files discovered at
      collection time.
   b. **Class B2 — checkout-rendering module, enumerated:**
      `tests/unit/config/test_versioning.py`. Its divergent case is a **static** parametrization
      whose value renders the checkout-absolute path into the node ID; **no `git ls-files`
      derivation can produce it**, which is why v8's single Class B rule was unsatisfiable here.
   c. **Class A = every other manifest test module.** Exact node-ID set equality: the diff of the
      two collected lists, restricted to Class A, is **empty**. No explained-differences escape
      hatch. If any divergence appears in Class A, stop and return — the diagnostic's two
      new-only nodes are expected in Class B1, and a Class A divergence would mean something else
      changed.
   d. **Function-inventory equality, globally and per module:** node IDs truncated at the first
      `[`, deduplicated and sorted, identical on both sides — expected **1,191** entries, sha256
      `200bb976c671a0f7a6e5ffa31bdb3417ff8b83f444ac2366a3654f6bc5795f1f`; per-module counts pasted
      for the four Class B modules (45 / 32 / 17 / 47). This proves no test function was lost,
      added or renamed by the transplant.
   e. **Class B1 — parameter-set derivation:** quote each module's parametrization expression from
      the transplanted source, compute the expected file set independently from the repository
      tree (`git ls-files` filtered to the same root and glob), and show the collected parameter
      ids equal that derivation. This proves the divergence is exactly "same tests, different
      tree", not "different tests".
   f. **Class B2 — normalized node-ID equality:** replace, on each side, **the checkout root as
      it is rendered inside the node ID** with the literal `<REPO_ROOT>`, then compare the
      module's full node-ID sets — they must be **equal**. Rendering matters: pytest doubles each
      backslash of a Windows path inside the ID (`C:\\Users\\…`), so a raw filesystem-path
      replacement matches nothing; on a POSIX runner the root renders with forward slashes and no
      escaping. Measured on both sides: 70 nodes each, normalized sha256
      `8a0941ab8112e18194cd79717f6ae7dc703067bdcb8d35f69044e1c12a6ba1df`, equal.
   g. Both full node-ID lists, both function inventories, and both normalized Class B2 sets are
      attached, each with its line count and sha256.
6. **Full suite green in CI on the PR**, with the deselect list active (URL pasted), plus:
   a. the collection summary line showing **`(6 deselected)`** — proof every deselect matched,
      since a deselect that matches nothing is a silent no-op;
   b. **the tag-side control:** the same six deselects applied to the tag tree remove exactly
      six nodes and the tag suite stays green — proof the list targets precisely these nodes and
      masks no real failure;
   c. the pass/skip pattern compared to the tag's for the non-deselected nodes: **4 skips both
      sides**, the same platform skips, no glossary-unavailable skips.
7. **All eight architecture guard modules demonstrated live, red for the RIGHT reason**
   (plan-v2 finding 6; plan-v3 finding 4): config, deployment-contract, determinism, evaluation,
   exception-handling, golden, import, and scoring boundaries (`static_analysis.py` is a shared
   helper, exercised through the eight). For each module, one deliberate violation of its
   namesake boundary → red → revert → green, on the demonstration-PR pattern (closed unmerged).
   **The pasted failure must include the failing test node ID from the module under
   demonstration** — a red caused only by ruff, mypy, or another suite does not count. `test_deployment_contract.py` retains **six live tests** once
   `docs/STREAMLIT_PROTOTYPE.md` is ported, so it is demonstrated exactly like the other seven —
   **there is no exception clause, and a module with no live test would be a plan defect, not a
   disclosure** (plan-v8 finding 5). Accepted scope, stated
   openly: one demonstration proves the module fires on its namesake boundary; it does not prove
   every rule inside the module.
8. `mypy --strict src/` green.
9. `tests/fixtures/README_VALIDATION_ARTIFACTS.md` present with the OQ-4 statement — fixture
   files themselves untouched (byte-identical to manifest); synthetic YAML header intact (OQ-2).
10. **Prohibited-language check, precisely defined** (plan-v3 finding 3): the transplanted 138
    files are byte-pinned by criterion 3, so searching them is meaningless and legitimate domain
    artifacts (`domain/outcome.py`, `test_outcome_record.py`, `outcome_record.json` — a domain
    type, permitted under D-017) are not violations. The check therefore runs over **only the
    files this implementation PR ADDS or MODIFIES outside the manifest** (the enumerated new file
    and the `pyproject.toml` block), with this pattern list: `likely`, `chance`, `probability`,
    `odds`, `expected value`, `projected to`, `due for`, `best bet`, `bet siz`, `bankroll`,
    `today's plays`, `unit recommendation` — each hit listed with a disposition. The file set and
    pattern list are fixed here, not chosen by the builder.
11. Checker clean (its partition rule now reads 138 + 4 + 1 + 1 = 144); revision binding; **Regime
    B evidence** — the CI run on the reviewed branch with its `headSha` equal to the reviewed head,
    and the merge-gate state; source archive delivered as a base64 transfer document.

---

## GMR-003R — Plan revision: commit the approved plan, re-pin, manifest v3

**Builder:** Fable · **Regime:** B · **Runs before GMR-003 resumes.**

The lifecycle requires that a revised plan is committed "together with the checker's new hash, in
a dedicated PR." The lifecycle does not state that PR's criteria, so they are fixed here and are
part of what the reviewer approves when it approves these plan bytes.

### Scope — exactly seven files (v9; plan-v8 findings 2 and 3; plan-v9 finding 4)
`tickets/REBUILD_PLAN.md` (these bytes), `scripts/check_consistency.py` (new pinned hash;
partition constants 138/4/1/1 = 144; the order table gains GMR-005; the new rule 7 below),
`docs/PORT_MANIFEST.md` (v3), **`DECISIONS.md`** (D-037..D-046 appended), **`PROJECT_STATE.md`**,
**`CONTEXT_PACK.md`** (plan version, approved hash and decision count brought current), and
**`docs/TEAM_ROLES.md`** — whose per-object regime table was verified against the plan at GMR-001
and would otherwise stop reproducing it the moment GMR-005 exists (plan-v9 finding 4).

v8 confined this PR to three files, which would have merged a repository whose own current-state
files still asserted that v7 was authoritative and v8 pending, and whose committed plan cited
decisions absent from its committed register. **A plan-revision PR that knowingly commits false
current state is not a smaller change; it is a defective one.** `tickets/ACTIVE.md` is still
untouched — GMR-003 remains active — and no completed record is created.

**New checker rule 7, the only rule this PR adds:** the plan hash recorded in `CONTEXT_PACK.md`
must equal `PINNED_PLAN_SHA256`. The freshness rules watch the active ticket and the decision
count; neither notices a stale plan version. Rule 7 makes that drift mechanical.

**Product Owner ruling — the plan-internal-consistency rules are removed from this PR's scope
(D-046).** Five consecutive reviews found no defect in GMR-003's transplant criteria and instead
found defects in a set of checker rules I had added to catch **my own** propagation errors when
revising the plan. Those rules do not govern the builder: a transplant is neither safer nor less
safe for them. They belong to Claude Lead's authoring toolchain, not to the repository's
executable authority, and claiming otherwise created an unbounded review surface — a text checker
cannot be proven complete against paraphrase, so each round closed real holes while opening the
next round. **The repository checker implements rules 1-7 and nothing more.** Claude Lead's kit
checker retains the plan-consistency rules as an unreviewed authoring tool; it is **not** claimed
as enforcement, is not a gate on any ticket, and its output is offered as disclosure rather than
evidence. Hardening it further is Lead housekeeping, tracked outside the plan.

The structured `**Closeout pointer:**` declarations and the deselection ledger stay in the plan.
They are good drafting whether or not a script reads them: the field is unambiguous where prose
was not, and a builder following the field cannot be misled by a sentence.

**Supersession, stated so the two texts cannot be read as contradicting each other:** §GMR-001's
scope item 3 names the partition `135 + 4 + 1 + 1 = 141` and six checker rules. That was correct
for the manifest GMR-001 committed and for the verdict that approved it; §GMR-001's text is
preserved unchanged as the historical instruction under which a completed, approved ticket ran.
This PR supersedes those constants with `138 + 4 + 1 + 1 = 144` and adds rule 7. Completed
records link back to the plan hash they executed under, so GMR-001's record continues to name
`f9c9089f…` and remains accurate.

### Criteria
1. The committed `tickets/REBUILD_PLAN.md` is byte-identical to the bytes the reviewer's approval
   names by sha256; that value is pasted and equals the checker's new `PINNED_PLAN_SHA256`.
2. The diff touches exactly the seven files above, and all seven are changed. `tickets/ACTIVE.md`,
   `tickets/completed/`, and every other repository file are untouched — shown by
   `git diff --stat`.
3. `docs/PORT_MANIFEST.md` is v3: rows 142-144 present with the blob hashes this plan names,
   **re-verified against the tag** (`git cat-file blob legacy-v0.2^{commit}:<path> | sha256sum`,
   all three pasted); row count 144; owner partition 138/4/1/1; and **every statement in the file about who verified what** is
   correct: GMR-001 committed and verified 141 rows; rows 142-144 and the 144/144 total are
   verified here. No paragraph of the manifest may credit GMR-001 with a 144-row verification
   (plan-v9 finding 5).
4. `DECISIONS.md` runs D-001..D-046 with no gap or duplicate, and every decision the committed
   plan cites now exists in the committed register — **no dangling reference**, demonstrated by
   grepping the plan's `D-0NN` citations against the register.
5. `PROJECT_STATE.md` and `CONTEXT_PACK.md` record **this** plan version and approved hash, the
   decision count 46, and GMR-003 as active. No line of either file asserts a superseded plan
   version or a pending revision, **and no sequencing line survives that the new plan falsifies**
   — specifically "Feature phase planned after GMR-004" becomes "after GMR-005" (plan-v9
   finding 4). `grep -n "GMR-00" PROJECT_STATE.md CONTEXT_PACK.md` is pasted with a disposition
   per line. **Neither file may misstate this PR's own scope** — v11's state file said "§GMR-003R
   expanded to six files" while the plan defined seven (plan-v11 finding 3) — so the grep must
   show every sentence describing this revision, each dispositioned as correct at this commit.
5b. `docs/TEAM_ROLES.md` reproduces the plan's **complete** per-object regime table, GMR-005's two
   objects included, and its two-PR lifecycle and D-020 clauses are re-verified against the plan
   text in the diff.
6. **Four checker demonstrations, each red for the right reason** — a changed or new guard is
   demonstrated before it is trusted (D-012). Each break is made in an uncommitted working tree,
   the nonzero exit and the **rule-specific message** are pasted, the tree is restored, and one
   clean run follows:
   (i) **partition constants** — set one manifest row's owner wrong; the failure names the broken
   sum;
   (ii) **rule 7** — set the pack's recorded plan hash wrong; the failure names the pin;
   (iii) **pointer order, GMR-005 expected** — with `tickets/completed/` holding the prefix
   through GMR-004, point `ACTIVE.md` at the sentinel; the rule must fail naming **GMR-005**;
   (iv) **pointer order, sentinel expected** — with `completed/` holding the table through
   GMR-005, point `ACTIVE.md` at GMR-005; the rule must fail naming the **sentinel**.
   Demonstrations (iii) and (iv) use temporary marker files, removed before the clean run.
7. Checker clean; CI green on the branch with the run's `headSha` equal to the reviewed head;
   merge-gate state pasted; revision binding (branch, verbatim `git rev-parse HEAD`, full diff).

---

## GMR-004 — Shell and staging deploy

**Builder:** Fable · **Regime:** B · **Two submissions, then the standard closeout PR** (the
lifecycle's two-PR structure, with review split in two for the implementation): submission 1
(shell + requirements + deployment config) is reviewed before merge; submission 2 (redeploy +
rollback evidence) is produced after merge, before any production merge; the closeout PR follows
submission 2's approval, per the universal lifecycle, its completed record quoting both
submissions' verdicts. Rollback runs **before** closeout, so the tree-equality check is never polluted by
closeout files.
**Closeout pointer:** GMR-005

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
4b. **Re-enable this ticket's two owned deselections** (narrative; GMR-003 deselection
   register, rows 3-4):
   remove exactly those two entries from `pyproject.toml`'s `addopts` — the resulting block is
   pasted in full — and show
   `tests/unit/config/test_nonproduction_config_location.py::test_no_consumer_still_references_the_retired_fixture_path[streamlit_app.py]`
   and `…::test_every_consumer_uses_the_canonical_path[streamlit_app.py]` **passing**, by node ID,
   in the CI run. The remaining **four** entries stay — narrative: the deployment-contract pair
   and the `[generate_gm041_sample_evaluation.py]` pair — and the collection summary shows
   `(4 deselected)`, the ledger's second stage. The arithmetic is the ledger's, not prose's
   (narrative; v9 misstated it, plan-v9 finding 2). The complete resulting
   `[tool.pytest.ini_options]` table, exactly:

   ```toml
   [tool.pytest.ini_options]
   minversion = "8.0"
   testpaths = ["tests"]
   # --hypothesis-seed=20260724 is the GM-008 fixed property-test seed (ADR-0008):
   # Hypothesis's supported pytest seed mechanism, configured explicitly here —
   # never derived from a date, a clock, or an environment variable. A developer
   # overrides it deliberately on the command line (a later --hypothesis-seed
   # wins), e.g. --hypothesis-seed=12345 or --hypothesis-seed=random.
   addopts = "-ra --strict-markers --strict-config --hypothesis-seed=20260724 --deselect tests/architecture/test_deployment_contract.py::test_requirements_txt_sits_beside_the_entrypoint --deselect tests/architecture/test_deployment_contract.py::test_the_release_archive_ships_requirements_under_the_outer_directory --deselect \"tests/unit/config/test_nonproduction_config_location.py::test_no_consumer_still_references_the_retired_fixture_path[generate_gm041_sample_evaluation.py]\" --deselect \"tests/unit/config/test_nonproduction_config_location.py::test_every_consumer_uses_the_canonical_path[generate_gm041_sample_evaluation.py]\""
   ``` A deployment shell that does not satisfy the config-location contract is not a
   deployment shell.
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
   submissions' verdicts and SHAs; `ACTIVE.md` points at **GMR-005**, the next ticket in the
   approved order (narrative: the final pointer belongs to GMR-005's closeout; this ticket's own
   instruction is its `**Closeout pointer:**` field — plan-v9 finding 1). Reviewed against the fixed
   closeout criteria.

---

## GMR-005 — Deselection retirement

**Builder:** Fable · **Regime:** B · **Runs after GMR-004 is COMPLETE.**
**Closeout pointer:** SENTINEL

Created because "the feature phase" is not a review object (plan-v8 finding 6). Every node still
deselected after GMR-004 has an owner here, with fixed criteria, so no transplanted test can be
left permanently disabled by silence.

### Scope
The nodes still deselected at this ticket's start — the ledger's third stage begins here
(narrative):
`test_deployment_contract.py::test_requirements_txt_sits_beside_the_entrypoint`,
`test_deployment_contract.py::test_the_release_archive_ships_requirements_under_the_outer_directory`,
and the two `test_nonproduction_config_location.py` cases parametrized
`[generate_gm041_sample_evaluation.py]`.

### Implementation criteria
1. Plan binding; `ACTIVE.md` points at GMR-005.
2. **Every one of the four nodes reaches exactly one of three terminal states, each evidenced:**
   (a) **re-enabled** — the deselect entry is removed and the node is shown passing by ID in CI;
   (b) **replaced** — a rebuild-appropriate test is authored that asserts the same contract
   against the rebuild's own layout, shown passing by ID, and the legacy node is removed from the
   suite with its deselect entry; or (c) **removed** — the legacy test is deleted with a written
   justification naming the recorded ruling that makes it inapplicable (OQ-7 for the evidence
   bundle, D-029 for the never-port generator), and the deselect entry goes with it.
   A node left deselected fails this criterion. "Still pending" is not a terminal state.
2b. **Removal may not take live coverage with it** (plan-v9 finding 6). For every file this
   ticket deletes from or edits, paste the module's collected node-ID inventory **before and
   after**: the only nodes permitted to disappear are the register nodes being retired. Deleting
   `tests/architecture/test_deployment_contract.py` to retire two nodes — taking its six live
   tests with them — or deleting `tests/unit/config/test_nonproduction_config_location.py` to
   retire two generator parameters would leave the suite green precisely because the coverage was
   destroyed, and fails this criterion.
2c. **One node may not use state (c) at all.**
   `tests/architecture/test_deployment_contract.py::test_requirements_txt_sits_beside_the_entrypoint`
   asserts four things; only the evidence-bundle assertion is inapplicable under OQ-7. The others
   — the entrypoint and the deployment configuration — are live rebuild concerns. This node
   reaches **(a) re-enabled** or **(b) replaced with those applicable assertions preserved and
   shown passing by ID**; outright removal is not available for it, and the package lists which
   assertions the replacement carries forward, one line each.
3. `pyproject.toml`'s `addopts` contains **no `--deselect` argument** at the end of this ticket;
   the complete resulting table is pasted. If any deselect must survive, this ticket cannot
   complete and returns to Claude Lead for a plan revision that says so explicitly.
4. Full suite green in CI; the collection summary shows **`(0 deselected)`**; the pass/skip
   pattern is pasted and every previously deselected node is accounted for by (a), (b) or (c).
5. Any test file this ticket authors or deletes is enumerated in its package with the reason;
   the transplanted files it does not touch remain byte-identical to the manifest, re-verified.
6. D-015/D-017 prohibited-language check over the files this PR adds or modifies; checker clean;
   Regime B evidence; revision binding.

## After GMR-005
Bootstrap complete — GMR-005 retires the last deselection, so no transplanted test is left
disabled. Claude Lead plans the feature phase (screens; the ingestion decision OQ-3;
the confidence surface and legibility guards from D-030's deferred register) as its own small
package, GPT-reviewed before any feature ticket starts.
