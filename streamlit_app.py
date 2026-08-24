"""GreenMachine composition root — shell, batter grid, metrics screen, parks.

Through GMR-004 this page was a shell with no product screens; GMF-002 added
the first visible product surface (FEATURE_PHASE_PLAN §GMF-002), a batter grid
rendering an ``InputSnapshot`` fixture, §GMF-003 added the metrics screen —
pitch types against seven metrics, each over its own named denominator — plus
the selection-driven detail panel D-058 established, and §GMF-004 adds the
parks screen: thirty venues with park factors per handedness beside venue
type, the weather seam bound to a fixture, and D-055's roof states each
rendering as its own. The page still renders the shell's deployment fields —
environment, version, commit — because the staging deployment is verified end
to end through them.

**The parks screen carries three provenances and says so.** Its factor columns
render the pinned Savant manual export with its export date. Its forecast column
is **live from api.weather.gov** in a deployed environment and fixture-bound
locally — §GMF-005 bound the live adapter behind the §GMF-004 seam, and the
discriminator is the environment, so a local render never becomes a network
call. Its roof column stays **fixture-bound everywhere**: §GMF-005 gave weather
a source and gave roof none, and a reader who saw weather go live would
otherwise reasonably assume roof went with it. Real and fixture data share a
table here, which is exactly why none of it is left to be inferred.

**The live path exists in one place.** ``greenmachine.weather.transport`` is the
only module in ``src`` that can open a connection, and every hop it makes — the
request it is handed and any redirect target — is checked against one pinned
host. Nothing else in this application fetches anything. The adapter that uses
it is held across reruns by ``live_weather_adapter`` below, because a cache
rebuilt on every rerun is not a cache.

Every widget lives here and only here: ``src/`` imports no streamlit
(architecture-enforced), and both screens' logic — frames, grading, selection
consumption, eligibility — is ordinary importable code under
``greenmachine.grid`` and ``greenmachine.splits``, proven by direct tests within
D-061's stated boundary. The page renders a snapshot; it never fetches (§7).

No automated ranking or selection (D-015/D-017): both screens open in neutral
identity order — batter name, pitch-type name — and every metric ordering,
column choice, density change, window choice and batter choice is user-initiated.
The metrics screen's 15% usage threshold is not a ranking but §GMF-003
criterion 3's stated display rule: it is printed on the screen, and every pitch
type it removes is named rather than dropped.
"""

from __future__ import annotations

import base64
import html
import os
import subprocess
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from importlib import metadata
from pathlib import Path

import pandas as pd
import streamlit as st

from greenmachine.common.clock import SystemClock
from greenmachine.config.loader import load_config
from greenmachine.config.schema import GreenMachineConfig
from greenmachine.domain.enums import Grade, SampleStatus
from greenmachine.domain.grade_result import EvaluatedGradeResult
from greenmachine.fixtures import FixtureWeatherAdapter, grid_demo_snapshot, parks_demo_snapshot
from greenmachine.grid import (
    DENSITY_ROWS,
    METRIC_COLUMNS,
    batter_for,
    detail_handle,
    display_texts,
    frame_height,
    graded_styler,
    grid_frame,
    row_batter_ids,
    selected_batter_id,
    style_frame,
    styled_text_frame,
    visible_columns,
)
from greenmachine.inputs import InputSnapshot, WeatherForecast, Window
from greenmachine.inputs.contract import Handedness, ParkFactor, ParkVenue, VenueType
from greenmachine.inputs.savant_park_factors import basis_statement, read_factors
from greenmachine.live.backtest import (
    BacktestRow,
    outcomes_for_day,
    roi_per_unit,
    slate_as_of,
    tally_grades,
)
from greenmachine.live.form import FormSection, FormValue
from greenmachine.live.grading import QUALIFYING_USAGE_SHARE
from greenmachine.live.mlb_api import FetchFailure, GameLogEntry, MlbStatsApi
from greenmachine.live.pipeline import (
    SEASON_IDS_PER_REQUEST,
    BatterCard,
    BatterGridLine,
    GameCard,
    PitcherCard,
    PitcherRecentLine,
    PitcherSeasonReads,
    PitchLine,
    SlateBoard,
    build_board,
)
from greenmachine.live.savant import BaseballSavant
from greenmachine.live.transport import UrllibTransport as MlbTransport
from greenmachine.parks import ALL_COLUMNS as PARK_COLUMNS
from greenmachine.parks import FACTOR_COLUMNS as PARK_FACTOR_COLUMNS
from greenmachine.parks import (
    VENUE_COLUMN,
    factor_absence_notes,
    forecast_suppression_notes,
    unavailable_forecast_notes,
)
from greenmachine.parks import (
    screen_frames as park_frames,
)
from greenmachine.shell import (
    BLOT_CSS,
    BLOT_HTML,
    DIAL_CSS,
    FIELD_CSS,
    SHELL_CSS,
    TITLE_HTML,
    field_wind_html,
    orb_html,
)
from greenmachine.splits import ABSENCE_WORDS as SPLIT_ABSENCE_WORDS
from greenmachine.splits import METRIC_COLUMNS as SPLIT_METRIC_COLUMNS
from greenmachine.splits import (
    PITCH_TYPE_COLUMN,
    absence_notes,
    absent_metric_notes,
    build_screen,
    denominator_notes,
    provenance_notes,
    screen_frames,
    suppression_notes,
    threshold_statement,
    window_label,
)
from greenmachine.weather.nws import CONTACT_ENV_VAR, DEFAULT_CONTACT, NwsWeatherAdapter
from greenmachine.weather.transport import UrllibTransport, real_sleep

REPO_ROOT = Path(__file__).resolve().parent

# The canonical non-production configuration directory (GM-041.5). The page
# loads no configuration; this constant exists because the config-location
# contract pins every repository-root consumer to the canonical path — never
# to a copy under the test tree.
NONPRODUCTION_CONFIG_DIR = REPO_ROOT / "config" / "nonproduction"


def _secret(key: str) -> str:
    """Read one value from Streamlit secrets, tolerating their absence.

    Local runs have no secrets source, and Streamlit raises on any secrets
    access when none exists; a missing secret must never crash the page.
    """
    try:
        return str(st.secrets.get(key, "")).strip()
    except (FileNotFoundError, KeyError):
        return ""


def bridge_secrets_into_environment() -> None:
    """Fill absent ``GM_*`` environment variables from Streamlit secrets.

    Streamlit Community Cloud configures an app through its secrets store,
    not through environment variables. The bridge fills only absent keys, so
    a real environment variable always wins and the commit resolution order
    stays exactly as REBUILD_PLAN §GMR-004 defines it: git, then
    ``GM_COMMIT``, then ``unknown``.
    """
    for key in ("GM_ENVIRONMENT", "GM_COMMIT"):
        if not os.environ.get(key):
            value = _secret(key)
            if value:
                os.environ[key] = value


def resolve_environment() -> str:
    """The configured environment label, with an explicit ``local`` fallback.

    ``staging`` and ``production`` are configuration values (``GM_ENVIRONMENT``);
    when nothing is configured the page says ``local`` rather than guessing.
    """
    return os.environ.get("GM_ENVIRONMENT", "").strip() or "local"


def resolve_version() -> str:
    """Installed package metadata, with an explicit ``unknown`` fallback."""
    try:
        return metadata.version("greenmachine")
    except metadata.PackageNotFoundError:
        return "unknown"


def resolve_commit() -> str:
    """The displayed commit, resolved git-first (REBUILD_PLAN §GMR-004).

    1. ``git rev-parse --short HEAD`` when a git checkout is present —
       including detached HEAD, which is a valid state with a valid SHA;
    2. else ``GM_COMMIT``, displayed with the explicit ``(env)`` provenance
       marker so a reader can see the value came from configuration, not the
       checkout — a stale environment variable can never mask a live checkout;
    3. otherwise the literal ``unknown``. Never a crash.
    """
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        completed = None
    if completed is not None and completed.returncode == 0 and completed.stdout.strip():
        return completed.stdout.strip()
    env_value = os.environ.get("GM_COMMIT", "").strip()
    if env_value:
        return f"{env_value} (env)"
    return "unknown"


@st.cache_resource(show_spinner=False)
def live_weather_adapter(contact: str) -> NwsWeatherAdapter:
    """The live adapter, held across reruns rather than rebuilt on each one.

    **This is what makes "a reload is not a fetch" true.** Streamlit re-executes
    this whole script on every widget interaction, so an adapter constructed
    inside the render would start each rerun with empty caches and re-fetch all
    thirty venues — the criterion's own bound, defeated by the page's execution
    model rather than by the adapter's logic. ``st.cache_resource`` gives the
    object a lifetime longer than one run, which is the only place that lifetime
    can live: ``src/`` cannot import streamlit (architecture-enforced), so the
    adapter stays a plain object with injected collaborators and the composition
    root owns its persistence.

    **The cache is shared across sessions, and that is chosen, not incidental.**
    A resource cache is process-wide, so two viewers share one adapter. The data
    it holds is keyed by venue and by nothing else — no viewer's identity, query
    or selection reaches it — so sharing leaks nothing between them and spares
    the source duplicate work. D-051's sole-user posture is untouched: this
    changes who repeats a request, not who may see the page.

    Keyed on ``contact`` so a configuration change yields a new adapter rather
    than silently reusing one built with the previous identity.
    """
    return NwsWeatherAdapter(
        transport=UrllibTransport(),
        clock=SystemClock(),
        sleep=real_sleep,
        contact=contact,
    )


def weather_binding() -> tuple[object, bool]:
    """Which weather adapter this environment gets, and whether it is live.

    **The discriminator is the environment, stated rather than implied.** A local
    run binds the fixture: a local render must never become a network call, or
    the local-render evidence route §GMF-003 and §GMF-004 both used quietly
    dies — and every test in this suite runs local. Only a deployed environment
    binds the live NWS adapter, which is what §GMF-005 submission 2 observes.

    The contact string is configuration read here at the composition root and
    injected, never reached for from inside the adapter: ``GM_NWS_CONTACT`` if
    set, otherwise the committed repository URL. It is not a secret — it grants
    no access and identifies rather than authenticates — so D-056's deferral of
    ``st.secrets`` stands untouched.
    """
    if resolve_environment() == "local":
        return FixtureWeatherAdapter(), False
    contact = os.environ.get(CONTACT_ENV_VAR, "").strip() or DEFAULT_CONTACT
    return live_weather_adapter(contact), True


def retrieval_statement(snapshot: InputSnapshot) -> str:
    """When the forecasts on screen were obtained from their source.

    A freshness bound stated only in code says nothing to the reader it exists
    for. Because answers are cached, two rows can carry different ages, so the
    span is reported rather than a single reassuring number.
    """
    obtained = sorted(
        park.forecast.value.obtained_at for park in snapshot.parks if park.forecast.value
    )
    if not obtained:
        return "No forecast on this page carries a retrieval time: none was obtained."
    first, last = obtained[0], obtained[-1]
    if first == last:
        return f"Forecasts retrieved {first.isoformat()}."
    return f"Forecasts retrieved between {first.isoformat()} and {last.isoformat()}."


def render_grid() -> None:
    """The batter grid — the §GMF-002 product surface, fixtures only."""
    snapshot = grid_demo_snapshot()
    st.subheader("Batter grid")
    st.caption(
        "Synthetic fixture data (OQ-4): deliberately non-baseball values. "
        "Initial order is neutral — batter name — and every metric ordering "
        "is yours to apply in the column headers. A value always shows its "
        "sample beside it; an absent value names its reason and is never a "
        "blank or a zero."
    )
    window_value = st.selectbox(
        "Window",
        options=[window.value for window in Window],
        index=0,
        key="grid_window",
        help="Named windows per D-025 — the screen does no date arithmetic.",
    )
    window = Window(window_value)
    chosen = st.multiselect(
        "Columns",
        options=list(METRIC_COLUMNS),
        default=list(METRIC_COLUMNS),
        key="grid_columns",
        help="The batter column always shows, so a selection stays readable.",
    )
    density = st.radio(
        "Density",
        options=list(DENSITY_ROWS),
        index=1,
        horizontal=True,
        key="grid_density",
        help="Rows in view before the grid scrolls (the 1.37-floor control).",
    )
    data = grid_frame(snapshot, window)
    styler = graded_styler(data, display_texts(snapshot, window), style_frame(snapshot, window))
    event = st.dataframe(
        styler,
        column_order=visible_columns(tuple(chosen)),
        height=frame_height(density, len(data)),
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="grid",
    )
    ids = row_batter_ids(snapshot)
    selected = selected_batter_id(tuple(event.selection.rows), ids)
    if selected is None:
        st.caption("Select a row to open its detail surface.")
    else:
        render_detail(snapshot, selected, window)


def render_detail(snapshot: InputSnapshot, batter_id: str, window: Window) -> None:
    """The selection-driven detail surface (D-058) — GMF-003's content.

    Every grid metric's state, **in words**. The deployed component renders a
    null-data cell as its own ``None`` and discards the Styler's display value
    there, so the grid's three absence reasons survive on the canvas only as
    background colours. The payload was always correct; this panel is where the
    reason can be read.

    The interaction that opens this panel is not AppTest-observable at the 1.37
    floor (D-061), which is why the metrics screen below does **not** live behind
    it: a surface reachable only by an unsynthesizable click could not discharge
    criterion 6, which asks for AppTest and offers no deployed submission to fall
    back on. What this panel computes is direct-tested as ordinary code.
    """
    handle = detail_handle(snapshot, batter_id)
    batter = batter_for(snapshot, batter_id)
    st.markdown(f"**Selected:** {handle.name}")
    st.markdown(f"**Grid metrics — {window.value}, in words**")
    for note in absent_metric_notes(batter, window):
        st.markdown(f"- {note}")
    st.caption(
        "Each metric's state stated in words, so an absent value's reason is "
        "readable rather than inferred from a cell's colour."
    )


def render_metrics_screen(snapshot: InputSnapshot) -> None:
    """The §GMF-003 metrics screen: pitch types against seven metrics.

    The window is **fixed** — this screen requests SEASON_TO_DATE and names it.
    Criterion 2 asks for the window to be named rather than implied, and the
    name is read off the split set that produced the rows, so the label cannot
    drift away from the data it describes. There is deliberately no window
    control here; the one on the batter grid belongs to that screen.

    Choosing whose splits to read is the user's, through an ordinary control —
    and **the initial state chooses nobody**. `index=None` renders the control
    empty until the user picks: a default of "the first neutral item" would
    still be a product-composed initial choice of one hitter, which
    D-015/D-017 prohibit as automated selection, not merely as ranking. Until a
    user-composed choice exists, an invitation renders in place of the metric
    surface — the same shape as the grid's own no-selection state, which is
    already approved product language. The product neither picks a batter nor
    orders the pitch types by any metric — rows arrive in the pitch type's own
    name order.
    """
    st.subheader("Pitch-type metrics")
    names = [batter.name for batter in snapshot.batters]
    chosen_name = st.selectbox(
        "Batter",
        options=names,
        index=None,
        placeholder="Choose a batter",
        key="splits_batter",
        help="Whose pitch-type splits to read. A filter you compose, never a ranking.",
    )
    if chosen_name is None:
        st.caption("Choose a batter to read their pitch-type splits. Nothing is selected for you.")
        return
    batter = next(b for b in snapshot.batters if b.name == chosen_name)
    screen = build_screen(batter.splits_for(Window.SEASON_TO_DATE))
    st.markdown(f"**Window:** {window_label(screen)} — current season")
    st.caption(
        f"Window: {window_label(screen)} (current season), named here and taken "
        "from the split set that produced these rows. "
        f"{threshold_statement(screen)} Row order is neutral — the pitch type's "
        "own name — and every metric ordering is yours to apply in the headers."
    )

    if screen.set_absence is not None:
        st.info(
            f"No pitch-type splits to show for {window_label(screen)}: "
            f"{SPLIT_ABSENCE_WORDS[screen.set_absence]}."
        )
    elif screen.observed_no_pitches:
        st.info(
            f"Observed: this batter faced no tracked pitches in "
            f"{window_label(screen)}. The source answered — this is a "
            "measurement, not a missing one."
        )

    if screen.has_rows:
        data, texts, styles = screen_frames(screen)
        st.dataframe(
            graded_styler(data, texts, styles, SPLIT_METRIC_COLUMNS),
            column_order=visible_columns(
                SPLIT_METRIC_COLUMNS, PITCH_TYPE_COLUMN, SPLIT_METRIC_COLUMNS
            ),
            height=frame_height("Cozy", len(data)),
            hide_index=True,
            key=f"splits_{batter.batter_id}",
        )

    for note in suppression_notes(screen):
        st.markdown(f"- {note}")

    missing = absence_notes(screen)
    if missing:
        st.markdown("**Absent metrics on the rows above, in words**")
        for note in missing:
            st.markdown(f"- {note}")
        st.caption(
            "The component renders a null-data cell as its own `None` and drops "
            "the display value carried for it, so an absent cell's reason is "
            "stated here rather than left to a cell's background colour. The "
            "data behind those cells is absent-with-a-reason, never zero."
        )

    with st.expander("Denominators — what each rate is over"):
        for note in denominator_notes():
            st.markdown(f"- {note}")
    with st.expander("Provenance — sourced or derived, per metric"):
        for note in provenance_notes(screen):
            st.markdown(f"- {note}")
        st.caption(
            "Read from each field's own derivation record, not asserted here. "
            "Whiff% and SwStr% share a numerator and differ only in denominator, "
            "so either could be computed from the other — a computed value would "
            "say so on this list."
        )


# --------------------------------------------------------------------------
# GMF-006: the live slate board (D-069/D-070/D-071/D-072)
# --------------------------------------------------------------------------

# The board rebuilds at most this often; per-day event files refresh hourly.
BOARD_TTL_SECONDS = 900
DAY_EVENTS_TTL_SECONDS = 3600


@st.cache_resource
def live_mlb_adapters() -> tuple[MlbStatsApi, BaseballSavant]:
    """The two live adapters, held across reruns (a reload is not a refetch)."""
    transport = MlbTransport()
    return MlbStatsApi(transport), BaseballSavant(transport)


@st.cache_resource
def production_config() -> GreenMachineConfig:
    """The one approved production grading configuration (D-071)."""
    return load_config(REPO_ROOT / "config" / "production" / "gm_hr_v1.yaml")


@st.cache_resource
def park_factor_table() -> dict[int, dict[Handedness, ParkFactor]]:
    """The pinned Savant park-factor snapshot (digest-verified on read)."""
    return read_factors()


@st.cache_data(ttl=DAY_EVENTS_TTL_SECONDS, show_spinner=False)
def _day_events(day_iso: str, year: int) -> object:
    """One day's pitches, cached: a past day never changes."""
    _, savant = live_mlb_adapters()
    return savant.fetch_pitch_events(year=year, day=day_iso)


# Bound on live-weather failures per board build. A black-holed venue costs one
# transport timeout (~10s); without a cap, a network path that drops every NWS
# packet would multiply that by every open-air venue on the slate. After this
# many failures the reader stops asking and the remaining venues take the
# ordinary weather-unavailable absence instead (D-054: absence is a value).
WEATHER_FAILURE_CIRCUIT_BREAKER = 3

# Diagnostics from board builds' weather reads, keyed by slate date and
# rendered after the board. Keyed, not one shared list: a cached board serves
# without rebuilding, so a single list could show one slate's failures under
# another (D-103). A cache hit keeps its own build's diagnostics forever.
LIVE_WEATHER_DIAGNOSTICS: dict[str, list[str]] = {}


def _forecast_lookup(pick: Callable[[WeatherForecast], object], diagnostics: list[str]) -> object:
    """A venue -> forecast-reading closure over the weather seam.

    ``pick`` chooses which reading a present forecast yields; the closure
    answers ``None`` locally, on absence, on a read failure (recorded in the
    build's ``diagnostics``), and once the circuit breaker has tripped — one
    discipline shared by every conditions reader.
    """
    adapter, live = weather_binding()

    def read(venue: ParkVenue) -> object | None:
        if not live or len(diagnostics) >= WEATHER_FAILURE_CIRCUIT_BREAKER:
            return None
        try:
            field = adapter.forecast_for(venue)
        except Exception as exc:  # composition-root last resort: weather downgrades to absence
            diagnostics.append(f"{venue.venue_id}: {type(exc).__name__} on {type(venue).__name__}")
            return None
        if field.value is None:
            return None
        return pick(field.value)

    return read


def _temperature_lookup(diagnostics: list[str]) -> object:
    """A venue -> °F reader over the weather seam; None locally or on absence."""
    return _forecast_lookup(lambda forecast: forecast.temperature_f, diagnostics)


def _wind_lookup(diagnostics: list[str]) -> object:
    """A venue -> (wind mph, compass direction) reader over the weather seam;
    None locally or on absence — same discipline as the temperature lookup."""
    return _forecast_lookup(
        lambda forecast: (forecast.wind_speed_mph, forecast.wind_direction), diagnostics
    )


def _humidity_lookup(diagnostics: list[str]) -> object:
    """A venue -> relative-humidity-percent reader over the weather seam
    (D-111); None locally or on absence — same discipline as the other
    conditions readers."""
    return _forecast_lookup(lambda forecast: forecast.relative_humidity_percent, diagnostics)


@st.cache_data(ttl=BOARD_TTL_SECONDS, show_spinner=False)
def live_board(slate_iso: str) -> SlateBoard | FetchFailure:
    """Assemble and grade the slate; cached so a rerun is not a refetch."""
    api, savant = live_mlb_adapters()
    slate_date = date.fromisoformat(slate_iso)
    year = slate_date.year

    def fetch_day(day: date) -> object:
        return _day_events(day.isoformat(), year)

    weather_diagnostics: list[str] = []
    board = build_board(
        api=api,
        savant=savant,
        slate_date=slate_date,
        as_of=datetime.now(UTC),
        config=production_config(),
        fetch_day_events=fetch_day,  # type: ignore[arg-type]
        temperature_for=_temperature_lookup(weather_diagnostics),  # type: ignore[arg-type]
        park_factors=park_factor_table(),
        wind_for=_wind_lookup(weather_diagnostics),  # type: ignore[arg-type]
        humidity_for=_humidity_lookup(weather_diagnostics),  # type: ignore[arg-type]
    )
    LIVE_WEATHER_DIAGNOSTICS[slate_iso] = weather_diagnostics
    return board


_NOT_EVALUABLE = "not evaluable"


# Console-palette highlight: a lime wash pre-blended onto the dark cell green.
# It must be OPAQUE — the data grid composites an alpha background over white,
# not over the themed cell, which read as a washed-out pale block; the old
# light-theme #d4edda washed the cell text out entirely.
_HIGHLIGHT = "background-color: #427010; color: #eaffcf"

# Muted italic for a cell that carries a reason instead of a value.
_REASON_CSS = "color: #7d8f84; font-style: italic"

# Opaque amber for a value shown with its INSUFFICIENT advisory: present, but
# below its sample floor (D-068). Opaque for the same canvas-compositing
# reason as the highlight — an alpha background reads as a washed-out block.
_INSUFFICIENT_CSS = "background-color: #7a5c14; color: #ffe9a8"

# Neon-green money tag (D-094): a "$" beside a shortlist batter who homered
# in his most recent game day on or before this slate. Text shadow gives the
# neon glow; no background, so the cell keeps its theme fill.
_MONEY_CSS = "color: #39ff14; text-shadow: 0 0 8px #39ff14; font-weight: 700"


def _weather_text(game: GameCard) -> tuple[str, bool]:
    """(text, is-absent) for the shortlist's weather column: the temperature
    for open-air venues, or the plain reason there is no reading (D-084)."""
    if game.venue_type is not VenueType.OPEN_AIR:
        return "roofed — indoor neutral value", False
    if game.temperature_fahrenheit is None:
        return "source unavailable", True
    return f"{float(game.temperature_fahrenheit):.0f}°F, open air", False


# D-109: the shortlist tags' firing lines, ratified in the O-8 batch and
# printed in the tab caption (the D-079 pattern — a surface prints every
# emphasis line it uses).
_HIGH_K_SHARE = Decimal("0.27")
_LOW_WHIFF_SHARE = Decimal("0.22")
# D-110: the x-gap tag fires when either season gap's absolute value reaches
# .030 (ratified O-8); contact-first needs squared-up ≥ 35% of competitive
# swings AND bat speed ≥ 72 mph on the season contact board — both.
_X_GAP_LINE = Decimal("0.03")
_SQUARED_UP_LINE = Decimal("0.35")
_CONTACT_BAT_SPEED_LINE = Decimal("72")

# The ratified pitch-type sample floor (10 BBE) for the breakup table's
# per-pitch EV and Air% — below it the INSUFFICIENT treatment, never hidden.
_MIN_BBE_PITCH_TYPE = 10

# D-111: the starter header cards' and Arms tab's emphasis and sample
# lines, each printed on its surface (the D-079 pattern). Green marks the
# digest's pitcher-vulnerability reads only: HR/9 at or above 1.4, and wOBA
# above xwOBA — no invented bands. The L30 side rows carry the ratified
# pitcher-vulnerability floor (80 batters faced / 40 batted balls); contact
# reads carry the general 15-BBE floor. Below a floor the value stays
# visible under the amber INSUFFICIENT advisory, never hidden (D-068).
_HR9_LINE = Decimal("1.4")
_VULN_MIN_BF = 80
_VULN_MIN_BBE = 40
_MIN_BBE_CONTACT = 15


def _ordinal(position: int) -> str:
    """The lineup-slot ordinal — never "1th"."""
    if 10 <= position % 100 <= 20:
        return f"{position}th"
    return f"{position}" + {1: "st", 2: "nd", 3: "rd"}.get(position % 10, "th")


def _card_tags(card: BatterCard, opposing: PitcherCard | None) -> str:
    """The shortlist's tags box: advisories and absences as compact tags,
    plus the D-109 context tags (lineup slot, high-K reads). Tags join with
    " · ", so no tag carries an interpunct inside itself — commas inside,
    interpuncts between."""
    tags: list[str] = []
    insufficient, missing = _component_flags(card)
    if insufficient:
        tags.append(f"low sample: {insufficient}")
    if missing:
        tags.append(f"missing: {missing}")
    if card.lineup_is_estimate:
        tags.append("est. lineup")
    if card.order_position is not None:
        slot = f"bats {_ordinal(card.order_position)}"
        tags.append(slot + (" (est.)" if card.lineup_is_estimate else ""))
    k_share = card.season_k_share
    high_k = k_share is not None and k_share >= _HIGH_K_SHARE
    whiff = opposing.season_whiff_weighted if opposing is not None else None
    if high_k and whiff is not None and whiff <= _LOW_WHIFF_SHARE:
        pa = card.season.plate_appearances if card.season is not None else 0
        tags.append(
            f"high-K bat vs low-whiff arm: K% {float(k_share) * 100:.1f} "
            f"({pa} PA), arsenal whiff {float(whiff) * 100:.1f}%"
        )
    elif high_k:
        pa = card.season.plate_appearances if card.season is not None else 0
        tags.append(f"high-K profile: K% {float(k_share) * 100:.1f} ({pa} PA)")
    # D-110: the regression-gap tag — both gaps always shown, fired by either
    # crossing the ratified line; no expected-stats row, no tag.
    gaps = card.season_gaps
    if gaps is not None and (
        abs(gaps.xiso_minus_iso) >= _X_GAP_LINE or abs(gaps.xwoba_minus_woba) >= _X_GAP_LINE
    ):
        tags.append(
            f"x-gap: xISO {_signed_avg_text(gaps.xiso_minus_iso)}, "
            f"xwOBA {_signed_avg_text(gaps.xwoba_minus_woba)} "
            f"(season, {gaps.plate_appearances} PA)"
        )
    squared = card.squared_up_share
    if (
        squared is not None
        and squared >= _SQUARED_UP_LINE
        and card.squared_up_bat_speed is not None
        and card.squared_up_bat_speed >= _CONTACT_BAT_SPEED_LINE
    ):
        tags.append(
            f"contact-first profile: squared-up {float(squared) * 100:.1f}% "
            f"({card.squared_up_swings} swings), "
            f"bat speed {float(card.squared_up_bat_speed):.1f} mph"
        )
    return " · ".join(tags)


def _slugger_frames(board: SlateBoard) -> tuple[pd.DataFrame, pd.DataFrame, list[BatterCard]]:
    """(texts, styles, cards) — the D-084 shortlist: grades A and S only.

    The shortlist is a reading list, not a metrics table: batter, team, the
    pitcher they face, the grade, the park factor for their batting side, the
    weather, and a tags box carrying the advisories (low sample, missing
    components, estimated lineup). Per-batter metrics moved into the batter
    detail popup (D-084). The third return is the card behind each row, in
    row order, so a grid selection resolves to a batter (GMF-007).
    """
    text_rows: list[dict[str, str]] = []
    style_rows: list[dict[str, str]] = []
    cards: list[BatterCard] = []
    for game in board.games:
        for batters, opposing in (
            (game.away_batters, game.home_pitcher),
            (game.home_batters, game.away_pitcher),
        ):
            for card in batters:
                if not isinstance(card.result, EvaluatedGradeResult):
                    continue
                if card.result.grade not in (Grade.S, Grade.A):
                    continue
                factor = _side_factor(game, card.batting_side)
                weather, weather_absent = _weather_text(game)
                texts = {
                    "Batter": card.full_name,
                    "HR": "$" if card.homered_on_last_game_day else "",
                    "Team": card.team,
                    "Versus": opposing.full_name if opposing else "TBD",
                    "Grade": card.result.grade.value,
                    "Park factor": (
                        f"{float(factor.factor):.0f}" if factor is not None else "not covered"
                    ),
                    "Weather": weather,
                    "Tags": _card_tags(card, opposing),
                }
                styles = {"Grade": _HIGHLIGHT}
                if card.homered_on_last_game_day:
                    styles["HR"] = _MONEY_CSS
                if factor is None:
                    styles["Park factor"] = _REASON_CSS
                if weather_absent:
                    styles["Weather"] = _REASON_CSS
                text_rows.append(texts)
                style_rows.append(styles)
                cards.append(card)
    return pd.DataFrame(text_rows), pd.DataFrame(style_rows), cards


def _component_flags(card: BatterCard) -> tuple[str, str]:
    """(insufficient-sample tags, missing-with-reason tags) for one card."""
    insufficient = [
        obs.component_id.value.replace("_", " ")
        for obs in card.result.present_observations
        if obs.sample_status is SampleStatus.INSUFFICIENT
    ]
    missing = [
        f"{obs.component_id.value.replace('_', ' ')} "
        f"({obs.missing_reason.value.replace('_', ' ').lower()})"
        for obs in card.result.missing_observations
    ]
    return ", ".join(insufficient), ", ".join(missing)


def _side_factor(game: GameCard, side: str | None) -> ParkFactor | None:
    if side == "L":
        return game.home_run_factor_left
    if side == "R":
        return game.home_run_factor_right
    return None


# --------------------------------------------------------------------------
# GMF-007: the recent-form section (D-068) behind the batter detail dialog
# --------------------------------------------------------------------------

# Display precision per form metric: the rates and angles at one decimal,
# matching the live board.
_FORM_PRECISION = {
    "Barrel%": 1,
    "EV": 1,
    "AtkAng": 1,
    "IdealAtkAng%": 1,
    "SwSp%": 1,
    "Pull Air %": 1,
    "Oppo Air %": 1,
    "Hard%": 1,
}

# D-078's wording for a metric with no observations at either window reach.
_FORM_ABSENT_TEXT = "not enough data available"


def _form_section_frames(form: FormSection) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(texts, styles) for ``styled_text_frame`` — D-068's one-row section.

    The columns are D-068's set minus xwOBA, which left the popup under
    D-102 (it stays on the Matchups main tables). A metric present and
    sufficient shows its value; one resolved on the L14 fallback names the
    window ("· L14"); one below its sample floor keeps its value with its
    exact sample and an INSUFFICIENT marker on amber — present, never absent
    (D-023/D-025); one with no observations at either reach reads "not enough
    data available" (D-078). Built on the §GMF-002 grid machinery, like every
    live surface.
    """
    fields: tuple[tuple[str, FormValue | None], ...] = (
        ("Barrel%", form.barrel_pct),
        ("EV", form.exit_velocity),
        ("AtkAng", form.attack_angle_degrees),
        ("IdealAtkAng%", form.ideal_attack_angle_pct),
        ("SwSp%", form.sweet_spot_pct),
        ("Pull Air %", form.pull_air_pct),
        ("Oppo Air %", form.oppo_air_pct),
        ("Hard%", form.hard_hit_pct),
    )
    texts: dict[str, str] = {}
    styles: dict[str, str] = {}
    for column, metric in fields:
        if metric is None or metric.value is None:
            texts[column] = _FORM_ABSENT_TEXT
            styles[column] = _REASON_CSS
            continue
        value_text = f"{float(metric.value):.{_FORM_PRECISION[column]}f}"
        if not metric.sufficient:
            texts[column] = f"{value_text} · n={metric.sample} · INSUFFICIENT"
            styles[column] = _INSUFFICIENT_CSS
        elif metric.window_days == 14:
            texts[column] = f"{value_text} · L14"
        else:
            texts[column] = value_text
    return pd.DataFrame([texts]), pd.DataFrame([styles])


# Every selectable grid's key carries this epoch. Dismissing the detail dialog
# bumps it, so the grids remount under fresh keys with empty selections —
# otherwise the dismissed dialog reopens on the next rerun, because a data
# grid's row selection persists in the widget's state.
def _selection_epoch() -> int:
    return int(st.session_state.get("selection_epoch", 0))


def _bump_selection_epoch() -> None:
    st.session_state["selection_epoch"] = _selection_epoch() + 1


_BB_TYPE_CODES = {
    "ground_ball": "GB",
    "fly_ball": "FB",
    "line_drive": "LD",
    "popup": "PU",
}

_EVENT_LABELS = {
    "field_out": "Out",
    "force_out": "Out",
    "single": "Single",
    "double": "Double",
    "triple": "Triple",
    "home_run": "HR",
    "strikeout": "Strikeout",
    "walk": "Walk",
    "hit_by_pitch": "HBP",
    "sac_fly": "Sac Fly",
    "sac_bunt": "Sac Bunt",
    "field_error": "Error",
    "grounded_into_double_play": "Double Play",
    "double_play": "Double Play",
    "fielders_choice": "Fielder's Choice",
    "fielders_choice_out": "Fielder's Choice",
    "intent_walk": "Int. Walk",
    "strikeout_double_play": "Strikeout",
}

# Exit-velocity heat, hottest at the top — opaque blends on the dark cell so
# the grid's white compositing never washes them out (the D-076 rule).
_EV_HEAT = (
    (100.0, "background-color: #a41616; color: #ffe9e9"),
    (95.0, "background-color: #7a1f12; color: #ffd9c8"),
    (88.0, "background-color: #5c2a10; color: #ffe0b8"),
)
_HR_CSS = "background-color: #2e7d32; color: #eaffcf; font-weight: 700"


def _exit_velo_frames(
    card: BatterCard, threshold_on: bool, threshold: float
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The recent exit-velocity log: one row per plate-appearance-ending
    pitch (D-086), newest game first.

    The threshold is a pitch-type filter over these rows — off lists every
    pitch type; on keeps only the qualifying pitch mix (types at or above the
    qualifying usage share across the window, D-070's 15%). The mix counts
    every pitch seen; the log lists the pitches that ended a plate
    appearance, so its exit-velocity cells are always about contact (or its
    absence: a strikeout carries no reading, shown as a dash).
    """
    total = len(card.recent_events)
    counts: dict[str, int] = {}
    for event in card.recent_events:
        if event.pitch_type:
            counts[event.pitch_type] = counts.get(event.pitch_type, 0) + 1
    # Dist carries the source's projected hit distance (D-091); a pitch
    # with no reading shows a dash, never an invented number.
    qualifying = {name for name, count in counts.items() if total and count / total >= threshold}
    text_rows: list[dict[str, str]] = []
    style_rows: list[dict[str, str]] = []
    for event in card.recent_events:
        if not event.event:
            continue  # mid-plate-appearance pitch: nothing to log
        if threshold_on and event.pitch_type not in qualifying:
            continue
        texts = {
            "Date": event.game_date,
            "Pitch": event.pitch_type or "—",
            "Event": _EVENT_LABELS.get(event.event, event.event.replace("_", " ")),
            "EV": f"{float(event.launch_speed):.1f}" if event.launch_speed is not None else "—",
            "LA": f"{float(event.launch_angle):.0f}" if event.launch_angle is not None else "—",
            "Dist": (f"{float(event.hit_distance):.0f}" if event.hit_distance is not None else "—"),
            "Type": _BB_TYPE_CODES.get(event.bb_type, "—"),
        }
        styles: dict[str, str] = {}
        if event.event == "home_run":
            styles["Event"] = _HR_CSS
        if event.launch_speed is not None:
            for floor, css in _EV_HEAT:
                if float(event.launch_speed) >= floor:
                    styles["EV"] = css
                    break
        text_rows.append(texts)
        style_rows.append(styles)
    return pd.DataFrame(text_rows), pd.DataFrame(style_rows)


_BELOW_MIX_CSS = "color: #8a9a8f"  # below the qualifying usage share: listed, dimmed


def _avg_text(value: Decimal | None) -> str:
    """A rate in the baseball three-digit shape (.250), a dash when absent."""
    if value is None:
        return "—"
    text = f"{float(value):.3f}"
    return text[1:] if text.startswith("0") else text


def _signed_avg_text(value: Decimal) -> str:
    """A signed three-digit rate for the D-110 regression gaps: +.041,
    -.012 — the sign always printed, the leading zero always dropped."""
    text = f"{float(value):+.3f}"
    if text.startswith(("+0", "-0")):
        return text[0] + text[2:]
    return text


def _pct_text(value: Decimal | None) -> str:
    return "—" if value is None else f"{float(value):.1%}"


def _metric_text(value: Decimal | None, spec: str, suffix: str = "") -> str:
    """A starter metric cell (D-111): the formatted value with any unit
    suffix, or the absence dash — one formatter so every cell names None
    the same way."""
    if value is None:
        return "—"
    return f"{float(value):{spec}}{suffix}"


_BREAKUP_CSS = """
<style>
.gm-breakup-wrap { overflow-x: auto; margin: 0.25rem 0 0.5rem; }
.gm-breakup { border-collapse: collapse; width: 100%; font-size: 0.82rem;
  color: #d6ecc9; }
.gm-breakup th, .gm-breakup td { padding: 3px 8px; text-align: right;
  white-space: nowrap; }
.gm-breakup th:first-child, .gm-breakup td:first-child { text-align: left; }
.gm-breakup .gm-halves th { background: #123a16; color: #b8e986;
  letter-spacing: 0.06em; font-size: 0.72rem; text-transform: uppercase;
  text-align: center; border-bottom: 1px solid #2e5b23; }
.gm-breakup .gm-cols th { color: #9dc48c; font-size: 0.72rem; font-weight: 600;
  border-bottom: 1px solid #2e5b23; }
.gm-breakup .gm-half-boundary { border-left: 3px solid rgba(155, 240, 11, 0.55); }
.gm-breakup tbody tr { border-bottom: 1px solid rgba(46, 91, 35, 0.35); }
.gm-breakup tr.gm-dim td { color: #8a9a8f; }
</style>
"""


def _arsenal_breakup_html(
    pitcher: PitcherCard,
    batter_lines: tuple[PitchLine, ...],
    *,
    threshold: float,
    side_filter: frozenset[str] | None,
    side_usage: dict[str, Decimal] | None,
    window_label: str,
    throws_text: str | None,
) -> str:
    """The arsenal breakup table (D-106): one row per pitch in the starter's
    season arsenal. Usage% is HIS — the board's season share, or his share of
    pitches to this hitter hand over the recent window when the side toggle
    is on (D-102); the batter's seen-share never appears. The first half is
    his season-long figures with the pitch; the second is the batter's
    against that pitch from the starter's side over the named window — a
    pitch he has not seen dashes rather than vanishing. Returns "" when a
    side filter removes every row, so the surface names that reason instead
    of rendering an empty table.
    """
    batter_by_type = {line.pitch_type: line for line in batter_lines}
    rows: list[tuple[Decimal, str]] = []
    for season in pitcher.season_lines:
        if side_filter is not None and season.pitch_type not in side_filter:
            continue
        shown_usage = (
            side_usage.get(season.pitch_type, season.usage_share)
            if side_usage is not None
            else season.usage_share
        )
        batter = batter_by_type.get(season.pitch_type)
        if batter is None:
            batter_cells = ["<td>0</td>"] + ["<td>—</td>"] * 10
        else:
            # Per-pitch contact shape (D-109): the ratified 10-BBE
            # pitch-type floor — below it the value keeps its exact sample
            # with an INSUFFICIENT marker; an empty denominator dashes.
            ev_text = "—"
            air_text = "—"
            insufficient_note = ""
            if 0 < batter.batted_balls < _MIN_BBE_PITCH_TYPE:
                insufficient_note = f" · n={batter.batted_balls} · INSUFFICIENT"
            if batter.mean_launch_speed is not None:
                ev_text = f"{float(batter.mean_launch_speed):.1f}" + insufficient_note
            if batter.air_ball_share is not None:
                air_text = _pct_text(batter.air_ball_share) + insufficient_note
            batter_cells = [
                f"<td>{batter.plate_appearances}</td>",
                f"<td>{_avg_text(batter.batting_average)}</td>",
                f"<td>{_avg_text(batter.slugging)}</td>",
                f"<td>{_avg_text(batter.iso)}</td>",
                f"<td>{batter.home_runs if batter.home_runs is not None else '—'}</td>",
                f"<td>{_pct_text(batter.barrel_share)}</td>",
                f"<td>{_pct_text(batter.hard_hit_share)}</td>",
                f"<td>{_avg_text(batter.expected_woba)}</td>",
                f"<td>{_pct_text(batter.whiff_share)}</td>",
                f"<td>{ev_text}</td>",
                f"<td>{air_text}</td>",
            ]
        batter_cells[0] = batter_cells[0].replace("<td>", '<td class="gm-half-boundary">', 1)
        dim = ' class="gm-dim"' if float(shown_usage) < threshold else ""
        name = html.escape(season.pitch_name or season.pitch_type or "— (untagged)")
        row = (
            f"<tr{dim}><td>{name}</td><td>{float(shown_usage):.1%}</td>"
            f"<td>{season.plate_appearances}</td>"
            f"<td>{_avg_text(season.batting_average)}</td>"
            f"<td>{_avg_text(season.slugging)}</td>"
            f"<td>{_avg_text(season.iso)}</td>"
            f"<td>{_avg_text(season.woba)}</td>"
            f"<td>{_avg_text(season.expected_woba)}</td>"
            f"<td>{_pct_text(season.whiff_share)}</td>"
            f"<td>{_pct_text(season.strikeout_share)}</td>"
            f"<td>{_pct_text(season.hard_hit_share)}</td>" + "".join(batter_cells) + "</tr>"
        )
        rows.append((shown_usage, row))
    if not rows:
        return ""
    if side_usage is not None:
        rows.sort(key=lambda item: item[0], reverse=True)
    side_clause = f"{throws_text}-handed pitching" if throws_text else "the starter's side"
    header = (
        '<tr class="gm-halves"><th colspan="2"></th>'
        '<th colspan="9" class="gm-half">Pitcher — season</th>'
        f'<th colspan="11" class="gm-half gm-half-boundary">Batter — '
        f"{html.escape(window_label)} vs {html.escape(side_clause)}</th></tr>"
        '<tr class="gm-cols"><th>Pitch</th><th>Usage%</th>'
        "<th>PA</th><th>AVG</th><th>SLG</th><th>ISO</th><th>wOBA</th><th>xwOBA</th>"
        "<th>Whiff%</th><th>K%</th><th>Hard-Hit%</th>"
        '<th class="gm-half-boundary">PA</th><th>AVG</th><th>SLG</th><th>ISO</th><th>HR</th>'
        "<th>Barrel%</th><th>Hard-Hit%</th><th>xwOBA</th><th>Swing-Str%</th>"
        "<th>EV</th><th>Air%</th></tr>"
    )
    return (
        '<div class="gm-breakup-wrap"><table class="gm-breakup"><thead>'
        + header
        + "</thead><tbody>"
        + "".join(row for _, row in rows)
        + "</tbody></table></div>"
    )


def _arsenal_side_note(pitcher: PitcherCard, side_set: frozenset[str], side_text: str) -> str:
    """What the side toggle did, in words (D-099). An empty record falls back
    to the full arsenal, and a record covering every shown pitch removes
    nothing — both are named, or a no-op toggle reads as broken."""
    if not side_set:
        return (
            f"He threw nothing to {side_text}-handed batters in the recent "
            "pitch record — showing the full arsenal."
        )
    shown = {line.pitch_type for line in pitcher.season_lines}
    if shown <= side_set:
        return (
            f"He threw every pitch in his arsenal to {side_text}-handed "
            "batters over the recent 31-day record — nothing to filter."
        )
    return ""


def _opposing_pitcher(game: GameCard, card: BatterCard) -> PitcherCard | None:
    """The starter this batter grades against — the other club's probable."""
    return game.away_pitcher if card.team == game.home_team else game.home_pitcher


def _game_of(board: SlateBoard, card: BatterCard) -> GameCard | None:
    """The slate game the selected batter plays in — the park panel's venue."""
    for game in board.games:
        if card in game.home_batters or card in game.away_batters:
            return game
    return None


def _render_batter_detail(card: BatterCard, game: GameCard | None) -> None:
    """The batter detail body (D-084): the 2D park with its live wind, the
    D-068 form section, and the recent exit-velocity sheet behind the
    pitch-mix threshold toggle.

    Reachable from the Sluggers and Matchups row selections (D-078), it is
    also the D-080 expanded matchup view: the batter's per-pitch table
    against the starter's side over L30 (D-088), the pitcher's season-long
    Arsenal with its side filter and last-season fallback (D-087), and one
    threshold slider driving every table and the event log.
    """
    st.markdown(f"**{card.full_name}** — {card.team}")

    st.markdown("**Park and conditions**")
    if game is None:
        st.caption("This batter's game is not on today's slate board.")
    else:
        factor = _side_factor(game, card.batting_side)
        detail_lines = [
            f"park factor {float(factor.factor):.0f}" if factor else "park factor not covered"
        ]
        if game.venue_type is VenueType.OPEN_AIR and game.temperature_fahrenheit is not None:
            detail_lines.append(f"{float(game.temperature_fahrenheit):.0f}°F at game time")
        roofed = game.venue_type is not VenueType.OPEN_AIR
        st.markdown(
            field_wind_html(
                venue_name=game.venue_name,
                detail_lines=tuple(detail_lines),
                wind_speed_mph=(
                    float(game.wind_speed_mph) if game.wind_speed_mph is not None else None
                ),
                wind_direction=game.wind_direction,
                wind_absent_text=(
                    "roofed — wind never reaches the field"
                    if roofed
                    else "wind reading unavailable"
                ),
            ),
            unsafe_allow_html=True,
        )

    st.markdown("**Recent form [L7]**")
    if card.form is None:
        st.caption(
            "Recent form is not covered by source: the form-event feed was not "
            "retrieved for this board, so no window could be resolved."
        )
    else:
        texts, styles = _form_section_frames(card.form)
        st.dataframe(styled_text_frame(texts, styles), hide_index=True)
        st.caption(
            "Each metric is the last 7 days [L7]; a metric whose L7 window is "
            "empty falls back to its L14 window, marked '· L14'. A metric below "
            "its sample floor keeps its value with its exact sample and an "
            "INSUFFICIENT marker; one with no observations at either reach reads "
            "'not enough data available' (D-068). Oppo Air % = opposite-field "
            "share of measurable air balls (fly balls, line drives and popups "
            "with hit coordinates and a known batting side); Pull Air % uses "
            "the same denominator."
        )

    st.markdown("**Season profile**")
    if card.babip is not None:
        st.caption(
            f"BABIP {_avg_text(card.babip)} — (H-HR)/(AB-K-HR+SF) over the "
            "season counting line (D-110)."
        )
    elif card.season is not None:
        st.caption(
            "BABIP not computable — the season counting line's BABIP "
            "denominator (AB-K-HR+SF) is empty."
        )
    else:
        st.caption("BABIP not computable — season counting line unavailable.")
    if card.sprint_speed_fps is not None:
        st.caption(
            f"sprint speed {float(card.sprint_speed_fps):.1f} ft/s — shown "
            "because sustained wOBA-over-x gaps co-occur with elite speed "
            "league-wide."
        )
    else:
        st.caption("sprint speed not covered by source for this batter.")

    pitcher = _opposing_pitcher(game, card) if game is not None else None
    threshold_pct = st.slider(
        "Usage threshold for this window's tables",
        min_value=5,
        max_value=40,
        value=int(QUALIFYING_USAGE_SHARE * 100),
        step=1,
        key=f"usage_threshold_{card.player_id}",
        help="Sets the usage line for the arsenal breakup and the event log "
        "below. A display filter only — grading's own qualifying line stays "
        "the ratified 15% (D-070).",
    )
    threshold = threshold_pct / 100.0

    throws_text = (
        "right"
        if pitcher is not None and pitcher.throws == "R"
        else "left"
        if pitcher is not None and pitcher.throws == "L"
        else None
    )
    st.markdown(
        "**Hitting stats — arsenal breakup**"
        + (f" · {pitcher.full_name}" if pitcher is not None else "")
    )
    if pitcher is None:
        st.caption(
            "No opposing starter is named for this game — the breakup appears once probables post."
        )
    elif not pitcher.season_lines:
        st.caption("No arsenal-board coverage for this pitcher, this season or last.")
    else:
        side_known = card.batting_side in ("L", "R")
        side_filter: frozenset[str] | None = None
        side_usage: dict[str, Decimal] | None = None
        side_note = ""
        side_text = ""
        if side_known:
            side_text = "left" if card.batting_side == "L" else "right"
            side_on = st.toggle(
                f"Only pitches he uses vs {side_text}-handed batters",
                value=False,
                key=f"arsenal_side_{card.player_id}",
                help="Filters the rows to the pitch types he has thrown to "
                "this side in the recent pitch record, and Usage% becomes his "
                "share of pitches to this side over that record (D-102); "
                "every other number stays season-long either way.",
            )
            if side_on:
                side_set = (
                    pitcher.pitches_vs_left
                    if card.batting_side == "L"
                    else pitcher.pitches_vs_right
                )
                if side_set:
                    side_filter = side_set
                    side_usage = (
                        pitcher.usage_vs_left
                        if card.batting_side == "L"
                        else pitcher.usage_vs_right
                    )
                side_note = _arsenal_side_note(pitcher, side_set, side_text)
        window_unit = st.segmented_control(
            "Batter-half window",
            ["Months", "Weeks"],
            default="Months",
            key=f"breakup_unit_{card.player_id}",
            help="The batter half's reach. Months is the full month the pitch "
            "record carries; Weeks is one to four weeks back, precomputed at "
            "each reach (D-106). The pitcher half stays season-long either way.",
        )
        if window_unit == "Weeks":
            weeks_back = int(
                st.number_input(
                    "Weeks back",
                    min_value=1,
                    max_value=4,
                    value=2,
                    step=1,
                    key=f"breakup_weeks_{card.player_id}",
                )
            )
            window_days = weeks_back * 7
            window_label = f"last {weeks_back} week" + ("s" if weeks_back != 1 else "")
        else:
            window_days = 30
            window_label = "last month"
        lines = card.matchup_lines_by_window.get(window_days, ())
        table_html = _arsenal_breakup_html(
            pitcher,
            lines,
            threshold=threshold,
            side_filter=side_filter,
            side_usage=side_usage,
            window_label=window_label,
            throws_text=throws_text,
        )
        if not table_html:
            # Only a side filter can empty the table (season_lines is
            # non-empty above): none of the pitches he used against this
            # side made his arsenal board, so season-long figures don't
            # exist for them — name that instead of showing a blank grid.
            st.caption(
                "None of the pitches he used against "
                f"{side_text}-handed batters in the recent record appear on "
                "his arsenal board, so there are no season-long figures to "
                "show for them."
            )
        else:
            st.markdown(_BREAKUP_CSS + table_html, unsafe_allow_html=True)
        if side_usage is not None:
            st.caption(
                f"Usage% is his share of pitches to {side_text}-handed "
                "batters over the recent 31-day record — the arsenal board "
                "publishes usage across all batters only, so the per-hand "
                "basis comes from the pitch window (D-102)."
            )
        if side_note:
            st.caption(side_note)
        season_note = f" Season board: {pitcher.season_lines_year}" + (
            " — no current-season record, so last season fills in (D-087)."
            if game is not None and pitcher.season_lines_year < game.scheduled_start_utc.year
            else "."
        )
        st.caption(
            "One row per pitch in his arsenal: Usage% and the first half are "
            "his season-long figures from the arsenal board — never a window "
            f"(D-087) — and the second half is the batter's {window_label} "
            "against that exact pitch from this side. A pitch the batter has "
            "not seen dashes instead of hiding. Rows dimmed sit below the "
            "threshold. Per-pitch EV and Air% carry the ratified 10-BBE "
            "pitch-type floor — below it the value keeps its exact sample "
            "with an INSUFFICIENT marker (D-109)." + season_note
        )

    st.markdown("**Recent exit velocity — event log**")
    threshold_on = st.toggle(
        f"Pitch-mix threshold (≥{threshold_pct}% usage)",
        value=False,
        key=f"pitch_mix_threshold_{card.player_id}",
        help="Off: every pitch type. On: only the qualifying pitch mix at the "
        "threshold set above — the log's rows are filtered to those pitches.",
    )
    if not card.recent_events:
        st.caption("No pitch-by-pitch events for this batter in the form window.")
        return
    sheet, sheet_styles = _exit_velo_frames(card, threshold_on, threshold)
    if sheet.empty:
        st.caption("No logged plate appearances on these pitches in the window.")
        return
    st.dataframe(styled_text_frame(sheet, sheet_styles), hide_index=True)


@st.dialog("Batter detail", width="large", on_dismiss=_bump_selection_epoch)
def _batter_detail_dialog(card: BatterCard, game: GameCard | None) -> None:
    _render_batter_detail(card, game)


def _render_sluggers(board: SlateBoard, config: GreenMachineConfig) -> BatterCard | None:
    st.caption(
        "The shortlist (D-084): only batters graded A or S under the provisional "
        "v1 model (D-071). Park factor is the batter-side home-run factor; "
        "weather is the venue reading; the tags box carries advisories — low "
        "samples, missing components, estimated lineups — plus context tags: "
        "the lineup slot, the high-K reads (D-109), and the regression-gap "
        "and contact-first reads (D-110). A neon **$** marks a "
        "batter who homered in his most recent game day on or before this "
        "slate (D-094). Tag firing lines: high-K at K% ≥ 27% of season plate "
        "appearances; the low-whiff interaction at an arsenal-wide whiff of "
        "≤ 22% — the interaction tag needs both. The x-gap tag fires when "
        "either season gap's absolute value reaches .030 — both sides of a "
        "gap read the same expected-statistics board, actual vs expected. "
        "Contact-first needs squared-up ≥ 35% of competitive swings AND bat "
        "speed ≥ 72 mph on the season contact board — both."
    )
    texts, styles, cards = _slugger_frames(board)
    if texts.empty:
        st.info(f"No batter grades A or S on the {board.official_date} slate.")
        return None
    event = st.dataframe(
        styled_text_frame(texts, styles),
        hide_index=True,
        height=frame_height("Roomy", len(texts)),
        on_select="rerun",
        selection_mode="single-row",
        key=f"live_sluggers_{board.official_date}_{_selection_epoch()}",
    )
    selected_rows = event.selection.rows
    if not selected_rows:
        st.caption("Select a row to open the batter's detail.")
        return None
    return cards[selected_rows[0]]


# Absence texts that appear in otherwise-plain cells on the Arms and Backtest
# tables. Every such cell takes the one muted reason style, so an absence reads
# the same wherever it appears on the board (the D-076 colour discipline).
_ABSENCE_TEXTS = frozenset({"starter not announced", "not yet observed", "no batters graded", "—"})


def _absence_styles(texts: dict[str, str]) -> dict[str, str]:
    """Per-cell reason CSS for every cell whose text names an absence."""
    return {column: _REASON_CSS for column, text in texts.items() if text in _ABSENCE_TEXTS}


_ARMS_METRIC_COLUMNS = (
    "PA",
    "BBE",
    "wOBA",
    "xwOBA",
    "HR",
    "HR/9",
    "BRL%",
    "LA",
    "ISO",
    "xISO",
    "Air %",
)


def _arms_season_metrics(
    reads: PitcherSeasonReads | None,
) -> tuple[dict[str, str], dict[str, str]]:
    """The season starter-metric columns on the Arms tab (D-111): samples
    as their own columns (D-014), every absence named, green only on the
    digest's two pitcher-vulnerability reads, amber contact reads below the
    ratified 15-BBE floor (D-068)."""
    if reads is None:
        dash = {column: "—" for column in _ARMS_METRIC_COLUMNS}
        return dash, {column: _REASON_CSS for column in dash}
    texts = {
        "PA": str(reads.plate_appearances) if reads.plate_appearances else "—",
        "BBE": str(reads.batted_ball_events) if reads.batted_ball_events else "—",
        "wOBA": _avg_text(reads.woba),
        "xwOBA": _avg_text(reads.expected_woba),
        "HR": str(reads.home_runs) if reads.home_runs is not None else "—",
        "HR/9": (
            f"{float(reads.home_run_per_nine):.2f}" if reads.home_run_per_nine is not None else "—"
        ),
        "BRL%": _pct_text(reads.barrel_share),
        "LA": (
            f"{float(reads.avg_launch_angle):.1f}°" if reads.avg_launch_angle is not None else "—"
        ),
        "ISO": _avg_text(reads.iso),
        "xISO": _avg_text(reads.expected_iso),
        # The season Statcast board against publishes no air-ball split
        # (its fbld/gb columns are exit velocities) — the season air share
        # names its absence; the L30 events carry the real split.
        "Air %": "—",
    }
    styles = {column: _REASON_CSS for column, text in texts.items() if text == "—"}
    if (
        reads.woba is not None
        and reads.expected_woba is not None
        and reads.woba > reads.expected_woba
    ):
        styles["wOBA"] = _HIGHLIGHT
    if reads.home_run_per_nine is not None and reads.home_run_per_nine >= _HR9_LINE:
        styles["HR/9"] = _HIGHLIGHT
    if 0 < reads.batted_ball_events < _MIN_BBE_CONTACT:
        for column in ("BRL%", "LA"):
            if texts[column] != "—":
                styles[column] = _INSUFFICIENT_CSS
    return texts, styles


def _arms_recent_metrics(
    line: PitcherRecentLine | None,
) -> tuple[dict[str, str], dict[str, str]]:
    """The L30 starter-metric columns on the Arms tab (D-111): the kept
    events' figures with their BF/BBE samples. The scope publishes no
    innings and no per-event expected SLG, so HR/9 and xISO name their
    absences and the HR count shows instead; amber contact reads below the
    ratified 15-BBE floor (D-068)."""
    if line is None:
        dash = {column: "—" for column in _ARMS_METRIC_COLUMNS}
        return dash, {column: _REASON_CSS for column in dash}
    texts = {
        "PA": str(line.plate_appearances),
        "BBE": str(line.batted_balls),
        "wOBA": _avg_text(line.woba),
        "xwOBA": _avg_text(line.expected_woba),
        "HR": str(line.home_runs),
        "HR/9": "—",
        "BRL%": _pct_text(line.barrel_share),
        "LA": (
            f"{float(line.avg_launch_angle):.1f}°" if line.avg_launch_angle is not None else "—"
        ),
        "ISO": _avg_text(line.iso),
        "xISO": "—",
        "Air %": _pct_text(line.air_ball_share),
    }
    styles = {column: _REASON_CSS for column, text in texts.items() if text == "—"}
    if line.woba is not None and line.expected_woba is not None and line.woba > line.expected_woba:
        styles["wOBA"] = _HIGHLIGHT
    if 0 < line.batted_balls < _MIN_BBE_CONTACT:
        for column in ("BRL%", "LA"):
            if texts[column] != "—":
                styles[column] = _INSUFFICIENT_CSS
    return texts, styles


def _render_arms(board: SlateBoard) -> None:
    st.caption(
        "Expected starters with their season line and the arsenal they actually "
        "throw (pitch types at or above the qualifying usage share)."
    )
    l30_view = st.toggle(
        "L30 starter metrics — the metric columns read the last 30 days of "
        "kept events; season is the default",
        value=False,
        key="arms_l30_view",
        help=(
            "D-111. Season metrics read the expected-statistics and Statcast "
            "boards against plus the statsapi season line. L30 reads the "
            "window's kept pitch events: it publishes no innings (HR/9 stays "
            "a season read, the HR count shows) and no per-event expected "
            "SLG (xISO stays a season read)."
        ),
    )
    st.caption(
        "Starter metrics (D-111): green marks the digest's "
        "pitcher-vulnerability reads only — HR/9 ≥ 1.4 (season) and wOBA "
        "above xwOBA. Amber: contact reads below the ratified 15-BBE floor — "
        "value shown, advisory attached (D-068). PA and BBE carry every "
        "rate's sample (D-014). Air % is the fly-ball-plus-line-drive share "
        "of the window's batted balls against — the ground-ball profile's "
        "air mirror; the season board publishes no air split, so the "
        "season scope names the absence and Air % reads L30 only."
    )
    text_rows: list[dict[str, str]] = []
    style_rows: list[dict[str, str]] = []
    for game in board.games:
        for card, team in (
            (game.home_pitcher, game.home_team),
            (game.away_pitcher, game.away_team),
        ):
            if card is None:
                tbd_texts = {
                    "Game": f"{game.away_team} at {game.home_team}",
                    "Pitcher": "TBD",
                    "Team": team,
                    "Throws": "starter not announced",
                    "ERA": "starter not announced",
                    "WHIP": "starter not announced",
                    "GS": "starter not announced",
                    "K": "starter not announced",
                    **{column: "starter not announced" for column in _ARMS_METRIC_COLUMNS},
                    "Arsenal": "starter not announced",
                }
                text_rows.append(tbd_texts)
                style_rows.append(_absence_styles(tbd_texts))
                continue
            arsenal = " · ".join(
                f"{row.pitch_type} {float(row.usage_share * 100):.0f}%"
                f" (whiff {float(row.whiff_share * 100):.0f}%)"
                for row in card.arsenal
            )
            observed = card.season is not None
            texts = {
                "Game": f"{game.away_team} at {game.home_team}",
                "Pitcher": card.full_name,
                "Team": team,
                "Throws": card.throws or "not yet observed",
                "ERA": card.season.era if card.season else "not yet observed",
                "WHIP": card.season.whip if card.season else "not yet observed",
                "GS": str(card.season.games_started) if observed else "not yet observed",
                "K": str(card.season.strikeouts) if observed else "not yet observed",
                "Arsenal": arsenal,
            }
            metric_texts, metric_styles = (
                _arms_recent_metrics(card.recent_overall)
                if l30_view
                else _arms_season_metrics(card.season_reads)
            )
            texts = _insert_after(texts, "K", metric_texts)
            text_rows.append(texts)
            style_rows.append({**_absence_styles(texts), **metric_styles})
    st.dataframe(
        styled_text_frame(pd.DataFrame(text_rows), pd.DataFrame(style_rows)),
        hide_index=True,
        key="live_arms",
    )


def _insert_after(texts: dict[str, str], after: str, additions: dict[str, str]) -> dict[str, str]:
    """A copy of the cells dict with ``additions`` placed right behind the
    ``after`` column — column order on this grid is dict insertion order."""
    out: dict[str, str] = {}
    for column, text in texts.items():
        out[column] = text
        if column == after:
            out.update(additions)
    return out


def _grid_line_cells(
    line: BatterGridLine | None, *, include_gaps: bool = False
) -> tuple[dict[str, str], dict[str, str]]:
    """One batter's metric cells for the matchups grid (D-079). A None
    scope or a None rate renders as a named absence, never an invented
    zero; a scope missing at every reach states 'no data available'
    (D-081). ``include_gaps`` is the season view's alone: the D-110
    regression-gap columns appear only there, each with its PA sample."""
    if line is None:
        texts = {
            "AB": "no data available",
            "H": "—",
            "Barrels": "—",
            "HR": "—",
            "EV": "—",
            "Barrel/PA %": "—",
            "Hard-Hit %": "—",
            "AVG": "—",
            "SLG": "—",
            "ISO": "—",
            "+350 ft": "—",
            "Pull Air %": "—",
            "Oppo Air %": "—",
            "xwOBA": "—",
            "Swing-Str %": "—",
        }
        styles = {column: _REASON_CSS for column in texts}
    else:
        rate_texts: dict[str, str | None] = {
            "EV": (f"{float(line.exit_velocity):.1f}" if line.exit_velocity is not None else None),
            "Barrel/PA %": (
                _pct_text(line.barrel_per_pa) if line.barrel_per_pa is not None else None
            ),
            "Hard-Hit %": (
                _pct_text(line.hard_hit_share) if line.hard_hit_share is not None else None
            ),
            "AVG": (_avg_text(line.batting_average) if line.batting_average is not None else None),
            "SLG": _avg_text(line.slugging) if line.slugging is not None else None,
            "ISO": _avg_text(line.iso) if line.iso is not None else None,
            "Pull Air %": (
                _pct_text(line.pull_air_share) if line.pull_air_share is not None else None
            ),
            "Oppo Air %": (
                _pct_text(line.oppo_air_share) if line.oppo_air_share is not None else None
            ),
            "xwOBA": _avg_text(line.expected_woba) if line.expected_woba is not None else None,
            "Swing-Str %": _pct_text(line.whiff_share) if line.whiff_share is not None else None,
        }
        texts = {
            "AB": str(line.at_bats),
            "H": str(line.hits),
            "Barrels": str(line.barrels) if line.barrels is not None else "—",
            "HR": str(line.home_runs),
            # D-097: a count of balls hit 350+ feet, not a rate — the PO reads
            # counting numbers (AB, H, barrels, HR, 350+ balls), not BIP shares.
            "+350 ft": (
                str(line.distance_350_count) if line.distance_350_count is not None else "—"
            ),
        }
        styles = {}
        if line.barrels is None:
            styles["Barrels"] = _REASON_CSS
        if line.distance_350_count is None:
            styles["+350 ft"] = _REASON_CSS
        for column, text in rate_texts.items():
            if text is None:
                texts[column] = "—"
                styles[column] = _REASON_CSS
            else:
                texts[column] = text
    if include_gaps:
        gaps = line.gaps if line is not None else None
        gap_cells = {
            "xISO-ISO": gaps.xiso_minus_iso if gaps is not None else None,
            "xwOBA-wOBA": gaps.xwoba_minus_woba if gaps is not None else None,
        }
        for anchor, name in (("ISO", "xISO-ISO"), ("xwOBA", "xwOBA-wOBA")):
            value = gap_cells[name]
            if value is None:
                texts = _insert_after(texts, anchor, {name: "—"})
                styles[name] = _REASON_CSS
            else:
                sample = gaps.plate_appearances if gaps is not None else 0
                texts = _insert_after(
                    texts, anchor, {name: f"{_signed_avg_text(value)} ({sample} PA)"}
                )
    return texts, styles


# D-111's starter header card: the overall row (Season, or L30 on the
# toggle) plus the two always-L30 side rows, with the drawn stadium between
# the two starters' cards.
_SP_CARD_COLUMNS = ("Scope", "wOBA", "xwOBA", "HR", "HR/9", "BRL%", "LA", "ISO", "xISO")


def _sp_season_row(reads: PitcherSeasonReads | None) -> tuple[dict[str, str], dict[str, str]]:
    """The season-scope row of a starter header card (D-111). Samples ride
    the Scope label beside the rates they basis (D-014); a missing source's
    cells name the absence, never an invented zero. Green marks only the
    digest's two pitcher-vulnerability reads; contact reads below the
    ratified 15-BBE floor keep their values under the amber advisory
    (D-068)."""
    dash = {column: "—" for column in _SP_CARD_COLUMNS[1:]}
    if reads is None or (
        not reads.plate_appearances and not reads.batted_ball_events and reads.home_runs is None
    ):
        return {"Scope": "Season — no season record", **dash}, {
            column: _REASON_CSS for column in dash
        }
    label = f"Season — {reads.plate_appearances} PA · {reads.batted_ball_events} BBE"
    if reads.innings_text:
        label += f" · {reads.innings_text} IP"
    texts = {
        "wOBA": _avg_text(reads.woba),
        "xwOBA": _avg_text(reads.expected_woba),
        "HR": str(reads.home_runs) if reads.home_runs is not None else "—",
        "HR/9": (
            f"{float(reads.home_run_per_nine):.2f}" if reads.home_run_per_nine is not None else "—"
        ),
        "BRL%": _pct_text(reads.barrel_share),
        "LA": (
            f"{float(reads.avg_launch_angle):.1f}°" if reads.avg_launch_angle is not None else "—"
        ),
        "ISO": _avg_text(reads.iso),
        "xISO": _avg_text(reads.expected_iso),
    }
    styles = {column: _REASON_CSS for column, text in texts.items() if text == "—"}
    if (
        reads.woba is not None
        and reads.expected_woba is not None
        and reads.woba > reads.expected_woba
    ):
        styles["wOBA"] = _HIGHLIGHT
    if reads.home_run_per_nine is not None and reads.home_run_per_nine >= _HR9_LINE:
        styles["HR/9"] = _HIGHLIGHT
    if 0 < reads.batted_ball_events < _MIN_BBE_CONTACT:
        for column in ("BRL%", "LA"):
            if texts[column] != "—":
                styles[column] = _INSUFFICIENT_CSS
        styles["Scope"] = _INSUFFICIENT_CSS
        label += " · INSUFFICIENT"
    return {"Scope": label, **texts}, styles


def _sp_recent_row(
    label: str,
    line: PitcherRecentLine | None,
    *,
    vulnerability_floor: bool = False,
) -> tuple[dict[str, str], dict[str, str]]:
    """One L30 row of a starter header card (D-111) — the toggle's overall
    row, or an always-L30 side row. The L30 scope publishes no innings and
    no per-event expected SLG, so HR/9 and xISO name their absences and the
    HR count shows instead. ``vulnerability_floor`` is the side rows'
    ratified 80-BF / 40-BBE line; the overall row carries the general
    15-BBE contact floor. Below a floor the values stay visible under the
    amber advisory, never hidden (D-068)."""
    dash = {column: "—" for column in _SP_CARD_COLUMNS[1:]}
    if line is None:
        return {"Scope": f"{label} — no L30 record", **dash}, {
            column: _REASON_CSS for column in dash
        }
    full_label = f"{label} — {line.plate_appearances} BF · {line.batted_balls} BBE"
    texts = {
        "wOBA": _avg_text(line.woba),
        "xwOBA": _avg_text(line.expected_woba),
        "HR": str(line.home_runs),
        "HR/9": "—",
        "BRL%": _pct_text(line.barrel_share),
        "LA": (
            f"{float(line.avg_launch_angle):.1f}°" if line.avg_launch_angle is not None else "—"
        ),
        "ISO": _avg_text(line.iso),
        "xISO": "—",
    }
    styles = {column: _REASON_CSS for column, text in texts.items() if text == "—"}
    if line.woba is not None and line.expected_woba is not None and line.woba > line.expected_woba:
        styles["wOBA"] = _HIGHLIGHT
    insufficient = (
        (line.plate_appearances < _VULN_MIN_BF or line.batted_balls < _VULN_MIN_BBE)
        if vulnerability_floor
        else 0 < line.batted_balls < _MIN_BBE_CONTACT
    )
    if insufficient:
        for column, text in texts.items():
            if text != "—":
                styles[column] = _INSUFFICIENT_CSS
        styles["Scope"] = _INSUFFICIENT_CSS
        full_label += " · INSUFFICIENT"
    return {"Scope": full_label, **texts}, styles


def _sp_card(card: PitcherCard | None, team: str, *, l30: bool) -> None:
    """One starter header card (D-111): name, team, and hand over the scope
    rows. An unannounced starter names the absence."""
    if card is None:
        st.markdown(f"**{team} starter**")
        st.caption("starter not announced")
        return
    throws = f" · throws {card.throws}" if card.throws else ""
    st.markdown(f"**{card.full_name}** — {team}{throws}")
    overall = (
        _sp_recent_row("L30", card.recent_overall) if l30 else _sp_season_row(card.season_reads)
    )
    rows = [
        overall,
        _sp_recent_row("vs L (L30)", card.recent_vs_left, vulnerability_floor=True),
        _sp_recent_row("vs R (L30)", card.recent_vs_right, vulnerability_floor=True),
    ]
    st.dataframe(
        styled_text_frame(
            pd.DataFrame([row for row, _ in rows]),
            pd.DataFrame([style for _, style in rows]),
        ),
        hide_index=True,
        key=f"sp_card_{card.player_id}_{'l30' if l30 else 'season'}",
    )


def _stadium_panel(game: GameCard) -> None:
    """The drawn stadium between the two starter cards (D-111): the field
    with its live wind flow, the park factors with their PA samples, and
    temperature beside humidity — each absence named, never an invented
    number."""
    factor_left = game.home_run_factor_left
    factor_right = game.home_run_factor_right
    if factor_left is not None and factor_right is not None:
        factor_text = (
            f"HR factor L {float(factor_left.factor):.0f} ({factor_left.plate_appearances} PA)"
            f" · R {float(factor_right.factor):.0f} ({factor_right.plate_appearances} PA)"
        )
    elif factor_left is not None:
        factor_text = (
            f"HR factor L {float(factor_left.factor):.0f} ({factor_left.plate_appearances} PA)"
            " · R not covered"
        )
    elif factor_right is not None:
        factor_text = (
            f"HR factor R {float(factor_right.factor):.0f} ({factor_right.plate_appearances} PA)"
            " · L not covered"
        )
    else:
        factor_text = "HR factor not covered"
    detail_lines = [factor_text]
    if game.venue_type is VenueType.OPEN_AIR:
        temperature = (
            f"{float(game.temperature_fahrenheit):.0f}°F"
            if game.temperature_fahrenheit is not None
            else "temp unavailable"
        )
        humidity = (
            f"humidity {float(game.relative_humidity_percent):.0f}%"
            if game.relative_humidity_percent is not None
            else "humidity unpublished"
        )
        detail_lines.append(f"{temperature} · {humidity}")
    roofed = game.venue_type is not VenueType.OPEN_AIR
    st.markdown(
        field_wind_html(
            venue_name=game.venue_name,
            detail_lines=tuple(detail_lines),
            wind_speed_mph=(
                float(game.wind_speed_mph) if game.wind_speed_mph is not None else None
            ),
            wind_direction=game.wind_direction,
            wind_absent_text=(
                "roofed — wind never reaches the field" if roofed else "wind reading unavailable"
            ),
        ),
        unsafe_allow_html=True,
    )


def _render_matchups(board: SlateBoard) -> BatterCard | None:
    st.caption(
        "One row per batter against the expected starter's mix — pitches at "
        "or above a 14% usage share over the named window (D-079). Every "
        "column is computed over that scope; the grade is always the L30 "
        "computation, whichever view is showing. Select a batter row to "
        "open their recent-form detail."
    )
    season_view = st.toggle(
        "Season view — every column reads the season sources; the grade stays L30",
        value=False,
        key="matchups_season_view",
        help=(
            "D-079's toggle. Season +350 ft, Pull Air % and Oppo Air % have "
            "no published source, so those cells name the absence. This view "
            "alone carries the D-110 regression gaps, xISO-ISO and "
            "xwOBA-wOBA — expected minus actual, both sides off the same "
            "expected-statistics board so the denominators match."
        ),
    )
    selected: BatterCard | None = None
    for game in board.games:
        pitchers = " vs ".join(
            card.full_name if card else "TBD" for card in (game.away_pitcher, game.home_pitcher)
        )
        with st.expander(f"{game.away_team} at {game.home_team} — {game.venue_name} · {pitchers}"):
            sp_l30 = st.toggle(
                "Starter metrics: L30 — season is the default",
                value=False,
                key=f"sp_l30_{game.game_pk}",
                help=(
                    "D-111. The overall row flips from the season boards to "
                    "the starter's last 30 days of kept pitch events. The "
                    "side rows always read that L30 window."
                ),
            )
            away_column, field_column, home_column = st.columns([5, 4, 5])
            with away_column:
                _sp_card(game.away_pitcher, game.away_team, l30=sp_l30)
            with field_column:
                _stadium_panel(game)
            with home_column:
                _sp_card(game.home_pitcher, game.home_team, l30=sp_l30)
            st.caption(
                "Starter cards (D-111): the overall row reads the season "
                "boards (expected-statistics and Statcast boards against, "
                "statsapi season line) or, on the toggle, the last 30 days "
                "of kept events; the side rows always read that L30 window. "
                "Green marks only the digest's pitcher-vulnerability reads — "
                "HR/9 ≥ 1.4 and wOBA above xwOBA. L30 publishes no innings "
                "and no per-event expected SLG, so HR/9 and xISO stay "
                "season reads and the HR count shows instead. Amber: below "
                "the ratified floor — 80 BF / 40 BBE on a side row, 15 BBE "
                "on contact reads — value shown, advisory attached (D-068)."
            )
            for label, batters, opposing_card in (
                ("Away", game.away_batters, game.home_pitcher),
                ("Home", game.home_batters, game.away_pitcher),
            ):
                st.markdown(f"**{label} lineup**")
                if batters:
                    if opposing_card is None:
                        scope_text = "no expected starter named — no mix to line up against"
                    elif batters[0].mix_label:
                        scope_text = f"vs {opposing_card.full_name}'s mix — {batters[0].mix_label}"
                    else:
                        scope_text = f"vs {opposing_card.full_name} — no mix record at any reach"
                    st.caption(
                        f"Scope: {scope_text}. "
                        + (
                            "Columns read the batter's season sources; the "
                            "xISO-ISO and xwOBA-wOBA gaps are season-scope "
                            "reads off the expected-statistics board, shown "
                            "on this view only (D-110)."
                            if season_view
                            else (
                                "Columns read the batter's last 30 days "
                                "against that mix's qualifying pitches."
                            )
                        )
                    )
                text_rows: list[dict[str, str]] = []
                style_rows: list[dict[str, str]] = []
                for card in batters:
                    # D-098: no Form column here — the full form section is one
                    # tap away in the batter detail, so the grid stays lean.
                    evaluated = isinstance(card.result, EvaluatedGradeResult)
                    line = card.season_line if season_view else card.mix_line
                    metric_texts, metric_styles = _grid_line_cells(line, include_gaps=season_view)
                    texts = {
                        "#": (str(card.order_position) if card.order_position is not None else "—"),
                        "Batter": card.full_name,
                        "Bats": card.bats,
                    }
                    texts.update(metric_texts)
                    texts["Grade"] = card.result.grade.value if evaluated else _NOT_EVALUABLE
                    texts["Total"] = (
                        f"{float(card.result.total_score):.1f}" if evaluated else _NOT_EVALUABLE
                    )
                    texts["Lineup"] = "est." if card.lineup_is_estimate else ""
                    text_rows.append(texts)
                    styles = dict(metric_styles)
                    if not evaluated:
                        styles["Total"] = _REASON_CSS
                    style_rows.append(styles)
                event = st.dataframe(
                    styled_text_frame(pd.DataFrame(text_rows), pd.DataFrame(style_rows)),
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    key=(
                        f"matchups_{board.official_date}_{game.game_pk}_"
                        f"{label.lower()}_{_selection_epoch()}"
                    ),
                )
                rows = event.selection.rows
                if rows and selected is None:
                    selected = batters[rows[0]]
    return selected


def _render_conditions(board: SlateBoard) -> None:
    st.caption(
        "Parks and conditions. A roofed venue grades at the assumed neutral "
        "indoor value — an assumption, labelled, not a measurement. A park "
        "factor carries its plate-appearance sample beside it (D-014)."
    )
    text_rows: list[dict[str, str]] = []
    style_rows: list[dict[str, str]] = []
    numeric_columns = ("HR factor (LHB)", "n", "HR factor (RHB)", "n ", "Temp °F")
    for game in board.games:
        left = game.home_run_factor_left
        right = game.home_run_factor_right
        temp_absent = (
            "roofed — neutral value"
            if game.venue_type is not VenueType.OPEN_AIR
            else "source unavailable"
        )
        values: dict[str, tuple[float | int | None, str]] = {
            "HR factor (LHB)": (float(left.factor) if left else None, "not covered"),
            "n": (left.plate_appearances if left else None, "not covered"),
            "HR factor (RHB)": (float(right.factor) if right else None, "not covered"),
            "n ": (right.plate_appearances if right else None, "not covered"),
            "Temp °F": (
                (
                    float(game.temperature_fahrenheit)
                    if game.temperature_fahrenheit is not None
                    else None
                ),
                temp_absent,
            ),
        }
        texts: dict[str, str] = {
            "Game": f"{game.away_team} at {game.home_team}",
            "Venue": game.venue_name,
            # Human label, not the enum's snake_case value.
            "Type": game.venue_type.value.replace("_", " "),
        }
        styles: dict[str, str] = {}
        for column in numeric_columns:
            value, absent_text = values[column]
            if value is None:
                texts[column] = absent_text
                styles[column] = _REASON_CSS
            else:
                texts[column] = f"{float(value):.0f}"
        text_rows.append(texts)
        style_rows.append(styles)
    st.dataframe(
        styled_text_frame(pd.DataFrame(text_rows), pd.DataFrame(style_rows)),
        hide_index=True,
        key="live_conditions",
    )
    if board.diagnostics:
        st.markdown("**Fetch diagnostics — what degraded, and why**")
        for line in board.diagnostics:
            st.markdown(f"- {line}")


def _render_tab(label: str, render: Callable[[], BatterCard | None]) -> BatterCard | None:
    """One tab's failure degrades to a named warning, never a blanked page.

    An exception escaping a tab renderer ends the whole Streamlit script run —
    every other tab vanishes with it, the failure shape observed on the
    deployed app when a NaN cell reached the highlight mapper (pandas stores a
    missing numeric as NaN, and ``Decimal('NaN') >= edge`` raises
    ``decimal.InvalidOperation``). Each view now stands or falls on its own
    (D-075). The renderer's return — the batter selected on its grid, if any —
    propagates so the board can open the one detail dialog per run.
    """
    try:
        return render()
    except Exception as exc:
        st.warning(
            f"The {label} view could not be rendered "
            f"({type(exc).__name__}). The remaining views are unaffected."
        )
        return None


def _open_batter_detail(card: BatterCard, game: GameCard | None) -> None:
    """Open the run's one detail dialog. The dialog is a view like any other:
    its failure must never end the whole script run (D-075), so it degrades
    to a named warning and the board stays up."""
    try:
        _batter_detail_dialog(card, game)
    except Exception as exc:
        st.warning(
            "The batter detail could not be opened "
            f"({type(exc).__name__}). The board is unaffected."
        )


def render_live_board() -> None:
    """The four live tabs (D-072). Live only in a deployed environment: a local
    render never becomes a network call, mirroring the weather seam."""
    if resolve_environment() == "local":
        st.subheader("Today's slate")
        st.caption(
            "The live board binds only in a deployed environment: locally it "
            "would be a network call, so it stays unbuilt here. Deployed, this "
            "surface pulls the day's slate, lineups, season boards, form events, "
            "park factors and forecasts from the two approved MLB hosts and the "
            "NWS adapter, then grades every batter under the v1 config (D-071)."
        )
        return
    # D-101: the slate day is any date on the calendar the viewer picks —
    # a date selector, not a three-way toggle. Only the slate changes; the
    # knowledge cutoff (lineup estimates, form windows) stays anchored to
    # now. The picker is bounded to a month back and a week ahead: beyond
    # that the sources cannot answer the slate's questions honestly.
    today = date.today()
    title_col, nav_col = st.columns([3, 2])
    with nav_col:
        chosen = st.date_input(
            "Slate date",
            value=today,
            min_value=today - timedelta(days=30),
            max_value=today + timedelta(days=7),
            key="slate_date_choice",
        )
    slate_date = chosen if isinstance(chosen, date) else today
    relative = {
        today - timedelta(days=1): "yesterday",
        today: "today",
        today + timedelta(days=1): "tomorrow",
    }.get(slate_date)
    heading = f"Slate — {slate_date.isoformat()}"
    if relative is not None:
        heading += f" ({relative})"
    with title_col:
        st.subheader(heading)
    blot = st.empty()
    blot.markdown(BLOT_HTML, unsafe_allow_html=True)
    board = live_board(slate_date.isoformat())
    blot.empty()
    if isinstance(board, FetchFailure):
        st.warning(f"The {slate_date.isoformat()} schedule could not be fetched: {board.reason}")
        return
    st.caption(
        f"Slate of {board.official_date}, assembled {board.as_of:%H:%M UTC}. "
        f"{len(board.games)} game(s). Board refreshes every "
        f"{BOARD_TTL_SECONDS // 60} minutes; form windows hourly."
    )
    sluggers, arms, matchups, conditions = st.tabs(["Sluggers", "Arms", "Matchups", "Conditions"])
    selected: BatterCard | None = None
    for label, container, render in (
        ("Sluggers", sluggers, lambda: _render_sluggers(board, production_config())),
        ("Arms", arms, lambda: _render_arms(board)),
        ("Matchups", matchups, lambda: _render_matchups(board)),
        ("Conditions", conditions, lambda: _render_conditions(board)),
    ):
        with container:
            choice = _render_tab(label, render)
        if selected is None:
            selected = choice
    # One dialog per script run, opened after the tabs: Streamlit allows a
    # single dialog call per run, and the grids' epoch keys guarantee at most
    # one selection survives a dismiss.
    if selected is not None:
        _open_batter_detail(selected, _game_of(board, selected))
    weather_failures = LIVE_WEATHER_DIAGNOSTICS.get(slate_date.isoformat(), [])
    if weather_failures:
        joined = "; ".join(weather_failures)
        st.caption(
            "Weather reads that failed during this build (absent on the board): "
            f"{joined}. Further venues were not asked."
        )


def render_parks_screen() -> None:
    """The §GMF-004 parks screen: thirty venues, factors per handedness.

    **Two provenances, stated apart.** The factor columns are the pinned Savant
    export — real values, digest-verified on read, with the manual export date
    on screen so the page can never imply fresher data than it holds. The roof
    and forecast columns are fixture-bound: the weather seam exists as one
    adapter interface (criterion 3) and §GMF-005 is where a live source binds
    behind it. Mixing the two silently would be the most expensive kind of
    correct, so the captions name which is which.

    No ranking and nothing pre-selected: rows open in the venue's own name
    order, and sorting by a factor is the user's click in the header
    (D-015/D-017). The ticket's name invites a target list; the product does
    not compose one.
    """
    adapter, live = weather_binding()
    snapshot = parks_demo_snapshot(adapter)
    screen = park_frames(snapshot)
    st.subheader("Parks")
    st.caption(
        f"{basis_statement()} A factor shows its plate-appearance sample beside "
        "it — the pinned export spans 13,560 to 31,517 PA, so two factors are "
        "not equally well evidenced (D-014). Initial order is neutral — the "
        "venue's own name — and every ordering is yours to apply in the headers."
    )
    environment = resolve_environment()
    if live:
        st.caption(
            f"**Three provenances on this table, and they are not the same.** Park "
            f"factors are the real pinned Savant export. Forecasts are **live from "
            f"api.weather.gov** in this `{environment}` environment. Roof state is "
            "still **fixture-bound** (OQ-4 values): §GMF-005 made weather live and "
            "gave roof no source, so a roof reading here is a validation artifact "
            "and not a measurement. "
            f"{retrieval_statement(snapshot)} "
            f"{getattr(adapter, 'freshness_statement', lambda: '')()}"
        )
    else:
        st.caption(
            "**Roof state and forecast are both fixture-bound** in this local "
            "environment: the weather seam is one adapter interface (§GMF-004), "
            "and the live NWS adapter (§GMF-005) binds only in a deployed "
            "environment, so a local render never becomes a network call. "
            "Their values are deliberately non-baseball (OQ-4). Park factors "
            "above are the real pinned export; conditions here are not. "
            f"{retrieval_statement(snapshot)}"
        )
    chosen = st.multiselect(
        "Columns",
        options=list(PARK_COLUMNS),
        default=list(PARK_COLUMNS),
        key="parks_columns",
        help="The venue column always shows, so a selection stays readable.",
    )
    st.dataframe(
        graded_styler(screen.data, screen.texts, screen.styles, PARK_FACTOR_COLUMNS),
        column_order=visible_columns(tuple(chosen), VENUE_COLUMN, PARK_COLUMNS),
        height=frame_height("Roomy", len(screen.data)),
        hide_index=True,
        key="parks",
    )

    for note in forecast_suppression_notes(snapshot):
        st.markdown(f"- {note}")
    unavailable = unavailable_forecast_notes(snapshot)
    if unavailable:
        st.markdown("**Forecast applies but the adapter had no value**")
        for note in unavailable:
            st.markdown(f"- {note}")
        st.caption(
            "The roof does not suppress these; the source did not supply them. "
            "That is a fact about the adapter, not about the ballpark."
        )

    reasons = getattr(adapter, "diagnostics", dict)()
    if reasons:
        st.markdown("**Why a forecast could not be shown, per venue**")
        by_name = {park.venue.venue_id: park.venue.name for park in snapshot.parks}
        for venue_id, reason in sorted(reasons.items()):
            st.markdown(f"- {by_name.get(venue_id, venue_id)} — {reason}")
        st.caption(
            "The contract records one reason — source unavailable — for a request "
            "that timed out and for a venue the source does not cover. Those read "
            "the same in the data and mean very different things to a person, so "
            "the distinction is stated here rather than by adding a fourth absence "
            "state to a contract that does not need one."
        )

    missing = factor_absence_notes(snapshot)
    if missing:
        st.markdown("**Absent park factors, in words**")
        for note in missing:
            st.markdown(f"- {note}")
        st.caption(
            "The component renders a null-data cell as its own `None` and drops "
            "the display value carried for it, so an absent factor's reason is "
            "stated here rather than left to a cell's background colour. The "
            "export answered completely; these venues have no row in it yet, "
            "and nothing is substituted for the gap."
        )


# --------------------------------------------------------------------------
# D-095: the backtest view — past slates regraded vs. their outcomes
# --------------------------------------------------------------------------

_BACKTEST_RANGES = {"Last 7 days": 7, "Last 14 days": 14}


@st.cache_data(ttl=DAY_EVENTS_TTL_SECONDS, show_spinner=False)
def _backtest_board(slate_iso: str) -> SlateBoard | FetchFailure:
    """Regrade a past slate as of the prior evening (D-095). Weather is not
    reconstructed: temperature and wind bind as absent, and the affected
    components name that absence like any other."""
    api, savant = live_mlb_adapters()
    slate_date = date.fromisoformat(slate_iso)
    year = slate_date.year

    def fetch_day(day: date) -> object:
        return _day_events(day.isoformat(), year)

    return build_board(
        api=api,
        savant=savant,
        slate_date=slate_date,
        as_of=slate_as_of(slate_date),
        config=production_config(),
        fetch_day_events=fetch_day,  # type: ignore[arg-type]
        temperature_for=lambda venue: None,  # type: ignore[arg-type]
        park_factors=park_factor_table(),
        wind_for=lambda venue: None,  # type: ignore[arg-type]
    )


@st.cache_data(ttl=DAY_EVENTS_TTL_SECONDS, show_spinner=False)
def _backtest_game_logs(
    slate_iso: str, player_ids: tuple[int, ...]
) -> dict[int, tuple[GameLogEntry, ...]] | FetchFailure:
    """One past day's hitting game logs for the slate's batters, cached: a
    completed day never changes. Outcomes read the near-real-time game log
    (D-100), not the day-indexed pitch record."""
    api, _ = live_mlb_adapters()
    start = end = date.fromisoformat(slate_iso).strftime("%m/%d/%Y")
    ordered = tuple(sorted(player_ids))
    logs: dict[int, tuple[GameLogEntry, ...]] = {}
    for i in range(0, len(player_ids), SEASON_IDS_PER_REQUEST):
        fetched = api.fetch_recent_game_logs(ordered[i : i + SEASON_IDS_PER_REQUEST], start, end)
        if isinstance(fetched, FetchFailure):
            return fetched
        logs.update(fetched)
    return logs


def _backtest_day_rows(rows: tuple[BacktestRow, ...]) -> pd.DataFrame:
    """One backtested day's outcome rows as a display frame."""
    return pd.DataFrame(
        [
            {
                "Batter": row.full_name,
                "Team": row.team,
                "Grade": row.grade,
                "Homered": "yes" if row.homered else "",
            }
            for row in rows
        ]
    )


def _render_backtest() -> None:
    """D-095's backtest: regrade past slates, pool hit rates per grade, and
    price them at the viewer's own entered odds."""
    st.subheader("Backtest — grade hit rates")
    st.caption(
        "Each past slate is regraded as of the prior evening, so no event from "
        "the measured day leaks into the grade (D-095). Two named "
        "approximations: season boards (hitting, pitch arsenals, statcast) are "
        "today's snapshots — the regrade reads current season rows for a past "
        "date — and weather is not reconstructed, so temperature and wind are "
        "absent on these boards. ROI is arithmetic on the odds you enter; the "
        "product holds no odds source. Not-evaluable batters carry no grade "
        "and are excluded from the tallies."
    )
    if resolve_environment() == "local":
        st.caption(
            "The backtest binds only in a deployed environment, like the live "
            "board: locally a regrade would be a network call, so this view "
            "stays unbuilt here."
        )
        return
    range_col, odds_col, _ = st.columns([2, 1, 2])
    with range_col:
        range_label = st.segmented_control(
            "Window",
            list(_BACKTEST_RANGES),
            default="Last 7 days",
            key="backtest_range",
        )
    with odds_col:
        odds = st.number_input(
            "American odds",
            value=-110,
            step=5,
            key="backtest_odds",
            help="Your own entry — +N pays N/100 per unit, -N pays 100/N, 0 is even.",
        )
    days = _BACKTEST_RANGES[range_label or "Last 7 days"]
    dates = [date.today() - timedelta(days=d) for d in range(1, days + 1)]
    blot = st.empty()
    blot.markdown(BLOT_HTML, unsafe_allow_html=True)
    per_day: dict[str, tuple[BacktestRow, ...]] = {}
    failures: list[str] = []
    for day in dates:
        iso = day.isoformat()
        board = _backtest_board(iso)
        if isinstance(board, FetchFailure):
            failures.append(f"{iso} board: {board.reason}")
            continue
        if not board.games:
            continue  # an off-day has nothing to measure
        batter_ids = tuple(
            card.player_id
            for game in board.games
            for card in (*game.away_batters, *game.home_batters)
        )
        logs = _backtest_game_logs(iso, batter_ids)
        if isinstance(logs, FetchFailure):
            failures.append(f"{iso} outcomes: {logs.reason}")
            continue
        if not logs:
            # No game-log lines at all for the slate's batters means the
            # outcome source did not answer; tallying it would fabricate a
            # row of zero homers, so the day is excluded and named
            # (D-023/D-025).
            failures.append(f"{iso} outcomes: source returned no game logs — not tallied")
            continue
        per_day[iso] = outcomes_for_day(board, logs)
    blot.empty()
    all_rows = tuple(row for rows in per_day.values() for row in rows)
    summary_rows: list[dict[str, str]] = []
    for tally in tally_grades(all_rows):
        rate = tally.hit_rate
        if rate is None:
            summary_rows.append(
                {
                    "Grade": tally.grade,
                    "Batters": "0",
                    "Homered": "0",
                    "Hit rate": "no batters graded",
                    "ROI / 1u": "—",
                }
            )
            continue
        summary_rows.append(
            {
                "Grade": tally.grade,
                "Batters": str(tally.batters),
                "Homered": str(tally.homered),
                "Hit rate": f"{float(rate) * 100:.1f}%",
                "ROI / 1u": f"{float(roi_per_unit(rate, int(odds))) * 100:+.1f}%",
            }
        )
    st.dataframe(
        styled_text_frame(
            pd.DataFrame(summary_rows),
            pd.DataFrame([_absence_styles(row) for row in summary_rows]),
        ),
        hide_index=True,
        key=f"backtest_summary_{days}",
    )
    st.caption(
        "ROI / 1u prices every graded batter as a 1-unit stake at the entered "
        "odds: hit rate x profit - (1 - hit rate). It is arithmetic on your "
        "entry, never a recommendation (D-015/D-017)."
    )
    for iso, rows in per_day.items():
        homered = sum(1 for row in rows if row.homered)
        with st.expander(f"{iso} — {len(rows)} graded batters, {homered} homered"):
            st.dataframe(
                _backtest_day_rows(rows),
                hide_index=True,
                key=f"backtest_day_{iso}",
            )
    if failures:
        st.caption("Days not tallied: " + "; ".join(failures) + ".")


@st.cache_data
def _logo_data_uri() -> str | None:
    """The D-107 mark as inline data: read once from the repo asset, handed
    to the shell as a data URI so the header never makes a remote request.
    Absent asset → None, and the shell's hand-drawn orb stands in."""
    path = REPO_ROOT / "assets" / "gm_logo.png"
    if not path.is_file():
        return None
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def main() -> None:
    st.set_page_config(page_title="GreenMachine", layout="wide")
    bridge_secrets_into_environment()
    st.markdown(SHELL_CSS, unsafe_allow_html=True)
    st.markdown(DIAL_CSS, unsafe_allow_html=True)
    st.markdown(BLOT_CSS, unsafe_allow_html=True)
    st.markdown(FIELD_CSS, unsafe_allow_html=True)
    orb, header, action = st.columns([1, 5, 1])
    with orb:
        st.markdown(orb_html(_logo_data_uri()), unsafe_allow_html=True)
    with header:
        st.markdown(TITLE_HTML, unsafe_allow_html=True)
        st.markdown(
            '<p class="gm-tagline">Home-run research board — criteria tallies, '
            "never predictions (D-015/D-017).</p>",
            unsafe_allow_html=True,
        )
        live_weather = resolve_environment() != "local"
        weather_clause = (
            "live NWS weather"
            if live_weather
            else "fixture weather (local runs never make network calls)"
        )
        st.markdown(
            f'<p class="gm-status">ENVIRONMENT {resolve_environment()} · '
            f"VERSION {resolve_version()} · COMMIT {resolve_commit()} · "
            f"{weather_clause}</p>",
            unsafe_allow_html=True,
        )
    # D-095: the backtest is a separate view behind a top-right button, not a
    # tab on the dial — the dial is for reading a slate, this is for auditing
    # the grades.
    with action:
        st.markdown('<div style="height: 3.2rem"></div>', unsafe_allow_html=True)
        # st.rerun after the swap: the button itself is drawn from the view
        # state, so without a rerun the header would show the stale button
        # until the next interaction.
        if st.session_state.get("view") == "backtest":
            if st.button("← Board", key="view_board"):
                st.session_state["view"] = "board"
                st.rerun()
        elif st.button("Backtest", key="view_backtest"):
            st.session_state["view"] = "backtest"
            st.rerun()
    if st.session_state.get("view") == "backtest":
        _render_backtest()
    else:
        render_live_board()


if __name__ == "__main__":
    main()
