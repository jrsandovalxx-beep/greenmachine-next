# Provenance: `savant_park_factors_2023-2026.csv`

Supersedes the 2026-09-01 two-season snapshot (`savant_park_factors_2025-2026.csv`,
sha256 `c077ec83…`) per **D-171** (PO, 2026-09-01): "lets use years 2023 - 2026
instead." Asked which fallback to use when the source turned out not to publish
that window, the PO expressed **no preference**, so the builder's recommendation
— a documented derivation from the source's own single-year boards — is what
follows.

## Why this window is derived, not pulled

Baseball Savant publishes only **one, two or three-year** rolling windows on
this leaderboard: `rolling=1`, `rolling=2` and `rolling=3` answer with data;
`rolling=4` answers with an empty payload (probed 2026-09-01). The four-season
window the PO asked for does not exist on the source. The three-season board
(2024-2026) is not an acceptable substitute: it still excludes Sutter Health
Park, the gap D-166 closed. So the window is built from the source's own
single-year boards, by the deterministic rule below, and pinned like every
snapshot before it.

## Acquisition — eight scripted pulls, with the Product Owner's blessing

Same posture as the superseded record (D-166): the live product reads Baseball
Savant programmatically every day under D-128's source-of-truth directive; each
single-year page was pulled once — same host, same headers the live app uses —
and the embedded `var data = [...]` payload parsed. **No code path fetches this
data at runtime**: the pinned file is the only input the reader accepts, and
the digest gate stands.

URL template (eight pulls — `year` ∈ {2023, 2024, 2025, 2026} × `batSide` ∈ {L, R}):
`https://baseballsavant.mlb.com/leaderboard/statcast-park-factors?type=year&year={year}&batSide={side}&stat=index_wOBA&condition=All&rolling=1&parks=mlb`

| Page | Bytes | sha256 |
|---|---:|---|
| 2023 L | 122,908 | `8ac37c4a3f4cfbefd6d7d977eae8057cc5a4364c0605ba171049b004a2256acf` |
| 2023 R | 122,942 | `94473f740aa776fdda00c1bdc66dea18803c5a926b268745e0fb879313d3f2ea` |
| 2024 L | 122,906 | `961fa6383146e38d957d6ec4f053ce0f054564f608830718083c4e8b587d5724` |
| 2024 R | 122,947 | `63619dcbe2e1e96d116c673b11f43973f05abcdc4438bbab51ba7a4b8ee5df5a` |
| 2025 L | 122,945 | `44bf3b6d72acbb9825fd2e4e9e0a06a2e6d68cc48a90d566734162fa82c04f57` |
| 2025 R | 122,949 | `b6b521799d324c320fab4f915ebdcc362325a82f47ece511ebcb31b685c7f11c` |
| 2026 L | 122,909 | `ffdfd8df9a590fc6446bf6c104f55a7ed68a68c71aafea63ddcf740b56bd3370` |
| 2026 R | 122,930 | `6cc2aafdbe82c47469025d2dfd85b5fecae32ab1d6728a82555b98be996eac26` |
| **derived CSV (this file's sibling)** | **7,506** | **`67ca75125fdeaab6db854267f85161969e855a6932983bb7f83f68033eecf5f4`** |

**Pull date:** 2026-09-01.

## Derivation rule, stated so it can be re-run

1. Parse the `var data = [...]` JSON payload from each of the eight pages;
   assert every record's `key_bat_side` equals the page's side, and that all
   records across all pages carry an identical key set (which is exactly the
   superseded snapshot's 27-column set — the header is unchanged).
2. The venue set is **the current thirty**: the venues on the 2026 board. Two
   venues on older boards are not current and are excluded: Oakland Coliseum
   (the Athletics' former home, 2023-2024) and George M. Steinbrenner Field
   (the Rays' temporary 2025 home). A current venue blends only the seasons it
   actually hosted: Sutter Health Park two (2025-2026), Tropicana Field three
   (2023, 2024, 2026 — the Rays played 2025 in Steinbrenner), every other
   venue all four.
3. Per venue-side: every `index_*` column is the **plate-appearance-weighted
   blend** of its single-year values — Σ(`index` × `n_pa`) ÷ Σ(`n_pa`),
   rounded half-up to the integer the boards carry; `n_pa` is the sum of the
   single-year samples. `name_display_club`, `main_team_id` and `venue_name`
   are asserted constant across a venue's years and carried forward.
4. Meta fields are the derived window's own descriptors, not any Savant page's
   flags: `key_year` = 2026 (the window's end season),
   `key_num_years_rolling` = 4, `key_is_year_rolling` = -1, `year_range` =
   **2023-2026**.
5. Sort by `(key_bat_side, int(venue_id))` — L block, then R block — and write
   the CSV with columns in sorted key order, `\n` line terminator, header row
   first.

The blend does not claim to be the number Savant would publish for a
four-year window — Savant computes its own rolling boards on pooled data by
its own method, and on the two-season window the two can differ by a few
points (Sutter RHB: 118 blended vs 122 on Savant's own 2025-2026 board). What
this file guarantees instead is that every number is reproducible from the
eight pinned page digests above by the rule in this section, with the method
stated honestly wherever the window is named.

## Shape

**60 data rows — 30 venues × 2 handedness.** 27 columns, identical to the
superseded snapshot's. `index_hr` is the home-run park factor the product
consumes; `index_woba` is the leaderboard's headline "Park Factor"; `n_pa` is
the sample size behind each row. Window fields are internally consistent
across all 60 rows (rule 4). Any screen rendering these values must say which
window they describe.

## Findings carried forward, and the one the PO asked about

1. **Thirty venues — the Athletics' gap stays closed.** Sutter Health Park
   carries `index_hr` **119 (LHB)** / **118 (RHB)** over 13,438 / 19,288 PA —
   the blend of its two played seasons. The absence machinery stays: a venue
   a future snapshot does not cover is still represented, never filled.
2. **The Rangers' factor is right, and the window was the question** (the PO's
   "park factor for rangers seems wrong, verify"). Globe Life Field reads
   **105 (LHB)** / **106 (RHB)** on this four-season window: it was a
   hitter's park in 2023-2024 (126/138, then 109/101), flipped pitcher-friendly
   in 2025 (80/81), and played neutral in 2026 (100/99). The superseded
   two-season window's 89/87 was verified correct for *its* window — the
   live two-season board showed the same 89 on the day this snapshot was
   pulled.
3. **`n_pa` varies enough to matter** — 13,438 (Sutter Health Park, LHB) to
   44,096 (Daikin Park, RHB). D-014 keeps evidence confidence beside the
   value, never fused into it: `n_pa` is carried as a field of the park-factor
   value in the contract, so no screen renders a 13,438-PA factor identically
   to a 44,096-PA one without deciding to.
