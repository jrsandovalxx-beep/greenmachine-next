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
