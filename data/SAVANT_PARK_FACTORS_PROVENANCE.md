# Provenance: `savant_park_factors_2024-2026.csv`

Supersedes the 2026-09-01 derived four-season snapshot
(`savant_park_factors_2023-2026.csv`, sha256 `67ca7512…`) per **D-172** (PO,
2026-09-02): "Remove that completely and make it three years." The derived
window is deleted — file, derivation rule, and every document that named it.
**Every number in this file comes straight off a board Baseball Savant
publishes; nothing is derived, blended, or filled.**

D-172 also records the standing rule, in the PO's words — "let's not build
anything like that again without asking": when the source does not publish
what was asked for, the builder stops and asks rather than deriving a
substitute.

## The window, and the one documented exception

The product window is Savant's **2024-2026 three-year rolling** board — the
span Savant's `rolling=3` leaderboard publishes for 2026. That span and the
handling of the one gap were put to the PO ("no preference" on both), so the
builder's recommendations hold:

- **Twenty-nine venues** read the published three-year board.
- **Sutter Health Park** (opened 2025) appears on no three-year board, so it
  reads Savant's **published 2025-2026 two-year board** — the only window
  Savant publishes for it. The Athletics keep real factors; no park goes
  back to a gap.

## Acquisition — four scripted pulls

Same posture as every snapshot since D-166: the live product reads Baseball
Savant programmatically every day under D-128's source-of-truth directive;
each page was pulled once — same host, same headers the live app uses — and
the embedded `var data = [...]` payload parsed. **No code path fetches this
data at runtime**: the pinned file is the only input the reader accepts, and
the digest gate stands.

URL template (`rolling` ∈ {3, 2} × `batSide` ∈ {L, R}, `year=2026`):
`https://baseballsavant.mlb.com/leaderboard/statcast-park-factors?type=year&year=2026&batSide={side}&stat=index_wOBA&condition=All&rolling={rolling}&parks=mlb`

| Page | Bytes | sha256 |
|---|---:|---|
| 2024-2026 L (rolling=3) | 119,068 | `b1f24ea377ef1e78db05ef0b4ac9d4077e368ba781fee2be1281a7f586b1e8ff` |
| 2024-2026 R (rolling=3) | 119,084 | `86ca4dca6f643daff9fc018c085723ed29be5e4ab1b70fa0006c602f85a46c48` |
| 2025-2026 L (rolling=2) | 119,671 | `27b996108a79967d1ae16a614be915fb89beb494a31aaf5d991ec3caa928712f` |
| 2025-2026 R (rolling=2) | 119,681 | `173ad8355d446b7daa457504e3d8534e4cd2849f44916602e5ad88dcda5b1d56` |
| **this CSV** | **7,457** | **`0cd621959fb47adebb008ac1a09f03d55b48474cead39fd9e91d1476ce16b7c7`** |

**Pull date:** 2026-09-02.

## Composition rule, stated so it can be re-run

1. Parse the `var data = [...]` JSON payload from each of the four pages;
   assert every record's `key_bat_side` equals the page's side and that all
   records carry the same 27-key set.
2. Take all 58 rows of the two three-year boards (29 venues × 2 bat sides).
3. Take exactly the Sutter Health Park rows (venue id `2529`, both bat
   sides) from the two two-year boards.
4. **No arithmetic on any value.** Every row is copied verbatim from its
   board, meta flags included: three-year rows carry
   `key_num_years_rolling=3`, `key_is_year_rolling=1`,
   `year_range=2024-2026`; Sutter's rows carry `2`, `-1`, `2025-2026` —
   exactly as Savant published them.
5. Sort by `(key_bat_side, int(venue_id))` — L block, then R block — and
   write the CSV with columns in sorted key order, `\n` line terminator,
   header row first.

## Shape

**60 data rows — 30 venues × 2 handedness.** 27 columns, identical to every
snapshot before it. `index_hr` is the home-run park factor the product
consumes; `index_woba` is the leaderboard's headline "Park Factor"; `n_pa`
is the sample size behind each row. Any screen rendering these values must
say which window they describe — including Sutter's two-season exception.

## Findings carried forward

1. **Thirty venues — the Athletics' gap stays closed.** Sutter Health Park
   carries `index_hr` **120 (LHB)** / **122 (RHB)** over 13,865 / 19,624 PA,
   verbatim off the published two-season board. The absence machinery stays:
   a venue a future snapshot does not cover is still represented, never
   filled.
2. **The Rangers' factor, three seasons deep** (the question that started
   this thread). Globe Life Field reads **95 (LHB)** / **92 (RHB)** on the
   2024-2026 window — pitcher-friendly across the three seasons (109/101 in
   2024, 80/81 in 2025, 100/99 in 2026). The park's hitter-friendly 2023
   (126/138) now sits outside the window, which is exactly what "stick to
   three years" means. Prior readings for reference: 105/106 on the retired
   derived four-season window, 89/87 on the two-season window before it.
3. **`n_pa` varies enough to matter** — 13,865 (Sutter Health Park, LHB) to
   32,992 (Daikin Park, RHB). D-014 keeps evidence confidence beside the
   value, never fused into it: `n_pa` is carried as a field of the
   park-factor value in the contract, so no screen renders a 13,865-PA
   factor identically to a 32,992-PA one without deciding to.
