# FEATURE_PHASE_PLAN v12 — GMF-001 … GMF-009

**v12 is revision r2's third candidate — it answers the two findings of the v11 rejection
(2026-08-20).** Finding 1 (GMF-007's seven form fields were never placed into the contract before
the field set is fixed at §GMF-006): §7 gains the three missing general-window fields — attack-angle
mean over swings, hard-hit share over batted-ball events, xwOBA per plate appearance — and
§GMF-006 criterion 6 ingests them alongside the other r2 fields; PO-N3's "Pull%" is ruled by the
Product Owner (2026-08-20) to **be** the existing D-023 Pull Air %, labelled as such on the surface,
so no new pull field exists. Finding 2 (the "locked floors" covered only four of the seven metrics):
the Product Owner ruled 2026-08-20 that each uncovered floor follows its shared denominator —
**AtkAng 25 swings** (as Ideal Attack Angle %), **Hard% 15 BBE** (as Barrel%/EV), **xwOBA 15 PA**
(its per-PA denominator, the same count) — and D-068 now carries the per-metric floor table, so no
builder infers a threshold anywhere.

**v11 is revision r2's second candidate — it answers the three findings of the v10 rejection
(2026-08-20).** Finding 1 (the candidate bytes were missing from the review submission): the review
package now carries the complete candidate bytes inline as the review object — the package is
self-contained per D-047, and the stated hash is computed over exactly those bytes. Finding 2
(D-065 collided with the switch-hitter rule of D-025, confirmed in D-026, without declaring
supersession): D-065 now declares the supersession explicitly and preserves D-025's never-average
clause — the append-only register gains a superseding entry, and history is not rewritten. Finding 3
(D-068's "absent with its reason" contradicted the missing-versus-insufficient rule of D-023/D-025
and had no absence state to mean it): D-068 now follows the standing rule — below floor is
**present with its value, its exact sample, and an INSUFFICIENT marker**; only a field with no
observations at all is absent, under the ordinary absence semantics. No new absence state is
invented and the contract's vocabulary is untouched.

**v10 is revision r2's candidate — it lands what the 2026-08-20 handoff recorded as banked, and
nothing else.** Two ratified-but-unlanded decisions (origin-first provider precedence; the sample
contract), one banked ruling without a number (switch-hitter side handling), and the three Product
Owner feature notations recorded 2026-08-18. The register extension is **D-063..D-068** (§4b-r2),
the order table gains **GMF-007, GMF-008, GMF-009** (§4a), the object total moves **19 → 30**
(§4c), the §7 contract gains the fields the notations need **before** §GMF-006 fixes the field
set, and §GMF-006's criteria extend accordingly. The Product Owner ruled the notations' postures
on 2026-08-20: the form section and the usage-scope toggle are authorized as tickets; the matchup
notation is authorized as a **window only — no score** (D-067). No criterion of
GMF-001..GMF-005 changes; no completed record is touched; completed link-backs keep their
historical hashes per the v15 → v16 precedent (§3a) and the r1 precedent (§4b-r1).

**v9 was revision r1's third candidate — it answers the one finding of the v8 rejection**: r1 is
**two** review objects, not one — the candidate-bytes document review and the later revision-bound
commit review are distinct objects, exactly as the original lifecycle counted "this plan" and
§GMF-000R separately. §4c now carries both r1 rows, the exact total is **19**, the `TEAM_ROLES.md`
mirror moves to the same number, and the r1 package must sweep the tree for any other committed
statement of the object total, reporting rather than absorbing anything it finds.

**v8 was revision r1's second candidate — it answered the four findings of the v7 rejection**: the
ruling date v7 memorialized was false (the ruling was issued 2026-08-10, not 2026-08-11 — a wrong
date written into the paragraph that exists to keep the record accurate); v7's r1 delta omitted
`docs/TEAM_ROLES.md`, whose committed text mirrors §4c at 17 objects and would have contradicted
the plan the moment r1 merged; v7's register statement blurred the reviewed submission-1 head
against `staging`; and D-061 claimed an AppTest capability Streamlit 1.37 does not provide — the
testing boundary is now stated falsifiably and §GMF-002's coverage criterion binds to it.

**Revision r1 repairs one dangling referent, nothing else.** Executing §GMF-002 exposed
that its phrase *"the five research-captured decisions"* had no committed referent: the GR-002 grid
decisions were captured in Lead working notes, designated for the D-047 landing, and dropped from
§GMF-000R's delta — an omission the plan's own "count: 57" made self-consistent, so it survived
every prior review (D-050: a criterion whose referent is uncommitted is a criterion defect). The
reviewer's 2026-08-10 ruling rejected both landing-without-revision vehicles and required this
revision. r1 enumerates the five as **D-058..D-062** (§4b-r1, Product-Owner-ratified 2026-08-10),
authorizes their landing **inside §GMF-002 submission 1** with the coupled pack-count move, and
adds the revision's two objects to §4c (total 19). No ticket criterion outside §GMF-002 submission 1
changes; no completed record is touched.

**v6 answers the two findings of the v5 rejection**: v5 mis-stated what the v4 rejection was, and its
version-label coupling protected only one of the two plan records. **The v4 rejection, stated
correctly: v4's §5a fixed the active record as `FEATURE_PHASE_PLAN v3` while v4's own title
identified v4** — a v3-versus-v4 mismatch, not the v4-versus-v5 one v5 described. Revision history:
v5 answered v4's one, v4 answered v3's three, v3 answered v2's three, v2 answered v1's seven. Six were drafting defects and are fixed here.
v1's finding 1 was **overridden by the Product Owner** under D-020 and the reviewer has accepted the
override as controlling project governance; the finding stands unretracted. **Every finding of every round is accepted and fixed** — the manual-export boundary is now mechanically enforced
rather than attested (§8, GMF-001 and GMF-006), the context pack's authority statement enters the
permitted delta (§6), and the second pack-hash guard gets a fixed record form and negative
demonstrations (§5, §6).

Bootstrap state at the time of writing: `staging` = `b854f23cbd8b54d8a4f938c93fe71a4d62dfec2b`,
six completed records, zero deselections, `ACTIVE.md` at the sentinel, checker clean on `staging`.

---

## 1. The override, stated before anything is built on it

GPT finding 1 held that the plan had not demonstrated authorization to obtain, commit and publicly
display Baseball Savant data. **The Product Owner has overridden that finding** (D-057). The record
is honest about what it sets aside:

> "Except for downloading one copy … for your personal, non-commercial home use, you must not
> reproduce … distribute, perform or **display** the MLB Digital Properties without first obtaining
> the written permission of MLB"

The use is non-commercial; it is not confined to one copy on one device for home use, because the
deployment is public; written permission has not been sought. **No claim is made that the conduct is
permitted.** This is a decision to proceed despite the terms.

**The override is narrow. Two boundaries survive it:**

- **Automated collection remains prohibited** — MLB terms clause (xi) is a *separate* term and is
  not overridden. All MLB-derived data enters by **manual export performed by the Product Owner**.
  §GMF-006 is re-scoped accordingly and must prove no code path fetches from an MLB host.
- **Ballpark Pal remains excluded** (D-051). Its terms are an affirmative click-through agreement,
  not a site notice, and the Product Owner does not rely on the provider.

The reviewer is asked to review the plan **as overridden** — that is, to test everything except
finding 1, and to say so if the override's boundaries are drawn incoherently.

---

## 2. Inherited rules, and where they stop applying

Plan v15's lifecycle continues: two-plus PRs per ticket with distinct implementation and closeout
criteria; the fixed four-file closeout delta; revision binding per D-028a with the **full diff**;
Regime B evidence; D-038 verdict certification; the D-015/D-017 surface; merges into `staging` only
after approval of a named head, **no exception in this phase**.

**Finding 3 fix — the path-specific portions are superseded for GMF objects.** "Inherits unchanged"
could not bridge these; each is now fixed text:

| Lifecycle element | Bootstrap form | **GMF form** |
|---|---|---|
| Active pointer, line 1 | `Active: GMR-00N per REBUILD_PLAN §GMR-00N` | `Active: GMF-00N per FEATURE_PHASE_PLAN §GMF-00N` |
| Active pointer, line 2 | `Completed records: tickets/completed/ — order table in REBUILD_PLAN (lifecycle, closeout rule c).` | `Completed records: tickets/completed/ — order table in FEATURE_PHASE_PLAN (lifecycle, closeout rule c).` |
| Implementation plan binding | `sha256(tickets/REBUILD_PLAN.md)` | `sha256(tickets/FEATURE_PHASE_PLAN.md)`, **and** the REBUILD_PLAN hash pasted unchanged as proof the historical plan was not touched |
| Completed record | `tickets/completed/GMR-00N.md` | `tickets/completed/GMF-00N.md` |
| Record link-back | `ticket text: REBUILD_PLAN §GMR-00N @ sha256 …` | `ticket text: FEATURE_PHASE_PLAN §GMF-00N @ sha256 …` |
| Closeout criterion (c) order authority | REBUILD_PLAN order table | **FEATURE_PHASE_PLAN §4 order table**, which carries the complete combined sequence |
| Context pack | one plan record | **two plan records**, historical and active, each with its own pinned hash |

**Two practice additions earned in the bootstrap, both binding here:**

- **Inventories travel whole** — an inventory criterion is satisfied by the inventory or its content
  hash, never by a diff of it. (GMR-005 verdict.)
- **A criterion satisfiable only by fabricating output is a criterion defect** — the builder states
  the impossibility, supplies the evidence the criterion reached for, and discloses the substitution.
  (GMR-005 criterion 4; D-050.)

---

## 3. Defect fixes carried by this plan

### 3a. REBUILD_PLAN §GMR-005 criterion 4 — an unsatisfiable literal, and a version bump

Current text requires "the collection summary shows **`(0 deselected)`**". pytest emits a
`deselected` figure only when the count is nonzero. **Replacement:** *"the collection summary shows
no `deselected` term and selection equals collection, with the deselect-free `addopts` table
pasted."* This corrects a completed ticket's text; it does not reopen GMR-005.

**The amended plan becomes REBUILD_PLAN v16** (v3 finding 3 fix). v3 changed the bytes while keeping
the label "v15", so two different byte streams would both have been called v15 and the statement
"Plan v15, approved 2026-07-28" would have named two things. **§GMF-000R changes the version line in
the same commit**, and the package pastes the **old v15 hash
`3daa28b952f3c78d80c2d01764f495e3866eb68e32d13de86ac6f7a67646d904`, the new v16 hash, and the
complete two-line diff** — the version line and the criterion correction, and nothing else.

**Completed records keep their v15 link-backs, untouched.** `tickets/completed/GMN-000A.md` through
`GMR-005.md` record the authority those tickets actually ran under; rewriting them to say v16 would
falsify the record. This is a forward version bump, not a retroactive one.

### 3b. `PROJECT_STATE.md` — the stale GMR-003R line

Replace `- **GMR-003R: the revision object of this PR** — …` with the COMPLETE form naming merge SHA
`21cd7d1e021dbde825900d5711bdc23f081a887c`. Directed by the reviewer to "the next scope-authorized
state-file update"; §GMF-000R is that object.

---

## 4. Order table, decision register, and object arithmetic

### 4a. Order table — the complete combined sequence, authoritative here

```
GMN-000A → GMR-001 → GMR-002 → GMR-003 → GMR-004 → GMR-005
        → GMF-001 → GMF-002 → GMF-003 → GMF-004 → GMF-005 → GMF-006
        → GMF-007 → GMF-008 → GMF-009 → sentinel
```

Sentinel unchanged: `NO ACTIVE TICKET — next phase pending planning` (em dash, U+2014).

### 4b. Decision register — finding 4 fix, the gap closed

**The committed register ends at D-046.** D-047 and D-048 were drafted in Lead working notes and
never landed, so v1's "D-049 … D-056, count 56" asserted a sequence with a hole in it. The new
decisions are therefore numbered **continuously from D-047**, and the two drafted rules — both
operationally in force through the entire bootstrap — are landed rather than skipped.

| ID | Decision |
|---|---|
| **D-047** | **Transport envelope.** Every artifact between conversations travels as `.md`. Byte-exact artifacts travel as base64 inside it, with the decode command and target hash stated. Documents over 180 KB are chunked with an index and a receipt protocol. Five delivery failures paid for this rule. |
| **D-048** | **Cover-message authority.** The paste message accompanying an artifact is Claude Lead's instrument and carries Lead's instructions; it is not a summary of the artifact. Where a cover message and the plan disagree, **the plan wins**, and the builder reports the conflict rather than resolving it. |
| **D-049** | **Permitted deltas are content-scoped, not path-scoped.** A file in a permitted path list licenses only the content changes that list enumerates. A reviewer aside cannot widen a hash-pinned plan; only a plan-revision object can. |
| **D-050** | A criterion satisfiable only by fabricating output is a criterion defect. See §2. |
| **D-051** | **Ballpark Pal is excluded from the deployed application.** *(Finding 7 fix.)* Its terms bar powering anything "made available to others," and a private deployment with invited viewers still makes it available to others. Provider data may enter a deployment only where access is limited to the licensed Product Owner **as sole user**, with no invited or shared viewers, **or** under written provider permission covering the actual audience. Private-versus-public is not the test; sole-user-versus-anyone-else is. |
| **D-052** | **No third-party provider data becomes a repository fixture or golden file.** Committing it is redistribution. This binds for Ballpark Pal and any future licensed provider; it does **not** bind MLB-derived data, which D-057 addresses expressly. |
| **D-053** | **Park factors: the pinned Baseball Savant per-handedness snapshot is the source of record.** Reinstated under D-057. Provenance-pinned: source URL, export date, row count, sha256. |
| **D-054** | **Weather: `api.weather.gov` (NWS).** Open data, free for any purpose; no API key; an identifying `User-Agent` required; unpublished rate limits, over-limit requests retryable typically within ~5 seconds; documentation notes a key may be introduced later. |
| **D-055** | **Venue type is part of the park reference data.** Fixed/closed roof → forecast suppressed with a stated reason; open air → forecast applies; retractable with status unknown → explicit unknown. NWS covers the US only; Rogers Centre renders the same explicit unavailable state. |
| **D-056** | **The project has no secrets.** Neither source needs a credential. The `st.secrets` provisioning deferred through GMR-004 stays deferred until an object introduces a credentialed provider and states its handling rule first. |
| **D-057** | **Product Owner override of GPT finding 1**, per D-020, with the two boundaries of §1. Reversible: withdrawal means removing the committed snapshot and MLB-derived surfaces from the deployment, which the manual-export path and the adapter seam keep recoverable. |

**Resulting decision count: 57 (D-001..D-057), continuous, no gap.** §GMF-000R must prove
continuity mechanically, not assert it.

### 4b-r1. Register extension at revision r1 — D-058..D-062 (the five grid decisions)

From the GR-002 grid-component research brief; **Product Owner ratified all five as recommended,
2026-08-10.** These are the referent of §GMF-002 submission 1's criterion, and that submission
lands them in `DECISIONS.md` **verbatim from this table**, moving `CONTEXT_PACK.md`'s decision
count 57 → 62 in the same commit (the checker binds the two together).

| ID | Decision |
|---|---|
| **D-058** | **No inline master-detail; selection-driven detail panel.** Inline expansion forces AG Grid Enterprise licensing, an untestable iframe grid, and version-coupling risk. Row selection (`on_select`) drives a detail surface instead. |
| **D-059** | **No `matplotlib` dependency.** Cell grading is hand-rolled via `Styler.map`; revisit only if hand-rolled grading proves inadequate, as a new decision. |
| **D-060** | **Theming via `.streamlit/config.toml` only.** Never style against `st-emotion-cache-*` classes or `data-testid` attributes — not public API, breaks silently on upgrade. Cell colour comes from `Styler` inline styles. |
| **D-061** | **The core table stays testable: native `st.dataframe`, with the testing boundary stated at the version floor.** An untestable core UI surface is not acceptable — and neither is a claimed test capability the floor version does not provide. At Streamlit 1.37, `AppTest` exposes the dataframe as an element and **cannot synthesize row selection** (selection state is not programmatically settable). The boundary, falsifiable at 1.37: **AppTest proves the element's handed-off data and configuration** — column set, order and visibility, density configuration, graded values, and every absence state's rendering as data; **the selection-consumption path** (the code receiving a selection and producing detail state) **is proven by direct tests as ordinary code**; **the click-to-detail interaction and visual legibility are observed at §GMF-002 submission 2** on the deployed page. No AppTest capability is claimed beyond the floor's. |
| **D-062** | **Streamlit is version-bounded; upgrades land through `staging` first.** Floor **>= 1.37** (`on_select` arrived 1.35; `st.fragment` stable in 1.37), with a defended upper bound against third-party breakage. |

**Register statement, by state.** The reviewed §GMF-002 submission-1 head itself carries the
landing — `DECISIONS.md` through D-062 and the pack count at **62** — and that head's package and
checker prove exactly that state, pre-merge, as the lifecycle requires. **`staging` remains at 57**
until that approved head merges, and reads **62 (D-001..D-062), continuous, no gap** after it.
The r1 plan-revision commit itself moves no decision: its permitted delta is exactly four
files — `tickets/FEATURE_PHASE_PLAN.md` (this text), `scripts/check_consistency.py` (the
`PINNED_FEATURE_PLAN_SHA256` constant only), `CONTEXT_PACK.md` (the active-plan record line
only: version label and hash; **the decision count does not move at r1**), and
`docs/TEAM_ROLES.md` (**the object-structure mirror only**: its
"17 review objects" total becomes 19 and its object list gains the two r1 entries,
mirroring §4c — nothing else in that file changes; its committed text was authored by §GMF-000R to
mirror §4c, so §4c moving without it would leave two committed object structures in
contradiction). **The r1 package must additionally sweep the tree for any other committed
statement of the object total** and demonstrate `TEAM_ROLES.md` is the only mirror; a further
mirror, if one exists, is reported as a finding — the delta does not authorize touching it.
§GMF-002 submission 1's package proves the landing mechanically — the
`DECISIONS.md` tail and the pack count, shown together. **Completed records keep their v6-hash
link-backs untouched**, per the v15 → v16 precedent (§3a): a forward version bump, never
retroactive.

### 4b-r2. Register extension at revision r2 — D-063..D-068 (providers, samples, switch-hitters, and the three notations)

The 2026-08-20 handoff recorded two decisions **ratified by the Product Owner and banked for this
revision** (origin-first provider precedence; the sample contract), one banked ruling carried
without a number (switch-hitter side handling), and **three Product Owner feature notations
recorded 2026-08-18**. This revision lands all six. **The Product Owner ruled the notations'
postures on 2026-08-20**: the form section and the usage-scope toggle are authorized as tickets
(§GMF-007, §GMF-008); the matchup notation is authorized as a **window only — no score** (D-067,
§GMF-009).

| ID | Decision |
|---|---|
| **D-063** | **Origin-first provider precedence.** (a) Baseball Savant is the origin source for Statcast-derived fields and takes precedence wherever it carries the field. (b) FanGraphs is admitted only for fields the project computes itself from its own inputs — never for re-display of FanGraphs-authored metrics (the §24 marks posture stands). (c) Origin-unavailable exception: where Savant does not carry a field at all, a secondary provider may supply it, and the exception is named in that field's provenance note. |
| **D-064** | **The sample contract.** AB, H and K are carried as raw counts, each with its unit and an observed/derived flag. `BIP_est = AB − K` is a derived estimate that understates balls in play by sacrifice flies and hits; the understatement is stated wherever the estimate appears, never hidden. K is carried as a count, never reconstructed as K% × AB. A derived field propagates the absence reason of every input it derives from, intact. |
| **D-065** | **Switch-hitter side handling (supersedes the switch-hitter resolution rule of D-025, confirmed in D-026).** A switch hitter's row carries **both** batting sides, each labelled by the opposing pitcher hand that produces it. The batting side used in any display is derived from the matchup and labelled as derived; it is never silently chosen. Probable-starter resolution is not a dependency of any surface; if it ever arrives it is an additive derived layer, never a contract input. D-025's never-average clause stands: both sides are never averaged into one number for a criterion. |
| **D-066** | **Pitch-usage scope toggle (PO-N1).** The batter metrics surface gains a user toggle between (a) usage measured against batters of the evaluated side and (b) all pitches the pitcher throws. The toggle requires the handedness-split usage denominator, which enters the contract at §7 and is ingested at §GMF-006, before the field set is fixed there. The three usage states (qualifies · measured below threshold · absent/unevaluable) survive both toggle positions, and the prose names which scope produced each suppression. Scheduled as §GMF-008. |
| **D-067** | **Matchup window; score deferred (PO-N2).** The matchup section is computed over a **rolling 30 days** ending at `as_of` — not a calendar month. **This ruling authorizes the window only. No score is authorized.** A windowed score is ranking-shaped under D-015/D-017 and requires its own explicit Product Owner posture ruling before any ticket text names it. Scheduled as §GMF-009. |
| **D-068** | **Form section (PO-N3).** Seven metrics, no toggle: Barrel%, EV, AtkAng, IdealAtkAng%, Pull%, Hard%, xwOBA — where **Pull% is the D-023 Pull Air %**, labelled as such on the surface (Product Owner, 2026-08-20). Window **L7 with an L14 fallback**, the fallback triggered by **each metric's own sample floor** — never by mere emptiness. Floors: Barrel% and EV **15 BBE** (D-023/D-026); IdealAtkAng% **25 tracked swings** (D-023); Pull Air % **15 air balls** (D-023); **AtkAng 25 swings**, **Hard% 15 BBE**, **xwOBA 15 PA** (Product Owner, 2026-08-20 — each uncovered floor follows its shared denominator). A field whose L14 sample is below its floor is **present with its value, its exact sample, and an INSUFFICIENT marker** — the missing-versus-insufficient rule of D-023/D-025 is unchanged, and no new absence state is created. A field with no observations at all is absent with its reason under the ordinary absence semantics. The window actually used is named on the surface, per D-025's stated-window rule. Scheduled as §GMF-007. |

**Landing vehicle.** Unlike r1 — which authorized the landing inside a later submission because
its decisions belonged to that submission's implementation — the r2 decisions are ratifications
that exist independent of any one ticket, so the r2 commit object (§6-r2) lands D-063..D-068 in
`DECISIONS.md` **verbatim from this table** and moves `CONTEXT_PACK.md`'s decision count **62 → 68**
in the same commit. This is the §GMF-000R precedent: the plan-commit object itself appended
D-047..D-057. The r2 package proves the landing mechanically — the `DECISIONS.md` tail and the
pack count, shown together, plus the continuity check over D-001..D-068 (§6-r2 criterion 4).

**Register statement:** after the r2 commit merges, the register reads **68 (D-001..D-068),
continuous, no gap**. `staging` remains at 62 until it does.

### 4c. Review objects — finding 5 fix, determinate

v1 stated fourteen while its own ticket text described more. Every ticket now has a **fixed** object
structure; none is builder-elective.

| Ticket | Objects | Why |
|---|---|---|
| this plan | 1 | document review |
| this plan, revision r1 — document review | 1 | candidate-bytes review of the revision text; mirrors the "this plan" row |
| this plan, revision r1 — commit | 1 | plan-revision commit, GMF-000R shape — repairs §GMF-002's referent; delta fixed in §4b-r1 |
| this plan, revision r2 — document review | 1 | candidate-bytes review of the revision text; mirrors the r1 rows |
| this plan, revision r2 — commit | 1 | plan-revision commit, GMF-000R shape — lands D-063..D-068 and the post-freeze tickets; delta fixed in §6-r2 |
| §GMF-000R | 1 | plan commit; no completed record |
| §GMF-001 | 2 | impl + closeout; no deployed surface |
| §GMF-002 | **3** | impl + **post-merge deployed verification** + closeout |
| §GMF-003 | 2 | fixtures; verified by test and local render |
| §GMF-004 | 2 | fixtures; verified by test and local render |
| §GMF-005 | **3** | impl + **post-merge deployed verification** + closeout |
| §GMF-006 | **3** | impl + **post-merge deployed verification** + closeout |
| §GMF-007 | **3** | a new surface rendering real provider data on the public app gets the §GMF-002 pattern: impl + deployed verification + closeout |
| §GMF-008 | **3** | as above — a behaviour change on a live surface |
| §GMF-009 | **3** | as above |

**Exact total: 30 review objects** (19 at v9; +2 for r2, +9 for the three post-freeze tickets).

### 4d. Deployed evidence — finding 6 fix, a route that exists

The deployed app tracks `staging`; an unmerged feature head is not deployed. v1 demanded deployed
evidence with no route to produce it. **The route is the proven GMR-004 two-submission pattern:**

- **Submission 1** — implementation. Reviewed on its own head, approved, **then merged**.
- **Submission 2** — post-merge deployed verification. Head of record is `staging` after that merge.
  Reviewed against its own criteria. **No D-018-style exception:** submission 1 merges only after
  its own approval, and submission 2 merges nothing.
- **Closeout** follows submission 2's approval and quotes **both** verdicts, as GMR-004's did.

*A preview deployment tracking feature branches was considered and rejected:* it adds a second
public Streamlit app to keep clean and a standing risk of divergence between two deployments, to
save a review object on three tickets. The two-submission pattern is already reviewed and understood
by all three parties.

---

## 5. The checker, and what §GMF-000R must change in it

`scripts/check_consistency.py` today hard-codes the bootstrap and parses two prefixes:

```python
ORDER = ("GMN-000A", "GMR-001", "GMR-002", "GMR-003", "GMR-004", "GMR-005")
PINNED_PLAN_SHA256 = "3daa28b9…"
m = re.search(r"^Active:\s*(GM[NR]-\w+|NO ACTIVE TICKET.*?)\s*(?:per\b.*)?$", txt, re.M)
```

**`GMF-001` does not match `GM[NR]-\w+`** — tested: `active_pointer()` returns the empty string and
rules 1 and 4 both fail. Reviewer approved the widening over renumbering.

**Finding 2 fix — two plans, two independently checked pins.** A single constant cannot guard two
files, and a hash pasted in a package is review-time evidence, not a continuing mutation guard.
§GMF-000R replaces the single constant with two:

```python
PINNED_REBUILD_PLAN_SHA256 = "<sha256 of REBUILD_PLAN v16>"
PINNED_FEATURE_PLAN_SHA256 = "<sha256 of the committed FEATURE_PHASE_PLAN.md>"
```

and adds a rule per file, so **any later change to either plan turns the checker red.**
Rule count rises from 8 to **10**.

**The banned-phrase rule must also follow the active authority (v3 finding 1 fix).** Rule 5 scans
`tickets/REBUILD_PLAN.md` for the seven retired-lifecycle phrases. It was not in v3's checker delta,
and under D-049 the builder could not have extended it on inference. Leaving it bound to the
historical plan means **a later, legitimately reviewed and re-pinned feature-plan revision could
carry a retired phrase with the checker still green** — the hash rules protect today's approved
bytes, but the phrase rule exists precisely to survive tomorrow's authorized re-pins. §GMF-000R
therefore **extends rule 5 to scan both plans outside fenced blocks**. This is an expansion of an
existing rule, not an eleventh rule; the count stays at **10**.

**What r2 changes in the checker, and what it does not.** The r2 commit (§6-r2) updates
`PINNED_FEATURE_PLAN_SHA256` to the v12 hash and extends `ORDER` with GMF-007, GMF-008, GMF-009 per
§4a. **No rule is added, removed, or reworded; the count stays at 10.** The two record-anchored
pack rules and the version-label coupling are untouched — they bind to the records and titles,
not to any version literal, which is exactly why a revision can re-pin without weakening them.

### 5a. The two pack records — fixed forms, and why the form matters (v2 finding 3 fix)

Existing rule 7 does not search `CONTEXT_PACK.md` for a hash-shaped string. It anchors to the Plan
record itself — `^- Plan: REBUILD_PLAN.*?(?=^- |\Z)` — precisely so that *"an unrelated entry
carrying the right value cannot mask a stale Plan record."* The new parallel rule gets the same
hardening or it is weaker than the rule it sits beside.

**The two records take exactly these forms, with distinct labels:**

```
- Plan (bootstrap, historical): REBUILD_PLAN v16, sha256 `<64 hex>` — the pinned authority for
  GMN-000A … GMR-005; no longer the active ticket source.
- Plan (active, feature phase): FEATURE_PHASE_PLAN v12, sha256 `<64 hex>` — the pinned authority for
  GMF-001 … GMF-009.
```

**The self-reference trap, and why it is closed mechanically rather than by care.** This plan fixes
the exact text of a record that names *this plan's own version*. Every revision therefore falsifies
that line — **the v4 rejection was exactly that: v4's record read `FEATURE_PHASE_PLAN v3` while v4's
title read v4.** Bumping the number each round fixes the instance and leaves the trap.

**§GMF-000R therefore makes the coupling mechanical, for both records — not one.** v5 bound only the
feature record and claimed the class; the bootstrap record stayed protected by hash alone. That was
insufficient for a reason this very object demonstrates: **§GMF-000R is itself an authorized
revision of `REBUILD_PLAN.md`, v15 → v16.** A later authorized revision could change its bytes, hash
and pin while the pack label stayed at v16, and the hash rule would pass over a record that
misidentifies the plan it names. "Historical" does not mean immutable; this object proves it.

Both pack rules therefore additionally require **the version label in each record to equal the
version string in that plan's own title line**:

| Pack record | Version label must equal the title version of |
|---|---|
| `- Plan (bootstrap, historical): REBUILD_PLAN v16 …` | `tickets/REBUILD_PLAN.md` |
| `- Plan (active, feature phase): FEATURE_PHASE_PLAN v12 …` | `tickets/FEATURE_PHASE_PLAN.md` |

A revision that updates either plan's title without its record, or either record without its title,
turns the checker red instead of shipping a record that misnames its own authority.

**Each rule anchors to its own complete record** and extracts the hash from within that record only:

```python
BOOT = re.search(r"^- Plan \(bootstrap, historical\): REBUILD_PLAN.*?(?=^- |\Z)", pack, re.M | re.S)
FEAT = re.search(r"^- Plan \(active, feature phase\): FEATURE_PHASE_PLAN.*?(?=^- |\Z)", pack, re.M | re.S)
```

A missing record **fails** the rule rather than passing vacuously, exactly as rule 7 does today. The
label change means §GMF-000R must also re-anchor rule 7 itself; both anchors are part of the
`scripts/check_consistency.py` delta.

---

## 6. §GMF-000R — plan commit, with an exact permitted delta

**Builder:** Fable · **Regime:** B · **No completed record** (plan-revision object, GMR-003R
pattern) · **Base:** `staging` at `b854f23cbd8b54d8a4f938c93fe71a4d62dfec2b`

**Finding 4 fix — the permitted delta is exactly these eight paths, and all eight change:**

| Path | Change |
|---|---|
| `tickets/FEATURE_PHASE_PLAN.md` | **new** — these approved bytes, unaltered, sha256 pasted |
| `tickets/REBUILD_PLAN.md` | §3a: criterion-4 correction **and the version line v15 → v16**; old and new hashes pasted with the complete two-line diff |
| `scripts/check_consistency.py` | `ORDER` per §4a; regex → `GM[NRF]-\w+`; dual pins and two record-anchored pack rules per §5/§5a; **rule 5 extended to scan both plans**; rule 7 re-anchored to its new label; **both pack record rules additionally bind each record's version label to that plan's own title line** |
| `tickets/ACTIVE.md` | **both lines** — pointer to GMF-001, and the order-table location corrected to FEATURE_PHASE_PLAN |
| `DECISIONS.md` | D-047 … D-057 appended per §4b |
| `PROJECT_STATE.md` | §3b GMR-003R correction; phase-transition line |
| `CONTEXT_PACK.md` | **four** enumerated changes: the opening **authority statement** (see below); active ticket GMF-001; the two **plan records** of §5a replacing the single one; decision count 57 |
| `docs/TEAM_ROLES.md` | the per-object regime table extended to the six GMF tickets and their 17-object structure |

**The `CONTEXT_PACK.md` authority statement — v2 finding 2 fix.** The pack opens by naming
`tickets/REBUILD_PLAN.md` as *the* authoritative ticket text. That sentence becomes **false on the
first GMF ticket**, and v2's enumerated delta did not authorize touching it — so under D-049 the
builder could neither fix it nor leave it correct. It is now inside the delta, with its replacement
fixed here:

> Hand-maintained orientation for builders. The authoritative state is `PROJECT_STATE.md`; the
> authoritative history is `DECISIONS.md`. **Ticket text has two pinned authorities:
> `tickets/REBUILD_PLAN.md` governs the completed bootstrap (GMN-000A … GMR-005) and
> `tickets/FEATURE_PHASE_PLAN.md` governs the feature phase (GMF-001 … GMF-006); `tickets/ACTIVE.md`
> selects which one governs the current object.** If this file disagrees with any of them, this file
> is wrong — the repository checker's freshness gate fails on a wrong active ticket or decision
> count here.

*(r2 note: §6-r2's delta authorizes the one further change to this statement — the feature-phase
range becomes `(GMF-001 … GMF-009)`. The quote above stays as committed: it is the historical
record of the text §GMF-000R authorized, and editing it here would falsify that record to fix a
label.)*

**The base-state inventory — corrected, and the correction matters more than the number.** v3
asserted three `REBUILD_PLAN` references in the pack, counting an active-ticket line that reads
`GMR-005 … per REBUILD_PLAN §GMR-005`. **That line does not exist at the stated base.** The GMR-005
closeout replaced it with the sentinel form, which names no plan. I produced the count by searching a
**stale copy** in the Lead workspace rather than the committed blob — the same failure I had caught
once already on `PROJECT_STATE.md` and then warned the builder about. Blob ID distinguishes them;
byte count does not.

**The actual base state**, verified against the committed blob `31223c3a248b97ea9b2c4eeffef778673e295b0c`
at `b854f23cbd8b54d8a4f938c93fe71a4d62dfec2b` — **two references:**

```
line  5:  `tickets/REBUILD_PLAN.md`. If this file disagrees with any of them, this file is wrong — the
line 21:  - Plan: REBUILD_PLAN v15, **APPROVED WITH NOTES 2026-07-28**, sha256
```

**Expected post-image inventory — also two**, both deliberate: the rewritten authority statement
names `tickets/REBUILD_PLAN.md` as the bootstrap authority, and the `Plan (bootstrap, historical)`
record names REBUILD_PLAN v16. The active-ticket line names `FEATURE_PHASE_PLAN` and contributes
none.

**§GMF-000R pastes both inventories in full** — before and after, every matching line — per this
plan's own whole-inventory rule (§2), which v3 violated by summarizing an inventory into a count.
A third base occurrence appearing between now and the build is then caught rather than carried.

**Standing correction to Lead practice, recorded here because it caused this defect:** a base-state
inventory is taken from the committed blob with its blob ID stated, or it is taken from the builder
at its own head. It is never taken from a working copy in the Lead workspace.

**Criteria**

1. Plan binding: the committed `FEATURE_PHASE_PLAN.md` bytes equal the approved bytes; sha256 pasted
   and equal to the reviewed value.
2. **Atomicity.** Every change above lands in **one commit**. No committed state may carry a plan
   whose hash disagrees with its pin — that invariant is the whole purpose of the pin.
3. **Both pins proven, in both directions:** each pinned constant equals the sha256 of its file, and
   editing either file by one byte turns the checker red. **Show the negative case**, not only the
   positive.
4. **Parser proven negatively and positively** — reviewer's requirement: a GMF pointer parses; a
   malformed prefix fails; the exhausted-table sentinel still resolves. All three pasted.
5. **Decision register continuity proven mechanically:** every ID D-001..D-057 present exactly once,
   no gap, no duplicate, no dangling citation to a nonexistent decision. Paste the check, not a claim.
6. `ACTIVE.md` at GMF-001, both lines exact per §2's table.
7. **Both pack records proven, positively and negatively.** The two records take the §5a forms with
   their distinct labels. Beyond the positive pass, **five red outcomes are demonstrated and
   pasted**, then the pack is restored and the ten-rule checker shown clean:
   (i) wrong historical-plan hash in its own record; (ii) wrong feature-plan hash in its own record;
   (iii) historical record missing entirely; (iv) feature record missing entirely; (v) **the decoy** —
   an unrelated pack entry carrying the correct hash while the authoritative record carries a wrong
   one, which must still fail. Case (v) is the shape rule 7 was hardened against; the new rule
   inherits that hardening or it is weaker than the rule beside it.
8. **Version-label coupling proven for BOTH records**, in the five steps the reviewer enumerated:
   (i) both labels match their respective plan titles and the rules pass; (ii) alter only the
   bootstrap record **or** the `REBUILD_PLAN.md` title and show the named failure; (iii) restore;
   (iv) alter only the feature record **or** the `FEATURE_PHASE_PLAN.md` title and show the named
   failure; (v) restore and show the final checker clean. An extension of the two existing pack-record
   rules; the count stays at ten.
9. **Banned-phrase rule proven against the new plan**: insert one fixed retired-lifecycle phrase
   outside a fence in `tickets/FEATURE_PHASE_PLAN.md`, show the named banned-phrase failure, restore
   the file, show clean. A rule that scans a file it has never been shown to fail on is untested.
10. **Both pack inventories pasted in full** — the two base occurrences and the two post-image
   occurrences, every matching line, per §6's corrected inventory.
11. Checker clean at **10** rules; full suite green; D-015/D-017 clean; Regime B; revision binding
   with full diff inlined.

**No feature code.** A single non-plan, non-checker, non-governance source change fails this object.

---

## 6-r2. The r2 commit — plan revision, with an exact permitted delta

**Regime:** B · **No completed record** (plan-revision object, the §GMF-000R / GMR-003R pattern) ·
**Base:** `staging` at the head current at build time, pasted in the package.

**The permitted delta is exactly these five paths, and all five change:**

| Path | Change |
|---|---|
| `tickets/FEATURE_PHASE_PLAN.md` | these approved v12 bytes, unaltered, sha256 pasted |
| `DECISIONS.md` | D-063 … D-068 appended **verbatim** from §4b-r2's table |
| `scripts/check_consistency.py` | `PINNED_FEATURE_PLAN_SHA256` → the v12 hash; `ORDER` gains `GMF-007`, `GMF-008`, `GMF-009` per §4a. **No rule added, removed, or reworded — the count stays at 10** (§5) |
| `CONTEXT_PACK.md` | **three** enumerated changes: the active plan-record line per §5a (label `v12`, the v12 hash, range `GMF-001 … GMF-009`); the decision count **62 → 68**; the authority statement's feature-phase range `(GMF-001 … GMF-006)` → `(GMF-001 … GMF-009)` |
| `docs/TEAM_ROLES.md` | **the object-structure mirror only**: the regime table gains the five r2-and-later rows (§4c), and the total sentence moves **19 → 30** with its new breakdown — nothing else in that file changes |

`tickets/ACTIVE.md` **does not change**: GMF-005 remains the active ticket under the revised plan,
and the r2 commit must not move the pointer. `PROJECT_STATE.md` **does not change**; the revision is
recorded here and in the pack, and GMF-005's own closeout remains the next scope-authorized
state-file update. The §6 quote of the pack's authority statement **stays as committed** — it is the
historical record of the text §GMF-000R authorized; r2's own change to that statement lives in the
delta above, and conflating the two would falsify the history to fix a label.

**The mirror sweep.** The r2 package must sweep the tree for any other committed statement of
(a) the object total, (b) the decision count, (c) the feature-phase ticket range `GMF-001 … GMF-006`,
and (d) the plan version label — and demonstrate `TEAM_ROLES.md` and `CONTEXT_PACK.md` are the only
mirrors. A further mirror, if one exists, is **reported as a finding, not absorbed** (D-049).

**Criteria**

1. Plan binding: the committed `FEATURE_PHASE_PLAN.md` bytes equal the approved v12 candidate bytes;
   sha256 pasted and equal to the reviewed value.
2. **Atomicity.** Every change above lands in **one commit**. No committed state may carry a plan
   whose hash disagrees with its pin.
3. **The feature pin proven in both directions:** the pinned constant equals
   sha256(`tickets/FEATURE_PHASE_PLAN.md`), and a one-byte edit to the file turns the checker red.
   **Show the negative case**, restore, show clean. The bootstrap pin is re-pasted unchanged as proof
   the historical plan was not touched (§2's binding rule).
4. **Decision register continuity proven mechanically:** every ID D-001..D-068 present exactly once,
   no gap, no duplicate, no dangling citation to a nonexistent decision. Paste the check, not a claim.
5. **Decision-count coupling:** the pack states **68** and the register holds 68 decision headers —
   checker rule 2's own output pasted, both sides shown.
6. **The feature pack record proven positively and negatively.** The record takes the §5a form with
   the `v12` label and the new hash. Beyond the positive pass, **three red outcomes are demonstrated
   and pasted**, then the pack is restored and the ten-rule checker shown clean: (i) wrong hash in
   the feature record; (ii) the feature record missing entirely; (iii) **the decoy** — an unrelated
   pack entry carrying the correct hash while the authoritative record carries a wrong one, which
   must still fail.
7. **Version-label coupling re-proven for the feature record:** the record's `v12` label equals the
   plan title's version; alter one side, show the named failure, restore, show clean.
8. **Banned-phrase rule proven against the v12 bytes**: insert one fixed retired-lifecycle phrase
   outside a fence in `tickets/FEATURE_PHASE_PLAN.md`, show the named banned-phrase failure, restore
   the file, show clean. A re-pinned plan the phrase rule has never failed on is untested (§6
   criterion 9's reasoning, carried forward).
9. **The mirror sweep pasted in full** — every matching line, not a count (§2's whole-inventory
   rule).
10. Checker clean at **10** rules; full suite green; D-015/D-017 clean; Regime B; revision binding
    with full diff inlined.

**No feature code.** A single non-plan, non-checker, non-governance source change fails this object.
The split-usage denominator and the D-064 sample fields enter the tree at §GMF-006, not here.

---

## 7. The `InputSnapshot` contract

Authored by §GMF-001, consumed by everything after it.

- **One snapshot, one moment** — explicit capture timestamp and the identity of every contributing
  source. A screen renders a snapshot; it never fetches.
- **Windows are named** — `RECENT_7D`, `RECENT_14D`, `SEASON_TO_DATE` per D-025. A screen requests a
  named window and does no date arithmetic.
- **Absence is a value** — every field distinguishes *not applicable*, *not yet observed* and
  *source unavailable*. D-014 keeps evidence confidence beside the value, never fused into it.
- **Denominators are named in the field.** Batted-ball rates use **BBE — Statcast batted-ball
  events, home runs included** — not the BABIP definition, which excludes home runs and would
  silently remove the outcome this product exists to study. An ambiguous denominator fails review.
- **Pitch-type splits carry their usage share**, so the 15% threshold is applied by the screen from
  data in the snapshot rather than assumed upstream.
- **Usage share is carried against two scopes** (r2, D-066) — for each pitch type, usage is measured
  against batters of the evaluated side **and** against all batters faced, each scope labelled. A
  screen applies its threshold to the scope the user selected and never re-derives a denominator.
- **Sample fields are raw counts with provenance flags** (r2, D-064) — AB, H and K travel as counts,
  each with its unit and an observed/derived flag; a derived field propagates the absence reasons of
  its inputs, intact. `BIP_est = AB − K` understates balls in play by sacrifice flies and hits, and
  the estimate says so wherever it appears.
- **The general window carries the seven form fields** (r2, D-068) — beside the existing four
  (barrel rate, exit velocity, ideal-attack-angle share, pull-air share): **attack-angle mean over
  swings**, **hard-hit share over batted-ball events**, and **xwOBA per plate appearance**, each
  with its denominator named and its observed/derived flag per D-064.
- **Batting side is derived, never assumed** (r2, D-065) — a switch hitter carries both sides, each
  labelled by the opposing pitcher hand that produced it. Probable-starter resolution is not a
  contract input; if it ever arrives it is an additive derived layer.
- **Provenance travels with the data** — every MLB-derived field records the export it came from, so
  D-057's manual-export chain is auditable from the snapshot alone.

**The field set is fixed at §GMF-006.** The four r2 bullets above enter the contract **before**
§GMF-006 executes, precisely so that fixing does not strand the authorized §GMF-008 toggle. A field
needed later and absent from §GMF-006's ingestion is a contract reopen, with its own revision.

---

## 8. Tickets

Criterion 1 of every implementation object is plan binding (both hashes per §2) plus `ACTIVE.md`
naming the ticket; the final criterion is always D-015/D-017 clean, checker clean, CI green, Regime
B, revision binding with full diff. Not repeated below.

### §GMF-001 — Input contract and reference data · 2 objects · closeout pointer GMF-002

2. `InputSnapshot` per §7, every field documented with unit, denominator and absence semantics.
3. Park reference data for thirty venues including **venue type** per D-055, provenance-pinned.
4. The **Savant per-handedness park-factor snapshot** committed with its full provenance record:
   source URL, **manual** export date, row count, sha256.
4b. **D-057 boundary 1, enforced mechanically rather than attested** (v2 finding 1). An attestation
   that "no code path fetched it" is not a control. This ticket pastes a **whole-repository search
   over tracked code at the reviewed head** — not over the diff — showing that no MLB or Savant
   fetch implementation exists anywhere in the tree. The search is defined by pattern list and by
   the file set it covered, both pasted, so the reviewer can re-run it.
5. Synthetic fixtures exercising every absence state.
6. Property tests: any absent field renders a defined state; no field silently defaults.

### §GMF-002 — Grid component · 3 objects · closeout pointer GMF-003

**Submission 1 — implementation.** Grid renders an `InputSnapshot` fixture; **the five grid
decisions D-058..D-062 (§4b-r1) implemented and each named with the behaviour satisfying it — this
submission lands them in `DECISIONS.md` verbatim from §4b-r1 and moves `CONTEXT_PACK.md`'s decision
count 57 → 62 in the same commit, the landing proven mechanically in the package** (register tail
and pack count together); sorting, column visibility and density user-controlled; no automated
ranking or selection (D-015/D-017); absence states visibly distinct from zero — a blank cell that
could mean either fails; test coverage of each **within D-061's stated boundary** — AppTest for the
element's data and configuration, direct tests for the selection-consumption path, the interaction
itself observed at submission 2. Merges on approval.

**Submission 2 — deployed verification.** Head of record is `staging` after that merge. The grid is
observed rendering on https://greenmachine.streamlit.app/ — **the first visible product surface** —
with the GMR-004 criterion-9 leakage check re-run against the public page.

**Closeout** quotes both verdicts.

### §GMF-003 — Metrics and grading screen · 2 objects · closeout pointer GMF-004

2. Window is **current season**, named in the UI, not implied.
3. Batter metrics against pitch types shown **only above 15% usage share**; the threshold is stated
   on the screen and suppressed types are visibly acknowledged, not silently dropped.
4. Rates use the **BBE denominator**, legible to the user.
5. Built on the §GMF-002 grid — a second copy of grid logic fails this ticket.
6. Fixtures only; no network call in the rendering path. Verified by AppTest and a pasted local
   render; no deployed evidence required, so no second submission.

### §GMF-004 — Parks to target screen · 2 objects · closeout pointer GMF-005

2. Renders pinned Savant park factors per handedness beside venue type.
3. The **weather seam** exists as one adapter interface, bound here to a fixture. The screen renders
   correctly with the adapter returning *unavailable*.
4. D-055's three roof states render distinctly; a forecast is never printed for a closed roof.
5. No Ballpark Pal, no provider call, no credential — D-051, D-056.
6. Fixtures only; AppTest and local render as GMF-003.

### §GMF-005 — NWS weather adapter, live · 3 objects · closeout pointer GMF-006

**Submission 1.** Live `api.weather.gov` behind the GMF-004 seam with the required identifying
`User-Agent`. **Failure is designed:** timeout, non-200, malformed payload and rate-limit responses
each map to *unavailable* and are each exercised by a test; the retry posture is stated and bounded.
Caching with a stated freshness bound, so a reload is not a fetch. No secret (D-056); no live
payload committed as a fixture — synthetic payloads shaped like the API only.

**Submission 2 — deployed verification.** The deployed app observed rendering **both** a live
forecast and the *unavailable* state, each captured with its timestamp.

**Closeout** quotes both verdicts.

### §GMF-006 — Statcast ingestion and wire-through · 3 objects · closeout pointer GMF-007

**Submission 1.**

2. **OQ-3 decided here and argued from the contract as built**, not asserted: legacy ingestion
   transplanted under GMR-003's byte-identity discipline, or rebuilt against `InputSnapshot`.
   **Constrained by criterion 3(d):** the legacy ingestion is presumed to contain network paths, so
   the transplant option is available only if control 3(a) finds none. If it finds one, the decision
   is made for this ticket and the package says so.
3. **Acquisition is manual export — D-057 boundary 1, and this is the ticket's hardest criterion.**
   v2 offered a diff search plus a path-accepting test; the reviewer showed both are evadable — an
   untouched or transplanted module outside the diff can hold a fetch path, a function can accept a
   path and still open a socket, a URL can be assembled without a literal hostname, and a generic
   client can fetch a caller-supplied endpoint. **Four controls replace them, and the third is the
   one that actually binds:**
   (a) a **whole-repository** tracked-code search at the reviewed head, not a diff search, with the
   pattern list and covered file set pasted;
   (b) the ingestion boundary **rejects URLs and URL-like schemes as inputs** — `http`, `https`,
   `ftp`, `file`, protocol-relative and any string parsing as a URL — rather than merely accepting a
   `Path`; each rejection exercised by a test;
   (c) **ingestion executed under an outbound-network-deny harness**, proving the local-file path
   completes with **no socket or HTTP attempt of any kind**. The repository already carries
   `tests/unit/golden/test_network_blocking.py`; this criterion extends that existing machinery
   rather than inventing a second mechanism, and the package states which it used;
   (d) **a transplanted implementation containing any network path automatically fails OQ-3's
   transplant option** — the transplant is then not available and the rebuild route is taken. This
   is stated as a rule so criterion 2's decision cannot be argued around it.
   An automated fetch here is a scope violation, not an optimisation.
4. Real data flows into `InputSnapshot`; the fixture bindings of GMF-002 … GMF-004 are replaced by
   live ones **with no change to the screens themselves**. A screen edited in this ticket is a
   contract failure and is reported as one rather than patched.
5. Ingestion failure degrades to the same absence states the screens already render. A stale value
   is never shown as current.
6. **The §7 r2 fields are ingested** (r2): both usage scopes per pitch type, each labelled (D-066);
   the D-064 sample counts — AB, H, K — each with its unit and its observed/derived flag; and the
   three general-window form fields — attack-angle mean, hard-hit share, xwOBA per plate
   appearance — each with its denominator named (D-068). Every
   one is shown **populated or absent-with-reason** against the real export; no field silently
   defaults, and a derived field carries its inputs' absence reasons intact.
7. **A switch hitter's row carries both sides** (r2, D-065), each labelled by the opposing pitcher
   hand that produced it — proven against at least one real switch hitter in the export, named in
   the package.

**Submission 2 — deployed verification.** The public app observed rendering real data, leakage check
re-run against real content.

**Closeout** quotes both verdicts, pointer to **GMF-007**.

### §GMF-007 — Form section (PO-N3, D-068) · 3 objects · closeout pointer GMF-008

**Submission 1.** The seven-metric form section: Barrel%, EV, AtkAng, IdealAtkAng%, Pull%, Hard%,
xwOBA — **no toggle**; **Pull% is the D-023 Pull Air %, labelled as such on the surface**.
Window **L7 with an L14 fallback**, the fallback triggered by **each metric's own floor per
D-068's table**, never by mere emptiness; a field whose L14 sample is below floor is **present
with its value, its exact sample, and an INSUFFICIENT marker** (D-023/D-025: insufficient is present,
never absent); a field with no observations at all is absent with its reason. The window actually
used is **named on the surface** (D-025's stated-window rule). All seven fields come from the
snapshot per §7 — none is derived in the view. Built on the §GMF-002 grid — a third copy of grid logic fails this ticket. No automated ranking or selection
(D-015/D-017); colour communicates data state only, per the standing convention.

**Submission 2 — deployed verification.** The section observed on the deployed app rendering real
data — including at least one field below floor at L14 carrying its value with an INSUFFICIENT marker, and the window-used label.

**Closeout** quotes both verdicts.

### §GMF-008 — Pitch-usage scope toggle (PO-N1, D-066) · 3 objects · closeout pointer GMF-009

**Submission 1.** A user toggle on the batter metrics surface between (a) usage measured against
batters of the evaluated side and (b) all pitches the pitcher throws, **both denominators supplied
by the snapshot per §7 — never derived in the view**. The three usage states (qualifies · measured
below threshold · absent/unevaluable) survive both positions, and the prose names which scope
produced each suppression. The default position is a Product Owner choice, stated in the package;
nothing is pre-selected beyond it.

**Submission 2 — deployed verification.** Both toggle positions observed on the deployed app, with
the scope-named suppression prose under each.

**Closeout** quotes both verdicts.

### §GMF-009 — Matchup window (PO-N2, D-067) · 3 objects · closeout pointer SENTINEL

**Submission 1.** The matchup section computed over a **rolling 30 days** ending at `as_of`, the
window named on the surface in words. **No score is authorized.** D-067 rules the window in and the
score out: a windowed score is ranking-shaped under D-015/D-017 and requires its own explicit
Product Owner posture ruling before any ticket text names it. **A package presenting a score, a
ranked order, or a default sort by any metric fails this ticket.**

**Submission 2 — deployed verification.** The section observed on the deployed app with its named
window.

**Closeout** quotes both verdicts, pointer to **SENTINEL**.

---

## 9. After the feature sequence

The dashboard renders real data across every surface, and UI/UX refinement begins. Deferred by name:
the confidence surface and legibility guards from D-030's register; any retrospective surface, which
has no source and needs its own; **a windowed matchup score, which D-067 leaves unauthorized pending
its own posture ruling**; and D-051's Ballpark Pal gate, which stays closed while anyone but the
Product Owner can reach the app.
