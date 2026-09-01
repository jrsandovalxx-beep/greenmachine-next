# Provenance: `savant_park_factors_2025-2026.csv`

Supersedes the 2026-08-06 snapshot (`savant_park_factors_2024-2026.csv`, sha256
`2bbaee9d…`) per **D-166** (PO, 2026-09-01).

## Acquisition — scripted pull, with the Product Owner's blessing

The superseded snapshot entered by hand (browser Save Page As) because D-057
boundary 1 then prohibited scripted collection from an MLB Digital Property. The
live product now reads Baseball Savant programmatically every day under D-128's
source-of-truth directive, and for this refresh the Product Owner expressed **no
preference** between another hand export and a scripted pull. The builder pulled
each bat-side page once — same host, same headers the live app uses — parsed the
embedded `var data = [...]` payload, and derived the CSV deterministically.
**No code path fetches this data at runtime**: the pinned file is the only input
the reader accepts, and the digest gate stands.

| | |
|---|---|
| **Source URL (LHB)** | `https://baseballsavant.mlb.com/leaderboard/statcast-park-factors?type=year&year=2026&batSide=L&stat=index_wOBA&condition=All&rolling=2&parks=mlb` |
| **Source URL (RHB)** | same, `batSide=R` |
| **Pull date** | 2026-09-01 |
| **Method** | scripted pull of the leaderboard's embedded `var data` payload (D-166) |

## The pinned artifacts

| Artifact | Bytes | sha256 |
|---|---:|---|
| page, `batSide=L` | 123,127 | `8c0dde3ed1f8730d81bc9b480f6c2da00b876f8c6122e4aab52b500487fc1b82` |
| page, `batSide=R` | 123,138 | `4ccf83b6d26031dba89f521f6e0b745b8ced4c2e2f7caf264d1aa6752a5c504d` |
| **derived CSV (this file's sibling)** | **7,505** | **`c077ec837e811a470b47c614eaa1bc173fa5d22d5de241d256dd869cce920d73`** |

**Derivation rule, stated so it can be re-run** (unchanged from the superseded
record): parse the `var data = [...]` JSON payload from each page; assert every
record's `key_bat_side` equals the page's side; concatenate; assert all records
carry an identical key set; sort by `(key_bat_side, int(venue_id))`; write CSV
with columns in sorted key order, `\n` line terminator, header row first.

## Shape

**60 data rows — 30 venues × 2 handedness.** 27 columns, identical to the
superseded snapshot's. `index_hr` is the home-run park factor the product
consumes; `index_woba` is the leaderboard's headline "Park Factor"; `n_pa` is
the sample size behind each row.

Window fields are internally consistent across all 60 rows: `key_year` = 2026,
`key_num_years_rolling` = 2, `key_is_year_rolling` = 1, `year_range` =
**2025-2026**. The snapshot is a **two-season rolling window** — D-166 moved off
the three-season default because it is the only uniform window that can cover
Sutter Health Park: the Athletics' home opened in 2025, and a window reaching
back to 2024 can never hold it. Mixing a three-season board for 29 venues with a
two-season row for one is exactly what the reader's uniform-window check
refuses, so the whole board moved together. Any screen rendering these values
must say which window they describe.

## Findings carried forward, and one that closed

1. **Thirty venues — the Athletics' gap is closed.** The superseded record's
   finding 1 (twenty-nine venues, the Athletics' factor `NOT_YET_OBSERVED`) was
   a property of the three-season window, not of the park: on the two-season
   board Sutter Health Park carries `index_hr` **119 (LHB)** / **122 (RHB)**
   over 13,794 / 19,510 PA. The absence machinery stays — a venue a future
   snapshot does not cover is still represented, never filled.
2. **`n_pa` varies enough to matter** — 6,995 (Tropicana Field, LHB) to 21,365
   (Daikin Park, RHB). D-014 keeps evidence confidence beside the value, never
   fused into it: `n_pa` is carried as a field of the park-factor value in the
   contract, so no screen renders a 6,995-PA factor identically to a 21,365-PA
   one without deciding to.
