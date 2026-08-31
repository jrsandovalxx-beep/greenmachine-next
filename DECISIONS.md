# DECISIONS.md

Append-only. Add a superseding decision instead of silently rewriting history.

## D-001 - Product identity (NARROWED by D-017)
GreenMachine is an evaluation and research platform, not a betting advisor. It must not produce
wagers, stakes, picks, or automated betting recommendations.

**See D-017** for what this forbids precisely, and what it permits. The word "picks" here was read
for a time as forbidding any ranked output, which conflicted with the product itself; D-017 states
the boundary in enforceable terms.

## D-002 - Workflow order
The primary workflow is pitcher matchup -> weather/park -> batters -> hitter metrics -> longer-term matchup -> external line shopping.

## D-003 - Visual identity
The original Xbox dashboard is the primary visual language: dark green mood, neon/lime highlights, glowing orb, generous spacing, console navigation, grid background, and smooth animations.

## D-004 - Repository strategy
GreenMachine Next uses a clean repository with one canonical root tree and no inherited Git history from the legacy repository.

## D-005 - Branch strategy
`main` is production, `staging` is Product Owner testing, and `feature/*` is implementation.

## D-006 - AI team (SUPERSEDED by D-011)
ChatGPT is lead engineer/reviewer; Claude Code Fable is complex builder; Claude Code Sonnet is routine builder; Claude Research is external research analyst; Grok is baseball specialist. Gemini is not used.

## D-007 - Context cadence
Update small project-state files after every ticket. Regenerate `CONTEXT_PACK.md` after every ticket. Perform a full handoff audit every three tickets or after major architecture/provider/storage/deployment changes.

## D-008 - Current workflow thresholds (SUPERSEDED by D-023 - it was wrong)
For workflow screening: Pull >= 40%, Ideal Attack Angle >= 50%, Barrel Rate >= 10%, vulnerable pitcher or strong environment, and at least 3 of 5 criteria. These remain workflow rules until formally converted into approved production model logic.

**This decision counted pitcher vulnerability and environment among the five criteria. The Product
Owner had already locked them as sitting OUTSIDE that count.** See D-023.

## D-009 - UI filter preferences
Keep handedness, year, pitch-mix, and usage-threshold controls where relevant. Exclude home/away and day/night split filters.

## D-010 - Desktop priority
Design desktop-first because research normally occurs at night or early morning on desktop.

## D-011 - Leadership change (supersedes D-006)
Claude is appointed Lead Engineer for GreenMachine Next. Claude Lead owns ticket definitions,
acceptance criteria, architecture recommendations, roadmap sequencing, specialist assignments,
and context discipline.

GPT is retained as independent reviewer and release approver. GPT no longer defines tickets or
sets architecture. GPT reviews the actual branch, diff, tests, and CI output, and approves or
rejects before any production merge. GPT retains a genuine veto: a rejection blocks the merge
until the blocker is fixed, or until the Product Owner explicitly overrules it and that overrule
is appended here as a new decision.

Rationale: the previous arrangement combined ticket authorship and final approval in one role,
so mistakes introduced at the ticket-definition stage were reviewed by the role that made them.
Splitting authorship from approval preserves the independent check that was working while
removing the single point of inconsistency.

Unchanged by this decision: Claude Code Fable remains complex builder, Claude Code Sonnet remains
routine builder, Claude Research remains external research analyst, Grok remains baseball
specialist, Gemini is not used, and the Product Owner remains the final production approver.

## D-012 - Bootstrap ticket split
The original single GMN-000 bundled repository creation, branch protection, package skeleton,
CI, context files, context-pack generation, six Claude Code skills, safety hooks, and staging
deployment into one ticket. It is replaced by a sequenced series, GMN-000A through GMN-000H,
each with its own bounded scope and independently demonstrable acceptance criteria.

Rationale: a single ticket of that size produces a diff with too many independent surfaces for
any reviewer to check properly, so review degrades into trusting the builder's summary. Smaller
tickets keep each review small enough to actually perform, and leave the repository in a working,
verified state at every step.

Standing requirement introduced with this decision: a guardrail is accepted only when a negative
test demonstrates it blocks what it claims to block. Branch protection, CI failure, lint failure,
context-pack staleness, skill integrity, and each safety hook must each be shown failing on
purpose before the ticket that introduces them is approved. Configuration that has only ever been
observed passing is not evidence.

Where a guardrail could plausibly block legitimate work, the ticket also requires a false-positive
test showing the nearest allowed operation still succeeds.

Two items from the original GMN-000 are deliberately NOT in the new series, and are recorded here
so the split does not quietly lose them:

- The Xbox-inspired placeholder landing shell moves to GMN-001A in `REBUILD_ROADMAP.md` Stage 3.
  Bootstrap tickets are verified by command output; a visual shell is verified by the Product
  Owner's eye. Mixing the two degrades both reviews. GMN-000C ships a plain readable page.
- Nothing else. The environment (staging/production) display, the canonical-root check, type
  checking, the Streamlit smoke test, the six named skills, and the five named hooks are all
  retained and assigned to specific tickets.

Ordering note: GMN-000F (skills) is last rather than early, because `/close-ticket` and
`/refresh-context` wrap the GMN-000E context-pack generator and `/deploy-staging` wraps the
GMN-000H rollback procedure. A skill authored before the capability it wraps encodes a guess.

## D-013 - Rebuild the shell, transplant the core
GreenMachine Next is built as a clean repository with correct Git topology, protection, and CI,
into which proven components of `greenmachine-dashboard` are **transplanted** rather than
rewritten.

### Why
The GMS-001 salvage review found that the legacy repository's problems were structural and
procedural, not code quality: a duplicated project tree, stray directories, and an open Product
Owner decision backlog.

**Corrected 2026-07-27 by witness testimony.** This decision originally attributed the duplicate
tree to a Git submodule misconfiguration. That was wrong. The duplicate came from extracting a
release ZIP inside the repository root - `build_release_archive.py` sets
`ARCHIVE_PREFIX = "greenmachine"`. The `[submodule]` setting exists only in one working copy on the
Product Owner's machine and is a local, unversioned artifact, not repository content. The
transplant argument does not depend on the original mistaken diagnosis, but the record must not
assert a fact the project now knows to be false. The legacy engineering is strong: `mypy --strict`, an enforced `ruff` ruleset,
a fixed Hypothesis seed, twelve architecture-boundary test modules plus a shared helper, a
golden-case harness with
network blocking, and ten architecture decision records. Rewriting that from scratch would
discard proven work and reintroduce bugs already paid for.

### What this supersedes
- **D-004 is amended, not revoked.** GreenMachine Next still uses a clean repository with one
  canonical root tree and **no inherited Git history**. Transplanted files arrive as new commits
  with recorded provenance. No legacy history, no submodule, no duplicate tree.
- **D-012's ordering changes.** The bootstrap series no longer authors the toolchain and CI from
  scratch; GMN-000C and GMN-000D become verified ports. A new GMT series transplants the core
  before staging deployment rather than at GMN-006.

### What this does NOT change
- Branch topology, protection, and every negative test in the bootstrap series.
- The requirement that a guardrail is proven only by demonstrating it blocks something.
- The separation of duties: Claude Lead defines, Claude Code builds, GPT approves, Product Owner
  merges.
- The prohibition on inheriting legacy Git history.

### Standing rules for transplant
1. **Provenance or reject.** Every transplanted file records its legacy path, the source commit
   `57cd833`, and its source sha256. A file without provenance does not enter the repository.
2. **Byte-identical by default.** A transplanted file is copied unchanged. Every deviation is
   listed explicitly with its reason. "Improved while porting" is a rejected ticket.
3. **Behavior equivalence is demonstrated, not assumed.** A transplanted test must produce the
   **same result** in the new repository as in legacy - passing where legacy passes, failing where
   legacy fails. Equivalence is the rule; "all tests pass" is not. A test failing identically in
   both trees is evidence the transplant worked, and its failure is recorded and raised as a
   finding rather than fixed inside the port ticket.
4. **No transplant of anything the witness statement (GMS-001B) reports as inert, skipped, or
   abandoned.** Importing a dead guard is worse than having no guard, because it is trusted.
5. **Open Product Owner decisions do not transplant.** Q11-Q16 remain open. Nothing carrying an
   unapproved threshold becomes production configuration.

### Legacy repository disposition
`greenmachine-dashboard` is tagged `legacy-v0.2` and frozen. Its duplicate tree and stray
directories are NOT repaired; the repository is read-only reference from that point. Local
working-copy artifacts on the Product Owner's machine are not repository content and are out of
scope entirely.

## D-014 - Evidence confidence replaces the betting signal
The `signal` / `signal_reason` betting classification is removed from the evaluation contract. It
is replaced by a **confidence in the evidence**, not a confidence in the outcome.

### The distinction, which is the whole decision
- **Permitted:** how much data stands behind a number. "This barrel rate rests on 47 batted-ball
  events." "Weather was unavailable." "This metric used a fallback source." The reader learns how
  far to trust the measurement.
- **Forbidden:** how strongly the model rates a hitter's chance of a home run. That is a pick with
  a friendlier vocabulary, and D-001 forbids it regardless of what it is called.

Renaming is the most common way a removed classifier returns. This decision exists to make the
boundary explicit so that a future ticket cannot cross it by accident.

### Binding constraints on any confidence surface
1. **Never fused with the score.** Confidence is a separate axis. It is never multiplied into,
   weighted against, or combined with the total score or tier. A combined value is a pick.
2. **Never a probability-shaped number.** No "87% confidence", which reads as an 87% chance of a
   home run. Ordinal labels only, each stating its denominator.
3. **Always states its denominator.** "Based on 47 BBE", never a bare "High".
4. **Never the primary sort.** Ranking hitters by confidence, or by score-and-confidence together,
   reconstructs a recommendation ordering.
5. **Thresholds are a baseball ruling, not an engineering choice.** They come from Grok via GB-001
   and are approved by the Product Owner before use.

### Known trap carried from legacy
The existing `SampleStatus` values are computed from validation-only minimums of 2 (`RECENT_7D`)
and 13 (`LONG_TERM_2Y`). A witness described these as meaningless for baseball while looking
authoritative, and they are baked into archived snapshot content and therefore into snapshot
identity. They must **not** be carried forward as though they were real baseball thresholds.

### Sequencing
Removal and replacement are separate tickets. GMT-006 removes the signal contract and blocks
deployment. GMT-007 builds the confidence surface and is blocked on GB-001, so threshold research
never holds up D-001 compliance.

## D-015 - What the score and tier measure
Raised by GPT's independent review of the plan, 2026-07-27, as the conflict D-014 did not reach.

### The ruling
**The score measures how well a hitter matches the Product Owner's stated criteria. It does not
estimate a home-run outcome.**

The thresholds are the Product Owner's: pull percentage, ideal attack angle percentage, barrel
rate, pitcher vulnerability, park and weather environment. The score expresses degree of match
against those. Sorting your own filter is not a prediction, and ranking by "fits what I asked for"
is not ranking by "likely to happen".

### Consequences
- **The odds and probability surface is deleted.** The main dashboard specification previously
  called for "optional probability/odds context". That is removed. GreenMachine displays no odds,
  no probability, no implied likelihood, and no expected value, anywhere, ever.
- **Score and tier must never be described in outcome language.** Not "likely", "chance",
  "probability", "expected", "projected to", "due", or "best bet". A tier is a band of criteria
  match, not a confidence in an event.
- **The score is only as meaningful as the criteria.** This makes Q11-Q16 and GB-001 more
  important, not less: an unapproved threshold set produces a score that measures nothing.
- **Ranking is permitted** because it orders a filter the Product Owner defined. It is not
  permitted to be presented as an ordering by likelihood.

### Erosion vectors, named because GPT named them
A separate evidence-confidence label does not stop the application from communicating "top-scoring
hitter with strong evidence", which a reader will interpret as a recommendation. The following are
forbidden and must each carry a guard:

1. Filtering out low-confidence high scores, which turns confidence into a screen.
2. Promoting rows into a featured, highlighted, or "top picks" group.
3. Conditional badges keyed on score, confidence, or both.
4. UI grouping that separates strong from weak.
5. Secondary sorts or tie-breaks on confidence.
6. Composite values hidden behind aliases, dataframe operations, or computed columns.

Guards must target **behavior**, not vocabulary. A rename is not a fix.

### Open, deferred to the Product Owner
The screen names "Batters to Target" and "Pitchers to Target" use action language. Under this
ruling they mean "matches your criteria and is worth your research attention". Whether to rename
them is a Product Owner decision, recorded here as open rather than settled silently.

### What this does not change
D-001 stands unamended. GreenMachine remains an evaluation and research platform and must never
produce a wager, stake, pick, or automated betting recommendation.

## D-016 - Mechanical consistency check before review
Raised by GPT's second plan review, 2026-07-27.

Of that review's nine findings, **five were the same failure**: a decision changed in some files and
not others. Separately, two fixes reported as complete had silently reverted, because a batch edit
failed partway and the helper wrote nothing on failure. Both are absences of a mechanical check,
not reasoning errors, and neither should have consumed a reviewer's attention.

### Rule
`scripts/check_consistency.py` runs before any package goes to GPT, and its output is pasted into
the review package. A finding a script can catch must never reach a reviewer.

It currently verifies: decision IDs have no gaps or duplicates; every file asserting a decision
range names the current maximum; no controlling file or diagram lets deployment precede GMT-006;
no odds or probability surface survives anywhere; the builder prompt's criterion count and
authorised operations match the active ticket; and no guide still describes superseded sequencing.

### Second rule
An edit is verified by **re-reading the file**, never by trusting a helper's return value. A tool
reporting success is not evidence the file changed.

### Why this is a decision and not a note
The pattern recurred five times in one round after recurring twice in the round before. Treating it
as carelessness and resolving to be careful had already failed. It needed a mechanism.

## D-017 - What GreenMachine is, stated precisely (narrows D-001)
Raised by GPT twice, in both plan reviews. Ruled by the Product Owner 2026-07-27.

### The problem D-001 could not survive
D-001 said GreenMachine must never produce a "pick". The product ranks hitters by barrel rate,
pull percentage, attack angle, pitcher vulnerability, and park environment - which are home-run
predictors - and the workflow then proceeds to external line shopping. Calling that output
"criteria match" rather than "likelihood" did not change its function. Two attempts to resolve the
conflict with definitions failed. D-001 as written forbade the product being built.

### The ruling
GreenMachine tells the Product Owner **which hitters hit which criteria, and which thresholds they
passed.** It ranks on that basis. That is a tally of stated rules, not a forecast.

### Forbidden, absolutely
- Odds, from any source, user-supplied or provider-supplied.
- Probabilities, implied likelihood, percentage chance, or expected value of any outcome.
- Stakes, bet sizing, bankroll guidance, or unit recommendations.
- Wagering recommendations of any kind.
- Automated selection: the system never picks players for the Product Owner and never produces a
  "today's plays" list. **Amended by D-019:** filtering and screening ARE permitted - they are the
  Product Owner's workflow - provided every exclusion is visible, explained, reversible, and traces
  to an approved threshold. What remains forbidden is a shortlist presented as what to act on with
  the excluded population hidden or unreachable.
- Outcome language applied to a hitter or a score: "likely", "chance", "probability", "expected",
  "projected to", "due", "best bet".

### Permitted
- Ranking hitters by criteria met and thresholds passed.
- Showing the count: met 4 of 5, passed these thresholds, failed these.
- Score and tier as an expression of that tally.
- Screens named for the Product Owner's own workflow language.

### The legibility requirement - the load-bearing part
The ranking must be **fully explainable as which criteria were hit and which thresholds were
passed.** Every position in the ordering traces back to that, and the reasoning is visible in the
product, not just in the code.

No opaque weighting, learned coefficient, fitted model, or hidden transform may influence the
ordering. If a hitter ranks above another and the interface cannot say which criteria and
thresholds produced the difference, the ordering has become a prediction and this decision is
violated.

This is what makes the boundary hold. A tally that shows its work is a screener. A number that
cannot explain itself is a forecast wearing a screener's clothes - and no vocabulary fixes that.

The transplanted engine already serves this: its ordered audit derivation makes every awarded and
withheld point explain itself, with observed value, bucket bounds, points, reason, and rule
reference (GMT-004).

### Status of D-001
**Narrowed, not revoked.** GreenMachine remains an evaluation and research platform and still
produces no wager, stake, or automated betting recommendation. D-017 states precisely what that
means, so the rule can be enforced rather than argued about.

### Status of D-015
Stands, and is strengthened. The score measures degree of match against stated criteria, and
D-017 adds that the match must be legible as a tally. D-015's six erosion vectors and their
required negative tests are unchanged.

## D-018 - Two review regimes
Raised by GPT's third plan review, 2026-07-27.

### The problem
The review process required a PR number, a CI run, and a green build. GMN-000A has no CI - it does
not exist until GMN-000D - and deletes its only branch by design. The first three tickets therefore
could not produce a valid review package. The process assumed preconditions its own first tickets
create.

### The ruling
Two regimes, distinguished by whether CI exists.

**Regime A - pre-CI (GMN-000A through GMN-000D).**
Evidence is pasted command output and observable repository state: `git` output, `gh` API output
for settings, local test runs. No PR number, no CI run, no persistent branch is required, because
none reliably exists.

GPT still reviews and still approves. Independence is preserved; only the evidence format changes.
A reviewer can perfectly well assess "here is `git push origin main` and here is the remote's
rejection." What it cannot assess is a CI run that does not exist.

**Regime B - post-CI (GMN-000D onward).**
The full package: base and head SHAs, PR, diff, CI result, verdict bound to the head SHA, SHA
re-verified before merge.

The regime switches the moment GMN-000D is approved. That ticket is the last reviewed under
Regime A and the first to produce the CI its successors depend on.

### Deployment verification is inherently post-merge
GMN-000H cannot prove a redeploy without something having been merged to `staging` first, and
cannot prove a rollback without a deployment to roll back. Requiring approval before merge and
merge before evidence is a deadlock.

Resolution: **GMN-000H is reviewed in two submissions.**
1. Configuration, documentation, and the deployment itself - reviewed before merge, as normal.
2. Redeploy and rollback evidence - produced after merge to `staging`, reviewed before any
   production merge.

A merge to `staging` may precede GPT approval **only** for deployment-verification evidence, and
only into `staging`. A production merge never may.

### No squash merges on reviewed branches
An approval names a head SHA. A squash merge creates a new commit, so the merged SHA is not the
reviewed SHA and the binding is broken. Reviewed branches merge with a merge commit, and the
reviewed SHA must be an ancestor of it - which is mechanically checkable.

## D-019 - Filtering is permitted when visible and reversible (amends D-017)
D-017 said the system must never reduce its output to a shortlist. That wording was too broad: it
banned filtering, which is what a screener does and what the Product Owner's pitcher-first workflow
requires at every step.

### The real distinction
A screener **shows you what it dropped and why.** A picks service hides it.

**Permitted:** screening games by pitcher vulnerability and environment, excluding hitters below
thresholds, and the 3-of-5 gate - the Product Owner's stated workflow.

**Required of every exclusion:**
1. It is **visible** - the interface shows that hitters or games were excluded, and how many.
2. It is **explained** - each exclusion states which criterion or threshold it failed, with the
   observed value.
3. It is **reversible** - the full population is always reachable in one action. No screen may
   present a reduced set as the only set.
4. It is **the Product Owner's rule**, not the system's. Every filter traces to an approved
   threshold, never to a heuristic the system chose.

**Still forbidden:** a shortlist presented as what to act on, with the excluded population hidden,
unexplained, or unreachable. That is the thing D-017 meant to ban, and this states it precisely.

## D-020 - GPT's veto is overridable, deliberately
GPT's fourth plan review pointed out that the stated veto was in fact advisory: a rejection blocked
production only until the Product Owner overruled it in writing. That was accurate, and it was a
drift from what the Product Owner originally chose, made by Claude Lead without asking.

Put back to the Product Owner and ruled 2026-07-27: **overridable, as written.** This is now a
deliberate choice rather than an accident.

### The rule
A GPT rejection blocks the production merge until either the blocker is fixed, or the Product Owner
overrules it. An overrule requires:
1. a written entry appended to `DECISIONS.md`;
2. the specific blocker being overruled, quoted;
3. the reason;
4. the date and the release it applies to.

An overrule is never silent, never verbal, and never retroactive.

### What this means honestly
This is an advisory rejection with an audit trail, not an absolute veto. The Product Owner can ship
over a GPT objection. The protection this provides is that doing so leaves a permanent record that
someone chose to, and why - which is what makes a later reader able to tell a considered override
from an oversight.

Claude Lead cannot override a rejection. Only the Product Owner can, and only in writing.

## D-021 - Everything after GMN-000A is unreviewed draft
Four independent plan reviews produced 38 findings, every one valid. None of them was about
GMN-000A. All of them concerned the plan for the fifteen tickets that follow.

The cause is structural: those tickets are predictions about a repository that does not exist, and
the only available test is a careful reader finding flaws. A careful reader keeps finding them,
because ~30,000 words of untested assertions always contain more. Two rounds produced fixes that
created new defects, one of them worse than the finding it resolved.

### The ruling
- **GMN-000A is approved to build.** It is the one ticket no review has faulted, and the reviewer
  explicitly endorsed its lighter evidence standard.
- **`tickets/BACKLOG.md` and `tickets/TRANSPLANT_BACKLOG.md` are UNREVIEWED DRAFT.** No builder
  starts from them. They record intent, not approved work.
- **After GMN-000A is merged, the remaining plan is rewritten against the real repository** and
  re-reviewed, much smaller. Criteria will then be checkable against something that exists rather
  than against another document.

### Known unresolved, carried forward for that rewrite
1. Revision binding and CI availability are separate concerns and must not be one regime: GMN-000B
   and GMN-000C produce PRs and SHAs, and GMN-000D produces CI runs as its own evidence.
2. The production checklist requires the staging head to equal the approved SHA while also
   requiring merge commits, which is impossible after the first merge. It must check ancestry.
3. GMT-004 still deadlocks: `make check` runs the suite, so an identically failing transplanted
   test fails the gate the ticket also requires to pass.
4. GMT-007 requires UI-level guards before any UI exists.
5. GMN-000I is absent from the sequence diagrams and assigned to a role barred from running it.
6. Toolchain and CI transplants are excluded from the independent provenance process that covers
   GMT tickets.
7. D-019's visible-and-reversible filtering rule is not reflected in the master context or the
   workflow specification.
8. GMT-006's tie-break criterion is satisfiable by writing a sentence.
9. The consistency script checks that GMN-000I exists but not that the sequence incorporates it.

These are recorded so the rewrite starts from them rather than rediscovering them.

## D-022 - The legacy source is a tag, not a commit hash
Discovered 2026-07-27 while tagging the legacy repository.

### What happened
The salvage review, the transplant scope, and six planning documents all named `518024d9` as the
canonical legacy commit. The Product Owner's working copy was **17 commits behind `origin/main`**.
The real head was `57cd833`, which includes the rev-17 closeout recording GM-040 and GM-040-HF1 as
APPROVED and FROZEN.

Every GMT ticket would have transplanted from a stale tree, including a version of GM-040 that had
not yet been approved. Nobody could have caught this from a document review: it was a fact about a
machine, invisible to every reviewer and to the lead.

### The rule
**The legacy source of truth is the tag `legacy-v0.2`, not a hash written into a document.**

A tag is a name the repository resolves; a hash copied into fifteen files is a claim that goes stale
silently and propagates by copy-paste. Where a specific hash must appear, it is quoted **from** the
tag at the time of use and stated as "`legacy-v0.2` = `<hash>`", never as a bare hash.

Any ticket transplanting from legacy resolves the tag itself and reports what it resolved to. If it
does not match what the ticket expected, it stops and reports rather than proceeding.

### Consequence for the salvage audit
The GMS-001 inventory and the transplant scope derived from it were based on stale code and must be
**re-derived against `legacy-v0.2`**. The audit's first action is to verify what the tag resolves to
and confirm the working copy is not behind.

### The general lesson
Four review rounds could not have found this, because it was not a contradiction between documents -
it was a mismatch between documents and the world. Reviewing a plan against itself has a ceiling,
and this is what sits above it.

## D-023 - The locked baseball decisions, recovered (supersedes D-008)
Found 2026-07-27 in `GreenMachine_Next_Launch_Pack_v2.0`, which the third witness said contained
rulings absent from every register. It did. **Grok's first baseball brief was already complete and
the Product Owner had already locked twelve decisions from it.** None had reached this register, and
D-008 contradicted one of them.

### Locked by the Product Owner
1. **Pitcher vulnerability sits OUTSIDE the hitter 3-of-5 count.**
2. **The 3-of-5 rule is a watchlist gate**, not a hard rejection.
3. General Barrel Rate and general Exit Velocity are **independent** Power Profile points.
4. General power is evaluated **before** any pitch-mix or handedness filter.
5. Pitch-mix power is a **second** comparison, using the pitcher's qualifying arsenal against the
   batter's relevant handedness.
6. Power Profile is **2 points general power, 1 point pitch-mix confirmation**.
7. Pitchers to Target must separate weakness versus LHB and RHB.
8. Pitch-usage thresholds apply **after** selecting the handedness split.
9. **Park and weather are modifiers outside the five counted hitter criteria.**
10. Season HR and Barrel Rate versus the specific pitcher are **tiebreaker/modifier evidence only**.
11. Put-away and highest-whiff identification use **full-season** pitcher data, preferably versus
    the batter's handedness.
12. Sonnet implements approved baseball rules; it does not decide them.

### The five criteria - which are not what D-008 said
1. General Barrel Rate
2. General Exit Velocity
3. Handedness-specific pitch-mix confirmation
4. Ideal Attack Angle percentage
5. Pull-power profile

D-008 listed Pull, IAA, Barrel Rate, vulnerable pitcher, and environment. Two of those are not
criteria at all (locked items 1 and 9), and two real criteria were missing entirely (Exit Velocity
and pitch-mix confirmation). Any work built on D-008 would have counted the wrong things.

### Grok's minimum sample sizes - and why they matter more than they look
| Metric | Minimum | Preferred |
|---|---|---|
| Recent Barrel Rate / EV | 15 BBE | 25 BBE |
| Ideal Attack Angle % | 25 tracked swings | 40 |
| Pull Air % | 15 air balls (FB+LD) | 25 |
| Pitch-type Barrel / EV | 10 BBE on the mix | 20 |
| Pitcher vulnerability (side) | 40 BBE or 80 BF | 60 BBE |
| Highest-whiff / put-away | 40 pitches of type | 60 |
| Batter-vs-pitcher | 8 BBE / 15 PA | 20 PA |

**Three different sample-minimum sets now exist and they disagree by an order of magnitude.**
Legacy used 2 and 13 (validation placeholders). The Savant spike used 5 and 50 (explicitly
experimental). Grok says 15 minimum, 25 preferred, for recent barrel rate.

The spike's real data settles which matters: its three test hitters had **7, 4, and 10** batted-ball
events in a seven-day window. Under Grok's minimum of 15, **none of them would have had sufficient
recent data at all.** That is not a threshold detail - it is a finding about whether a 7-day window
can carry a criterion, and it needs a Product Owner ruling before RECENT_7D scoring is built.

### Pull Air % and the opposite-field exception - both defined
**Pull Air %:** numerator is pulled fly balls plus line drives; denominator is all fly balls and
line drives with valid coordinates and row-level stand; geometry `pull_side_x >= tan(15 deg) * y` in
exact Decimal; provisional threshold >= 40%; RECENT_7D primary with season as a stability check.
Overall Pull % is audit-only context, never the primary gate.

**Extreme opposite-field exception** - all five must hold: opposite-field Barrel Rate >= 12% (or
clearly elevated opposite-field HR rate) on >= 20 opposite-field BBE; opposite-field EV at least
equal to overall EV; documented history of opposite-field home runs; park dimensions rewarding
opposite-field power or a clear handedness-park match; >= 40 total BBE in the window. Rare by
design, manually flagged, and it does **not** auto-award the Pull criterion.

### Batter-versus-pitcher
No additional scoring point. A positive / neutral / negative / insufficient-sample flag, used as a
**deterministic sort tiebreaker after total score**. This also answers GMT-006's tie-break question
(criterion 6h): ties resolve on BvP flag, then on stable identifier, and never on confidence (D-014).

### Missing versus insufficient - already ruled
- **Missing:** provider returned nothing. Explicit `SOURCE_UNAVAILABLE` / `MISSING`, no numeric value.
- **Insufficient:** data present, below minimum. Numeric value shown with an `INSUFFICIENT` flag;
  criterion not awarded.
- **Poor:** sample sufficient, value below threshold. Criterion fails, value still displayed.

This is the evidence-confidence surface D-014 and GMT-007 describe, already specified.

### Still genuinely open
Exact strong/neutral/poor pitch-mix thresholds; whether pitch-mix confirmation requires both Barrel
and EV to agree; Last-7-Days fallback hierarchy; switch-hitter side assignment; the exact
pitcher-vulnerability definition; environment modifier strength; and whether BvP may apply a small
modifier or only reorder within a tier.

### Process consequence
**GB-001 as scoped is cancelled.** Grok's own handoff says "Do not rerun the full first brief."
Re-running it would have re-derived twelve locked decisions and probably contradicted some. The
replacement is a narrow follow-up on the list above.

## D-024 - License and staging host
Both carried forward from legacy rather than chosen fresh, 2026-07-27.

### License: Proprietary
The legacy `pyproject.toml` already declares `license = { text = "Proprietary" }` and the
`Private :: Do Not Upload` classifier. The repository is private and personal, and it is built on
provider data whose licensing terms remain an open question (legacy Q7). Carrying that declaration
forward is continuity; adopting an open-source license would be the change requiring justification.

GMN-000A may commit a real `LICENSE` file stating proprietary, all rights reserved, rather than the
placeholder.

### Staging host: Streamlit Community Cloud
Legacy deployed there, and the transplanted `requirements.txt` is written specifically for it -
including the `-e .` self-install line that exists because of a Community Cloud failure mode
(`PackageNotFoundError` at import). Choosing another host means rewriting that file and re-solving a
problem already solved.

Free, reversible, and GMN-000H is far enough out to revisit. Note that GMN-000I must resolve the
`requirements.txt` ruling conflict before deployment either way.

## D-025 - GB-002 baseball rulings
Grok's narrow follow-up, 2026-07-27. It reopened no locked decision.

### The finding that shapes the product
**15 batted-ball events stands as the minimum for awarding recent Barrel Rate or Exit Velocity**,
25 preferred. Real seven-day samples came in at 7, 4, and 10. Grok's conclusion is that the
threshold is right and the samples are genuinely thin: *"That is not a defect; it is the data
speaking."* Lowering to 8-10 for screening was considered and rejected - "a softer gate that awards
points on samples no serious analyst would trust."

**Consequence:** on an ordinary night, recent power criteria will frequently read INSUFFICIENT
rather than awarded. The product shows the observed rate, the exact BBE count, and an explicit
INSUFFICIENT badge, and withholds the criterion point.

### Window fallback hierarchy
1. RECENT_7D - always displayed; flagged INSUFFICIENT below 15 BBE.
2. RECENT_14D - used when the 7-day sample is insufficient.
3. Season-to-date - stability and context only, never presented as "recent form".

**The interface must state which window supplied the value that was actually scored.** Silently
substituting season for seven days and calling it recent form is forbidden.

### Tiny samples
A rate on a sample below its floor is displayed with its sample size and an INSUFFICIENT flag, and
its criterion is withheld. Suppressing the number is worse (it hides the thin sample); treating it
as evidence is also worse. A 0.0% pull-air rate on one air ball is "noise wearing a number"; 0.0%
barrel on 10 BBE is "weak information, still noise."

### Pitch-mix confirmation
- Requires **both** metrics at least neutral, **or** one strong with the other not poor. A single
  extreme metric never carries the point - elite EV with zero barrels is usually a small-sample
  artifact or a different contact profile.
- Minimum 10 BBE on the qualifying mix, 15-20 preferred. Handedness-split, pitch-type slices are
  thinner than overall, so insufficiency will be common here too.
- Exact strong/neutral/poor bands: **insufficient evidence.** Provisional working values only -
  strong is Barrel >= 12% and EV at least 2-3 mph above league average, or top-quartile against the
  pitcher's own arsenal. These are placeholders pending a season of side-specific data, and must not
  be treated as approved.

### Pitcher vulnerability - a measurable definition
On a sufficient sample (>= 40 BBE or >= 80 batters faced versus that side), a pitcher is vulnerable
when barrel rate allowed is >= roughly 10-12%, **or** hard-hit rate and exit velocity allowed are
clearly elevated relative to league or to the pitcher's own opposite-side numbers - **and** the
pitches being punished are the highest-usage ones.

Exact numbers await calibration; the structure is usable now. Vulnerability stays a gate outside the
five counted criteria (locked decision 1).

### Switch hitters
Expected batting side is resolved against the announced starter's handedness. If the starter changes
after capture, re-resolve and re-flag the snapshot as using the updated side. With no known starter,
use the hitter's majority side this season and annotate "side assumed."

**Never average both sides into one number for a criterion.**

### Environment
Park and weather may re-order within a tier or surface a visible boost/drag annotation. They may
**never** award or remove a counted criterion point, and **never** rescue a hitter who fails the
3-of-5 watchlist gate. This closes an ambiguity D-023 left open.

### Batter-versus-pitcher - reorder only, confirmed
A deterministic sort key after total score, then stable identifier. No point adjustment, no score
modifier. The score stays a pure tally of the five criteria.

**This settles the tie-break question GMT-006 criterion 6h left open.** Ordering is: total score,
then BvP flag, then stable identifier. Never confidence (D-014), never anything evaluative that
isn't already a counted criterion.

### Still awaiting calibration data, not judgment
- Final numeric bands for pitch-mix strong/neutral/poor.
- Exact numeric thresholds for pitcher vulnerability.

Both need a season of side-specific samples. Grok declined to invent numbers for either, which is
the correct answer to give.

## D-026 - GB-002 confirmed by the Product Owner
Reviewed item by item, 2026-07-27. Grok's brief is accepted in full.

### Sample minimums - CONFIRMED as Grok specified
| Metric | Minimum | Preferred |
|---|---|---|
| Recent general Barrel Rate / Exit Velocity | **15 BBE** | 25 |
| Pitch-type Barrel / EV on the qualifying mix | **10 BBE** | 15-20 |

**Considered and withdrawn:** lowering the general floor to 10 BBE for screening. It was briefly
chosen, then reversed on discovering the consequence - Grok set general at 15 and pitch-type at 10
*deliberately*, because handedness-split pitch-type slices are thinner than overall samples. A
general floor of 10 would have given the thinner slice the same bar as the broader one, inverting
the relationship. The register records the reversal rather than hiding it.

Also weighed: on the three real captured hitters (7, 4, and 10 BBE), a floor of 10 still produced
INSUFFICIENT for two of three. Lowering the bar would not have cleared the badges, only moved the
line past one hitter.

### Frequent INSUFFICIENT is accepted product behaviour
On an ordinary night, recent power criteria will commonly read INSUFFICIENT rather than awarded.
The rate displays with its exact BBE count and an INSUFFICIENT badge, and the criterion point is
withheld. This is the seven-day window reporting honestly on itself.

### Confirmed without change
1. **Window fallback:** RECENT_7D, then RECENT_14D when the 7-day sample is short, then
   season-to-date as stability context only. **The interface must state which window supplied the
   value that was scored.** Silently substituting season and calling it recent form is forbidden.
2. **Pitch-mix confirmation requires BOTH** Barrel Rate and Exit Velocity at least neutral, or one
   strong with the other not poor. A single extreme metric never carries the point.
3. **Switch hitters:** resolve to the announced starter's handedness; re-resolve and re-flag if the
   starter changes after capture; with no known starter use the majority side this season and
   annotate "side assumed". **Never average both sides into one number for a criterion.**
4. **Environment annotates or re-orders only.** Park and weather never award or remove a counted
   criterion point and never rescue a hitter who failed the 3-of-5 watchlist gate. A modifier that
   could rescue a failure would be a scoring input wearing a modifier's label.
5. **Batter-versus-pitcher is reorder-only.** A deterministic sort key after total score, then
   stable identifier. No point adjustment, no score modifier.

### Ordering, now fully specified
Total score, then BvP flag, then stable identifier. Never confidence (D-014), never anything
evaluative that is not already a counted criterion (D-017). **This closes GMT-006 criterion 6h.**

### Deferred pending real data - not open decisions
- Exact strong / neutral / poor numeric bands for pitch-mix confirmation.
- Exact numeric thresholds inside the pitcher-vulnerability rule.

Grok declined to invent either without a season of side-specific samples. That refusal was correct
and is not treated as an unanswered question. The structural definitions from D-025 are usable now;
only the numbers wait.

## D-027 - GMN-000A complete; infrastructure facts
Recorded 2026-07-27 from the builder's final report.

### Completion
All thirteen acceptance criteria demonstrated with pasted output. All six destructive operations
rejected by the remote: direct push, force push (from proven-divergent refs - `[ahead 1, behind 1]`,
left-right count `1 1`, not a vacuous "Everything up-to-date"), and deletion, against both `main`
and `staging`. A `feature/*` false-positive check confirmed protection does not overreach. Initial
commit `3d5e4fd` untouched.

### Infrastructure facts no document previously captured
- **The GitHub account is on GitHub Pro**, purchased by the Product Owner 2026-07-27 to unlock
  branch protection on the private repository. Free-plan private repos cannot protect branches;
  the builder correctly stopped rather than running vacuous tests against unprotected branches.
- **Protection configuration:** PRs required with **0 approving reviews**, `enforce_admins` on,
  force pushes and deletions disallowed, identical on both branches. The 0-approvals setting is
  the builder's judgment call, endorsed by Claude Lead: GitHub forbids approving your own PR, so
  requiring 1 approval would deadlock every solo merge. GPT confirms or overrules at review.
- **`main` deletion rejection honesty note:** GitHub's default-branch guard fires before the
  protection rule is consulted, so `main`'s rejection does not exercise the rule itself. The rule
  is proven by `staging`'s rejection, and both branches carry identical config. Preserved as the
  builder stated it.
- Protection evidence is **point-in-time** (settings are configuration, not content). Re-capture
  before any production merge remains on the merge checklist.

## D-028 - Post-review corrections and reaffirmations
From GPT's fifth review and the GMS-001 salvage audit, 2026-07-27.

### (a) Regime A now requires revision binding - GPT was right
Lack of CI never justified omitting revision identity. Regime A submissions must state the branch
name, the head commit SHA (`git rev-parse HEAD` pasted), and attach the full diff - all available
from bare Git with no PR and no CI. Only the CI-run and PR-merge-gate fields are waived before
GMN-000D. The verdict binds to the stated SHA in both regimes. This closes D-021 carried-forward
defect 1.

### (b) The veto ruling stands - GPT's objection preserved, not adopted
GPT rejected D-020 on the ground that "a rejection that can be overruled is not a veto." True as a
matter of language - and D-020 says so itself, in those words. But the reviewer's charter comes
from the Product Owner, and the Product Owner ruled twice, deliberately, with the tradeoff stated
plainly. A reviewer cannot block the governance decision that defines the reviewer's own authority;
that would make the reviewer sovereign over its charter. The objection is recorded here
permanently. The ruling stands.

### (c) PROJECT_STATE.md rewritten clean - GPT was right
The file had accreted five rounds of corrections and contradicted itself: it claimed all findings
addressed AND nine unresolved; salvage complete AND needing re-derivation. Rewritten to current
state only. Historical narrative lives in this register, where it belongs.

### (d) Tag resolution procedure corrected - the salvage audit was right
`legacy-v0.2` is an **annotated** tag: bare `git rev-parse legacy-v0.2` returns the tag object
(`6c6ba745...`), not the commit. A naive equality check against `57cd833` false-alarms. The
correct procedure is `git rev-parse legacy-v0.2^{commit}`. Amends the D-022 procedure.

## D-029 - Salvage audit findings that change the draft plan
GMS-001 completed 2026-07-27 against the frozen tag. **778 tracked files, every one categorized:
PORT 141, REFERENCE 104, EXTRACT 3, REJECT 530**, with a full per-file reject log. Secret scan
clean. The earlier 1,183 figure was a filesystem count of the stale checkout including `.git`.

### The betting-signal blocker is already resolved at the tag
At `legacy-v0.2`, `grade_result.py` carries no `signal`/`signal_reason` fields - GM-041 removed
them. MODEL_SPEC section 16 records the signal engine as removed history, and `test_engine.py`
lines 384-391 actively ban the vocabulary. The witness reconciliation's "live right now" claim
described the stale checkout. **GMT-006 as drafted is largely moot.** What survives of it - the
D-015 odds/probability removals in our planning documents, and the D-017 legibility guards - moves
into the plan rewrite.

### The GMT-004 deadlock contingency is not needed
The two suspect engine tests pass, verified by name. Full suite at the tag: **3,800 passed, 6
platform-conditional skips, 0 failed.** CI on the tag push is green.

### The transplant scope was missing verified dependencies
Exactly the failure mode GPT predicted in its first review - a ticket transplanting a module that
imports something no ticket covers - now confirmed with specifics:
- **`evaluation/` (3 files: snapshot identity + canonical serialization) is imported by
  `tests/golden/runner.py` and `tests/unit/scoring/test_engine.py`.** GMT-004 and GMT-005 could
  not have completed. Its exclusion was wrong.
- Also missing: `tests/conftest.py` + `tests/README.md`, `tests/network_guard/`,
  `scripts/update_goldens.py`, the test fixture trees + synthetic engine YAML, and the entire
  `tests/property/` determinism suite, which appeared in no ticket.
- About 60 of 101 test modules sit outside the drafted scope; the at-risk coverage is catalogued
  in the audit's SCOPE_AUDIT Q4.

### The .gitattributes defect reproduced at the tag
A fresh clone with Windows-default `core.autocrlf=true` hashes a digest-pinned evidence CSV
differently from its committed blob. Real, reproduced - and already prevented in the new
repository by GMN-000A's authored `.gitattributes`.

### Consequence
The plan rewrite (D-021) now has its evidence base: a real protected repository, a complete
inventory at the frozen tag, passing tests, and closed research questions. The rewrite draws its
transplant scope from the audit's PORT/REFERENCE lists, not from the lead's fifteen-file sample.

## D-030 - The plan rewrite: four tickets, drawn from evidence
2026-07-27. This is the rewrite D-021 promised, now that its evidence base exists: a real
protected repository (D-027), a complete blob-sourced inventory at the frozen tag (D-029), a
passing suite (3,800/0 at the tag), and closed research questions.

### The dead draft is replaced
GMN-000B..I and GMT-001..007 are **retired as ticket definitions** - never built, four times
rejected, and superseded by findings (signal already removed; suspect tests pass; scope misses
confirmed). Their files remain as archive. The new series is **GMR-001..004**
(`tickets/REBUILD_PLAN.md`), sized so GPT can review the whole plan in one pass.

- **GMR-001 - Foundation:** context system + toolchain transplant + package skeleton. Regime A
  with full revision binding (D-028a).
- **GMR-002 - CI:** transplant the legacy workflow; prove red and green. Last Regime A ticket.
- **GMR-003 - Core transplant:** the audit's verified PORT surface in one ticket, byte-identical,
  blob-sourced provenance, suite green in CI with pass/skip pattern matching the tag. One ticket
  rather than five because the audit proved the surface is dependency-interlocked: the five-way
  split could not complete (`evaluation/` needed by three of them, `conftest.py` by all). A single
  mechanical review - hash table + suite equivalence - is more checkable than five partial states
  in which the suite cannot run.
- **GMR-004 - Shell and staging deploy:** minimal Streamlit page (name, environment, version,
  commit), requirements finalized, Community Cloud staging, two-submission review (D-018).

### Requirements ruling folded in (retires GMN-000I)
D-024 chose Streamlit Community Cloud; the `-e .` self-install line exists because Community Cloud
fails without it (GM-040-HF1, `PackageNotFoundError`). Keeping `-e .` is therefore a technical
consequence of D-024, not an open product decision. **The GM-030-r2 four-bounded-specs ruling is
superseded.** GMR-004 updates the contract test to match and records the supersession.

### Rulings on the audit's open questions
- **OQ-1:** the draft tickets did not name the missing files; the misses were real. Moot - GMR-003
  includes all six.
- **OQ-2 (synthetic YAML):** confirmed - it transplants as a **test fixture, never configuration**,
  and GMR-003 requires its header to keep stating its numbers are deliberately wrong.
- **OQ-3 (ingestion):** deferred to feature-phase planning. The audit's evidence (passes keep
  tests 1-4; encodes every witness-listed provider behavior) makes transplant the leading option,
  but no ticket consumes it yet and the protocol quarantines salvage until one does.
- **OQ-4 (SampleStatus in fixtures):** acceptable with a required marker - GMR-003 adds a comment
  in the fixture trees stating the baked statuses are validation artifacts, never baseball
  judgments.
- **OQ-5 (excluded-layer guards):** stay REFERENCE. An inert guard violates D-013 rule 4; they
  move with their layers if their layers ever arrive.
- **OQ-6 (retrospective capture):** recorded in the deferred register; first gap to close if
  ingestion promotes.
- **OQ-7 (evidence bundles):** agreed - they stay in the frozen legacy repository; any future
  ticket wanting one names it specifically and copies with blob-sourced hashes.
- **OQ-8 (stale numbers):** consistency checker extended to flag 1,183 / 139 / 44 / 3,424-class
  claims outside historical context.
- **OQ-9 (annotated tag):** already D-028d; every GMR criterion uses the `^{commit}` form.

### The deferred register - nothing vanishes silently
Deferred beyond GMR-004, to be planned with the feature phase:
1. Local safety hooks (server-side protection now proven; hooks are defense-in-depth).
2. The six Claude Code skills.
3. Deterministic context-pack generation (hand-maintained pack until then).
4. The evidence-confidence surface (D-014/GMT-007) - needs real screens to guard.
5. D-017 legibility guards at screen level - same reason.
6. The ingestion transplant-vs-rebuild decision (OQ-3), and retrospective capture (OQ-6).
7. Fixture-vs-live reconciliation policy (audit E-2: a synthetic fixture can encode the same wrong
   assumption as the parser it tests - proposed as a standing decision when ingestion returns).

### Provenance applies to every transplant
The review template's source-artifact requirement (source files or archive + blob-sourced hashes +
diff against source) applies to **any ticket transplanting legacy files** - GMR-001, GMR-002, and
GMR-003 alike - not only the former GMT series. Closes D-021 carried-forward defect 6. Hashes are
computed from git blobs, never from a Windows working tree (the audit reproduced why).

### Production checklist corrected
"Staging head still equals the approved SHA" was unsatisfiable alongside required merge commits
(GPT round 4). The checklist now verifies **ancestry**: every approved head SHA is an ancestor of
the staging head, and the `main...staging` diff contains only reviewed changes. Closes D-021
carried-forward defect 2.

## D-031 - Plan v2: the nine fixes
GPT's review of REBUILD_PLAN v1 returned nine findings. All accepted; v2 incorporates all nine.
It also confirmed the two structural calls: the four-ticket shape ("materially better") and the
one-ticket transplant ("defensible; splitting would recreate the failures the audit demonstrated").

1. **Ticket lifecycle is now scope of every ticket:** the ticket text freezes in its first commit
   (making criteria mutation mechanically visible in the freeze-to-head diff of `ACTIVE.md`);
   closeout updates the record, project state, context pack, and stages the next ticket; the
   repository-adapted `scripts/check_consistency.py` is a GMR-001 deliverable with a
   context-pack freshness gate, and a clean run is pasted into every review package.
2. **No merge before approval:** CI red/green demonstrations run on throwaway demonstration PRs
   that are closed unmerged and their branches deleted. What a criterion demonstrates is merge
   *state*, never a merge. Scratch commits never enter `staging` history.
3. **The transplant universe is `docs/PORT_MANIFEST.md`** - all 141 audited PORT files with blob
   hashes, extracted verbatim from the salvage inventory and committed in GMR-001, frozen before
   GMR-003 exists in the repository. GMR-003's provenance must cover exactly its rows; a script
   diff against the manifest is pasted. The comparison universe can no longer be defined by the
   transplant itself.
4. **Toolchain files are exercised, not just installed:** `make check`, `pre-commit run
   --all-files`, and a `requirements.txt` install in a second fresh venv are GMR-001 criteria.
5. **All four CI gates get negative tests**, including the formatting gate.
6. **Non-falsifiable language removed:** deviations are enumerated in advance and otherwise
   zero - an unenumerated deviation stops the ticket; suite equivalence is full node-ID list
   equality with an empty diff, not counts; all nine architecture guards are demonstrated live,
   an undemonstrated guard being presumed inert.
7. **Commit resolution is specified:** GM_COMMIT env var, then git (detached HEAD is valid and
   must display its SHA), then `unknown`. The no-metadata negative test is a directory copy
   without `.git` - not detached HEAD, which was the wrong failure condition.
8. **Rollback is objective:** a revert PR whose result is shown by tree-hash equality with the
   prior commit, the new revert SHA displayed, and the marker gone.
9. **The base gate is explicit:** GMR-001 does not start until GMN-000A holds an APPROVED verdict
   naming its SHA. Plan approval does not cure an unapproved base.

The GMN-000A supplement flow remains in flight; its INSUFFICIENT EVIDENCE verdict stands until
GPT reviews the supplement and issues a verdict naming the SHA.

## D-032 - Plan v3: the seven fixes
GPT's review of plan v2 returned seven findings; all accepted. It also confirmed the v2
corrections it had demanded (demonstration PRs, four-gate negative tests, node-ID equality,
objective rollback, the base gate) and re-endorsed the one-ticket transplant and the frozen
manifest as "the correct verification model."

1. **The lifecycle contradiction is resolved by moving, not preserving.** The mutation check is
   now: the completed-ticket record must be byte-identical to `ACTIVE.md` at the freeze commit,
   and `ACTIVE.md`'s freeze-to-head history must contain exactly one change - the closeout swap.
   v2's "unchanged at head" demanded a file be simultaneously unchanged and replaced. After the
   last ticket, `ACTIVE.md` holds a sentinel: NO ACTIVE TICKET.
2. **The manifest is partitioned by owner.** 141 rows: 135 to GMR-003 (zero deviations), 4 to
   GMR-001 (enumerated deviations), 1 to GMR-002 (`ci.yml`, zero deviations), 1 SUPERSEDED by
   GMN-000A's authored `.gitignore` - the legacy blob is deliberately not transplanted and the
   difference is a recorded ruling. GPT's hash recomputation proving the approved `.gitignore`
   differs from the legacy blob was correct and is now the documented intent. The skeleton's
   empty `__init__.py` files are replaced by the manifest's real ones by design.
3. **The OQ-4 marker is its own file** - `tests/fixtures/README_VALIDATION_ARTIFACTS.md` - so
   fixture bytes stay manifest-identical. GMR-003's scope is its manifest rows plus an enumerated
   list of new files; "nothing else" applies to transplanted content.
4. **GMR-004 gains an explicit closeout PR** after submission 2, amending the same-PR lifecycle
   rule for that ticket only. Rollback runs before closeout, so tree equality is never polluted
   by closeout files, and the closeout PR is itself reviewed.
5. **The freshness checker is negatively demonstrated in GMR-001:** wrong active ticket and wrong
   decision count each shown producing a nonzero exit with a specific message, in an uncommitted
   working tree. A checker that has only ever passed is not a guard.
6. **Eight guards, not nine.** `tests/architecture/` at the tag holds eight `test_*` modules plus
   the shared `static_analysis.py` helper; the helper is exercised through the eight, not
   independently demonstrated. The wrong count was Claude Lead's arithmetic error, repeated from
   an earlier correction.
7. **Commit resolution is git-first.** `GM_COMMIT` is a fallback only, displayed with an explicit
   `(env)` provenance marker; where it is the only route, updating it becomes a step of the
   deploy procedure itself and the redeploy test proves the procedure does so. The "never a
   stale value" claim is withdrawn in favor of a documented procedural ownership.

Additionally, GMR-001 now grounds the manifest against the repository itself: every row's hash is
re-verified against the tag's blobs in the legacy clone (`git cat-file`), converting the
manifest's provenance from document-trust to machine-verification.

## D-033 - Plan v4: the seven fixes
GPT's review of plan v3 returned seven findings; all accepted. It confirmed the v3 repairs
("resolves the seven Plan v2 findings substantially and correctly"), the manifest partition's
internal consistency, and - for the third consecutive review - the one-ticket core transplant.

1. **Every ticket is two PRs.** Implementation PR (freeze + work, no closeout) is approved first;
   a closeout PR then moves the frozen text to the completed record and appends an approval annex
   below a marker line: GPT's verdict as issued, the approved head SHA, the date. The repository's
   completion history thereby records the independent decision rather than the builder's
   self-assessment, and the record can be byte-checked above the marker while still carrying the
   verdict below it. Closeout PRs get a bounded five-point conformance review, not a re-review.
2. **Mutating a guardrail re-proves it.** GMR-002's protection change requires a full config diff
   against the GMN-000A-approved state - only permitted delta: the added status check - plus one
   live direct-push rejection per branch.
3. **The prohibited-language check is fixed in advance:** defined pattern list, defined file set
   (only files the ticket adds or modifies outside the byte-pinned manifest), each hit listed with
   disposition. `domain/outcome.py` and its tests are legitimate domain artifacts under D-017, and
   the builder no longer chooses the grep.
4. **Guard demonstrations must be red for the right reason:** the pasted failure must contain the
   failing node ID from the module under demonstration; a red caused only by ruff, mypy, or
   another suite does not count. Accepted scope stated openly: one firing per module, not per
   rule.
5. **Every resolution route is tested unconditionally:** all three environment labels including
   `production`; the `GM_COMMIT` env route with its `(env)` marker tested locally rather than
   conditionally on Community Cloud's behavior; and git-over-env precedence proven with both
   present.
6. **Requirements completion is evidenced:** full file pasted, every bound listed, the changed
   contract test named, the old contract shown failing against the new file, and the committed
   supersession quoted from the repository.
7. **The "workflow-only" claim is now accurate:** implementation PRs carry the work plus the
   freeze, nothing else, because closeout moved to its own PR (resolved by fix 1).

Process note: the v3 package reached GPT without files 01, 05, and 09 - three UNVERIFIABLE items
existed only because attachments were missing. Every future review message instructs GPT to open
its verdict by listing the files actually received, so an attachment miss is caught in the first
line rather than diagnosed from the findings.

## D-034 - Plan v5: the lifecycle machine is removed, and GMN-000A is approved
GPT's review of plan v4 returned eight findings, all in the freeze/annex lifecycle added across
v2-v4. It simultaneously verified the manifest against the full inventory (all 141 rows exact),
declared D-013 "adequately supported at the plan level", and stated the plan was "rejected for
lifecycle governance, not because the transplant scope is unsound".

### GMN-000A is APPROVED
Disclosed in that review: the supplement was reviewed and **GMN-000A holds APPROVED WITH NOTES
for SHA `3d5e4fde3d6065fad1078749c85eb61b96fde9de`**. The base gate is cleared. The full verdict
text is required for the GMN-000A completed record in GMR-001 (the Product Owner holds it in the
review thread).

### The diagnosis, stated honestly
Findings 1, 2, 3, 5, and 8 were all defects in machinery Claude Lead invented - the per-ticket
freeze commit, the byte-identical completed record, the approval annex. Each repair round added
apparatus, and the apparatus generated the next round's defects: staging a ticket made it
unfreezable (finding 1); freezing bound a ticket to itself but not to the approved plan
(finding 2); annexing a verdict required the verdict to exist before its own approval
(finding 5). v5 removes the machine instead of patching it.

### The v5 lifecycle
1. **The plan file is the freeze.** GMR-001 commits `tickets/REBUILD_PLAN.md` byte-identical to
   the GPT-approved version, and the repository checker embeds its sha256 - any edit turns the
   checker red. The executed ticket IS the approved ticket because both are the same hash-pinned
   bytes. `ACTIVE.md` is a two-line pointer with no freeze semantics. Plan changes ship only as a
   GPT-reviewed revised plan plus the checker's new hash, in a dedicated PR.
2. **Two review objects with distinct criteria:** implementation criteria (per ticket) and fixed
   closeout criteria (lifecycle). A ticket is COMPLETE when both verdicts exist. GPT's
   implementation approval no longer asserts criteria that cannot yet be met.
3. **Closeout has an exact permitted delta:** four files, templated changes, the
   prohibited-language check runs on the closeout diff, checker clean. The completed record
   quotes the implementation verdict and SHA as issued, with a link-back to the pinned plan
   section rather than a text copy.
4. **The regress is acknowledged, not hidden:** a repository cannot contain the approval of its
   own final commit. Closeout approvals live in the review thread like every PR approval; the
   repository records each ticket's implementation verdict. The prior claim was corrected rather
   than defended.
5. **Deviations now carry exact resulting values** (finding 7): `version = "0.3.0"`, ruff
   specifier exactly `>=0.6,<0.17`, `-e .` retained. A category is not a deviation; a result is.
6. **`PROJECT_STATE.md` accuracy at commit time is a GMR-001 criterion** (finding 6), and it now
   records the GMN-000A approval.

## D-035 - Plan v6: the seven fixes
GPT's review of plan v5 returned seven findings; all accepted. It endorsed the plan-hash mechanism
("ready in principle"), re-verified the manifest row-for-row a second time, and restated that the
rejection "is not based on the transplant decision."

1. **The retired vocabulary is scrubbed from the ticket sections** - "frozen first commit" in
   GMR-001, "ticket freeze" in GMR-002, lifecycle files in GMR-003's new-file list, "annex" in
   GMR-004 - and the kit checker now bans the retired instruction phrases from the plan outright.
   This was the propagation failure again, inside the file that is about to become hash-pinned;
   a stale instruction there would have been frozen into authority.
2. **The ruff ceiling excludes what it names:** exactly `>=0.6,<0.16`. v5's `<0.17` permitted
   0.16.x, the version the pin exists to exclude - a one-character logic error that survived one
   full review round.
3. **Closeout criteria now require the updates, not just permit them:** all four files changed;
   the pointer verified against the approved order table (001→002→003→004→sentinel); the
   templated state line present with the approved SHA and no stale line remaining; pack in
   agreement.
4. **GMR-004's requirements evidence moved from scope prose into submission-1 implementation
   criteria** - the enforceable boundary, per the lifecycle's own rule.
5. **Pointer order is mechanically enforced:** the repository checker derives the expected next
   ticket from `tickets/completed/` and fails unless `ACTIVE.md` names exactly it.
6. **PROJECT_STATE's stale "In flight" sequencing line corrected** - the file now states the
   GMN-000A review is closed, APPROVED WITH NOTES.
7. **"Verdict as issued" is defined:** the full verdict text verbatim in a fenced `VERDICT`
   block, and the closeout language check excludes fenced VERDICT blocks - a verdict may
   legitimately discuss the vocabulary it is evaluating.

## D-036 - Plan v7: version-proof binding; every checker rule proven falsifiable
GPT's sixth plan review (v6) returned seven findings; all accepted. The same review confirmed
the substance holds - hash match exact, manifest agreement 141/141 re-verified, the one-ticket
transplant and all v6 corrections upheld ("This rejection is not based on D-013 or the
transplant scope"). The rejection was confined to the freeze mechanism's edges. v7 is the
revision.

1. **(Critical) Plan binding is version-proof.** v6's GMR-001 criterion 1 bound the commit to a
   named superseded revision - there was no compliant implementation: committing it violated the
   approved-bytes rule, committing the approved bytes violated the criterion. The criterion now
   names **no version numeral**: the committed plan must be byte-identical to the bytes GPT's
   approval names by sha256; that hash is the checker's pinned value. The kit checker now bans
   "approved v<digit>" from the plan so the staleness class cannot re-enter.
2. **(Critical) Every checker rule has a negative demonstration.** Criterion 3c grows from two
   demonstrations to six - freshness (ticket), freshness (count), plan hash, pointer order
   (exercising the base case), banned phrase, manifest partition - each red for the right
   reason, then one final clean run. D-012 applied to the freeze mechanism itself: the plan
   hash is the only freeze this plan has, so its failure path is demonstrated, not trusted.
3. **(High) The pointer-order table has a base case.** The completed order table now begins at
   GMN-000A: GMN-000A → GMR-001 → GMR-002 → GMR-003 → GMR-004 → sentinel. Checker semantics
   exact: `tickets/completed/` must be a prefix of the table; `ACTIVE.md` names the first
   ticket after the prefix, or the sentinel; unknown files in `completed/` fail.
4. **(High) Review regime follows infrastructure state, not the ticket label.** Per-object
   table added to the lifecycle: GMR-001 both PRs and GMR-002 implementation are Regime A;
   GMR-002 closeout - which follows the CI-creating merge - and everything after are Regime B.
5. **(High) The GMN-000A completed record has criteria** (new 1b): verbatim fenced VERDICT
   block (label, every note, the point-in-time protection limitation), the reviewed SHA
   3d5e4fde…, the verdict date. The verbatim text ships in the build package; GPT is asked to
   re-emit its GMN-000A verdict in the v7 round so the record quotes it as issued.
6. **(High) Governance documents are bound clause-by-clause** (new 1c): required clauses
   enumerated for TEAM_ROLES, GPT_REVIEW_PACKAGE_TEMPLATE, PRODUCTION_MERGE_CHECKLIST, and
   CLAUDE.md, verified in the Regime A implementation diff. The documents are authored fresh in
   GMR-001 to satisfy exactly those clauses - no kit template is ported, so no stale template
   can compete with the pinned plan.
7. **(Medium) The banned-phrase list is the plan's own text.** The exact seven phrases sit in a
   fenced BANNED-PHRASES block inside the checker spec; fenced code blocks are excluded from
   the scan (the VERDICT-block precedent), so the list can name what it bans. The kit checker
   applies the same exclusion and verifies the plan's block equals its own list, so plan and
   checker cannot drift.

**Schedule ruling (Product Owner time pressure, 2026-07-28, recorded):** GMR-001 build
preparation proceeds **in parallel** with the v7 review. The builder may stage all work against
v7; the implementation PR is not submitted for review until a plan approval exists naming a
sha256, and if the approved bytes differ from v7 the plan-binding steps re-run against the
approved bytes. Merges remain approval-gated (D-018). Parallelism moves the waiting, not the
gates.

## D-037 - Mutable configuration is captured raw, before and after
GPT's GMR-002 approval carried a capture-method note: the pre-change branch-protection record
was a jq **projection**, not a raw API capture, so the comparison was not literal
raw-to-raw equality across every response field. It accepted the round on stated grounds -
same projection both sides, full raw post-change JSON supplied, omitted fields individually
disclosed and currently false, live direct-push re-tests - and ruled explicitly that this
"does not establish projected pre-change captures as the preferred future standard."

**The rule, from GMR-003 onward:** when a ticket changes any mutable configuration - branch
protection, deployment settings, repository settings - the builder retains the **full raw API
response before the change and after it**, and diffs raw against raw. A projection may
accompany the raw diff as a reading aid; it may not replace it. This binds GMR-004's
deployment configuration work and the production-merge protection re-capture in
`docs/PRODUCTION_MERGE_CHECKLIST.md`.

Why it is a decision and not a preference: mutable configuration is the one class of evidence
a commit SHA cannot bind. A projection is a claim about which fields matter, authored by the
same party whose change is under review - exactly the judgment a reviewer exists to make
independently.

## D-038 - Verdict-of-record certification, and the fence-width rule
Standing method, established after the GMN-000A defect and confirmed twice since. A completed
record's verdict block is never transcribed on trust:

1. Claude Lead produces a canonical verdict file from the relayed text and states its sha256.
2. GPT hashes that file and **certifies** the value as the binding, publicly reproducible
   reference - or returns exact byte differences for mechanical correction.
3. The builder inserts the certified bytes programmatically and proves
   `sha256(fenced block content) == certified value` from both the working tree and the
   committed blob.
4. GPT re-verifies the same arithmetic from the closeout diff alone.

Certified so far: GMN-000A `064fa760...`, GMR-001 `23109bb2...`, GMR-002 `d934523e...` - all
three certified on first submission, each verdict dated 2026-07-27. GPT confirmed the
four-backtick construction satisfies criterion (b) and that the criterion (f) language scan may
exclude it in the same manner as three-backtick verdict blocks.

**Fence width follows the content.** The GMR-002 verdict is the first containing fenced code
blocks of its own; a three-backtick `VERDICT` fence would be terminated early by them and the
record would be silently truncated - the failure would be invisible in rendered markdown and
would surface only as a hash mismatch. The record therefore uses a fence **wider than any
fence inside the verdict** (four backticks for GMR-002), and the extraction, verification and
language-scan-exclusion commands use the same width. Restated as a rule: **the fence must be
one backtick wider than the widest fence the verdict contains.**

The interface-rendering tokens GPT's emissions sometimes carry (citation markers, fenced-block
`id="..."` attributes) are normalized out and the normalization is disclosed in the
certification request; GPT's GMN-000A certification ruled such tokens immaterial to a verdict's
substance.

## D-039 - Plan v8: the GMR-003 verification defect, and its repair
GMR-003's builder stopped before committing anything and returned the ticket. The stop was
correct and the defect was Claude Lead's: **criterion 5 assumed a test's node IDs are a function
of its own source.** They are a function of the whole repository tree, and in one case of the
absolute checkout path. Nothing was xfailed, skipped or reordered to make the numbers come out -
the stop-and-return rule produced exactly the behavior it exists to produce, and the evidence
below is the builder's, measured before any commit.

**The three findings.**

1. **Node IDs are tree-dependent.** Four modules parametrize over files discovered at collection
   time (`sorted(root.rglob("*.py"))` and similar). Trees of different sizes produce different
   node counts; pytest's duplicate-id disambiguation renumbers ids even for shared files; and one
   static case in `test_versioning.py` renders a checkout-absolute path into its id, so that id
   cannot match across any two machines, ever. Measured: 2,885 tag nodes vs 2,620 new; 267
   tag-only, all inside those four modules; 2 new-only, same phenomenon in reverse.
2. **Two documents were miscategorized by the salvage audit.** Four transplanted tests read
   `docs/GLOSSARY.md` and `docs/adr/0008-golden-testing-strategy.md` and assert against their
   content. **A document a ported test asserts against is a dependency of that test, not
   reference material.** Confirmed empirically: with both present the affected modules go 4
   failed + 17 skipped to 37 passed, and the suite's skip set becomes byte-identical to the
   tag's; node-ID collection is unperturbed (the scans collect `*.py`). PORT_MANIFEST v3 adds
   them as rows 142-143, owner GMR-003; the partition becomes 137 + 4 + 1 + 1 = 143. Their blob
   hashes come from the D-029 inventory unchanged, so the recategorization adds no unverified
   bytes.
3. **Seven tests read files the rebuild does not have**, five of which it will never have
   (an evidence bundle under OQ-7, the never-port synthetic demo generator, the legacy release
   archiver, the legacy prototype document). They are transplanted byte-identical as content and
   deselected by an exact list fixed in the plan, each node carrying a disposition and an owning
   ticket. Two are owned by GMR-004, which must re-enable them and prove them green.

**What replaced criterion 5.** Test-surface equivalence is now proven **by module class**:
exact node-ID set equality for every tree-independent module (empty diff, no escape hatch), and
for the four enumerated environment-dependent modules, **function-inventory equality** plus a
**parameter-set derivation** showing the collected parameters equal the live tree computed
independently. Function inventories were measured equal across both trees - 1,191 entries,
sha256 `200bb976c671a0f7a6e5ffa31bdb3417ff8b83f444ac2366a3654f6bc5795f1f`, equal per module -
which is what makes the new shape both attainable and strong: it proves no test function was
lost, added or renamed, and that the parameter divergence is exactly "same tests, different
tree" rather than "different tests".

**Guards against the deselect becoming a hiding place.** A deselect that matches nothing is a
silent no-op, so the plan requires the `(7 deselected)` summary line as proof every entry
matched; a **tag-side control** applying the same seven deselects to the legacy tree, removing
exactly seven nodes and leaving it green, proves the list masks no real failure; and the skip
pattern must match the tag's exactly (4 platform skips both sides).

**GMR-003R.** The lifecycle requires a revised plan to be committed with the checker's new hash
in a dedicated PR but never stated that PR's criteria. They are now fixed in the plan itself and
are part of what the reviewer approves when it approves v8. §GMR-001's text is preserved
unchanged - it is the historical instruction under which a completed, approved ticket ran - and
GMR-003R states the supersession of its partition constants explicitly rather than editing
history.

## D-040 - Plan v9: the seven v8 blockers
GPT rejected plan v8 with seven findings; all accepted. It confirmed the repair direction -
module-class equivalence, the document recategorization, the 143-row arithmetic, the skeleton
deletion - and rejected the execution. Each fix below is grounded in a measurement the builder
produced, not in an argument.

1. **(Critical) The `pyproject.toml` deviation was invalid.** v8 said the file "gains exactly one
   block"; the repository already has a `[tool.pytest.ini_options]` table, so that reading
   produces duplicate TOML, and the alternative reading silently deletes `minversion`,
   `testpaths`, `-ra`, `--strict-markers`, `--strict-config` and the fixed Hypothesis seed. v9
   specifies the **complete resulting table**. The builder then found what the reviewer's
   reconstruction had missed: the table also contains a **five-line comment block** citing
   ADR-0008 for the seed. v9 reproduces it verbatim and requires a byte-for-byte pre-edit check
   (522 bytes) with stop-and-return on any difference. Two reviews and a measurement were needed
   to get one table right.
2. **(High) GMR-003R would have committed knowingly false state.** Confined to three files, it
   would have merged plan v9 while `PROJECT_STATE.md` and `CONTEXT_PACK.md` still asserted that
   v7 was authoritative and v8 pending. The permitted delta becomes **six files**, adding those
   two and `DECISIONS.md`. A plan-revision PR that commits false current state is not a smaller
   change; it is a defective one.
3. **(High) Dangling decision references.** v8 cited D-037..D-039 as its authority while
   forbidding them from entering the repository until after GMR-004. GMR-003R now commits
   `DECISIONS.md` through D-040, and a criterion greps the plan's citations against the register
   to prove none dangles. The decision-lag disclosed at the GMR-002 closeout is retired here.
4. **(High) The manifest rewrote GMR-001's history.** v3 claimed all rows were "committed and
   frozen in GMR-001" and verified `143/143`. GMR-001 committed 141 and its verdict said
   `141/141`. The provenance paragraph now states that plainly and attributes rows 142-144 to
   GMR-003R.
5. **(High) An architecture guard would have gone inert.** v8 deselected all three
   non-parametrized `test_deployment_contract.py` tests and let the builder *explain* the absence
   instead of demonstrating the guard. Explaining why a guard cannot fire is not a negative test.
   The fix follows the same principle as the glossary: `docs/STREAMLIT_PROTOTYPE.md` is a
   document a ported test asserts against, so it is a dependency. Ported as manifest row 144, the
   documentation test passes (content-only assertions, measured) and the module keeps **six live
   tests**; criterion 7 loses its exception clause. Measured note: the module has 8 test
   functions and only 3 ever failed, so it was never wholly inert - but the plan permitted it to
   be, which is the defect.
6. **(High) "The feature phase" is not an owner.** Five deselections had no bounded owner. **A
   new ticket, GMR-005 - Deselection retirement**, is added to the plan and the order table with
   fixed criteria: every remaining node must reach one of three terminal states - re-enabled,
   replaced by a rebuild-appropriate test, or removed with a written justification naming the
   ruling that makes it inapplicable - and the ticket cannot complete while any `--deselect`
   survives. "Still pending" is not a terminal state.
7. **(High) Criterion 5(d) was unsatisfiable for one module.** `test_versioning.py`'s divergent
   node is a **static** parametrization rendering the checkout-absolute path, not a file scan, so
   no `git ls-files` derivation exists for it. Class B splits: **B1** (three tree-scanning
   modules) keeps the derivation; **B2** (`test_versioning.py`) requires **normalized node-ID
   equality** - the checkout root **as rendered inside the node ID** replaced with `<REPO_ROOT>`.
   Rendering matters: pytest doubles Windows backslashes inside the ID, so a raw path replacement
   matches nothing. Measured: 70 nodes each side, normalized sha256
   `8a0941ab8112e18194cd79717f6ae7dc703067bdcb8d35f69044e1c12a6ba1df`, equal.

The deselection register drops from seven nodes to six, and every one now names a review object:
two to GMR-004, four to GMR-005.

## D-041 - Plan v10: seven propagation failures, and the checker that now catches them
GPT rejected plan v9 with seven findings; all accepted. It confirmed the substance - the complete
pytest table with its comment block, the 522-byte stop condition, D-001..D-040 with no dangling
citation, 144 path-unique rows partitioned 138/4/1/1, the STREAMLIT_PROTOTYPE recategorization,
the B1/B2 split and its rendered-path qualifier, rule 7, and GMR-005 as the right structural
owner. **Every one of the seven blockers was the same failure: GMR-005 was added to the plan
without sweeping the places ticket order and counts appear.** That is the propagation class
D-016's checker exists to catch, and it caught none of them because the checker had no rule about
the plan's internal consistency. It does now.

1. **(Critical) GMR-004's closeout still handed `ACTIVE.md` the sentinel** while the order table
   put GMR-005 after it - two instructions with no compliant implementation. Fixed to point at
   GMR-005.
2. **(High) GMR-004's deselect arithmetic said "the remaining five entries stay"** where six
   minus two is four. The resulting `pyproject.toml` was therefore not determinable from the
   ticket text - exactly the ambiguity the fixed-result rule exists to prevent. Fixed, and the
   complete resulting table is now pasted in §GMR-004 as it is in §GMR-003.
3. **(High) The pointer-order guard is changed by GMR-003R and was not demonstrated.** D-012
   applies to a mutated guard as much as a new one. GMR-003R's demonstrations go from two to
   four, adding "sentinel where GMR-005 is expected" and "GMR-005 where the sentinel is expected"
   - the first of which is precisely the demonstration that would have caught finding 1.
4. **(High) GMR-003R's delta left governance and sequencing stale.** `docs/TEAM_ROLES.md` was
   verified at GMR-001 as reproducing the regime table and would have stopped doing so the moment
   GMR-005 existed; `PROJECT_STATE.md` still said "Feature phase planned after GMR-004". The
   delta becomes **seven files**, and the state criterion now requires that no sequencing line
   survive which the new plan falsifies, proven by a pasted grep with a disposition per line.
5. **(High) The manifest still credited GMR-001 with a 144-row verification** in a later
   paragraph while the corrected provenance paragraph said 141. Verification is now stated by
   review object: GMR-001 verified 141/141; GMR-003R verifies rows 142-144 and the 144/144 total;
   GMR-003 re-verifies its own 138.
6. **(High) GMR-005 could have declared success by deleting live coverage** - dropping
   `test_deployment_contract.py` to retire two nodes would have taken its six live tests with it
   and left the suite green precisely because the coverage was gone. New criterion 2b requires
   before/after node inventories for every file touched, with only the retiring nodes permitted
   to disappear. New criterion 2c removes the "delete" option entirely for
   `test_requirements_txt_sits_beside_the_entrypoint`: only its evidence-bundle assertion is
   inapplicable, so it must be re-enabled or replaced with its applicable assertions preserved.
   The reviewer named that node; the plan names it back.
7. **(Medium) The GMR-003 narrative still carried v8's counts** - two documents where there are
   three, seven deselections where there are six, "approves v8" in a v9 document. Corrected.

**The mechanical fix, which matters more than any of the seven.** Reasoning failed to catch this
class twice running, so the kit checker gained a "Plan internal consistency" section: the order
table is parsed from the lifecycle text; **only the last ticket in it may hand `ACTIVE.md` the
sentinel**; every ticket in the table must have a section; the deselection register's size must
equal the first `(N deselected)` figure and the figures may only shrink; prose claiming a
remaining-entry count must match a stated figure; and **every partition statement in the plan
must equal the manifest's actual owner counts unless it is explicitly marked historical**. That
last rule fired immediately on this revision, catching two live statements of the superseded
141-row partition that I had left unmarked - a finding a reviewer would otherwise have returned.

## D-042 - Plan v11: two silent no-ops, and a checker described but not required
GPT rejected plan v10 with five findings; all accepted. Two are the same mechanical failure, and
it is the one this project has already been bitten by twice.

1. **(Critical) GMR-005's criteria 2b and 2c were absent from the plan bytes.** D-041 described
   them; the plan did not contain them. The cause: a scripted `str.replace` whose anchor did not
   match, which returns the unchanged text silently while the surrounding script prints
   "applied". I trusted the script's output instead of re-reading the file - **exactly what
   D-016's second rule forbids, in the register I wrote it in.** The consequence would have been
   real: v10 as pinned still permitted GMR-005 to delete `test_deployment_contract.py` entirely,
   taking six live tests with it, and the node the reviewer specifically protected was
   unprotected in the authority that governs the builder. A decision register is not executable;
   only the pinned plan is.
2. **(Medium) The same class produced a surviving reference to approving a superseded revision.**
   Another anchor that did not match, another silent no-op.
   **The fix is mechanical, not resolve:** every scripted edit now runs through a helper that
   asserts the anchor exists, asserts it is unique, and **re-reads the file afterward to verify
   the new text is present and the old text is gone**. An edit that cannot be verified is not an
   edit. The first run of the new helper immediately aborted on a bad anchor rather than
   reporting success - the failure mode that caused this finding, caught at its source.
3. **(Critical) The plan-internal-consistency checker was described in D-041 but never required
   by §GMR-003R.** This is the deeper version of the same error: the mechanism the plan named as
   its defence against the fourteen prior findings existed only in the kit script and in a
   decision, while the pinned ticket text required four demonstrations and never mentioned rules
   8-12. A builder could have satisfied every criterion and shipped a checker without them. Rules
   7-12 are now **specified in §GMR-003R with their semantics**, and criterion 6 requires **ten
   demonstrations**, including one proving rule 12's historical exemption is narrow rather than a
   hole - an exemption nobody demonstrates is an escape hatch.
4. **(High) GMR-003R's criterion 4 still said D-001..D-040** inside the very PR whose purpose
   includes eliminating stale governance references. Now D-001..D-042, and the kit checker gained
   a rule comparing every decision range asserted **inside the plan** against the register, with
   the same historical-marker exemption the partition rule uses.
5. **(Medium) The manifest still said "both"** where three documents are now recategorized.

**What this round is really about.** Three of the five findings are one failure - a claim about
the artifact that the artifact does not support - and the reviewer caught all three by reading
the bytes rather than the description. That is the entire argument for an independent reviewer
who is given the file and not the summary, and for a checker that reads the plan the way the
reviewer does.

## D-043 - Plan v12: a guard that checked one spelling, and a demonstration that could not exist
GPT rejected plan v11 with three findings; all accepted. Two are the same shape as D-042's and
one is new.

1. **(Critical) The plan's opening line asserted `D-031..D-040` while the register held D-042** -
   a stale range in the first sentence of the document whose currency the whole apparatus exists
   to protect. Worse, the kit rule I added in D-042 *to catch exactly this* matched only ranges
   beginning `D-001`, and this one begins `D-031`. **A guard that checks one spelling of a claim
   does not check the claim.** The rule now matches any `D-0AA..D-0BB`, and - the part that
   matters for the pinned authority - **rule 13 is specified in §GMR-003R** rather than living
   only in the kit script and a decision. That was v11's own finding 2 recurring one level down:
   describing a guard is not requiring it.
2. **(Critical) Criterion 6's demonstration (x) was internally unsatisfiable.** It sat inside
   "ten demonstrations, each red for the right reason, each with a nonzero exit" while itself
   requiring a **pass**, and the criterion also stated that editing the plan copy makes the
   plan-hash rule red - so no run could be simultaneously clean and red as written. Restructured:
   (x) becomes a real rule-13 failure demonstration, and the exemption controls move to a new
   **criterion 6b** whose pass condition is stated precisely - **the absence of the named rule
   from the failure list**, with the plan-hash red expected and disclosed - followed by one
   fully clean run at the end. The underlying instinct was right: an exemption nobody tests is
   an escape hatch. The expression was impossible.
3. **(High) `PROJECT_STATE.md` still said "§GMR-003R expanded to six files"** while the plan
   defined seven - a known-false claim inside one of the seven files the PR commits, in the
   artifact whose purpose is current-state accuracy. Criterion 5 now requires that neither the
   state file nor the pack misstate **this PR's own scope**, proven by a grep with a disposition
   per sentence.

**The pattern worth recording.** Across v10, v11 and v12 the same failure recurs at descending
levels: a claim about an artifact that the artifact does not support - first in the plan versus
the decision register, then in the register versus the checker, now in the checker's regex versus
the class it claims to cover. Each round the reviewer found it by reading the bytes rather than
the description. The lesson is not "be more careful"; it is that **every claim of the form "X is
enforced" must name the enforcing text and be demonstrated against it**, which is what criteria 6
and 6b now do for all seven repository rules.

## D-044 - Plan v13: the specification checked against the implementation
GPT rejected plan v12 with three findings; all accepted. It first verified the delivered checker
source independently - 23,478 bytes, 470 lines, sha256 `21b4694195cc83e6...`, syntax valid - and
then did the thing the previous four rounds could not: **compared the plan's rule specification
against the code that claims to enforce it.** Every finding came out of that comparison.

1. **(Critical) Rule 9 was implemented in one direction only.** The plan requires both that every
   ticket in the order table has a section and that **every section carrying implementation
   criteria appears in the order table**. The code checked only the first. An orphan ticket
   section could therefore have held executable criteria outside the approved sequence with the
   rule green. The reverse direction is now implemented and demonstration (vi) is restated to
   exercise it explicitly rather than incidentally.
2. **(High) Rule 13's exemption window was 300 characters where the plan fixes 500** - the same
   boundary rule 12 uses and the one criterion 6b's control is written against. A historical
   marker sitting 301-500 characters away would pass the specification and fail the code: a
   **false positive in a guard whose entire purpose is distinguishing preserved history from
   drift**. Corrected to 500.
3. **(Medium) The rule list's introduction contradicted the rule list** - "New checker rules
   7-12 ... All six are implemented" above an enumeration of seven - inside the section whose
   purpose is eliminating plan-internal contradictions. Fixed, and **rule 14** now checks a
   stated rule range and count against the rules actually enumerated. It fired on this revision
   before submission, which is the only reason v13 does not carry the same defect forward.

**What this round establishes.** The reviewer moved from reading the plan to reading the plan
against the artifact it names, and found two real divergences plus one self-contradiction. That
is the natural end state of D-043's rule - "every claim of the form 'X is enforced' must name the
enforcing text and be demonstrated against it" - and it is why the checker source now travels
with every plan package: a specification nobody diffs against its implementation is a description,
not a guarantee. The checker is at fourteen repository rules and forty-five kit checks; the
enforcing artifact and the specification now agree, and the reviewer has both.

## D-045 - Plan v14: structure beats spelling
GPT rejected plan v13 with three findings; all accepted, and this time it did not merely read the
checker - it **attacked** it, inserting evasions and showing them pass:

- `ACTIVE.md points to the sentinel` in a non-final ticket - rule 8 stayed green, because the
  code matched the single phrase "gets the sentinel";
- `Five entries remain after this ticket.` - rule 10 stayed green, because the code matched only
  `remaining <word> entries`;
- rule 13's heading replaced by a second rule 14, giving `7,8,9,10,11,12,14,14` - rule 14 stayed
  green, because it compared only minimum, maximum and length.

**The root cause is not three regexes. It is regex over prose.** Natural language has unbounded
paraphrase; a guard that matches sentence forms can always be walked around, and each round of
"add another spelling" is a round the reviewer wins. v14 changes the shape of the problem:

1. **The two prose-dependent claims are now structured fields.** Every ticket declares
   `**Closeout pointer:** <GMR-00N|SENTINEL>` on its own line, and a **deselection ledger** table
   states the count at each stage. **The field is the instruction a builder executes**; prose
   about pointers or counts is explicitly narrative and non-operative. Rule 8 compares
   declarations to the order table; rule 10 compares figures to the ledger. Rephrasing a sentence
   now changes nothing, because no sentence was load-bearing.
2. **Where a prose net remains, it is written to over-trigger.** The net matches the *claim
   shape* in five orderings - "N entries remain", "remaining N entries", "N deselections",
   "register has N" - rather than one spelling, and anything it flags must either be a ledger
   figure or carry an explicit `narrative` marker. **A guard that under-triggers is silent; a
   guard that over-triggers is merely annoying.** Marking eight lines in this revision was the
   whole cost, and the first draft of the net - proximity-based - was rejected in testing because
   it flagged unrelated numbers without catching anything the claim-shape version misses.
3. **Rule 14 now requires the exact contiguous set**, scoped to the section that states the
   range, with no gap and no duplicate. Minimum, maximum and length do not establish that a list
   is what it claims to be.

**The general rule, recorded because it outlives this plan:** when a guard must enforce a claim
that lives in prose, either move the claim into a structured field the guard reads exactly, or
accept a net that over-triggers and demand explicit marking. Never a regex that matches one way
of saying it - that is not a guard, it is a spelling test.

## D-046 - Product Owner ruling: the consistency rules leave the plan's scope
GPT rejected plan v14 with four findings; all four were real and all four were about the kit
checker's plan-internal-consistency rules. So were the three before them, and the three before
those. **Five consecutive reviews found no defect in GMR-003's transplant criteria** - the
reviewer has confirmed the module-class equivalence design, the manifest partition, the
deselection register and GMR-005's coverage protections sound in every round since v9 - and
instead found progressively more elaborate evasions of a guard I had added: a rephrased sentence,
a malformed duplicate field, a phantom ledger row, a digit where a number word was expected.

**The Product Owner ruled to remove those rules from the plan's scope.** The reasoning, recorded
because it is a governance judgment and not a technical one:

1. **They do not govern the builder.** Rules 8-14 catch *Claude Lead's* propagation errors when
   revising the plan. A transplant is neither safer nor less safe for their existence. The
   repository's executable authority should contain what a builder must do, and nothing else.
2. **The surface was unbounded.** A text checker cannot be proven complete against paraphrase.
   Each round closed real holes and opened the next; the findings were shrinking in severity but
   not in number, and there was no state in which the rules could be declared finished.
3. **Claiming enforcement was the actual error.** D-042 established that describing a guard is
   not requiring it; the correction was to require it. The better correction, visible only after
   four more rounds, was to **stop claiming it at all**. A tool that helps its author is not a
   guarantee to a reviewer, and dressing it as one invited exactly the scrutiny it could not
   survive.

**What changes:** the repository checker implements rules 1-7 - the six GMR-001 rules plus the
context-pack plan-hash rule - and GMR-003R demonstrates four failures rather than eleven. **What
does not:** the structured `**Closeout pointer:**` declarations and the deselection ledger stay in
the plan, because they are good drafting independent of any script; the field is unambiguous
where prose was not. The kit checker keeps its consistency rules as an **unreviewed authoring
tool**, offered as disclosure and never as evidence, and hardening it further is Lead
housekeeping outside the plan.

**The lesson, stated for whoever reads this later:** an independent reviewer will scrutinize
exactly as hard as the claims invite. Claim that a script enforces a semantic property and the
reviewer will - correctly - test whether it does, indefinitely. The discipline is not to claim
less than is true; it is to **claim only what the artifact must guarantee for the work to be
sound**, and to keep authoring aids out of the contract.

## D-047 - Transport envelope
Recorded from FEATURE_PHASE_PLAN v6 §4b (2026-08-04); operationally in force through the entire
bootstrap. Every artifact between conversations travels as `.md`. Byte-exact artifacts travel as
base64 inside it, with the decode command and target hash stated. Documents over 180 KB are
chunked with an index and a receipt protocol. Five delivery failures paid for this rule.

## D-048 - Cover-message authority
Recorded from FEATURE_PHASE_PLAN v6 §4b (2026-08-04); operationally in force through the entire
bootstrap. The paste message accompanying an artifact is Claude Lead's instrument and carries
Lead's instructions; it is not a summary of the artifact. Where a cover message and the plan
disagree, **the plan wins**, and the builder reports the conflict rather than resolving it.

## D-049 - Permitted deltas are content-scoped, not path-scoped
A file in a permitted path list licenses only the content changes that list enumerates. A
reviewer aside cannot widen a hash-pinned plan; only a plan-revision object can. (Established by
the GMR-004 closeout V1 rejection; recorded from FEATURE_PHASE_PLAN v6 §4b.)

## D-050 - A criterion satisfiable only by fabricating output is a criterion defect
The builder states the impossibility, supplies the evidence the criterion reached for, and
discloses the substitution. (Established by GMR-005 criterion 4 — the `(0 deselected)` literal —
and its verdict; recorded from FEATURE_PHASE_PLAN v6 §2/§4b.)

## D-051 - Ballpark Pal is excluded from the deployed application
Its terms bar powering anything "made available to others," and a private deployment with
invited viewers still makes it available to others. Provider data may enter a deployment only
where access is limited to the licensed Product Owner **as sole user**, with no invited or
shared viewers, **or** under written provider permission covering the actual audience.
Private-versus-public is not the test; sole-user-versus-anyone-else is.

## D-052 - No third-party provider data becomes a repository fixture or golden file
Committing it is redistribution. This binds for Ballpark Pal and any future licensed provider;
it does **not** bind MLB-derived data, which D-057 addresses expressly.

## D-053 - Park factors: the pinned Baseball Savant per-handedness snapshot is the source of record
Reinstated under D-057. Provenance-pinned: source URL, export date, row count, sha256.

## D-054 - Weather: api.weather.gov (NWS)
Open data, free for any purpose; no API key; an identifying `User-Agent` required; unpublished
rate limits, over-limit requests retryable typically within ~5 seconds; documentation notes a
key may be introduced later.

## D-055 - Venue type is part of the park reference data
Fixed/closed roof → forecast suppressed with a stated reason; open air → forecast applies;
retractable with status unknown → explicit unknown. NWS covers the US only; Rogers Centre
renders the same explicit unavailable state.

## D-056 - The project has no secrets
Neither source needs a credential. The `st.secrets` provisioning deferred through GMR-004 stays
deferred until an object introduces a credentialed provider and states its handling rule first.

## D-057 - Product Owner override of GPT finding 1
Per D-020, the Product Owner overrides the feature-phase-plan review's finding 1 (authorization
to obtain, commit and publicly display Baseball Savant data). The record is honest about what it
sets aside (FEATURE_PHASE_PLAN v6 §1): the use is non-commercial; it is not confined to one copy
on one device for home use, because the deployment is public; written permission has not been
sought. **No claim is made that the conduct is permitted.** This is a decision to proceed
despite the terms. The override is narrow and two boundaries survive it: **automated collection
remains prohibited** — all MLB-derived data enters by manual export performed by the Product
Owner, and §GMF-006 must prove no code path fetches from an MLB host — and **Ballpark Pal
remains excluded** (D-051). Reversible: withdrawal means removing the committed snapshot and
MLB-derived surfaces from the deployment, which the manual-export path and the adapter seam
keep recoverable.

## D-058 - No inline master-detail; selection-driven detail panel
**No inline master-detail; selection-driven detail panel.** Inline expansion forces AG Grid
Enterprise licensing, an untestable iframe grid, and version-coupling risk. Row selection
(`on_select`) drives a detail surface instead.

## D-059 - No `matplotlib` dependency
**No `matplotlib` dependency.** Cell grading is hand-rolled via `Styler.map`; revisit only if
hand-rolled grading proves inadequate, as a new decision.

## D-060 - Theming via `.streamlit/config.toml` only
**Theming via `.streamlit/config.toml` only.** Never style against `st-emotion-cache-*` classes or
`data-testid` attributes — not public API, breaks silently on upgrade. Cell colour comes from
`Styler` inline styles.

## D-061 - The core table stays testable: native `st.dataframe`, with the testing boundary stated at the version floor
**The core table stays testable: native `st.dataframe`, with the testing boundary stated at the
version floor.** An untestable core UI surface is not acceptable — and neither is a claimed test
capability the floor version does not provide. At Streamlit 1.37, `AppTest` exposes the dataframe
as an element and **cannot synthesize row selection** (selection state is not programmatically
settable). The boundary, falsifiable at 1.37: **AppTest proves the element's handed-off data and
configuration** — column set, order and visibility, density configuration, graded values, and
every absence state's rendering as data; **the selection-consumption path** (the code receiving a
selection and producing detail state) **is proven by direct tests as ordinary code**; **the
click-to-detail interaction and visual legibility are observed at §GMF-002 submission 2** on the
deployed page. No AppTest capability is claimed beyond the floor's.

## D-062 - Streamlit is version-bounded; upgrades land through `staging` first
**Streamlit is version-bounded; upgrades land through `staging` first.** Floor **>= 1.37**
(`on_select` arrived 1.35; `st.fragment` stable in 1.37), with a defended upper bound against
third-party breakage.

## D-063 - Origin-first provider precedence
**Origin-first provider precedence.** (a) Baseball Savant is the origin source for Statcast-derived
fields and takes precedence wherever it carries the field. (b) FanGraphs is admitted only for fields
the project computes itself from its own inputs — never for re-display of FanGraphs-authored metrics
(the §24 marks posture stands). (c) Origin-unavailable exception: where Savant does not carry a
field at all, a secondary provider may supply it, and the exception is named in that field's
provenance note.

## D-064 - The sample contract
**The sample contract.** AB, H and K are carried as raw counts, each with its unit and an
observed/derived flag. `BIP_est = AB − K` is a derived estimate that understates balls in play by
sacrifice flies and hits; the understatement is stated wherever the estimate appears, never hidden.
K is carried as a count, never reconstructed as K% × AB. A derived field propagates the absence
reason of every input it derives from, intact.

## D-065 - Switch-hitter side handling (supersedes the switch-hitter resolution rule of D-025, confirmed in D-026)
**Switch-hitter side handling (supersedes the switch-hitter resolution rule of D-025, confirmed in
D-026).** A switch hitter's row carries **both** batting sides, each labelled by the opposing
pitcher hand that produces it. The batting side used in any display is derived from the matchup and
labelled as derived; it is never silently chosen. Probable-starter resolution is not a dependency of
any surface; if it ever arrives it is an additive derived layer, never a contract input. D-025's
never-average clause stands: both sides are never averaged into one number for a criterion.

## D-066 - Pitch-usage scope toggle (PO-N1)
**Pitch-usage scope toggle (PO-N1).** The batter metrics surface gains a user toggle between (a)
usage measured against batters of the evaluated side and (b) all pitches the pitcher throws. The
toggle requires the handedness-split usage denominator, which enters the contract at §7 and is
ingested at §GMF-006, before the field set is fixed there. The three usage states (qualifies ·
measured below threshold · absent/unevaluable) survive both toggle positions, and the prose names
which scope produced each suppression. Scheduled as §GMF-008.

## D-067 - Matchup window; score deferred (PO-N2)
**Matchup window; score deferred (PO-N2).** The matchup section is computed over a **rolling 30
days** ending at `as_of` — not a calendar month. **This ruling authorizes the window only. No score
is authorized.** A windowed score is ranking-shaped under D-015/D-017 and requires its own explicit
Product Owner posture ruling before any ticket text names it. Scheduled as §GMF-009.

## D-068 - Form section (PO-N3)
**Form section (PO-N3).** Seven metrics, no toggle: Barrel%, EV, AtkAng, IdealAtkAng%, Pull%, Hard%,
xwOBA — where **Pull% is the D-023 Pull Air %**, labelled as such on the surface (Product Owner,
2026-08-20). Window **L7 with an L14 fallback**, the fallback triggered by **each metric's own
sample floor** — never by mere emptiness. Floors: Barrel% and EV **15 BBE** (D-023/D-026);
IdealAtkAng% **25 tracked swings** (D-023); Pull Air % **15 air balls** (D-023); **AtkAng 25
swings**, **Hard% 15 BBE**, **xwOBA 15 PA** (Product Owner, 2026-08-20 — each uncovered floor
follows its shared denominator). A field whose L14 sample is below its floor is **present with its
value, its exact sample, and an INSUFFICIENT marker** — the missing-versus-insufficient rule of
D-023/D-025 is unchanged, and no new absence state is created. A field with no observations at all
is absent with its reason under the ordinary absence semantics. The window actually used is named on
the surface, per D-025's stated-window rule. Scheduled as §GMF-007.

## D-069 - Automated acquisition authorized for the two named MLB hosts; review gate suspended under the directive
**Automated acquisition authorized for the two named MLB hosts; review gate suspended under the
directive.** (a) The Product Owner's 2026-08-20 directive authorizes automated, unattended data
pulls from `statsapi.mlb.com` and `baseballsavant.mlb.com`, superseding D-057 boundary 1 (manual
export) for those hosts only. The GMF-005 weather-adapter discipline binds: a host-pinned
transport module (allowlist constant, redirect re-validation, bounded timeout), network at the
composition root only, no caller-supplied URLs, failures mapped to named absence states, no
secret in code, no live payload committed as a fixture. (b) The directive grants the builder
merge/push authority on this repository; local verification — the 10-rule checker plus the full
test suite run on the exact merged tree — stands in for the pre-2026-08-20 review-chat gate for
the directive's scope. The no-odds surface (D-015/D-017) and the Ballpark Pal exclusion (D-051)
are unchanged.

## D-070 - Live sources of record
**Live sources of record.** Slate, probable pitchers, lineups and season hitting counts come
from the MLB Stats API (`statsapi.mlb.com`); Statcast-derived metrics — season leaderboards,
rolling L7/L14 windows, pitch-arsenal splits, per-event logs — come from Baseball Savant CSV
endpoints (`baseballsavant.mlb.com`), the origin source per D-063; weather comes from
`api.weather.gov` per GMF-005. Every fetch is cache-bound at the composition root with a stated
freshness bound, so a reload is not a refetch. A failed or stale fetch degrades to the contract's
named absence states; a stale value is never shown as current.

## D-071 - Grading v1 configuration
**Grading v1 configuration.** The production grading configuration is 12 total points across five
categories — power_profile 3, pitcher_matchup 3, form 2, pull_power 2, environment 2 — with grade
cutoffs D [0,4), C [4,6), B [6,8), A [8,10), S [10,12], per the spec recorded in the synthetic
engine config's header. Component bucket edges are provisional v1 values pending the Product
Owner's threshold rulings; they are configuration, not code, so a later ruling changes the config
file only. The v1 config lives at a new path (`config/production/gm_hr_v1.yaml`); the byte-pinned
synthetic test config is never edited.

## D-072 - Navigation: four tabs
**Navigation: four tabs.** The deployed app organises live surfaces as `st.tabs`: **Sluggers**
(slate board — lineup batters with season and L7 metrics, park and weather tags, grade, threshold
highlighting per the spec values, INSUFFICIENT badges), **Arms** (probable pitchers and their
arsenals), **Matchups** (per-game venue, probable pitchers, and both lineups), **Conditions**
(parks and live weather). A Record/betting-log surface is **not** authorized — it is
ranking-adjacent under D-015/D-017 and awaits an explicit Product Owner posture ruling.

## D-073 - GMF-006 implementation judgment calls
**GMF-006 implementation judgment calls.** Logged per the 2026-08-20 directive's judgment-call
rule; each was made to keep the build moving and each is reversible.
(a) *Provisional matchup derivations (Q15/Q16 stay open).* pitch_mix_pressure is the
usage-weighted share of the expected starter's >=15%-usage pitch types where the batter's season
expected wOBA meets or beats the league's PA-weighted expected wOBA **against that same pitch
type** (a per-pitch-type baseline, so fastball-heavy pitchers are not systematically easier).
put_away_pitch_exploitation is the batter's whiff suppression versus the league's pitch-weighted
whiff share on the starter's qualifying pitch with the highest put-away rate, clamped to
[0, 1] — a batter who whiffs *more* than league scores zero, never negative. The parallel QA
review recommended replacing both with continuous expected-wOBA margins; that replacement needs
PO-ratified boundaries (Q12/Q13) and lands as a config-plus-derivation change, not a rebuild.
(b) *Expected wOBA, not raw wOBA* (adopted from QA review): at per-pitch-type sample sizes the
raw figure is dominated by sequencing and defense.
(c) *Any roof means neutral conditions.* Fixed-roof **and** retractable-roof venues grade the
weather component at an assumed neutral indoor value (72 °F), labelled as an assumption, because
v1 has no roof-state source and an unobtained roof may be closed; only open-air venues use the
live NWS forecast. This follows the ratified withholding rule rather than the open-air default.
(d) *Unposted lineups are estimated, labelled.* The club's nine highest-usage bats on the batter
arsenal board stand in, marked `est.` wherever they render.
(e) *Observations carry the snapshot's 7-day window*; the D-068 14-day fallback reach is recorded
in each form observation's DataCoverage requested span, because the domain requires every
observation to share the snapshot's exact window.
(f) *Missing scheduled start* resolves to midday UTC for the game identity only; *an unannounced
starter* is represented by an explicit `UNCERTAIN` placeholder pitcher, never by guessing.
(g) *Savant CSV realities:* the export's BOM is stripped before parsing (it mis-splits the first
quoted header otherwise); a 200 with an empty body reads as no-data, not an error; rows with
empty required cells (tiny samples) drop row-wise while a fully unparseable board still fails;
`hard_hit_percent` ships empty this season and is read optionally.
(h) *Caching:* the composition root caches the assembled board 15 minutes and each day's pitch
file one hour; a reload is not a refetch (D-070).

## D-074 - The weather seam names its source at the interface
**Weather adapters expose their `SourceRecord` as `source`, not only inside each field.**
The input contract rejects a snapshot whose fields name an undeclared source, and a live
adapter's fields name the *adapter's* source — so the record has to be reachable from the
seam, or every snapshot builder would have to import each live adapter module to declare it.
`WeatherAdapter` gains a `source: SourceRecord` attribute; the NWS adapter answers its
module-level `SOURCE`, the fixture answers `CONDITIONS_SOURCE`. `parks_demo_snapshot`
declares whatever the bound adapter names alongside its own fixture sources, which is what
lets the §GMF-004 screen keep rendering when §GMF-005's live adapter binds (the deployed
`InputContractError` of 2026-08-20).

## D-075 - One tab's failure never blanks the page
**Each live-board tab renders inside its own isolation boundary.** An exception escaping a
tab renderer ends the whole Streamlit script run, taking the other three tabs and every
section below the board with it — the failure shape observed on the deployed app when a NaN
cell reached the highlight mapper (pandas stores a missing numeric as NaN, and
`Decimal('NaN') >= edge` raises `decimal.InvalidOperation`). Each tab now renders through a
helper that converts a failure into a named in-tab warning; the highlight mapper treats
non-numeric cells (None, NaN, text) as never-highlighted. Regression coverage drives the
full page through AppTest against a real `build_board` product mixing covered and uncovered
batters — the mixed float64/NaN columns that triggered the crash.

## D-076 - The main screen is the shell and the live board, nothing else
**The app's entry point renders the D-003 console shell (orb, title, environment status
line) above the four-tab live board — and nothing else.** The demo surfaces (batter grid,
metrics, parks) leave the main screen at the PO's direction; their machinery stays as
library code, and each keeps a standalone runner under `tests/app/runners/` so its
criteria stay testable end-to-end without occupying the page. Three rendering rules come
with the move:
(a) *A live-board column that can be absent is display text, not a number with a null.*
Streamlit's data grid renders a null cell as the literal "None" and never consults the
styler's display value for it (probed on 1.62.0, the deployed bound and the latest 1.x),
so the §GMF-002 numeric-plus-na_rep pattern cannot speak on this surface. Live frames
therefore carry uniformly string cells — Arrow-homogeneous, so no `ArrowInvalid` either —
with values formatted and absences worded at build time (`styled_text_frame`). What the
column gives up is numeric header-click sorting; the boards arrive pre-sorted by grade,
which is the intended read.
(b) *Absence is displayed, not hidden.* Every absent cell names its reason in words
(D-023/D-025), muted; a present value at its edge is highlighted at build time with float
comparisons, so no NaN ever reaches a comparison (the first deployed crash class).
(c) *The shell is original artwork and makes no remote request.* No console maker's
marks, no CDN font, image, stylesheet, or script — the theme is CSS plus an inline SVG
background, enforced by test.

## D-077 - The Sluggers board is a shortlist, not a spreadsheet
**The Sluggers tab shows only batters at or above a minimum grade, and only these
columns: Batter, Team, Versus (the opposing starter), Grade, Park factor, Weather
details, and a Tags box reserved for future markers (Product Owner, 2026-08-21).**
Season/L7 metric columns leave the main table; a per-row expand control opens the
batter metrics view (D-078). The minimum grade is configuration, not code — the
provisional floor is A and S pending the Product Owner's threshold ruling, which
they have reserved ("we will tweak grading and thresholds when ready"). This
sharpens D-072's sketch of the tab, not its intent.

## D-078 - The expanded batter view is the home of the form section
**One batter-metrics view, reachable from a batter's row in both Sluggers and
Matchups, carries: the matchup block (L30 pitch-mix data), the D-068 form section
(the seven metrics, L7 with the per-metric L14 fallback, each bracket-labelled
"L7" on the surface), Oppo Air Pull %, park factor, and weather (Product Owner,
2026-08-21).** Pull Air % and Oppo Air Pull % carry a user toggle between L7 and
season windows. A metric with no observations at either reach says "not enough
data available" in words — D-068's present-with-INSUFFICIENT rule stands for
below-floor samples. This placement is §GMF-007's surface.

## D-079 - The Matchups tab grades on L30 pitch mix
**Each matchup row is computed over the rolling 30 days versus the opposing
starter's pitch mix (pitches at or above a 14% usage share), with a user toggle
to the season view — but the matchup grade is always the L30 computation
(Product Owner, 2026-08-21).** Columns: ABs/H (or BIP), Barrels, HRs, Exit
Velocity, Barrel/PA %, Hard-Hit %, AVG, SLG, ISO, +350 ft Pull Air %, xwOBA,
Swing-Str %, recent form, grade. **This ruling is D-067's awaited posture
ruling: the Product Owner has explicitly authorized the matchup grade on the
named window; the no-score freeze is lifted for this surface only.**

## D-080 - The per-pitch expanded view mirrors batter against pitcher
**Inside a matchup's expanded view: the batter's per-pitch table (usage %, AVG,
SLG, ISO, HR, Barrel %, Hard-Hit %, plus xwOBA and Swing-Str %), a recent
exit-velocity game-by-game sheet, and a threshold on/off toggle that applies to
the whole expanded view only; scrolling further reveals the mirror table — the
pitcher's own per-pitch metrics against the batter's side, with xwOBA and Whiff %
added (Product Owner, 2026-08-21, reference images 6–8 of 2026-08-21).**

## D-081 - Pitcher and pitch-usage windows fall back L30 to L45 to last season
**Where a pitcher's pitch-mix or per-pitch sample is too small at L30, the reach
extends to L45, then to last season; a field empty at every reach states "no
data available" (Product Owner, 2026-08-21).** The window actually used is named
on the surface, per D-025's stated-window rule — the same discipline as D-068's
L7/L14 form windows, applied to the pitcher side.

## D-082 - The matchup card reads top-down: park, pitchers, teams
**Each matchup game card opens with a 2D field-view stadium panel — park factor
plus live conditions with a wind animation in the spirit of the PO's weather-man
reference (image 3 of 2026-08-21) — then a brief per-pitcher metrics strip
(reference image 8) behind an LHH/RHH toggle, then the two lineups behind a
team toggle rather than one long scroll (Product Owner, 2026-08-21).** The wind
animation consumes the park-orientation table and the Ballpark Pal receptiveness
capture (docs/reference/ballpark-pal-park-factors.md); both enter as data with
their provenance named, per the source discipline.

## D-083 - Tab navigation imitates the original-Xbox rotary dial
**Switching the four main tabs carries a dial motion — the selector ring rotates
the chosen tab into place, in the spirit of the PO's reference video
(20–22 s mark) — implemented as original CSS artwork only (Product Owner,
2026-08-21).** D-003's constraints stand: no console maker's marks, no remote
asset of any kind.

## D-084 - Sluggers shortlist columns; the expand is park, form, exit-velo
**The Sluggers grid becomes the D-077 shortlist in shape: columns Batter,
Team, Versus, Grade, Park factor, Weather details, and a Tags box; the
per-batter metric columns leave the grid (they live in the expand and on the
Matchups surfaces), and only batters graded A or S are listed — the Product
Owner's final ruling on the D-077 grade cut (2026-08-21).** The Sluggers
batter-expanded view holds exactly three blocks: the 2D stadium panel with
wind animation (D-082's panel, placed in the expand), the D-068 L7 form
section, and the recent exit-velocity game-by-game sheet, with a pitch-mix
threshold off/on toggle applying to the whole expanded view only. The
per-pitch tables and the pitcher mirror remain the Matchups popup's content
(D-079/D-080), not the Sluggers expand. The D-083 dial motion stands as
ratified: items ride a rotary ring and the selection slides into place,
original CSS artwork only.

## D-085 - Wind speed and direction join the game card; the expand draws them
**The slate board's game card carries the NWS forecast's wind speed and
direction alongside temperature — open-air venues only; a roofed game carries
no wind reading rather than a number that never reached the field (the D-073
rule extended).** The batter detail's drawn field panel renders the wind as
an animated flow rotated to the live compass bearing, and the shortlist's
weather column keeps naming temperature (Product Owner, 2026-08-21: "sluggers
is still missing wind direction"). Wind in baseball terms — blowing out to
centre, in from right — stays parked until the park-orientation table lands
(the D-082 memo); the panel claims only the compass reading, never a
field-relative direction it cannot yet derive.

## D-086 - The exit-velocity sheet is an event log; the toggle filters pitches
**The batter detail's exit-velocity sheet logs one row per
plate-appearance-ending pitch — Date, Pitch, Event, EV, LA, Type — newest
game first, over the seven most recent games in the form window; a home run's
event cell is lit, hot contact carries the red heat scale, and a no-contact
outcome (strikeout, walk) shows dashes rather than a fabricated reading
(Product Owner, 2026-08-21, correcting the D-084 game-by-game aggregate with
the EXV-log and game-by-game references).** The pitch-mix threshold toggle
filters the log's rows by pitch type: off shows every pitch type, on keeps
only the qualifying pitch mix — types at or above D-070's 15% usage share
computed across every pitch seen in the window — so toggling changes the
exit-velocity events shown, not a summary column. The 2D field panel was
re-drawn fuller (wall band, warning track, mound, base paths) with the wind
as streaking lanes clipped to the field; per-park wall heights and field
shapes remain undrawn for want of a ratified source, as with the
park-orientation table (D-082, D-085).

## D-087 - Pitcher metrics are season-long with a last-season fallback; the mirror is renamed Arsenal
**Every pitcher figure on the board is a full-season number, never a windowed
one; when a pitcher has no current-season record, last season's board fills
in and is labelled with its year (Product Owner, 2026-08-21: "when it comes
to any and all pitcher data/metrics, it will be based off the whole season,
and fallback and last season if no data is available").** The matchup popup's
pitcher table is renamed from "Pitcher mirror" to "Arsenal": it holds every
pitch he throws with season usage, PA, AVG, SLG, ISO, wOBA, xwOBA, Whiff%,
K% and Hard-Hit% from the arsenal board — the board publishes no per-pitch
home-run or barrel counts, so those columns do not exist there rather than
showing invented zeros. A toggle filters the rows to the pitch types he has
used against the batter's side; that per-side determination reads the recent
31-day pitch record (the only per-side split the approved feeds carry) and
the prose names it, while the numbers themselves stay season-long either
way. The season pitching line on the Arms tab was already season-scoped and
is unchanged; only the batter's recent-form section is an L7 surface (per
the same directive).

## D-088 - The matchup per-pitch table is vs the starter's side over L30; the popup threshold is adjustable
**The matchup popup's batter per-pitch table shows his metrics against the
opposing starter's side — right- or left-handed pitching — over the last 30
days, with the qualifying-mix toggle kept (off: every pitch type; on: only
the mix) and the usage threshold adjustable from inside the same popup
(Product Owner, 2026-08-21: "for matchup i should see batter metrics vs that
side pitcher. L30 days. With option to change and toggle on/off pitch usage
threshold"; "I want to be able to adjust the threshold somewhere, preferably
within the same pop up window").** One slider sets the line for the matchup
table, the Arsenal table's dimming, and the exit-velocity log's pitch-mix
filter — a display filter only: grading's qualifying usage line stays the
ratified 15% (D-070) and never moves with the slider. With no opposing
starter named there is no scope, and the table names the absence rather than
drawing an unscoped one. This supersedes D-080's season-arsenal batter table
and the D-066 windowed scope toggle, both absorbed into the popup's final
shape.

## D-089 - GMF-009 derivation definitions: L45 trigger, grid aggregation, season-view sources
**The Matchups-grid rework fixes its derivation definitions as follows
(builder record, 2026-08-21).** D-081's "too small at L30" trigger reads as
zero pitches in the window — a builder may not invent a sample floor, so the
reach to L45 fires exactly when the window holds none of the starter's
pitches, and the extra days are fetched only when some probable needs them.
The grid's batter line aggregates his last-30-days events against the
starter's qualifying (14%, D-079) mix pitches from the starter's side —
the same side scope as the popup's matchup table (D-088). A mix pitch's
put-away rate always reads the season board (pitch events carry no put-away
counts); a pitch type absent from the board is skipped by the put-away
derivation rather than scored on an invented zero. The season view composes
from the season sources only: the hitting line (AVG/SLG/ISO via total
bases), the statcast board (exit velocity, barrels, hard-hit), and the
arsenal board (PA-weighted xwOBA, pitch-weighted Swing-Str %); no season
source publishes a 350-foot pull-air read, so that cell states the absence
per D-081. The grid's recent-form cell shows the form section's exit
velocity with its window named. The grade is always the L30 computation in
either view (D-079).

## D-090 - +350 ft % and Pull Air % are two separate matchup-grid metrics
**The matchup grid carries "+350 ft %" and "Pull Air %" as separate columns:
the first is the share of batted balls hit that distance or farther, any
direction; the second is the pulled-air share, mirroring the form section's
definition — pulled air balls over measurable air balls (Product Owner,
2026-08-21: "+350 ft and Pulled air % are two separate metrics. the first
is balls hit that distance").** This splits D-079's single "+350 ft Pull
Air %" column into its two parts; neither has a season source, so the
season view names the absence in both cells (D-081). The same directive
reaffirmed that recent form is an L7 surface — the grid's form cell keeps
showing the form section's exit velocity with its window named, and the
L14 fallback stays labelled per D-068.

## D-091 - The recent exit-velocity log carries the hit's projected distance
**The batter detail popup's recent exit-velocity event log gains a Dist
column: the source's projected hit distance for each plate-appearance-ending
pitch, in feet, with a dash where the pitch carries no reading (Product
Owner, 2026-08-21: "lets include distance of the ball hit in the event log
for recent exit velo").** Display-only: the log's rows, ordering, and
threshold filter are unchanged.

## D-092 - The slate day is the viewer's choice: yesterday, today, or tomorrow
**The live board header gains a Yesterday / Today / Tomorrow control that
picks which slate date the board builds (Product Owner, 2026-08-22: "I want
the ability to back to the previous slate... I should have the ability to go
between yesterday todsay and tomorrow").** Only the slate changes; the
knowledge cutoff (lineup estimates, form windows, the 31-day pitch record)
stays anchored to now, so yesterday's board is yesterday's matchups read with
today's knowledge — named as such. Every selectable grid key carries the
slate date so a day switch remounts the grids with empty selections, and the
per-date board cache keeps the three days independently warm.

## D-093 - Park geometry binds to the Seamheads Ballparks Database
**The park-diagram feature (next phase) draws its outfield distances and wall
heights from the Seamheads Ballparks Database year pages, ratified by the
Product Owner (2026-08-22: "yes you can use seamheads").** The year page
publishes the twelve outfield distances (LF through RF with the gaps and
power alleys) plus wall heights per segment; the values were verified against
the Product Owner's example diagram (Coors Field: 347/390/415/375/350 with
the 13'/8'/17' wall profile) before ratification. Clem's Baseball
(andrewclem.com) supplies what Seamheads lacks — the home-plate-to-center
compass orientation the parked wind work needs. This decision ratifies
sources only; the diagram feature itself is next-phase scope.

## D-094 - A neon money tag marks batters who homered, on the Sluggers tab
**The Sluggers shortlist gains an HR column: a neon-green "$" beside any
batter who homered in his most recent game day on or before the slate,
blank otherwise (Product Owner, 2026-08-22: "a small icon or tag (money
sign in neon green) next to playerws who hit homeruns on the sluggers tab.
So somthing shouyld be checking for homeruns hit").** The pipeline computes
`homered_on_last_game_day` per batter: the batter's latest played day on or
before the slate is found, and the tag shows only when that day holds a
`home_run` event — a homer earlier in the record with a quieter game after
it does not tag. No record, no tag: the column never guesses. Viewed on a
past slate (D-092), the tag marks who homered on that slate day.

## D-095 - The backtest view tallies grade hit rates and ROI on entered odds
**A Backtest button in the header's top-right corner swaps the board for a
backtest view (Product Owner, 2026-08-22: "i also want a backtest tab that
tracks ROI or hit rates for the grades. we can add it as a button in top
right corner instead of adding it to the wheel").** Each past slate (last 7
or 14 days) is regraded with an as-of of 20:00 UTC the prior evening, so no
event from the measured day can leak into the grade; outcomes are that day's
`home_run` events. Hit rates pool per grade letter (S/A/B/C/D);
not-evaluable batters carry no grade and are excluded. ROI prices every
graded batter as a 1-unit stake at American odds the viewer enters — the
product holds no odds source. Two named approximations ride on screen:
season boards (hitting, arsenals, statcast) are current snapshots when
regrading a past date, and weather is not reconstructed (temperature and
wind bind as absent). The backtest is a view behind a button, not a dial
tab — the dial is for reading a slate, this is for auditing the grades.

## D-096 - BIP leaves the board; counting stats stand alone
**The BIP column is removed from every surface (Product Owner, 2026-08-22:
"I would like to move away from BIP as well and remove them where ever they
are, I prefer, ABs and Hits. alone.").** The matchups grid's counting
columns are now AB, H, Barrels, HR, and the +350 ft count. The batted-ball
count stays inside the pipeline as the hard-hit and pull-air denominators'
scope record, but it is never displayed.

## D-097 - +350 ft is a count of balls, not a share
**The +350 ft column shows the number of batted balls hit 350 feet or
farther in the scope — a counting number beside AB and H, not a percentage
(Product Owner, 2026-08-22: "also 350+ is number of balls hit 30ft+", read
with the metric's own name as 350 ft: a 30-foot filter would tally nearly
every batted ball and mean nothing on a home-run board).** D-090's
definition stands — distance only, any direction, off the source's
projected distance — only the display shape changes. The season view still
has no source for it and names the absence.

## D-098 - The matchups grid drops its Form column
**The Form (EV) column leaves the matchups grid (Product Owner, 2026-08-22:
"lets also remove 'form' column in matchups tab, since we can expand and
see the full form metrifcs").** The full form section remains one tap away
in the batter detail popup, so the grid stays lean; nothing about the form
computation itself changes.


## D-099 - A no-op arsenal side filter says so in words
**When the batter detail's "only pitches he uses vs this side" toggle removes
no rows — because the starter threw his entire arsenal to that side over the
recent 31-day record — a caption names it: "nothing to filter" (Product
Owner, 2026-08-22: "toggle doesnt seem to be wokring nothing changes, please
check it").** Investigation on the live board confirmed the toggle itself
was correct: Ryan Weathers threw all five of his pitch types to right-handed
batters in the window, so the filter legitimately changed nothing — the bug
was the silence, not the mechanics. The empty-record fallback caption
("showing the full arsenal") is unchanged.
## D-100 - Home-run outcomes read the real-time game log, and a truncated download gets one retry
**The $ money tag and the backtest's daily outcomes read MLB Stats API
hitting game logs — near-real-time, completed games only — instead of the
Savant pitch record, whose search CSV runs a day behind; and a response body
cut short mid-read is retried exactly once instead of crashing or silently
dropping a day (Product Owner, 2026-08-22: "Some people who hit home runs
are incorrect. Missing some $ as well. If it's because the game is still
ongoing I understand. Also there's a lot of missing information for recent
form data and the data for last 30 days seems choppy... it's readily
available for players like Olson or Spencer jones yet it's missing.").**
Three root causes, three fixes. First, Savant's statcast_search CSV is
day-indexed: yesterday's and today's files are header-only shells for much
of the day, so a homer hit last night never reached the tag and the last-30
windows ran a day short. The Stats API gameLog hydrate answers completed
games within minutes, five days of lookback covers off-days, and an
in-progress game is simply absent — exactly the lag the owner already
accepts. A log line with no plate appearances is not a played game: it
neither tags nor clears. Second, the backtest's outcome column shared the
lagged source and so mistimed or missed recent slates; it now reads the
same game logs, and a day whose log feed returns nothing is still excluded
and named, never tallied as invented zero-homer rows. Third, a truncated
multi-megabyte CSV body (http.client.IncompleteRead) escaped every existing
exception clause — it crashed renders outright, and because transport errors
were never retried, one severed download silently removed a whole day from
every 30-day window. The transport now names truncation its own error and
grants it exactly one more attempt; a second truncation answers as source
unavailable. What remains source-limited: the bat-tracking leaderboards
enforce their own sample floors, so a hitter short of a floor still shows a
named "not enough data" absence — that is the discipline, not breakage.

## D-101 - The slate day is a calendar date picker
**The Yesterday/Today/Tomorrow toggle becomes a date selector: the viewer
picks any slate date off a calendar, bounded to a month back and a week
ahead (Product Owner, 2026-08-22: "Instead of a today yesterday and
tomorrow let's have a date selector please.").** The relative words
survive where they are true — the heading still says "(today)",
"(yesterday)" or "(tomorrow)" on those dates — and any other date stands
on its own. Only the slate changes with the pick; lineup estimates and
form windows stay anchored to now, as under D-092. The bound is honesty,
not aesthetics: beyond a month back the pitch record thins and beyond a
week ahead there is no slate to answer for.

## D-102 - xwOBA leaves the popups, and the arsenal side toggle switches usage to the hitter hand
**xwOBA is removed from the recent-form grid in the batter detail popup —
it stays on the Matchups main tables — and the Arsenal side toggle now
rebases Usage% to the hitter hand: with the filter on, usage is the
pitcher's share of pitches to that side over the recent 31-day record,
named on screen, while every other arsenal number stays season-long
(Product Owner, 2026-08-22: "Let's remove xWOBA from recent form in all
pop ups. Leave it on match ups main tables. In arsenal, is the usage
based off HITTER HAND or is it just their usage in general? If it's in
general, the toggle should change usage to being based on hitter hand.").**
The owner's question diagnosed the gap precisely: the arsenal leaderboard
publishes one usage figure per pitch spanning all batters — verified
against the source, which honors no handedness parameter — so the toggle
used to filter rows while leaving an all-batters number on them. The only
per-side split on the board is the pitch window that already powers the
filter, so that record now carries the per-side shares; a side with no
pitches maps to nothing rather than inventing one. Rows sort and dim on
whichever basis the column shows. xwOBA's removal is from the form model
itself, not just the grid: the Matchups tables read their own grid-line
path, so nothing they show changed.

## D-103 - The form fallback window stays honest, and diagnostics name their slate
**Three correctness fixes out of the polish pass's recommendation list
(Product Owner, 2026-08-22, asked which of the list to implement: no
preference — the low-risk correctness items proceed under standing
authorization).** First, the real bug the polish pass surfaced but was
forbidden to touch: ``build_board`` rebound the local ``reach_start`` when
a starter's empty last-30-days forced the pitcher's 45-day mix reach, and
the form section's L14 fallback cutoff was computed from that rebound
value — so on any slate with such a starter, every batter's "L14" fallback
silently read 45 days while the screen said L14, and the swing-tracking
metrics beside them stayed at 14. The rebinding is renamed and a test pins
the window (it fails on the old code, passes now). Second, the
weather-failure caption is keyed by slate date instead of one shared list,
so a cached board can no longer wear another slate's diagnostics. Third,
two failure-message paths in the MLB adapter named JSON locations that do
not exist; they now name the real paths. The remaining recommendations —
wording changes, build-time work on the pinned fetch behavior, the
build_board restructure, dormant surfaces — stay parked for the owner's
call.


## D-104 - Range-chunk consolidation: built, measured, rejected
**The per-day pitch fetch stays (Product Owner, 2026-08-22: "Do what
ever you recommend for efficiency and smoothness").** The investigation
started from a belief that the cold build's one-CSV-per-window-day
pattern (31 days, 46 with the 45-day mix reach) dominated its minutes.
The consolidation was built in full — epoch-aligned 7-day range chunks
with recursive midpoint splitting against the search CSV's silent
truncation cap (observed and proven: a 7-day range needing 27,642 rows
answers exactly 24,999 without a word) — and then measured against the
existing path on the same network within the same hour. Per-day: a
cold board in 121s. Range chunks: 145s. The per-day fetch costs ~1.7s
of mostly fixed latency; a 7-day range costs ~7s of row volume, and a
week that hits the cap splits into extra requests that eat whatever the
fewer round-trips saved. The instrumented build's real cost profile:
~75s pitch window either way, ~17s of per-game batting orders, ~15s of
season boards, ~38s of in-process assembly — no single fetch shape
changes it. The consolidation was reverted rather than shipped: extra
machinery (cap detection, recursive splits, chunk-aligned caching) that
pays for nothing is the kind of complexity this project removes. The
remaining lever on cold-build time is concurrency across the
independent fetches, parked for the owner's call because it raises
politeness and rate-limit questions against two sources that a pure
client-side change cannot answer.

## D-105 - Three wording fixes from the parked polish list
**(Same authorization as D-104.)** The Sluggers intro caption no longer
carries a second copy of "select a row" — the point-of-use caption under
the grid already says it. The Conditions table's Type column shows a
human label ("retractable roof") instead of the enum's raw snake_case
value. And the Arsenal table's side filter can name pitch types his
season arsenal board lacks (thrown against this hand in the recent
window, never qualifying season-long); that case now captions the reason
instead of rendering a blank grid. A fourth parked item — a "forecasts
refresh every 30 minutes" line — does not exist anywhere in the codebase
and is recorded here as a no-op.

## D-106 - One arsenal breakup table, pitcher usage only
**The batter dialog's two per-pitch tables merge into a single "Hitting
stats — arsenal breakup" table (Product Owner, 2026-08-23: "I don't think
what you did was wrong , it was just a bit confusing . I'd prefer to only
see pitcher usage % , and no batter % for the arsenal. Additionally.
Instead of two seperate tables let's do one single table called hitting
stats - arsenal break up. This table wiill have two halves distinguished
by a line or something in the middle maybe an opaque sub header over. I
want pitcher metrics on on first half, and batter metrics on second half.
One pitch will have one row with usage percentage (pitcher) and season
long metrics for the pitcher + batter metrics that correspond to that
exact pitch . (one month) (I'd like the ability to toggle between months
and weeks. Single digit scroll. ) as for the metrics ,I will come back
with that for now finish what you're doing and get started on this.").**
The confusion being retired: the old matchup table's Usage% was the
batter's seen-share — what the league threw him — sitting next to the
pitcher's own season share in the arsenal table, so the same label meant
two things. Now Usage% is only ever the pitcher's: his season board share
by default, his share of pitches to this hitter hand over the recent
window when the D-102 side toggle is on (that exception survives; every
other number stays season-long either way). The table is one HTML grid
with an opaque sub-header row splitting the halves — pitcher season-long
figures first, batter window figures second, one row per pitch in his
arsenal. The batter half is precomputed pipeline-side at five reaches —
weeks one through four plus the full month the pitch record carries
(``MATCHUP_LINE_WINDOWS_DAYS``) — so the dialog's Months/Weeks control
selects, never derives (§GMF-008); months are pinned at the one month the
record reaches, weeks scroll one through four. A pitch the batter has not
seen from this side keeps its row with zeroed counts and dashed rates —
dashed, never hidden. Below-threshold rows dim; the old qualifying-mix
toggle on the matchup table is gone (the threshold slider still dims, and
the event log keeps its own mix toggle). The metric columns shown are the
ratified set carried over from the two merged tables; the owner will name
final columns later, and the builder is the single place that change
lands.

## D-107 - The logo is an ouroboros around a glowing baseball
**The header orb becomes the combination mark from the owner's reference
images (Product Owner, 2026-08-23: "I also want to Change the green orb ,
you can keep it but add the details in the image with the ouroboros ,
make a combination for the logo on the landing page", then "Actually make
it look like a baseball instead of an orb").** The mark — an ouroboros
ringed around a glowing neon-green baseball — is original artwork
generated for this project, shipped as a repo asset
(``assets/gm_logo.png``) and injected by the composition root as a data
URI, so the shell's standing rule survives intact: no remote request of
any kind. It rides the same circle clip and the same 4.5s pulse the
hand-drawn orb had; the painted seam orb stays in the module as the
fallback when the asset is absent.

## D-108 - The signals program's O-batch resolves to the builder's recommendations
**All eight owner-gated questions of the signals integration program were
put to the Product Owner in one batch (2026-08-23) and answered "No
preference" on every one — the recommendations proceed under standing
authorization (the D-103 posture).** O1: the never-built BvP flag design
from D-023 is RETIRED — the signals list's exclusion stands and no BvP
surface will be built. O2: spray sectors for the dominant-air-field read
are ±15° (echoing D-023's provisional pull cone). O3: projection systems
for call-ups are skipped entirely (the host pin and D-063(b) stand). O4:
SP-3's pitcher vulnerability reads join the Arms tab AS COLUMNS — wide
and sortable, nothing hidden behind clicks. O5: humidity shows always
beside temperature on the Conditions tab. O6: the builder captures the 30
park orientation bearings from Clem's Baseball, with the capture
provenance named in the pinned table's record. O7: the platoon-bench tag
rule is the strict one — a bench hitter (not in today's lineup) at the
SAME listed position who bats from the OPPOSITE side; switch-hitters
qualify against either side; ties break by roster order. O8: the emphasis
lines ratify as proposed — x-gap tag fires at |gap| ≥ .030; high-K at
K% ≥ 27%; low-whiff arm at arsenal-wide whiff ≤ 22%; contact-first at
squared-up ≥ 35% AND bat speed ≥ 72 mph; ground-ball profile at air
allowed ≤ 50% (high ≥ 62%); the lineup-vs-hand caption needs ≥ 100 AB in
L30. Each line is printed on the surface that uses it (the D-079
pattern).

## D-109 - SP-1: air spray both ways, SwSp% displayed, contact shape, context tags
**(Same program; the ticket's displays ship under the O-8 lines ratified
in D-108.)** Oppo Air % joins the form row and the Matchups grid — the
exact mirror of the shipped pull test over the identical measurable-air
denominator, spray exactly 0 counting as neither, with one shared spray
helper so the mirrors cannot drift. This amends the D-068 metric set, as
D-102's removal of xwOBA did. SwSp% (sweet-spot share, launch angle
8–32°) joins the form row beside it — computed per window and graded
(0.7 pts) from the start, displayed for the first time. The Matchups
season view renders Oppo Air % as the same reason-styled dash Pull Air %
shows, the season-toggle help naming the absence the same way ("no
published source"). The arsenal breakup table's batter half gains
per-pitch EV and Air% — computed pipeline-side onto PitchLine, carrying
the ratified 10-BBE pitch-type floor with the INSUFFICIENT treatment
below it and dashes on empty denominators; these are the standing
nominations for the owner's final metric-columns answer, and his list
supersedes when it arrives. The Sluggers tags box widens from advisories
to advisory-plus-context on the already A/S-filtered shortlist: the
ordinal lineup slot ("bats 1st", "bats 2nd (est.)" — never "1th"), the
high-K profile tag at the ratified 27% line, and the high-K-bat vs
low-whiff-arm interaction tag when the opposing starter's arsenal-wide
whiff (pitch-weighted over his season lines) is ≤ 22% — the interaction
tag supersedes the profile tag, never both. Batter K% is strikeouts over
season plate appearances, computed pipeline-side (the strikeouts count
was parsed and unread until now). The form caption names the Oppo Air %
denominator verbatim from the spec, and the breakup caption prints the
10-BBE floor.


## D-110 - SP-2: season regression gaps, sprint speed, BABIP, contact-first

**(Same program; displays ship under the O-8 lines ratified in D-108.)**
The dormant expected-statistics adapter is revived and its parse widened
from {player_id, pa, bip, est_woba} to the board's full actual-vs-expected
set — ba, slg, woba beside est_ba, est_slg, est_woba (column names verified
live 2026-08; every column required, so a renamed or dropped column fails
the whole board cleanly, never a wrong number). xISO is the board's own
est_slg - est_ba; the gap xISO-ISO subtracts the board's actual slg - ba,
and xwOBA-wOBA subtracts the board's actual woba from est_woba — the
season-wOBA source question answered by taking BOTH sides of each gap
from the one board, so denominators match by construction; this is named
in the surface captions as the provenance note. The Matchups season view
alone gains the two gap columns, signed three-digit with the PA sample
("+.041 (412 PA)"), placed beside their sibling columns, reason-styled
when the board has no row; the L30 view is unchanged and the scope
caption says the gaps are season-scope. The Sluggers x-gap tag —
"x-gap: xISO {±.xxx}, xwOBA {±.xxx} (season, {pa} PA)" — fires when
EITHER gap's absolute value reaches the ratified .030 line, both values
always printed. The dialog gains a Season profile block: BABIP off the
season counting line as (H-HR)/(AB-K-HR+SF) — sacFlies joins the
season-hitting parse for the denominator's SF term — with the two
absences named separately (no counting line vs an empty denominator),
and the sprint-speed line with its league-general wording, sourced from
a new sprint-speed leaderboard fetch on the same host with the same
board shape. The contact-first tag — "contact-first profile: squared-up
{s}% ({n} swings), bat speed {b} mph" — fires at the ratified paired
lines (squared-up ≥ 35% of competitive swings AND bat speed ≥ 72 mph),
sourced from a new season contact board in the bat-tracking family
(squared_up_per_swing over swings_competitive; verified live 2026-08 —
the attack-angle board carries no squared-up column, and the contact
board publishes one row per batter, no side split). Net new steady-state
cost: +3 board-cached calls per build. Every rate carries its sample,
every absence names its reason, and every firing line is printed in the
Sluggers caption (the D-079 pattern). Signed rates render ASCII
("+.041") because the lint gate bars the typographic minus in source.


## D-111 - starter header cards, stadium panel, Arms metrics, humidity

**(PO's Matchups/Arms redesign, ticket 1 of 2; PO delegated the ISO
choice — ISO paired with expected ISO, both off the one expected board,
was accepted.)** Each Matchups game expander now opens with the two
expected starters as header cards flanking the drawn stadium. The card's
overall row reads the season boards by default — wOBA and xwOBA against
plus ISO and expected ISO off a new expected-statistics pitcher board
(same metric columns as the batter board plus era/xera, which the read
ignores; every parsed column required, verified live 2026-08), barrel
rate and average launch angle against off a new Statcast pitcher board
(attempts/avg_hit_angle/barrels/fbld/gb, verified live 2026-08), and
HR/9 off the statsapi season line — homeRuns joins the season-pitching
parse, and the innings conversion treats the notation's fractional digit
as OUTS (.1/.2), never tenths, with anything outside the notation a
named absence. A per-game toggle flips the overall row to the starter's
last 30 days of kept pitch events; the two side rows always read that
L30 window ("vs L (L30)", "vs R (L30)"). L30 publishes no innings and no
per-event expected SLG, so HR/9 and xISO name their absences on L30 rows
and the HR count shows instead. Green marks ONLY the digest's
pitcher-vulnerability reads — HR/9 >= 1.4 and wOBA above xwOBA, no
invented bands — and below the ratified floors (80 BF / 40 BBE on a side
row, 15 BBE on contact reads) the values stay visible under the amber
INSUFFICIENT advisory, never hidden. Every sample rides the Scope label
beside the rates it basis. The stadium panel draws the field with its
live wind flow and adds detail lines: the hand-split HR park factors
with their PA samples, and temperature beside HUMIDITY — relative
humidity now flows end to end (NWS hourly relativeHumidity object, a new
optional WeatherForecast field validated 0..100, a humidity_for reader
injected at the composition root, GameCard.relative_humidity_percent),
None for a roofed venue or an unpublished reading, never an invented
number. The Arms tab gains the same starter metrics as season columns
(PA, BBE, wOBA, xwOBA, HR, HR/9, BRL%, LA, ISO, xISO, plus Air % — the
fly-ball-plus-line-drive share against, the ground-ball profile's air
mirror) with the same L30 toggle, the same green and amber rules, and
every firing line printed in the surface caption (the D-079 pattern).
Net new steady-state cost: +2 board-cached calls per build.

**(Live-verify correction, same PR — caught before merge.)** The
pre-merge live board exposed two faults the unit gate could not: the
Statcast pitcher board's fbld/gb columns are FB/LD and GB exit
velocities in mph, NOT air/ground counts, and the misread quietly
dropped 809 of 818 rows (decimal EV strings failing the int parse), so
every starter's season reads fell back to an invented-empty board —
0 BBE beside real wOBA figures — with no diagnostic. The air/ground
fields are removed: no season air-ball split against exists, so the
season Air % names its absence and the share reads the L30 events,
whose bb_type split is real. And the board parser now FAILS any board
that cannot parse at least half its rows ("only N of M rows parsed"),
so a changed payload can never shrink a board into silent absences
again.

## D-112 - slate "today" runs on the viewer's US timezone

**(PO report 2026-08-24: at 7pm Arizona the landing page treated
tomorrow as today and showed tomorrow's batters for the slate.)** The
cloud host keeps UTC, so a bare date.today() rolls the slate forward in
the early evening for every US viewer. The slate's "today" — the date
picker's default and bounds, the today/yesterday/tomorrow labels, and
the backtest's "last N days" — now reads America/Phoenix, the PO's
home zone: MST, UTC-7 year-round with no daylight-saving rule, so a
fixed -7 offset is the exact fallback when a host lacks the tz
database (ZoneInfoNotFoundError). The date picker's help names the
zone. Moving the slate to another US zone is a one-word switch
(_SLATE_ZONE).

## D-113 - robbed-HR column replaces the +350 ft column

**(PO directive 2026-08-24: swap the "+350 ft" grid column for "robbed
home runs" — balls hit 375+ feet — based off the last 7 days. This
supersedes D-090's distance read; D-090's text stands unchanged.)** A
robbed HR is a projected-375+ ft batted ball that STAYED IN THE PARK —
the play's result was not a home run, since a ball that left was robbed
of nothing. The count reads the batter's whole last-7-days kept event
record (the window the PO named), a deliberately different basis from
the row's L30-versus-the-mix scope, so it is computed pipeline-side
from the batter's full event pool and injected into the grid line; the
matchups scope caption names the exception. It is a raw count, never a
rate — one robbed ball a week is a regular's pace and zero is a real
observation, not a cold streak — and it is None, a named absence, only
when the event record itself failed. The season scope keeps the named
absence it always had: no season source publishes per-event distances.

## D-114 - v2.2 batch 1: split air-ball floors, HR/9 re-line, colored tag columns, pitcher-side tags

**(PO directive 2026-08-23, v2.2 thresholds doc: apply the refinements.
This is the first batch — floors, the HR/9 line, the tag coloring, and
the pitcher-side tags; the batter/situational tags follow in the next
entry.)** Four moves, each printed on its surface per the D-079 pattern.
(1) The air-ball sample floor splits by window — 8 air balls at L7, 15
at L14+ — ratified in the v2.2 doc ("~10 air balls is a normal week; 15
was unreachable for everyday regulars"); this partially supersedes
D-068, logged append-only per the doc's governance note, D-068's text
unchanged. (2) The pitcher-vulnerability green line moves from HR/9 1.4
to v2.2's season target 1.50 on the starter cards and Arms surfaces.
(3) The shortlist's single tags box becomes three columns — For HR
(green boosters), Against HR (red vetoes, the new veto style), and the
neutral Tags advisories — v2.2's green-good/red-bad tag coloring; the
exit-velo event sheet is untouched. (4) The pitcher-side tags land with
their v2.2 firing lines: low-whiff arm (arsenal whiff ≤ 20%, season),
the K interaction re-lined (unlock needs K% ≥ 22% AND the low-whiff
arm; without that matchup K% ≥ 28% reads binary and ≥ 30% is the
high-K caution — superseding D-109's 27%/22% lines), the ground-ball
profile (L30 ground-ball share ≥ 50%, extreme ≥ 55%, of classified BBE
— or season avg launch angle allowed ≤ 8°), the HR/9 suppressor
(≤ 0.80 season), the gas profile (HR/9 ≥ 1.50 season with the L30
ground-ball share under 40%), and the fly-vulnerable flag (season avg
LA allowed ≥ 18°). The season boards publish no ground-ball split
against (D-111's live lesson), so the GB% halves read the L30 kept-event
record and say so in the tag text; HR/FB is likewise unpublished, so
FB_VULNERABLE flies on the launch-angle half only. HR/9 stays a
season-scope read because the L30 window publishes no innings. Every
firing line rides in the Sluggers caption. Open items reported to the
PO, not stopped for: the temperature component cap (config decision),
the pulled-barrels raw-count display (doc says pending PO ratify), and
the GMN pull-air league baseline (awaits the raw Savant export).

## D-115 - v2.2 batch 2: the batter-side and situational tags

**(PO directive 2026-08-23, v2.2 thresholds doc, batch 2 of the tag
dictionary.)** The batter-side tags land with their v2.2 firing lines,
each printed in the Sluggers caption. The x-gap flag becomes an
under-performance read only — xISO-ISO >= +.050 or xwOBA-wOBA >= +.015,
riding the green column — superseding D-110's .030 absolute-value
neutral tag (D-110's text stands). Barrel elite: barrel% >= 15 over
>= 50 season BBE, shipped as `barrel {x}% ({n} BBE)`. The power
profile: season avg EV >= 91 mph AND bat speed >= 73 mph, both. The
contact-first tag flips to v2.2's veto — squared-up >= 35% of
competitive swings with a sub-70 mph bat speed is a contact profile,
not power — superseding D-110's >= 72 mph context tag. A top-5 lineup
slot is a booster (the 4-5 PA tier) and leadoff adds the extra-look
tag; slots 6-9 stay neutral advisories. Platoon advantage reads the
batter's resolved side against the starter's throwing hand; the
caption carries the +28/+16 long-run averages and the 2025 anomaly
caveat (LHP held RHB below league wOBA for the first time in 20+
years, so it stays a contact-quality signal). The robbed tag aligns to
D-113's column definition (375+ ft balls that stayed in the park,
last 7 days — the PO's newer definition wins over the doc's
385-409 ft band): a raw count, one or more fires it, zero stays
silent. Actual-over-expected (wOBA-xwOBA >= ~.040 with sprint
>= 28 ft/s) rides the NEUTRAL column, not the green one the doc's
section heading implies: the doc's own text marks it context-only with
no automatic speed attribution, and the green/red columns are reserved
for reads that argue for or against the home run — logged here so the
deviation is explicit. The power-badge eligibility gate follows the
v2.2 rule (season scope, denominator-based): both power tags gate on
>= 50 season BBE. Still queued: the park/weather tags (need the game
passed into the tag builder), the pulled-barrels form count, and the
MiLB call-up tag.

## D-116 - temperature cap, GB% placement, and the pulled-barrels count

**(PO rulings 2026-08-24, answering the three open v2.2 items.)**
(1) **Temperature: "cap for now."** The weather component adopts the
v2.2-ratified bucket edges (<45 / 45-64 / 65-74 / 75-84 / 85-89 / 90+)
with the award capped at the old 1.0 component max — the 85+ bands are
labels only at this cap; raising the max stays available as a config
change whenever the PO wants it. (2) **GB% placement: "only in Arms,
L30 only."** The GB% number appears exactly one place — the Arms tab's
L30 starter-metrics view gains a GB % column (ground-ball share of the
window's classified batted balls, with its own 15-BBE floor read on
the classified count). The season scope does not carry the column at
all, per the PO's pick — no season board publishes the split (D-111's
live lesson). The shortlist's ground-ball-profile and gas tags keep
their firing conditions (the share still decides) but never quote the
GB% number — the profile tag reads "(L30 record)" or the season
launch-angle line, the gas tag quotes HR/9 only. (3) **Pulled
barrels**, ratified by the same message: a raw count, never a rate,
shown in the batter detail popup's form table as `2 (41 BBE)` with the
L14 fallback naming its window. A pulled barrel is a barrel (launch
classification 6) whose spray points to the batter's pull side; 0 over
a real week is a real observation (a regular averages ~1 barrel a
week), and only a window pair with no measurable air ball reads the
absence. The count's source is the pitch-by-pitch event log — the
same record the form windows already read — and its use is wind/park
alignment work: pulled barrels are the balls that leave yard most
often, so they are the ones a pull-side wind or park factor speaks to.

## D-117 - the glossary lives behind a "?" button beside Backtest

**(PO directive 2026-08-24: "create a glossary that can be accessed
through a question mark button next to back text" — the Backtest
button in the header.)** The glossary itself is the PO-supplied
Glossary v2.1 document, kept verbatim as `GLOSSARY.md` at the repo
root so its plain-language wording can be revised without touching
code (and so its typographic quotes never trip the repo's
ambiguous-unicode lint). The app reads the file at runtime through a
cached loader; a missing file degrades to a named absence ("The
glossary file is not available in this deployment."), never a crash —
absence first, as everywhere else. The header's action column splits
into two: the view button (Backtest / ← Board) and a "?" button that
opens the glossary in a wide dialog. The "?" rides on both views, so
the metric meanings are reachable while auditing grades too. The
glossary answers what the metric means and why it matters; the
surfaces themselves still carry the firing math per D-079 — the two
layers never duplicate each other's job.

## D-118 - the park and weather shortlist tags

**(v2.2 tag dictionary, planned for D-116 and displaced by the PO's
GB%/pulled-barrels rulings — shipped now.)** Four game-state reads join
the shortlist's tag columns, fired off the game the batter plays in:
**park boost** (green) at a batter-side home-run factor ≥ 110 (strong
≥ 115) and **wrong-side park** (red) at ≤ 90 (strong ≤ 85), both read
off the hand-split factor for the batter's resolved side (D-065 — a
switch hitter's side resolves against the starter's hand, so his tag
quotes the side he will actually bat from); **heat boost** (green) at
≥ 85°F (strong ≥ 90°F) and **cold suppress** (red) below 45°F, both
open-air only — a roofed stadium is the indoor neutral value and fires
no weather tag at any temperature. A missing factor or temperature is
a silent tag, never an invented one (absence first). Two honest
limits, stated where they belong: the tags quote the factor and the
temperature, never a verdict about them (D-015/D-017); and
COLD_SUPPRESS's severe variant (< 38°F with the wind in) stays
unshipped — "wind in" needs the park-orientation table (SP-4), and
without it there is no honest read. The firing lines print in the
Sluggers caption with the rest (D-079). The tag builder now takes the
game as a keyword argument; without one the park/weather reads stay
silent, which keeps the unit fixtures two-argument.

## D-119 - the wind shortlist tags and the park-orientation table

**(v2.2 tag dictionary, SP-4 — shipped.)** The park-orientation table
lands: all 22 open-air venues carry their home-to-center-field axis in
whole degrees true, measured 2026-08-24 from ESRI World Imagery tiles
(north-up by construction, ground-square pixels via the
cos(latitude)-corrected bbox; home-to-mound's known 60'6" calibrates
each capture, and the ESRI street map of the identical bbox
cross-validated the method at three parks). Five published compass
readings the imagery contradicts (Target, Camden, PNC, Oracle,
Comerica) are recorded as such in the module's provenance; degraded
captures (a tarped Kauffman infield, construction at Angel, a patchy
Oracle) name the fallback they fell back to. The eight roofed venues
carry no row **by design** — the roof state is not sourced in v1
(D-073), so no axis applies indoors and a lookup that finds nothing
says exactly that. The GameCard now carries the axis and the parsed
wind from-direction (degrees true, from the NWS compass text); a
roofed venue, an unmapped park, or an unparseable reading degrades to
None, never a guessed bearing.

Four wind reads join the shortlist's tag columns, each resolving the
forecast against the batter's **dominant air field** — the largest
spray third in his form record (pull / center / oppo, L7 falling back
to L14 under the ratified 8/15-air-ball floors), because the season
view publishes no spray read (D-116). The pull corner sits 30° off the
park axis toward the batter's pull side, center rides the axis, oppo
mirrors. **Wind assist** (green) at ≥ 8 mph resolved out toward his
field (strong ≥ 12); **wind kill** (red) at ≥ 10 mph resolved in from
it, or ≥ 8 mph resolved out to the opposite corner — the v2.2 table
names no number for the opposing case, so it borrows the assist line
and the Sluggers caption says so. First match wins; a center-dominant
spray has no opposite corner and reads only the straight out/in lines.
**Cold suppress severe** (red) below 38°F with an in-wind ≥ 5 mph
along the axis replaces the plain cold tag — the in-axis resolution
needs no spray record, since a cold in-wind knocks the ball down
wherever it was headed (this closes the gap D-118 named). A roof, an
unmeasured axis, an unparseable compass text, or a spray record under
the floors is a silent tag, never an invented one (absence first). The
tags quote the resolved wind and the field, never a verdict
(D-015/D-017); every firing line prints in the Sluggers caption
(D-079). Live-verified on the 2026-08-24 slate: a light-wind night
(5-7 mph at the four open-air games with a reading) fired no wind tag
anywhere — the computed expectation, confirmed against the served
board — while the axis geometry resolved correctly on real sprays (an
oppo-dominant right-hander read as "right field" at Comerica).

## D-120 - the spray-alignment shortlist tags

**(v2.2 tag dictionary, SP-4 — shipped.)** Two reads join the shortlist's
green column, fired where the batter's air contact actually goes and the
park actually boosts. **Pull-air match** at a pull-air share ≥ 40% with
the same-side home-run factor at the park-boost line (≥ 110) — his air
balls go where the park helps his own side. **Oppo-air match** at an
oppo-air share strictly over 20% read against the OPPOSITE-side factor —
the v2.2 dictionary's Walker exception: an oppo-power bat reads as the
other hand for the park, because his damaging air contact goes to that
field, so a right-hander with oppo power is checked against the LHB
factor, never the RHB one. A `wind {x} mph out to {field}` rider joins
either tag when the forecast also resolves out to the matching field at
the wind-assist line (D-119's geometry, reused). The spray record is the
form section's floored pull/oppo shares, as for the wind reads; an
insufficient record, a neutral factor, or a missing game is a silent
tag, never an invented one (absence first). The tags quote the share,
its sample and window, the factor, and the wind — never a verdict
(D-015/D-017); every firing line prints in the Sluggers caption (D-079).

One convention, stated plainly because it shapes what the numbers mean:
the shipped pull/oppo air shares are D-071's **signed halves** over
measurable air balls (a dead-center ball claims no direction), the same
metrics the v2.2 glossary defines — so the 40/20 lines apply to halves,
and the park-factor gate does the selective work (a 40% pull half is
common; a ≥ 110 factor is not). A true pull/straight/oppo thirds record
would be a change to ratified surfaces, and it is not implied by the
v2.2 documents. D-119's caption language is corrected along the way:
the wind read resolves against the larger **half** of his measurable
air balls, not a "third" the record does not publish. Live-verified on
the 2026-08-24 slate: no shortlist batter aligned (spray shares present
but no boost-side factor, or an insufficient record, or a roof), and no
tag fired — the computed expectation, confirmed against the served
board.

## D-121 - the Conditions tab weather surface

**(v2.2 weather/environment — shipped.)** The Conditions tab now carries
the full weather reading, not just a bare temperature. Each game shows
the **temperature band** its reading lands in from the ratified v2.2 set
(ratified 2026-08-23): <45 → 0 (cold suppression) · 45-64 → 0.25 ·
65-74 → 0.5 · 75-84 → 1 · 85-89 → 1.25 · ≥90 humidity-supported → 1.5 —
the edges printed on the surface per D-079, with the award's cap at the
component max 1.0 named on the hot bands (the PO's 2026-08-24 "cap for
now" ruling, already in the config since D-116: the 85+ bands grade 1,
and the labels keep the raw band values visible). The ≥90 max band's
humidity support has no ratified line, so it is reported, never
resolved. **Humidity** joins as a plain percentage column — the v2.2
secondary modifier, never a standalone badge. **Wind** joins as the raw
forecast reading (speed and compass); the resolved assist/kill reads
stay on the Sluggers tags where the batter context lives (D-119). A
roofed venue's cell now reads "72°F assumed" in the muted reason style —
the assumption labelled in the cell itself, never dressed as a forecast
(the grading layer has fed that constant since D-116); a missing
open-air reading names the source gap, and a roofed venue's
humidity/wind read "roofed — not sourced", because the pipeline sources
neither indoors. Live-verified on the 2026-08-24 slate: eight games
banded from real readings (0.25 to 1), two named their NWS gap, three
roofed venues carried the labelled assumption.

## D-122 - wind receptiveness on the Conditions tab

**(D-082's colour rule, shipped as a display read.)** The Conditions
tab gains a **Wind recept.** column and a coloured Wind cell, from the
Ballpark Pal wind-receptiveness capture the PO supplied (model years
2023-2025, adjusted for yearly ball changes; printout captured
2026-08-21 and committed at docs/reference/ballpark-pal-park-factors.md).
The capture doc's own gate for entering the tree was "a DECISIONS.md
entry and a SourceRecord first" — this entry is the former; the module
ships the latter (MANUAL_EXPORT, digest-pinned 30-row CSV keyed by
venue slug, verified byte count and sha256 before any row is read, the
same pattern as the Savant park-factor snapshot). The seam guard that
bans the source's name anywhere under src/ is amended to exempt
exactly that one module — the provenance record cannot name its source
otherwise — with the amendment recorded in the test itself.

The read: the column quotes the park's **Overall** figure; the Wind
cell's colour is **direction-specific** — an out-wind judges the
park's out receptiveness, an in-wind the in figure — because the
model's signs differ by direction at the same park (Angel Stadium:
out -2.36, in +3.32; Wrigley: both positive). D-082's rule: green
when the wind in its current direction helps the HR environment at a
wind-receptive park, red when it hurts, neutral when the park barely
notices wind or the breeze is calm. **Neither cut has a ratified
number**, so the build lines are chosen and disclosed on the surface
(D-079): |directional receptiveness| at or past **1** (the capture runs
-3.2 to 9.2; under 1 is the barely-affected band) and **≥ 4 mph**
resolved along the park axis (the source's own calmest speed bucket
is 0-3). Display only — receptiveness never grades; the caption says so
in as many words. The game card now carries the venue slug so the view
joins the snapshot without re-deriving it. Absence semantics hold
throughout: an uncovered venue reads "not covered", a missing wind
reading names the source gap, and an unresolved breeze colours nothing.

Live-verified on the 2026-08-24 slate: all ten games render the column
from the pinned snapshot, and every Wind cell stays honestly neutral —
Comerica's 13 mph west wind resolves 8.2 mph out along the axis,
but its out receptiveness is 0.36, under the line despite an Overall of
5.05: the direction-specific read working as intended, where the
Overall figure alone would have coloured it.

## D-123 - SP-3 remainder: workload facts, stuff-drift caption, thin-sample caption

**(The signals program's SP-3 leftovers — shipped.)** Three raw-fact
reads close out the pitcher ticket.

**Workload lines** (Arms columns + dialog echo): "Last start" carries
"{p} pitches, {d} days ago" and "Last 3 starts" the newest-first counts,
off a pitching variant of the game-log hydrate (group=pitching — the old
constant hardcoded hitting; the pitch-count key `numberOfPitches` and
the `gamesStarted` flag were verified against the live API before the
parse shipped). The v2.2 firing line stands: a last start at 100+
pitches is named a workload flag — appended to the fact in the same
cell, never a colour, never a cap claim; the Arms caption prints the
line and the no-cap rule (a cap is only a cap if the team announced
one). Fewer than three counts means fewer starts in the record, and the
record's reach is 31 days — the same month the L30 surfaces read, so
the start count and the hand splits never disagree about the window. No
start in the lookback reads "no start record in the lookback window" in
the muted reason style. Relief outings never count as starts; the log
lists completed games only, so today's outing neither flags nor
clears.

**Stuff-drift caption** (the dialog, under the arsenal breakup): the
primary pitch's season whiff and usage shares off the arsenal board
against the same shares computed from the kept window events — "primary
pitch {name}: whiff {w}% season → {w}% L30 ({n} pitches L30), usage {u}%
→ {u}%". The primary pitch is the board's top-usage row. A window
whiff with no swings names its absence ("no swings at it"); a primary
pitch never thrown in the window is an honest 0% usage, not a hidden
row. This caption IS the v2.2 MIRAGE_CAUTION — the spec's ruling
stands: the mirage caution ships as drift facts alone, with no mirage
or decay wording on screen. The velocity/movement leg was evaluated and
deliberately not adopted: the arsenal board publishes no velocity, so no
season baseline exists for a delta, and a lone window velocity would
invite the reader to invent the comparison — an invented baseline is
worse than a named gap.

**Thin-sample caption** (the starter header card on Matchups): when the
window's record spans at most two starts, the card says so beside
the L30 hand splits — "L30 record: {n} start(s) — a thin sample: check
who he faced" — the v2.2 caution verbatim.

All three compute pipeline-side (the view formats, never derives —
GMF-008) and ride the pitcher card. Live-verified on the 2026-08-24
slate: 19 of 20 probables carry workload records (Jose Urquidy, no
starts in the window, names the absence); Logan Gilbert (100 pitches)
and Chase Burns (104) carry the named workload flag; every drift
caption renders both shares with samples; no probable spans two or
fewer starts, so the thin-sample caption stays correctly silent.


## D-124 - the batter-table remainder: star convention, launch angle, Form Score placeholder, hover notes

**(The PO's finish-the-Matchups-and-Sluggers-tabs ticket — shipped.)**
The PO's starred-column mock was unrecoverable (no copy in any session
file); asked twice (the mock's handling, and the per-pitch season-LA
fallback), the PO answered "No preference" both times — under the
D-103/D-108 standing authorization the builder's recommendations
shipped, disclosed here.

**The star convention (Matchups grid).** A ★ on a column header marks
a metric that carries a ratified v2.2 firing line, every line printed
in the tab caption (D-079's print rule). The L30 view stars Pull Air %
(≥ 40% of measurable air balls with a boosting same-side factor reads
the pull-air match) and Oppo Air % (over 20% read against the
opposite-side factor) — the D-120 spray reads. The season view stars EV
(the power profile: ≥ 91 mph with a bat speed ≥ 73 mph), xISO-ISO
(≥ +.050) and xwOBA-wOBA (≥ +.015) — the D-115 reads. The star is a
marker, never emphasis: no colour fires on the grid. Deliberately
unstarred: Barrel/PA % (the ratified barrel-elite line reads barrel%
per BBE over ≥ 50 season BBE — not the grid's per-PA figure, and
starring a sibling metric would misstate the line), Swing-Str %, xwOBA,
AVG/SLG/ISO and Robbed HR (no batter-side firing line), and LA (below).

**Season launch angle (Matchups, season view only).** The season
Statcast batter board carries `avg_hit_angle` — verified live against
the 2026 board before the parse shipped, the same column the pitcher
board has carried since D-111. It parses as a required column: a rename
or drop fails the whole board cleanly, never a wrong number. The column
sits after EV, one decimal with the degree sign, muted "—" without a
board row. It is deliberately unstarred context: v2.2's HR launch floor
reads the SHARE of contact above 18°, never the average, and the season
boards publish no share — the caption and the hover definition both say
so. The L30 view omits the column (the mix scope computes no
batter-level LA; the dialog carries the window's per-pitch read). The
grid keeps its plain-value convention — no amber on the grid; the
sample discipline lives in the dialog and the form section.

**Per-pitch launch angle (batter dialog).** The arsenal breakup's
batter half gains LA between EV and Air%: the window record's mean
launch angle against that pitch, over the same measured-event base
D-109's EV reads (a tracked foul is a measured event; it never swells
the BBE denominators, which stay classification-based). The window
label heads the half, so the read is honestly scoped. The arsenal board
publishes no per-pitch LA, so the pitcher half has none and the
season-scope line leaves the field None. The ratified 10-BBE
pitch-type floor's INSUFFICIENT note rides the value exactly as EV's
does. The caption prints the v2.2 per-pitch reads — 23°+ against a
pitch is strong, 30° elite, 18° the HR launch floor (below it, home
runs need ~115 mph EV) — with the average-is-context caution. The
fallback question (per-pitch season LA has no source anywhere) was the
PO's second "No preference": the window-record read shipped, labelled.

**Form Score placeholder (Sluggers).** A "Form Score" column between
Grade and Park factor, every cell the muted dash, captioned: v2.2
ratifies the form reads but no rollup formula, so the dash holds until
one is — never an invented number. The shortlist is the rollup's
future home; the Matchups grid stays lean per D-098.

**Hover notes (both surfaces).** Every column header carries a one-line
glossary-derived definition via column config help. One source of
truth: the star-rename maps feed both the grid cells and the help
config, and entries naming columns a view does not carry drop out.

Live-verified on the 2026-08-24 slate: 15 A/S batters dash the
placeholder; the L30 grids star the spray shares; the season view's LA
values match the Statcast board (Caminero 9.2°, Schwarber 21.5°); the
dialog renders the per-pitch LA with its floor notes (Valdez's sinker
7.3° · n=2 · INSUFFICIENT); the hover definitions render in both views'
column config, locked by a suite test. Full gate green on both Pythons
(3408 passed, 1 skipped), consistency check clean, all four showcase
runners clean.

## D-125 - regression reads leave the grid: Sluggers tags with reliability bands and why-riders

**Decided:** 2026-08-25 · **Status:** shipped (staging)

The PO's change list (uploaded 2026-08-25, items 43-44) settled the open
x-gap question his earlier "No preference" had left to the recommended
option: "Instead of showing the difference for xISO-ISO and xwOBA-wOBA,
remove them and make tags for regression or whatever term you think best,
only tag batters when they meet the criteria (these tags will only show in
sluggers tab)" — and "Keep iso and xwoba column." This supersedes the
grid-column half of the keep-plus-band plan; the band-and-rider half
ships inside the tags, which are now the gaps' only surface.

**The grid change (Matchups).** The xISO-ISO and xwOBA-wOBA columns are
gone from the season view (the L30 view never carried them), star
entries, hover definitions and all; ISO and xwOBA themselves stay, and
the season LA keeps its place after EV. The season view's only starred
metric is now EV. The captions say where the gaps went.

**The tags (Sluggers, unchanged columns).** The D-115 under-performance
flag keeps its v2.2 lines (xISO-ISO >= +.050 or xwOBA-wOBA >= +.015) and
now carries the reliability band off its season sample — thin under
200 PA, readable 200-399, established 400+ — so a May gap and an August
gap stop reading alike. **Disclosure:** the two band lines are builder
judgment informed by the ratified stabilization anchors (ISO ~160 AB,
BB% ~120 PA — an L30 window is too noisy for a gap read); they are NOT
v2.2 firing lines, and both print in the captions per D-079. A
suppressive home park attaches a why-rider — "home park HR factor 78
(LHB) can hold the gap open — x-stats are park-neutral" — read off the
pinned per-handedness snapshot at the batter's HOME venue (half the
season sample lives there; tonight's venue factor remains the D-118
tag's business). The D-110 over-performance advisory keeps its ~.040
gate and now names every structural reason present — sprint >= 28 ft/s,
a pull-heavy air profile (>= 40% of measurable air balls, sufficient
record only), a boosting home park (HR factor >= 110) — closing with the
park-neutral-and-direction-blind note. No reason present, no tag: an
over-performance with no identified driver says nothing rather than
implying regression due.

Live-verified on the 2026-08-24 slate: all 20 batter grids in both views
carry no gap column (ISO/xwOBA stay; LA after EV); Vargas reads "x-gap:
xISO +.006, xwOBA +.022 (season, 564 PA · established); home park HR
factor 89 (RHB) can hold the gap open", Nootbaar "(season, 234 PA ·
readable); home park HR factor 78 (LHB)...", Bohm carries no rider (his
home park boosts, not suppresses), and Valdez — over the .040 gate with
a 27.9 ft/s sprint, an insufficient spray record, and a suppressive home
park — correctly carries no over-performance tag. Full gate green on
both Pythons (3409 passed, 1 skipped), consistency check clean, all four
showcase runners clean.

## D-126 - Sluggers becomes bubble rows: For/Against columns out, tags as hover pills, weather in field words, the $ carries its date

**Decided:** 2026-08-25 · **Status:** shipped (staging)

Four items off the PO's change list (uploaded 2026-08-25) land together
because they all reshape the same surface.

**Items 7-8 — the columns.** The For-HR and Against-HR columns are gone
("these were a fluke") and the row reorders to the PO's sequence:
Batter, HR, Team, Versus, Tags, Weather, Park factor, Form Score,
Grade. Nothing the two columns said is lost — every read already lived
as a tag string, so the columns' semantics survive as pill COLOR: green
bubbles argue for the home run, red against it, grey the notes. The
caption and the Tags header hover say so.

**Item 9 — tags as bubbles.** A dataframe cell cannot render a hoverable
bubble, so the shortlist leaves st.dataframe for a per-row column layout:
each tag is a pill span whose native hover carries the full read with
its samples, and each column header is a span whose hover carries its
one-line definition — which also satisfies the list's hover-every-title
item for this tab. Row selection is gone with the grid; a **More**
button per row opens the same batter detail the row click used to. The
pill label is the tag's own name (the head before its colon, trimmed to
fit); the full text rides the hover, never truncated there.

**Item 10 — weather you can use.** The old cell named a compass
direction and left the geometry to the reader. The wind now resolves on
the park's measured home-plate-to-center axis into field words — eight
45-degree sectors: out to center/left/right, in to home, in from
left/right, left to right, right to left (`wind_field_words` in
`greenmachine.live.wind`, sweep-verified across the full rotation and
at every sector boundary). The cell reads "84°F · 12 mph out to right";
a park with no measured axis falls back to the compass point, a calm
reading says calm, a roofed stadium reads the indoor neutral value, and
a missing feed names itself ("source unavailable") — the absence rules
are untouched.

**Item 49 — the Schwarber $.** Investigation finding: not a bug. D-094's
tag means "homered in his most recent completed game day," and Schwarber
had homered the night before the slate the PO saw it on — the tag was
telling the truth and reading like "homered tonight." The fix is a
date-stamp, not a logic change: the pipeline field now carries the
tagging game day's ISO date (or None), the tab renders a neon **$8/23**,
and the hover says which game it was and that the tag clears once his
next game goes final. A pre-game read can no longer pass last night's
homer off as tonight's.

**Held:** Form Score stays a clearly-marked placeholder dash — v2.2
ratifies no rollup formula, so the dash holds until one exists rather
than inventing a number (disclosed to the PO).

Live-verified on the 2026-08-24 slate with the live NWS adapter: fifteen
A/S rows render as bubbles (Caminero's green "power profile"/"platoon
advantage" against red "air allowed"; Vargas keeps his D-125 "x-gap"
green and "wrong-side park" red as pills), the weather column speaks
field words off real readings ("66°F · 3 mph out to center" at Comerica,
"70°F · 5 mph in from left" at Guaranteed Rate, "82°F · 5 mph out to
left" at Angel Stadium, roofed venues neutral), the date-stamped $
renders with its hover, and More opens the batter detail. Full gate
green on both Pythons (3417 passed, 1 skipped), consistency check
clean, all four showcase runners clean.

## D-127 - every metric cell wears a researched color: six bands, league baselines, hover definitions on every table

**Decided:** 2026-08-25 · **Status:** shipped (staging)

The change list's headline items 1-3 (uploaded 2026-08-25): "color-grade
all cells with thresholds — dark red = very poor for HRs, dark green =
elite," at least three shades of each "via bands/buckets," "research
baselines where thresholds are missing," and "hover every column title
for a definition."

**The scale.** Six opaque fills — three greens (dark at elite), three
reds (dark at very poor) — with the unfilled theme cell as the neutral
middle. The two extremes ARE the console's existing highlight and veto
colors, so a researched "elite" bucket and a ratified green read speak
one color language. Precedence is absolute: a named absence, the amber
INSUFFICIENT advisory and the ratified green all outrank a bucket.
**Disclosure:** the bucket edges are researched baselines, NOT v2.2
firing lines; where an edge coincides with a ratified line the column's
hover says so, and every edge prints on its surface (D-079) — the
captions build from the same registry the cells grade with, so a moved
edge cannot drift from its printed line.

**The researched baselines (2025 MLB, sources on file).** Barrel 8.6%
of batted balls, whiff 25.3% of swings, ground balls 42.4%, fly-plus-
line 50.5%, pull/straight/oppo 39.2/36.4/24.5 (Baseball Savant league
page); wOBA .313, ISO .158, AVG .245, SLG .404 (StatMuse 2025 season);
average EV ≈ 88.8 mph and bat speed 71.5 mph (ESPN/Savant reporting);
hard-hit ≈ 40% (the third-worst TEAM sat at 38.4%; 2026 leaders 58%+);
HR/9 ≈ 1.16 derived from 5,650 HR over 4,860 team-games (StatMuse
totals); pull-air ≈ 31% of measurable air balls, derived from MLB.com's
17.8%-of-batted-balls pulled-in-the-air (2024) over Savant's 57.6% air
share, with the elite edge past the ratified 40% spray line (MLB.com's
top-10 territory ≈ 25% of BBE ≈ 43% of air balls); league average LA
≈ 12° (Rapsodo 2023). Ratified lines anchor edges where they exist:
EV 91 (power profile) and whiff ≤ 20 (unlock) on the batter scale;
HR/9 1.50/0.80, LA 18/8, GB% <40/≥50/≥55 on the vulnerability scale;
park factor 115/110/90/85 IS the Conditions factor scale; and the six
v2.2 temperature awards wear the six colors directly — the one fully
ratified color scale on the board.

**Judgment calls, disclosed.** Oppo Air % carries no quality scale — a
fit read against the park, not a grade; its read lives in Pull Air %
(the two shares are mirrors). The counting columns (AB, H, Barrels, HR,
Robbed HR, the factor samples) are volume, not quality, and stay
neutral. LA keeps its "an average carries no firing line" posture — it
wears a researched bucket, never a star. Pitcher cells grade
VULNERABILITY (greener = more forgiving), matching the Arms tab's
existing green-on-gas semantics. Form-table and arsenal colors ride
D-129's popup package on the same registry.

**Hover definitions (item 2).** The Matchups grids' hover pattern now
covers the Arms tab, the starter header cards and the Conditions table;
every graded metric's hover carries its definition plus its six edges.

Live-verified on the 2026-08-24 slate: Mullins's L30 row reads dark
green across nine cells; Feltner's season line reads vulnerable green
across wOBA/xwOBA/HR/9/BRL%/ISO/xISO; Rasmussen's wOBA .255 sits dark
red with his LA 12.6 neutral; the SP side rows show amber INSUFFICIENT
outranking every band; the Conditions tab grades both factors per hand
(Petco RHB 114 strong green, Oracle LHB 73 very-poor red) and wears the
temp-award colors (65-74 light red, 75-84 light green, 45-64 red), with
samples and "not covered"/"source unavailable" cells neutral. Full gate
green on both Pythons (3422 passed, 1 skipped), consistency check
clean, all four showcase runners clean.

## D-128 - Matchups structure: season-first with a counted recent window, two-month pitcher reads, the third air profile, published numbers over home-built ones

**Decided:** 2026-08-25 · **Status:** shipped (staging)

The change list's Matchups block (items 31-46): the tab loads the
season view first; the season/recent toggle becomes a timeframe
selector (a counter up to 3 months or 12 weeks, with the year as the
way back to the season); the pitcher tables read the season by default
with a recent-form toggle over the last two months; the pitcher tables
drop wOBA and ISO (xwOBA and xISO stay) and add Hard-Hit %; robbed HRs
show even on the season view with a note that the count is L7-based;
all three batted-ball air profiles grid (pull, straight, oppo); the
select boxes become "more" buttons; the mix scope is the pitcher's
whole season mix, with the RHB/LHB side usage confirmed side-correct.
Item 47 is skipped per the PO's own note.

**Standing data-sourcing directive (PO, 2026-08-25 — applies to every
future build).** Before building any stat, check whether Baseball
Savant, FanGraphs, or pybaseball already publishes it: "No need to
build our own numbers if it's readily available." Baseball Savant is
the source of truth; FanGraphs and pybaseball are good-enough backups,
and pybaseball is fully in wherever reasonable. This decision built on
it: the season view's three air profiles read Savant's published
batted-ball buckets instead of a home-built split, and the pitcher
Hard-Hit % reads the Savant pitcher board's own ev95plus count.

**The window.** A "Batter window" radio (2026 season / Recent window)
plus a counter and a weeks/months unit — no select boxes anywhere. The
season view is the default and sources the season boards; a recent
window counts 1-12 weeks or 1-3 months (months clamp at 3, named on
the surface). The grid's grade stays the L30 computation on the season
view and follows the shown window on a recent one. The fetch record
spans max(batter window, 60) days so the pitcher reads never starve —
a wider window costs one fetch per extra day on the first build, then
caches per slate-and-window (the caption says so).

**Pitcher reads: two months.** Every pitcher event read — the recent
lines, the side usage, the pitch sets, the stuff drift — now reads the
last 60 days of kept events (L30 before). The starter cards' overall
row flips season/two-month on the toggle; the side rows always read
the two-month window and are labeled "vs L (2M)" / "vs R (2M)".

**Pitcher tables.** wOBA and ISO left the starter cards and the Arms
tab; xwOBA and xISO stay. Hard-Hit % joined both scopes — the season
cell reads the Savant pitcher board's ev95plus count over its BBE
sample (verified live: the board carries the column), the recent cell
the 95+ mph share of the two-month record's batted balls against. The
wOBA-over-xwOBA green died with the wOBA column; HR/9 ≥ 1.5 stays the
one ratified pitcher-vulnerability green, and D-127's registry grades
the rest (Hard-Hit % band: elite ≥ 46% / very poor < 30%, mirrored
around the 2025 league ≈40%).

**The third air profile.** Pull and oppo keep D-071's ratified signed
spray convention — verified on real data, they partition measurable
air balls exactly, so a residue "straight" would always read zero.
Instead: the recent view's Straight Air % is the ±15° band around dead
center (Statcast's attack-direction convention) over the identical
measurable-air denominator — a near-center ball counts in its signed
side column too; one denominator, not a partition, and the hover says
so. The season view reads Savant's published pull/straight/oppo
buckets off the batted-ball board — shares of ALL batted balls whose
sum is the air share, verified live — rebased pipeline-side to shares
of the batter's air balls. Straight and oppo stay uncolored fit reads.

**Robbed HR on both views.** The 375+ ft count is always the last 7
days of the event record — the season sources publish no per-ball
distances — so it shows on the season view too, with the basis named
in the hover and the scope caption.

**The mix.** Scope precedence is the season arsenal board first
("season"), then last season's board ("last season"), then the
two-month event record ("last 60 days") — D-081's L45 reach is
deleted, subsumed. Verified live: the arsenal board's hand filter is
inert (identical bytes either way), so no published season per-side
mix exists; per the PO's documented fallback the side usage stays
event-derived over the two-month record — side-correct by
construction, with a pipeline test pinning it.

**More buttons.** Row selection left the grids (a 22-column grid
cannot carry in-grid buttons); a "More — {name}" button per batter
sits in rows of five under each grid and opens the same batter detail
dialog the Sluggers bubbles use.

**Judgment calls, disclosed.** (a) Items 39-vs-44: the pitcher tables
drop wOBA/ISO while the batter tables keep ISO/xwOBA — read as
pitcher-only, since 44 names the pitcher tables. (b) The wOBA>xwOBA
highlight died with its column rather than migrating. (c) The v2.2
tags that quoted an "L30 record" now read the same two-month record
the pitcher reads use — thresholds unchanged, texts renamed "(2-month
record)"/"2M". (d) Season per-side mix has no published board, so the
fallback above applies. (e) Straight Air %'s recent-view band overlaps
the signed reads by design — documented on the hover, never summed.
(f) The default fetch roughly doubles (61 day-queries) — cached per
slate+window. (g) More buttons in rows of five under each grid.
(h) On a custom recent window the grade follows the shown window; it
stays L30 on the season view.

Full gate green on both Pythons (3427 passed, 1 skipped), consistency
check clean, all four showcase runners clean.

## D-129 - Batter detail popup rebuild: starter details beside the park, season-based arsenal breakup with real per-hand splits, form-table thresholds, pulled-barrel surfaces

The PO's batter-detail-popup change list (19 items), implemented as one
rebuild of the dialog. The popup now carries the same starter card the
Matchups tab shows to the right of the stadium animation, with the
starter's reads as Sluggers-style bubble tags under it (the exact
D-114 firing conditions via one shared helper, so the two surfaces can
never disagree). The wind line speaks field words ("wind 12 mph out to
right") and the arrow rotates relative to the drawn field when the
venue's measured home-to-center axis and the wind's from-bearing both
ride along — the arrow and the words always agree; without them the
compass frame stands in, as before.

**The breakup is season-based with real splits.** Both halves read each
player's season pitch record — his pitches and the batter's pitches
seen — fetched lazily on the dialog open (one Savant query per player,
cached per slate day). The default scope is the matchup's hands (his
pitches to the batter's side, the batter's record against the starter's
hand); the "All pitches, all hands" toggle rebases EVERY metric, never
just the usage, because every figure derives from exactly one scope of
the record. The design driver: items 10-12 (hand-filtered season
metrics) are impossible off the published boards — verified live
2026-08-25 that the arsenal board's hand filter is inert (identical
bytes either way), so no published per-hand season split exists and the
split is computed pipeline-side over the raw record (§GMF-008: the view
formats, never derives). The game-type filter pins the regular season —
without it spring training leaks in (verified live). The months/weeks
toggles and filters are gone. Rows below the usage threshold now HIDE
(item 10) instead of dimming; an emptied table names the threshold and
the slider instead of rendering nothing.

**Column changes.** Pitcher half: ISO out, xISO in (mean expected SLG
minus mean expected BA over the scope's batted balls carrying both
readings — a constructed split, disclosed in the caption, since the
board publishes no per-hand expected rates), the raw barrel count added,
wOBA and K% added off the plate outcomes. Batter half: PA out, AB and
Hits in; LA right after Hits, then barrel rate and EV, then the rest;
Pull Air % and Oppo Air % added over the form section's exact
measurable-air convention (one definition both surfaces share). The
title names the starter and his throwing hand. A pitch the batter has
not seen shows AB 0 (a true count) and dashes the rest — never hidden,
never invented. Per-pitch contact reads keep the ratified 10-BBE floor
with the INSUFFICIENT marker (D-109).

**Form table thresholds (item 6).** The recent-form table is now
color-coded with six-band specs researched off the live 2026 boards
(481 player-sides at 100+ swings; the statcast board at min=100):
Barrel% 13/10/8.5·6/4/2.5 (league mean 7.76, P50 7.3, P75 10.3,
P90 13.2), EV 91/90/89·88/87/85.5 (mean 88.78, P90 91.8 — confirms
D-127's grid edges), attack angle 13.5/12/10.5·9/7.5/6 (mean 10.15°,
P10 5.8, P90 14.8), ideal-attack-angle rate 60/56/53·47/43/39 (mean
51%, P10 40.5, P90 61.5), Pull Air % 43/38/33·27/22/17 (the grid's
ratified D-127 spec, one scale both surfaces). SwSp% and Hard% left the
table (item 5). The bands are window-independent rate baselines — the
INSUFFICIENT marker already carries the window's sample risk, so the
color reads the level and the marker reads the trust. Oppo Air % stays
deliberately bandless (a fit read, not a quality scale). Form Score
prints at the end of the table as the D-124 placeholder dash. Pulled
BRL is a raw count with its own greens (1 / 2 / 3+ against D-116's
one-pulled-barrel-per-week reality; 0 stays neutral, never red).

**Pulled barrels surfaced (items 17-18).** The exit-velocity event log
now paints a pulled barrel's Event cell a lighter green (a home run
keeps the dark green), with the caption naming both. Item 18 ("make
sure the pulled barrel counter is working, I've only seen 0") —
VERIFIED WORKING, no bug: 59 batters on the live 2026-08-25 board
carry nonzero counts (Blaze Jordan 3; Contreras, Seager, Wetherholt,
Walker, Teoscar Hernández 2 each), 176 zeros, 26 absent. Zeros are the
expected state at roughly one pulled barrel per batter-week; the new
event-log highlight makes the nonzero ones visible when they happen.

**Row verdict (item 19).** A breakup row goes green when the starter's
xwOBA with the pitch sits in a green vulnerability band AND the
batter's SLG against it sits in a green band; red when both sit in red
bands; anything else neutral. A verdict requires 10+ batted balls on
BOTH halves (the ratified D-109 floor) so a thin row never grades
noise. The rule is a mechanical band check — a criteria tally, never a
prediction (D-015/D-017 stand).

**Judgment calls, disclosed.** (a) Item 2 ("instead of check boxes lets
use a 'more' button") read as already satisfied by D-126/D-128's More
buttons — no further change. (b) Switch hitters and unknown sides: the
all-hands toggle disables and the table reads both full season records
with a caption naming why (a switch hitter bats from both sides) — a
per-side split would invent a side. (c) xISO is the constructed split
above, disclosed on the surface — no published per-hand expected split
exists. (d) Form bands use display units (the form pipeline's rates are
percent-scale). (e) The lazy fetch adds one query per player per dialog
open — cached per slate day, so repeat opens are free. (f) The wind
arrow's rotation frame changed only when BOTH the measured axis and the
from-bearing exist; the compass path is byte-identical otherwise.
(g) A shell docstring/parameter rename (park_axis_degrees →
axis_degrees) satisfied the config-boundary guard's substring rule —
geometry unchanged.

Full gate green on both Pythons (3434 passed, 1 skipped), consistency
check clean, all four showcase runners clean.

## D-130 - Money tag marks only homers on the viewed slate day

The PO caught Scharber wearing a neon "$" on the Sluggers tab before
his game had even started. Cause: the tag followed D-094/D-126's
last-game-day read — a batter who homered on his most recent completed
game day kept the tag into the next slate, so last night's homer showed
on today's pre-game board (the date rider was D-126's mitigation, but
the tag itself still read as "homered tonight"). The PO's rule,
verbatim: "I only want to see who got the day of the slate I'm looking
at — if I'm looking at today's I shouldn't see any dollar signs since
games haven't begun."

**The fix.** The BatterCard field is now `homered_on_slate_day`: the
board build asks the game log one question — did he homer ON the viewed
slate day? — and carries the day's ISO date when yes, None otherwise
(supersedes `_homered_on_last_game_day`). The game log carries only
final games (D-100), so a pre-game slate tags nobody, and the tag lands
within a board refresh of his game going final. No log, no failed log,
no tag — absence semantics unchanged. The view reads the field
directly; the tooltip, the shortlist caption, and the column help now
say "homered on this slate day — appears once his game goes final, so a
slate whose games have not begun shows no tags at all."

**Why pipeline-side rather than a view filter:** a view-side comparison
against the old field would still under-tag a past slate — a batter who
homered on day D but played HR-less after it shows None under the
last-game-day read, so viewing slate D later would miss him. Asking the
log about the slate day directly answers the PO's question for every
viewed slate, past or present, with the data the build already holds.

The zero-PA guard left with the old function: the new question needs no
"last played day" logic, and a home run implies plate appearances. The
backtest's per-day "Homered" column is untouched — it already names the
day being graded.

Full gate green on both Pythons (3433 passed, 1 skipped), consistency
check clean, all four showcase runners clean.

## D-131 - Weather reads the forecast at first pitch, not the build hour

Source: PO directive — "Please do weather accuracy spot check." The
spot-check came first; the fix is what it found.

**The spot-check (2026-08-25 ~20:05 UTC, slate 08/26).** Every readable
venue on the board was compared against the source's own answer, and the
source was compared against an independent one:

- **Parsing, mapping, and units are correct.** At all 14 venues the
  board could read, the app's temperature, wind speed, and wind
  direction byte-matched the NWS hourly period the app was actually
  consuming. No conversion or compass-mapping defect exists.
- **One real defect found: the reading covers the wrong hour.** The
  board asked NWS for the *current* hour's period no matter when the
  game starts, so an afternoon board build showed an evening game the
  afternoon's weather. Roughly 5 of 14 games carried a different wind
  *direction* at first pitch than the board displayed (e.g. Yankee
  Stadium W at build time vs S at game time; Busch SE vs W). Wind
  direction drives the field words and tags, so this was not cosmetic.
- **NWS itself validated.** Against Open-Meteo at the same coordinates
  and hour, NWS sat within 2–6 °F and ~3 mph everywhere — no better
  free source exists, and no source change is warranted.
- **Named absences behaved correctly.** Rogers Centre answers absent
  (Toronto is outside NWS coverage — D-055's honest 404), and one
  transient venue absence recovered on retry.

**The fix.** `WeatherAdapter.forecast_for` now takes the moment the
reading should cover: `forecast_for(venue, at)`. The pipeline computes
each game's scheduled first pitch *before* its weather reads and passes
it to all three conditions readers (temperature, wind, humidity); the
composition root's closure forwards it. The NWS adapter caches the
venue's hourly **periods list** under the existing 30-minute freshness
bound — not one parsed forecast — and each read picks the period
covering `at`. When no period covers it (the game sits beyond the
hourly forecast's ~6-day reach), the **nearest** period stands in
rather than an absence: a stale reading from the source beats no
reading, and it stays honest — it is still the source's own number,
with `obtained_at` carrying the fetch moment so age survives the cache.
`at=None` keeps the old current-period read, so the fixture, the parks
page, and every existing caller behave exactly as before. The fixture
adapter accepts and ignores the moment (its one fixed forecast is
moment-invariant). Absence semantics are unchanged: source failures
stay SOURCE_UNAVAILABLE with their plain-language diagnostics, an
answered-but-empty period list stays NOT_YET_OBSERVED, roofed venues
still take no read at all (D-073/D-111), and `obtained_at` remains the
fetch time, not the pick time.

**Why nearest-period rather than absence beyond the forecast's reach:**
a future slate's game (the PO explicitly views future dates) would
otherwise show no weather at all even though the source published a
forecast covering most of the horizon. The stand-in is the source's
data, clearly aged by its own timestamp — presence with disclosed age,
not an invented number.

**Verified:** the gate's new tests prove the covering period is picked,
the nearest stands in beyond the horizon, untimed periods fall back to
the current period, two moments on one venue cost one fetch, and the
pipeline's readers receive the game's parsed start instant. A cached
read now returns an equal-but-fresh pick (the periods list is what
caches), so the prior object-identity assertion became a value-equality
one. Full gate green on both Pythons (3438 passed, 1 skipped),
consistency check clean, all four showcase runners clean.

**Noted, not fixed here:** Sutter Health Park (Athletics) carries no
`savant_venue_id` in the park registry, so its park-factor reads are
named absences; that is a data-registry gap predating this change and
is queued for a future decision.

## D-132 - Form Score shows the actual graded form subtotal

Source: PO directive — "For form score place holder, this acc ore will
be the score graded as part as the complete grade. In the future we
will be making adjustments to the weight and scoring itself. For right
now 2 is max score I believe. Go ahead and let the form score show the
actual score for recent form."

The D-124 placeholder dash is dead. Both Form Score surfaces — the
shortlist's column and the detail popup's form table — now show the
batter's actual form subtotal from his own grade: the
``CategoryScore`` for the ``form`` category, points awarded out of the
category's configured maximum ("1.5 / 2"). The maximum is read from
the one production config (2 in v1, as the PO confirmed) rather than
hardcoded, so a future weight change edits the config and nowhere
else. No new computation exists: the scoring core already graded the
form category; the screens simply stopped hiding it. Per the PO, the
weights and scoring may change later — the column is a read of the
current grade, not a new formula, and every hover/caption says the
weights may change.

Absence honesty is unchanged: a batter whose grade is not an evaluated
one (the Matchups tab can open one) reads "not evaluated" in the
muted-reason style — a named absence, never an invented number; the
shortlist only carries A/S-graded batters, so its cell always has a
real subtotal to show, with the dim dash left purely as the defensive
fallback.

The hovers and the shortlist caption now describe the live read and
name the max (2 in v1); the popup's form-table help says the same.
Tests: the placeholder assertion became the actual-subtotal assertion
(present value with no reason fill; non-evaluated names the absence),
and a shortlist seam test proves every row's cell ends " / 2" off the
production config's maximum.

Full gate green on both Pythons, consistency check clean, all four
showcase runners clean.

## D-133 - L7 air-ball floor drops from 8 to 5

Source: PO directive — "Let's move the minimum for L7 from 8 to 5, we
are still getting a lot of insufficient."

``MIN_AIR_BALLS_FORM_L7`` is now 5 (was 8, D-114). The L7 spray reads —
Pull Air %, Oppo Air %, and every tag built on them (the wind reads'
dominant air field, the spray-alignment reads) — resolve sufficient at
five measurable air balls in the week. The L14 floor is untouched at
15: the split by window stands, only the short window lightens. Five
is still an honest read — roughly three games' air contact — while 8
was marking everyday regulars INSUFFICIENT through ordinary light
weeks (5-9 air balls), which is the complaint the PO named.

Present-with-marker semantics are unchanged (D-023/D-025): a 3- or
4-ball week still shows its value with its exact sample and the amber
INSUFFICIENT marker — the floor moved, the honesty did not.

Every surface that prints the floor now says 5 at L7: the form-table
caption, the shortlist caption, the wind-read comment and docstring,
and the form module's own comment. The floor-boundary test moved with
it (5 resolves sufficient, 4 stays under the advisory; the 12-ball
L14 fallback still stays insufficient). That same form-table caption
also still named the Form Score a D-124 placeholder — text D-132 made
stale — and now names the actual graded subtotal instead.

Full gate green on both Pythons, consistency check clean, all four
showcase runners clean.

## D-134 - Pitcher two-month side-row floor drops to 50 BF / 30 BBE

Source: PO directive — "Also getting a lot of insufficient in the
recent form for pitchers (two month scope) let's lower the minimum so
that that goes away. Find a decent baseline, goal is around last 7
outings which is roughly 2 months but you can research it."

**The research.** Rather than reason from averages alone, the floor was
set against the population it serves: the 2026-08-26 slate's probable
starters. Fourteen starters' pitch records were pulled for the last two
months (2026-06-26 → 2026-08-26, 6-11 starts each) and split by batter
side:

- A regular starter's LIGHTER side over the window sits around 70-90
  batters faced (sampled median 75, p25 69) — that is the "last 7
  outings" baseline the PO named, and it is exactly where the old
  80-BF line cut: it marked 12 of 28 sampled side-rows INSUFFICIENT
  (43%), the flood the PO saw.
- At 50 BF the count drops to 1 of 28 — the one genuinely thin record
  in the sample (24 BF over a 6-start window), which *should* keep its
  marker. 60 was rejected: it still marked 3 of 28, including ordinary
  58-BF sides from 9-start regulars.
- 30 BBE keeps the pair proportional (~72% of BF reaches the batted-
  ball record) so a walk-heavy line cannot clear on batters faced
  alone; on the sample it marks the same one thin side.

**The change.** ``_VULN_MIN_BF`` 80 → 50, ``_VULN_MIN_BBE`` 40 → 30 —
the side rows of the starter header card (vs L / vs R over the
two-month record). The overall row's 15-BBE contact floor is
untouched, and the below-floor honesty is untouched (D-068): values
stay visible with their exact samples under the amber advisory; only
the line moved. Every surface that prints the floor now says 50/30 —
the constants comment, the row docstring, and the Arms caption — and
the boundary test moved to the line (exactly 50/30 carries no
advisory).

Full gate green on both Pythons, consistency check clean, all four
showcase runners clean.

## D-135 - Hotfix: the backtest's weather readers take the game-time call

Source: found while implementing the morning refresh — a D-131
regression, deployed.

D-131 changed the pipeline's conditions readers to receive the game's
scheduled start — ``temperature_for(venue, start_utc)`` — and updated
every call site the gate exercises. It missed one: the backtest board
build (D-095) still passed the one-argument ``lambda venue: None`` for
temperature and wind, so every real backtest build raised ``TypeError``
the moment a past slate was regraded. The backtest view on the deployed
app was broken from the D-131 merge until this fix. The suite never
crossed it because every backtest test patched ``build_board`` whole —
the lambdas lived on the far side of the patch.

**The fix.** The two lambdas are now one named reader,
``_absent_weather(venue, at)``, whose signature takes the game-time
call and whose docstring says why the answer is still always the same
named absence (D-095 does not reconstruct past weather). The new
regression test reads the readers the backtest function actually
passes and calls them the way the pipeline now does — it fails on the
old lambdas exactly as the deployed build did.

No behavior change beyond the un-breaking: the backtest's weather
cells name their absence precisely as before.

Full gate green on both Pythons, consistency check clean, all four
showcase runners clean.

## D-136 - Morning refresh: season sources day-anchor, a cron warms the board

Source: PO directive — "Let's have it refresh every morning whenever
savant and the rest update their numbers from day before. Unless you
click on a future date then obviously load it at the time of request."

**The anchor.** The season sources (the nine Savant season boards the
build reads, plus the MLB season hitting/pitching lines) update
overnight, so the board now trusts one morning's answer for the whole
day: ``_season_data_anchor`` flips at noon UTC — 5:00 AM in Arizona,
where the PO reads the board. Two composition-root proxies
(``_DayAnchoredSavant``, ``_DayAnchoredMlbApi``) wrap exactly those
season fetches in a cache keyed on the anchor date; the flip — and only
the flip — refetches. Everything intraday stays live: the slate, the
batting orders, the weather, and the game logs (the D-130 slate-day
money tag depends on their freshness). A board rebuild every fifteen
minutes now costs the slate, the orders, the logs, the resolving event
days and the weather — the expensive season boards come off the
morning's anchor. The backtest's regrade builds ride the same proxies.

**Failures never poison a day.** A season fetch that fails raises out
of the cache (``_SeasonFetchError``) — st.cache_data never caches a
raised call — and the proxy hands the pipeline the ordinary
FetchFailure it already renders as a named absence. The next build asks
the source again; a morning transient costs minutes, not a day.

**Day events split by finality.** A day before the anchor is final and
caches for 26 hours (it never changes once the morning update lands);
the anchor day and later keep the hourly read — yesterday becomes
"final" exactly when the refresh says its numbers landed.

**Future dates load on request — unchanged.** The anchor governs the
season sources, never the slate: clicking a future date builds that
slate on demand against the morning's season data, which is the only
season data that exists.

**The wake.** ``.github/workflows/morning-refresh.yml`` runs at 12:30
UTC (after the flip, with slack for the sources' publishes): a headless
browser opens the deployed app and waits for the board to render —
three attempts, long waits, loud failure — so the new anchor day's
season fetches and today's board build happen on the schedule, and the
first real visitor of the morning lands on a warm board instead of a
cold multi-minute build. The job needs no secrets (the app's own URL
only) and is also manually dispatchable.

The board caption now states the discipline: board every 15 minutes,
form windows hourly, season sources each morning (5 AM Arizona), a
future date on request. Tests prove the flip hour, the once-per-anchor
caching, the failure-never-cached rule, the slate staying live, and the
finality routing.

Full gate green on both Pythons (3446 passed, 1 skipped), consistency
check clean, all four showcase runners clean.


## D-137 - Force a clean Cloud rebuild after the deploy served a crash page

2026-08-26. After D-136 merged, the deployed app at
greenmachine.streamlit.app stopped serving the dashboard and instead
rendered Streamlit's redacted crash page: ``ImportError`` at the
``greenmachine.live.pipeline`` import in ``streamlit_app.py``. Every
check against the exact deployed commit (staging ``1adeb63``) passes
outside the host: the full gate on both Pythons was green at merge, a
fresh interpreter imports ``streamlit_app`` cleanly, all thirteen
imported names exist in the pipeline module, and no dependency changed
in any of D-131..D-136 (every addition was stdlib or internal). The
code at the tip is not the problem; the host's reused install
environment is the only remaining suspect — Streamlit Community Cloud
caches its package environment between deploys and rebuilds it only
when ``requirements.txt`` changes, and none of the six merges changed
it, so a corrupted or half-updated cache could ride forward across all
of them.

The remediation is operational, not a behavior change: a dated comment
in ``requirements.txt`` (a cache-bust marker) changes the file, which
forces the host to discard the cached environment and rebuild from
scratch on this deploy. No runtime specification moved — same bounds,
same packages. If the crash survives the clean rebuild, the next step
is the app's manage-console logs (owner-only), which would name the
specific unredacted failure; the expectation is that it does not
survive, because nothing in the code can produce the observed failure.

The verification discipline holds either way: the live dashboard is
re-checked end to end after the rebuild before the morning-refresh
work is called done.


## D-138 - The deployed crash is a wedged host-side checkout, not the code

2026-08-26. The crash page D-137 chased survived the forced environment
rebuild, so the diagnosis went deeper. Two temporary diagnostics shipped
to staging and were reverted within the incident:

1. ``client.showErrorDetails`` flipped to full for one deploy — the
   crash page stayed redacted, so the host redacts startup import
   failures regardless of the app's setting.
2. The ``greenmachine.live.pipeline`` import in ``streamlit_app.py``
   was wrapped so the failure re-raises as a dynamically named
   exception whose TYPE carries the original message — the crash page
   always prints the type even when it redacts messages. That read the
   answer straight off the deployed page: ``cannot import name
   'season_breakup_lines' from 'greenmachine.live.pipeline'``.

**Root cause.** The host's copy of
``src/greenmachine/live/pipeline.py`` is frozen at a state that matches
no committed version: it holds ``PitchLine`` (defined at line 203) and
``build_board`` (line 1528) but lacks ``season_breakup_lines`` (line
935) — all three added in the same D-129 commit, so no checkout of any
commit can produce that mix. Every other file, ``streamlit_app.py``
included, tracked staging perfectly across five diagnostic pushes. The
host's cached clone is wedged (a skip-worktree-style index freeze or a
partial checkout that nothing rewrites): a content change to the file
itself (a marker comment, shipped and reverted) did not update the
served copy, which rules out every push-side remedy. The app code at
staging is healthy — the gate, a fresh-venv import, and CI on every
push all pass — and no code change can fix a file the host refuses to
write.

**Remediation.** The fix is console-side and owner-only: reboot the
app first (ten seconds); if the crash page persists, delete the app in
the Streamlit console and redeploy it from the same repo and branch
(``staging``, entrypoint ``streamlit_app.py``) — a fresh clone replaces
the wedged one, and the custom subdomain is reclaimed by naming the new
app the same. Repo state was left clean for exactly that redeploy:
diagnostics reverted, error policy back to type-only, pipeline source
byte-identical to D-136.

**Adjacent finding.** The D-136 morning-refresh workflow can never
fire on its cron: GitHub registers scheduled workflows only from the
repository's default branch, and this repo's default branch is the
initial-commit ``main``, which the staging-first discipline never
touches. The workflow remains manually dispatchable; making the 5 AM
wake real needs either a workflow-only file on ``main`` (the PO's call,
since the no-push-to-main rule is theirs) or an external morning ping
to the app URL. Flagged for the PO alongside the redeploy steps.

Full gate green on both Pythons (3446 passed, 1 skipped), consistency
check clean, all four showcase runners clean. Live verification of
D-132..D-136 runs the moment the app is back.


## D-139 - Refresh anchor moves to 5 AM Eastern; the cron file lives on main

2026-08-26 (PO: "Put file on main. Let's change the time to EST for
earliest start up"). Two directives, one entry.

**The wake file goes to the default branch.** D-138 found the
morning-refresh workflow could never fire: GitHub registers scheduled
workflows only from the repository's default branch, and ``main`` here
is the initial commit. The PO authorizes a scheduler-only presence on
``main``: ``.github/workflows/morning-refresh.yml`` and its driver
``morning-refresh.mjs`` are now on ``main``, byte-identical to the
staging copies — no application code crosses, and the staging-first
discipline for the app itself is untouched. Future edits to either
file must land on both branches (the workflow's header comment now
says so). Because ``main`` is protected and its required checks can
never run against main's tree (no project code lives there), the merge
(PR #92) went in during a minutes-long, fully restored lift of the
required-status-check rule; the final protection configuration was
verified field-by-field identical to the original.

**The flip moves to 5 AM Eastern — the earliest defensible hour.** The
PO asked for the earliest Eastern startup, so the season-source anchor
flips at 09:00 UTC (5:00 AM Eastern through the baseball season, EDT;
4 AM in winter), moved from noon UTC (D-136). Earliest, not earlier:
West Coast slates finish as late as 1–2 AM Eastern, and the sources'
overnight publishes trail the final pitch — anchoring at, say,
midnight would risk the morning fetch landing before yesterday's
numbers post and caching day-old season data for the whole day (the
anchor's 26-hour trust is exactly the wrong failure to invite). 5 AM
Eastern keeps roughly three hours of slack after the latest possible
finish; if a stale morning ever shows, the knob is
``SEASON_DATA_REFRESH_HOUR_UTC`` and the cron half-hour after it. The
cron moves to 09:30 UTC on both branches, the board caption reads
"5 AM Eastern," and the anchor-flip test moves to the new hour.

Full gate green on both Pythons (3446 passed, 1 skipped), consistency
check clean, all four showcase runners clean.


## D-140 - The morning wake never checked out the repo

2026-08-30 (PO P0: "5 AM refresh failed, check why and fix if
possible"). All four morning-refresh runs since the scheduler landed on
``main`` (D-139) failed the same way: ``MODULE_NOT_FOUND`` for
``.github/workflows/morning-refresh.mjs`` before the app was ever
touched. Cause: the job installs Node and a headless browser but never
runs ``actions/checkout`` — a fresh runner's workspace is empty, and the
workflow file itself reaching GitHub's scheduler says nothing about the
workspace. One added step (``actions/checkout@v4``, first in the job)
fixes it; the file ships on both branches per the D-139 keep-identical
rule. A manual dispatch after the merge is the proof of life — the next
scheduled run lands at 09:30 UTC (5:30 AM Eastern).


## D-141 - The wake job's markers watched the wrong frame

2026-08-30 (PO P0: "5 AM refresh failed, check why and fix if
possible", continued). With the checkout fixed the job got three steps
further — and hung on "Load the board and wait for it to render" until
the 30-minute job timeout killed it. Two causes, both now fixed:

1. Empty permissions (fixed in the same D-140 round, recorded here
   because that merge changed only the workflow file). ``permissions:
   {}`` gave the job token no scopes, so the checkout of this private
   repo failed with "Repository not found." The job now declares
   ``permissions: contents: read`` — the minimum the checkout needs,
   nothing else.
2. Frame-blind markers. The script waited on page-level ``text=``
   selectors ("The shortlist", the empty-board and schedule-failure
   texts), but Streamlit renders the app inside a child ``/~/+/``
   frame — the top page is a management shell. Page-level selectors can
   never match app content (the same lesson the live-verification
   suite learned), and the three markers were awaited *sequentially*
   with 480-second timeouts, so the step ran to the job timeout. The
   checker now polls the ``/~/+/`` frame on a 5-second interval under
   one 300-second deadline per attempt, checking all three markers each
   pass; 300 seconds also keeps three attempts plus browser install
   comfortably inside the 30-minute job budget.

Proof of life is a manual dispatch that reaches "board rendered on
attempt 1"; the next scheduled run lands 09:30 UTC (5:30 AM Eastern).


## D-142 - Pitcher recent form rewindows to the last three months

2026-08-30 (PO change doc: "change pitcher recent form to the last 3
months everywhere applicable — currently 2 months").
``PITCHER_RECENT_WINDOW_DAYS`` goes 60 → 90. That single constant feeds
every pitcher recent-form read, so they all move together: the starter
cards' overall row on the toggle and the always-recent side rows (now
labelled "3M" / "vs L (3M)" / "vs R (3M)"), the Arms tab's recent view,
the per-side pitch usage and pitch sets, the stuff-drift caption, the
ground-ball-profile tags ("3-month record"), and the arsenal-mix
fallback ("last 90 days"). Captions, help texts, and the thin-sample
string all read three months now.

Two things checked along the way:

- The thin-sample start count had quietly gone stale. SP-3's pitching
  game-log reach was 31 days — it mirrored the window when the window
  was a month, D-128 stretched the event record to two months and left
  the log at 31, so the caption "2-month record: N starts" was counting
  starts over one month. ``PITCHING_LOG_LOOKBACK_DAYS`` is now pinned
  to ``PITCHER_RECENT_WINDOW_DAYS`` by construction.
- The D-134 floors stay 50 BF / 30 BBE. They are a minimum-credible-
  sample line, not a window-relative one; under three months more side
  rows clear them, which is the point of the longer window. The 15-BBE
  contact floor and the ≤2-starts thin-sample line are unchanged for
  the same reason — two starts in three months is genuinely thin.

Full gate green (3446 passed, 1 skipped), consistency check clean, all
four showcase runners clean.


## D-143 - The starter-card toggle flips all three rows; season side rows read his full-season pitch record

2026-08-30 (PO change doc P0: "SP table in batter detail popup: default
splits = season, toggle shows recent form for all three rows — right now
it doesn't work properly"). The card's toggle flipped only the overall
row; the side rows were pinned to the recent record in both modes, so
"season" showed a season overall over two recent side rows. Now the
toggle drives all three rows on every starter card (Matchups tab and
batter detail popup — same component): recent = the three-month record
(3M / vs L (3M) / vs R (3M)); season = the boards' overall row plus
"vs L (season)" / "vs R (season)".

The boards publish no per-side season split (the arsenal CSV's hand
parameter is inert — verified live 2026-08-25), so the season side rows
are computed from his full-season pitch record, one Savant query per
probable fetched at board build and cached per slate day — the same
D-129 endpoint the dialog's breakup uses, now sharing one cache entry
(the dialog's read returns the raw FetchFailure to the caller so the
board build can name the diagnostic). The pitch record publishes no
innings and no per-event expected SLG, so on the season side rows HR/9
and xISO name their absences exactly as the recent rows do — they live
on the season-boards overall row — and the HR count shows instead. The
50-BF / 30-BBE floor (D-134) applies to the season side rows the same
as the recent ones. Backtest boards wire no season-record fetcher (one
fetch per probable per backtest day would bury a range), so their season
side rows name the absence. Three missed "last 2 months" toggle labels
now read 3 months (D-142's sweep caught the digit-free spellings only).

Full gate green (3450 passed, 1 skipped — four new tests: splits land on
the card, fetch failure names itself, backtest absence, season-scope row
text), consistency check clean, all four showcase runners clean.


## D-144 - The form table gains volume counts and an all-contact pull read; the pulled-air tag leaves

2026-08-30 (PO change doc P1, five items landed together since they all
touch the popup's form table and tag set):

- The Recent form table opens with plain AB and H counts (PA-ending
  events less walks/HBP/sacrifices/interference; singles through homers),
  L7 with the L14 fallback named — a count carries no sample floor, and
  0 in a played window is a real observation. The PA-ending event sets
  moved from the pipeline into form.py so the counts and the grid's
  AVG/SLG denominators share one definition.
- New Pull % column right before Pull Air %: pulled share of measurable
  CONTACTS (the air reads' measurability — coordinates and a known
  batting side — widened past the air-ball filter, so a pulled grounder
  counts here). Green opens at the PO's 40 line (strong 44, elite 48),
  reds below 36/32/28 around the ~36-37% league-average pull share.
- The AtkAng column and the Pulled BRL count left the form table (the
  underlying reads still grade and the EV log still highlights pulled
  barrels — display only).
- The batter half of the popup's breakup table lost its Air% column.
- The pull-air match tag (D-120's spray-alignment booster) is removed
  completely. The oppo-air match stays. Untouched: the wind reads'
  internal pull/oppo field logic (not a tag) and the actual-over-expected
  advisory's pull-air sub-reason (a different tag's explanatory clause,
  D-125) — if the PO wants that clause out too, it is one line.

Full gate green (3452 passed, 1 skipped — new tests pin the column set
and order, the count semantics, the Pull % band anchors, the air-guard
partition, and the retired tag's absence), consistency check clean, all
four showcase runners clean.


## D-145 - Matchup rows end with their More button; K% replaces Swing-Str%; the pitch filter defaults to all pitches

2026-08-31 (PO change doc P1, the four matchup-table items landed together
since they all touch the same grid):

- The More button moved to the end of each batter's row — the Sluggers
  layout. The 22-column st.dataframe could not carry in-row buttons (the
  D-128 comment said so), so the grid left the dataframe: each batter row
  is now its own one-line HTML table in a two-column Streamlit row with
  the button beside it, vertically centered, exactly like the shortlist.
  The D-127 band fills ride as inline cell styles, the D-124 header
  definitions ride title attributes, and the stars still mark ratified
  v2.2 firing lines. The rows of five buttons under each grid are gone.
- K % replaced Swing-Str % on the matchup tables: strikeouts per plate
  appearance over the scope. The window lines count the scope's own
  events (the plate-outcomes block already computed the share for the
  popup breakup); the season line reads the statsapi counting line — the
  same figure the high-K tags use. The band: league K% ≈ 22.2% (2025),
  anchored to the ratified v2.2 K reads — the 22% unlock anchor is the
  above-average edge, the 28% binary read the poor edge, the 30% high-K
  caution the very-poor edge (elite ≤ 15%, strong ≤ 18.5%, below-average
  ≥ 26%).
- Scope clarified on the surface (the PO's question): the starter's mix
  is his whole-season arsenal against ALL hands off the arsenal board,
  with the named recent-record fallback; the batter's columns read his
  window events against the starter's hand of pitching. Both captions
  now say exactly that, and the per-lineup scope line names the hand.
- New pitch-filter toggle on the main matchup tables (recent-window view
  only — the season view reads the season boards, never the pitch
  filter). Off, the PO's stated default: every pitch type the batter saw
  enters the denominators — "all hands with all their pitches" — via a
  new unfiltered twin line (mix_line_all) computed beside the qualifying
  one. On: the D-079 qualifying mix only (≥14% of the mix's usage). The
  grading matchup read keeps the qualifying scope — grading is untouched.

Full gate green (3453 passed, 1 skipped — new tests pin the all-pitches
default, the toggle's two scopes, the K% basis on both lines, the HTML
rows' header hovers, and the no-raw-None cell guard), consistency check
clean, all four showcase runners clean.


## D-146 - The shortlist sorts, highest first; the extra-look tag leaves

2026-08-31 (PO change doc P2, all three sluggers items):

- The Sluggers tab loads highest grades at the top now — S before A, the
  total score breaking ties — and a Sort by radio orders the shortlist on
  Grade (the default), Park factor (the batter-side HR factor, an
  uncovered park last) or Form Score (the graded form subtotal off the
  same category read the cell prints — one derivation, so the sort and
  the cell can never disagree; a missing one sorts last). Highest first
  on every choice, the grade and the name breaking ties so a refresh
  never shuffles equals. A radio, not a selectbox — the no-selectbox
  board rule (D-015/D-017's chooser ban) stands; this is a row-order
  pick, not a ranking control, and the shell test's radio whitelist now
  names it.
- The leadoff "extra look at the starter (4-5 PA tier)" tag is removed
  completely — the top-5 slot booster ("bats Nth") stays; the v2.2 slot
  scoring itself was never the tag and is untouched.

Full gate green (3454 passed, 1 skipped — a new test pins the default
order, both alternate sorts, the absent-value tails and the tag's
removal), consistency check clean, all four showcase runners clean.


## D-147 - Pitcher and per-pitch contact reads drop tracked foul balls: the wrong launch angles, found and fixed

2026-08-31 (PO change doc P0 item 4, the data-accuracy audit's core
finding — "Launch angles for pitches were wrong"; the PO confirmed
mid-audit that players' statcast angle numbers for the pitch read
wrong):

- Root cause: Savant's pitch feed tracks exit velocity and launch angle
  on FOUL balls but never classifies them — a tracked foul carries
  launch_speed and launch_angle with launch_speed_angle None and no
  batted-ball type. Fouls skew steep (the unclassified tracked contact
  on the 2026 season averages ~24-27 degrees), so any average that
  includes them reads several degrees high.
- Two pipeline derivations built their contact base on "has a measured
  speed" instead of "is a classified batted ball", so tracked fouls
  entered every pitcher and per-pitch contact read: _pitcher_recent_line
  (the SP card's recent rows, the D-143 season side rows, the Arms
  recent columns) counted BBE on launch_speed and averaged the angle
  over every event with a measured angle; _pitch_lines (the popup
  breakup's per-pitch EV/LA/barrel/hard-hit rows) did the same. On live
  2026 data Skubal's foul-inclusive average read 17.5 degrees against
  10.5 classified and 11.7 on Savant's own board.
- The fix is one convention everywhere: the contact base is the events
  with a launch_speed_angle classification. Both functions now build
  BBE, barrels, hard-hit, mean exit velocity and mean launch angle off
  that single classified set — the same convention _batter_grid_line
  and the form aggregation already used (they were never wrong), and
  the same convention Savant's published boards use.
- Verified live against the source of truth (D-128) before the fix
  landed: on the closed 2025 season the classified convention
  reproduces Savant's published season boards within rounding (Ohtani
  14.95 vs 15, Judge 19.06 vs 19, Skubal 12.33 vs 12.7, Skenes 12.30
  vs 12.2; BBE within one batted ball), while the foul-inclusive base
  reads 4-7 degrees high. The batter-side season numbers on the
  matchup tables were checked at the same time: they are board-sourced
  and accurate.
- One test fixture needed repair, which confirmed the classification
  is the right discriminator: a strikeout event had inherited a barrel
  classification from its base event and only became a "batted ball"
  under the corrected base — the fixture now carries no classification,
  as a real strikeout does.

Full gate green (3455 passed, 1 skipped — a new regression test pins
that a tracked foul with a measured 60-degree angle and no
classification never enters the pitcher or per-pitch contact reads),
consistency check clean, all four showcase runners clean.


## D-148 - The scoped counting follows the official scoring: intent walks, truncated PAs, double-play strikeouts

2026-08-31 (PO change doc P0 item 5 — "confirm all the timeframe toggles
pull accurate info"; the window math checked out, and the live
cross-check behind it exposed three event-vocabulary gaps in the shared
counting):

- The audit's method: the app's own plate-outcome aggregation over
  Savant pitch events for a four-week window, compared against the
  official statsapi game logs for the same players and dates (Ohtani,
  Witt Jr, Raleigh). Once the source's one-day indexing lag is set
  aside (the search CSV had not yet indexed the previous day's games —
  a source freshness fact, not a window bug), every mismatch traced to
  three event strings.
- intent_walk was charged as an at-bat. An intentional walk is a walk —
  never an at-bat — and it is common: 81 across four 2025 seasons, 4 in
  one sample batter's four-week window. Every event-derived AVG/SLG/ISO
  on the matchup grids, the popup per-pitch lines and the form table
  understated slightly wherever an intentional walk landed in scope.
- truncated_pa counted as a plate appearance and an at-bat. It is
  neither on the official line (the inning or game ended on the bases
  with the appearance unresolved): the event-derived season PA count
  ran exactly the truncated count above the statsapi season line. It
  now leaves the PA denominator entirely.
- strikeout_double_play was missed by the strikeout reads (four across
  four 2025 seasons). The batter struck out; the K% columns count it.
- The never-observed sacrifice double-plays (sac_fly_double_play,
  sac_bunt_double_play) joined the non-at-bat family on the official
  rule — a sacrifice is never an at-bat — after ~17k scanned pitches
  across two seasons showed none: inclusion is zero-risk, omission
  would be a silently wrong at-bat.
- One shared vocabulary in form.py (NON_PLATE_APPEARANCE_EVENTS new,
  NON_AT_BAT_EVENTS extended, STRIKEOUT_EVENTS new) serves the matchup
  grid lines, the popup per-pitch lines and the form table, so the
  surfaces can never disagree. The season counting lines were already
  the official statsapi lines and needed nothing. After the fix the
  three sample batters' window PA/AB/H/HR/K match the official game
  logs exactly.
- The timeframe toggles themselves verified accurate: the count/unit
  math (weeks times seven, months capped at three times thirty), the
  90-day record span always covering the longest selectable window, the
  season endpoints pinned to the regular season and year, the form
  L7/L14 reaches, and the D-142 three-month pitcher window all pull
  what their surfaces name.

Full gate green (3456 passed, 1 skipped — a new regression test pins
the official scoring rules on the shared aggregation, and the form
table's volume-count test now carries an intentional walk and a
truncated PA), consistency check clean, all four showcase runners
clean.


## D-149 - Deploy repair: force the host's environment rebuild (the D-137 cache-bust, second use)

2026-08-31: after D-148 merged, the deployed app served a TypeError
crash page from inside the board build. The identical commit built the
same slate cleanly off-host — on Python 3.12 and on a freshly resolved
Python 3.14 environment (the host's interpreter family) — so this is
the D-137 failure mode again: Streamlit Community Cloud's cached
install environment drifting from the checked-out code. The fix is the
D-137 mechanism: the cache-bust comment in requirements.txt changes,
which forces the host to rebuild its environment from scratch on the
next deploy. No application code changed.


## D-150 - A build failure shows its own traceback; the redacted crash page never hides a frame again

2026-08-31: the deployed app kept serving the redacted TypeError crash
page after D-149's from-scratch environment rebuild, while the identical
commit built the same slate cleanly off-host on Python 3.12 and a fresh
3.14 environment — so the failure is real on the host and the redaction
was costing a full diagnostic round per guess. The build call now sits
inside the same degradation pattern the tabs already had (D-075): an
unexpected exception empties the build blot, names the failure in an
error banner, and prints the full traceback in a code block. This is
an owner-only app — a traceback names code paths, never secrets — and
the surface is permanent: any future host-side failure is diagnosable
on first load instead of after a deploy-and-wait per hypothesis. (D-149
stays as the record of the first repair attempt; its mechanism was the
right one under the D-137 precedent, it simply was not the cause.)

Full gate green (3457 passed, 1 skipped — a new AppTest drives a
synthetic build failure through the real entry path and asserts the
named surface, the printed traceback, and zero uncaught exceptions),
consistency check clean, all four showcase runners clean.


## D-151 - Deploy repair, second round: a real specification change, and the failure surface names the module's origin

2026-08-31: the deploy after D-149 still served the pre-D-143 installed
package — the traceback (now visible via D-150) reads
"build_board() got an unexpected keyword argument
'fetch_pitcher_season_events'", a D-143 parameter, while the checkout's
streamlit_app.py is current. The comment-only cache-bust did not rebuild
the host's environment, so its cache evidently keys on the dependency
specifications and ignores comments. This round moves the tzdata floor
for real (a specification change must invalidate any sane cache key) —
pyproject and the deployment-contract test move with it, deliberately,
since the contract pins the requirements file line-for-line. The D-150
failure surface also prints the resolved pipeline module file and
build_board's actual parameter list, so if the host still serves a
stale install the next load names exactly where it resolves from. No
application behaviour changed.

Gate: full suite green after the three-file dependency move; no logic
changed.
