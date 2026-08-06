# Provenance: `savant_park_factors_2024-2026.csv`

For **FEATURE_PHASE_PLAN §GMF-001 criterion 4** under **D-053** and **D-057 boundary 1**.
Committed by GMF-001 alongside the snapshot it describes; authored by Claude Lead and
delivered inline per D-047, verbatim in substance below.

## Acquisition — manual, by the Product Owner

**No code path fetched this data.** Baseball Savant's park-factor leaderboard offers no
CSV export, so the Product Owner opened each bat-side view in his own browser and used
**File → Save Page As (HTML only)**. Two saved pages, one keystroke each. That is a
human download inside MLB's one-copy personal-use carve-out, and it is the whole of the
collection step.

**Claude Lead declined to use browser automation to retrieve this table**, having the
capability to do so. Driving a browser to extract data from an MLB property is an
automated script collecting from an MLB Digital Property, which D-057 boundary 1 leaves
prohibited. The boundary is only worth keeping if it holds when it is inconvenient.

| | |
|---|---|
| **Source URL (LHB)** | `https://baseballsavant.mlb.com/leaderboard/statcast-park-factors?type=year&year=2026&batSide=L&stat=index_wOBA&condition=All&rolling=3&parks=mlb` |
| **Source URL (RHB)** | same, `batSide=R` |
| **Export date** | 2026-08-06 |
| **Method** | browser Save Page As, HTML only |

## The three pinned artifacts

Derivation is **deterministic and reproducible** — the CSV is generated from the saved
pages, not transcribed. Anyone re-running it gets the same bytes or learns immediately
that something moved.

| Artifact | Bytes | sha256 |
|---|---:|---|
| saved page, `batSide=L` | 421,517 | `181ebea1e6516f284d7d61ade8bb607406ba6e07d7c7a9987b2e7e1965ae18d3` |
| saved page, `batSide=R` | 425,396 | `4e791ac144866d009e9af47d03834208bb3fb588014febc99be3e108ca4aa192` |
| **derived CSV (this file's sibling)** | **7,196** | **`2bbaee9d049008bdd9887f8c68feecc683c4e1803513b12c9797cb9037252ebf`** |

**Derivation rule, stated so it can be re-run:** parse the `var data = [...]` JSON
payload from each saved page; assert every record's `key_bat_side` equals the page's
side; concatenate; assert all records carry an identical key set; sort by
`(key_bat_side, int(venue_id))`; write CSV with columns in sorted key order, `\n` line
terminator, header row first.

## Shape

**58 data rows — 29 venues × 2 handedness.** 27 columns. `index_hr` is the home-run
park factor the product consumes; `index_woba` is the leaderboard's headline "Park
Factor"; `n_pa` is the sample size behind each row.

Window fields are internally consistent across all 58 rows: `key_year` = 2026,
`key_num_years_rolling` = 3, `key_is_year_rolling` = 1, `year_range` = **2024-2026**.
The snapshot is a **three-season rolling window, not a single season** — a park factor
built on one season is noisy, and this is the leaderboard's own default. Any screen
rendering these values must say so.

## Verification against an independent rendering

Eight values were checked against the Product Owner's screenshots of the rendered
tables, captured before the pages were saved and therefore an independent witness to
the derivation:

```
L Fenway Park      index_hr    =  82     L Coors Field     index_woba =  114
L Fenway Park      n_pa        =  23125  L Coors Field     index_hr   =  116
R Coors Field      index_woba  =  112    R T-Mobile Park   index_woba =   90
L Tropicana Field  n_pa        =  13560  R Tropicana Field n_pa       =  17944
```

All eight match, re-verified from the committed bytes at commit time.

## Two findings that belong in the reference data, not in a later ticket

1. **Twenty-nine venues, not thirty — the Athletics have no row.** Both handedness
   views omit them; the 2022-2024 window held Oakland Coliseum, it aged out, nothing
   replaced it. This is a gap to represent, not to fill: a parks screen renders a
   defined *source unavailable* state for that club — never a blank, a zero, or a
   league-average substitute. The reference data carries all thirty clubs with the
   Athletics' park factor explicitly absent.
2. **`n_pa` varies enough to matter** — 13,560 (Tropicana Field, LHB) to 31,517 at the
   top. D-014 keeps evidence confidence beside the value, never fused into it: `n_pa`
   is carried as a field of the park-factor value in the contract, so GMF-004 cannot
   render a 13,560-PA factor identically to a 31,000-PA one without deciding to.
