# greenmachine-next

GreenMachine Next is an MLB home-run evaluation and research platform.

It does not produce wagers, stakes, picks, or automated betting recommendations.

## What it does

The app grades today's MLB slate for home-run likelihood. It pulls the day's
schedule, posted (or estimated) lineups, and probable pitchers from the MLB Stats
API; recent form and pitch-arsenal data from Baseball Savant; ballpark factors
from a bundled reference table; and (outside local runs) live forecasts from the
National Weather Service. Every batter on the slate is scored against a
versioned, config-driven grading contract and presented on one Streamlit board,
with the spec's threshold highlighting.

Deployed instance: <https://greenmachine.streamlit.app/> (tracks the `staging`
branch).

## Run it

```bash
pip install -r requirements.txt    # plus requirements-dev.txt for checks/tests
streamlit run streamlit_app.py
```

The app opens on today's slate. The reference-data screens (thresholds, parks,
sample players) sit below it.

## Checks

```bash
ruff format --check src/ tests/ streamlit_app.py
ruff check src/ tests/ streamlit_app.py
mypy --strict src/
pytest
python3 scripts/check_consistency.py   # plan/doc consistency rules
```

## File map

- `streamlit_app.py` — app entry; renders the live slate board and the reference
  screens.
- `src/greenmachine/live/` — the real-data path:
  - `transport.py` — pinned-host HTTP transport with retry (one of only two
    modules allowed to open a connection).
  - `mlb_api.py` — MLB Stats API client (slate, batting orders, season lines).
  - `savant.py` — Baseball Savant CSV client (rolling form boards, batter/pitcher
    arsenals, day pitch events).
  - `form.py` — rolling-form aggregation (L7 with per-metric L14 fallback) from
    pitch events.
  - `grading.py` — observation assembly; derives the matchup components; builds
    the frozen input snapshot and scores it via the domain engine.
  - `pipeline.py` — slate-board orchestration: lineups (posted or labelled
    fallback), park/weather components, per-batter grading.
- `src/greenmachine/domain/` — grading engine, enums, and component contracts
  (provider-agnostic).
- `src/greenmachine/park/` — venue registry and park-factor reference reader.
- `src/greenmachine/weather/` — NWS forecast adapter (non-local environments).
- `config/production/gm_hr_v1.yaml` — the production grading config (threshold
  table, weights, grade cutoffs). The only file that may hold production
  thresholds.
- `tickets/`, `DECISIONS.md`, `docs/` — governance: ticket records, the decision
  register, glossary, and the feature-phase plan.

## Data sources

| Source | Used for |
| --- | --- |
| MLB Stats API (statsapi.mlb.com) | schedule, probable pitchers, lineups, season stats |
| Baseball Savant (baseballsavant.mlb.com) | rolling form boards, pitch arsenals, pitch-by-pitch events |
| National Weather Service (api.weather.gov) | gametime temperature at open-air venues (non-local runs) |
| Bundled reference (`src/greenmachine/park/`) | venue metadata and park factors by handedness |

Lineup, form, and matchup fallbacks are labelled in the UI ("est." orders,
INSUFFICIENT advisories, assumption notes) rather than silently substituted.

## Branches

- `main` — production. Protected: changes arrive only by pull request.
- `staging` — Product Owner testing. Protected: changes arrive only by pull request.
- `feature/*` — implementation branches, created from `staging`.

## Line endings

Text files are committed and checked out with LF line endings on every platform;
see `.gitattributes`. Binary files and evidence paths are exempt from all text
conversion. This project ships digest-pinned evidence, so a default checkout must
reproduce the committed bytes exactly.
