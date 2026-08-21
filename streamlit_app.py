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

import os
import subprocess
from collections.abc import Callable
from datetime import UTC, date, datetime
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
from greenmachine.inputs import InputSnapshot, Window
from greenmachine.inputs.contract import Handedness, ParkFactor, ParkVenue, VenueType
from greenmachine.inputs.savant_park_factors import basis_statement, read_factors
from greenmachine.live.form import FormSection, FormValue
from greenmachine.live.grading import QUALIFYING_USAGE_SHARE
from greenmachine.live.mlb_api import FetchFailure, MlbStatsApi
from greenmachine.live.pipeline import (
    BatterCard,
    GameCard,
    PitcherCard,
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
    ORB_HTML,
    SHELL_CSS,
    TITLE_HTML,
    field_wind_html,
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

# Diagnostics from the last board build's weather reads, rendered after the
# board. Module-level because the reader closure runs inside the cached build;
# the list is cleared at the start of each build, so it always names the
# current board's weather story and nothing older.
LIVE_WEATHER_DIAGNOSTICS: list[str] = []


def _temperature_lookup() -> object:
    """A venue -> °F reader over the weather seam; None locally or on absence."""
    adapter, live = weather_binding()

    def read(venue: ParkVenue) -> Decimal | None:
        if not live or len(LIVE_WEATHER_DIAGNOSTICS) >= WEATHER_FAILURE_CIRCUIT_BREAKER:
            return None
        try:
            field = adapter.forecast_for(venue)
        except Exception as exc:  # composition-root last resort: weather downgrades to absence
            LIVE_WEATHER_DIAGNOSTICS.append(
                f"{venue.venue_id}: {type(exc).__name__} on {type(venue).__name__}"
            )
            return None
        if field.value is None:
            return None
        return field.value.temperature_f

    return read


def _wind_lookup() -> object:
    """A venue -> (wind mph, compass direction) reader over the weather seam;
    None locally or on absence — same discipline as the temperature lookup."""
    adapter, live = weather_binding()

    def read(venue: ParkVenue) -> tuple[Decimal, str] | None:
        if not live or len(LIVE_WEATHER_DIAGNOSTICS) >= WEATHER_FAILURE_CIRCUIT_BREAKER:
            return None
        try:
            field = adapter.forecast_for(venue)
        except Exception as exc:  # composition-root last resort: wind downgrades to absence
            LIVE_WEATHER_DIAGNOSTICS.append(
                f"{venue.venue_id}: {type(exc).__name__} on {type(venue).__name__}"
            )
            return None
        if field.value is None:
            return None
        return field.value.wind_speed_mph, field.value.wind_direction

    return read


@st.cache_data(ttl=BOARD_TTL_SECONDS, show_spinner=False)
def live_board(slate_iso: str) -> SlateBoard | FetchFailure:
    """Assemble and grade the slate; cached so a rerun is not a refetch."""
    api, savant = live_mlb_adapters()
    slate_date = date.fromisoformat(slate_iso)
    year = slate_date.year

    def fetch_day(day: date) -> object:
        return _day_events(day.isoformat(), year)

    LIVE_WEATHER_DIAGNOSTICS.clear()
    return build_board(
        api=api,
        savant=savant,
        slate_date=slate_date,
        as_of=datetime.now(UTC),
        config=production_config(),
        fetch_day_events=fetch_day,  # type: ignore[arg-type]
        temperature_for=_temperature_lookup(),  # type: ignore[arg-type]
        park_factors=park_factor_table(),
        wind_for=_wind_lookup(),  # type: ignore[arg-type]
    )


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


def _weather_text(game: GameCard) -> tuple[str, bool]:
    """(text, is-absent) for the shortlist's weather column: the temperature
    for open-air venues, or the plain reason there is no reading (D-084)."""
    if game.venue_type is not VenueType.OPEN_AIR:
        return "roofed — indoor neutral value", False
    if game.temperature_fahrenheit is None:
        return "source unavailable", True
    return f"{float(game.temperature_fahrenheit):.0f}°F, open air", False


def _card_tags(card: BatterCard) -> str:
    """The shortlist's tags box: advisories and absences as compact tags."""
    tags: list[str] = []
    insufficient, missing = _component_flags(card)
    if insufficient:
        tags.append(f"low sample: {insufficient}")
    if missing:
        tags.append(f"missing: {missing}")
    if card.lineup_is_estimate:
        tags.append("est. lineup")
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
                    "Team": card.team,
                    "Versus": opposing.full_name if opposing else "TBD",
                    "Grade": card.result.grade.value,
                    "Park factor": (
                        f"{float(factor.factor):.0f}" if factor is not None else "not covered"
                    ),
                    "Weather": weather,
                    "Tags": _card_tags(card),
                }
                styles = {"Grade": _HIGHLIGHT}
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
# matching the live board; xwOBA at the three-decimal convention.
_FORM_PRECISION = {
    "Barrel%": 1,
    "EV": 1,
    "AtkAng": 1,
    "IdealAtkAng%": 1,
    "Pull Air %": 1,
    "Hard%": 1,
    "xwOBA": 3,
}

# D-078's wording for a metric with no observations at either window reach.
_FORM_ABSENT_TEXT = "not enough data available"


def _form_section_frames(form: FormSection) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(texts, styles) for ``styled_text_frame`` — D-068's one-row section.

    The columns are exactly D-068's seven, in its order. A metric present and
    sufficient shows its value; one resolved on the L14 fallback names the
    window ("· L14"); one below its sample floor keeps its value with its
    exact sample and an INSUFFICIENT marker on amber — present, never absent
    (D-023/D-025); one with no observations at either reach reads "not enough
    data available" (D-078). Built on the §GMF-002 grid machinery, like every
    live surface.
    """
    fields: tuple[tuple[str, FormValue], ...] = (
        ("Barrel%", form.barrel_pct),
        ("EV", form.exit_velocity),
        ("AtkAng", form.attack_angle_degrees),
        ("IdealAtkAng%", form.ideal_attack_angle_pct),
        ("Pull Air %", form.pull_air_pct),
        ("Hard%", form.hard_hit_pct),
        ("xwOBA", form.xwoba),
    )
    texts: dict[str, str] = {}
    styles: dict[str, str] = {}
    for column, metric in fields:
        if metric.value is None:
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


def _exit_velo_frames(card: BatterCard, threshold_on: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
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
    qualifying = {
        name
        for name, count in counts.items()
        if total and count / total >= float(QUALIFYING_USAGE_SHARE)
    }
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


def _pct_text(value: Decimal | None) -> str:
    return "—" if value is None else f"{float(value):.1%}"


def _pitch_line_frames(
    lines: tuple[PitchLine, ...],
    *,
    whiff_column: str,
    qualifying_only: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A per-pitch table (D-080): usage, results, and contact quality, all
    computed pipeline-side over the scope the surrounding prose names
    (§GMF-008 — the view formats, never derives).

    Rows below the qualifying usage share are dimmed; with the mix filter on
    they leave the grid. A rate absent at source reads as a dash, never a
    zero, and carries the absence style.
    """
    text_rows: list[dict[str, str]] = []
    style_rows: list[dict[str, str]] = []
    for line in lines:
        below = line.usage_share < QUALIFYING_USAGE_SHARE
        if qualifying_only and below:
            continue
        texts = {
            "Pitch": line.pitch_name or line.pitch_type,
            "Usage%": f"{float(line.usage_share):.1%}",
            "PA": str(line.plate_appearances),
            "AVG": _avg_text(line.batting_average),
            "SLG": _avg_text(line.slugging),
            "ISO": _avg_text(line.iso),
            "HR": str(line.home_runs),
            "Barrel%": _pct_text(line.barrel_share),
            "Hard-Hit%": _pct_text(line.hard_hit_share),
            "xwOBA": _avg_text(line.expected_woba),
            whiff_column: _pct_text(line.whiff_share),
        }
        styles: dict[str, str] = {}
        if below:
            styles = {column: _BELOW_MIX_CSS for column in texts}
        else:
            rates: tuple[tuple[str, Decimal | None], ...] = (
                ("AVG", line.batting_average),
                ("SLG", line.slugging),
                ("ISO", line.iso),
                ("Barrel%", line.barrel_share),
                ("Hard-Hit%", line.hard_hit_share),
                ("xwOBA", line.expected_woba),
                (whiff_column, line.whiff_share),
            )
            styles = {column: _REASON_CSS for column, value in rates if value is None}
        text_rows.append(texts)
        style_rows.append(styles)
    return pd.DataFrame(text_rows), pd.DataFrame(style_rows)


def _pitcher_mirror_frames(
    pitcher: PitcherCard, side: str | None, side_scoped: bool
) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """The pitcher mirror (D-080): his per-pitch table in the chosen usage
    scope — D-066's toggle. All three usage states survive both positions
    (§GMF-008): qualifying rows read plain, below-threshold rows dim, and a
    pitch on his season board that never reached this scope is a named-absent
    row, never a zero. The returned prose names the scope's denominator so a
    suppression can always be traced to the scope that produced it.
    """
    if side_scoped and side == "L":
        lines = pitcher.pitch_lines_vs_left
        scope = "left-handed batters"
    elif side_scoped and side == "R":
        lines = pitcher.pitch_lines_vs_right
        scope = "right-handed batters"
    else:
        lines = pitcher.pitch_lines_all
        scope = ""
    texts, styles = _pitch_line_frames(lines, whiff_column="Whiff%", qualifying_only=False)
    seen = {line.pitch_type for line in lines}
    absent_texts: list[dict[str, str]] = []
    for row in pitcher.arsenal:
        if row.pitch_type in seen:
            continue
        absent_texts.append(
            {
                "Pitch": row.pitch_name or row.pitch_type,
                "Usage%": "not in this scope",
                "PA": "0",
                "AVG": "—",
                "SLG": "—",
                "ISO": "—",
                "HR": "0",
                "Barrel%": "—",
                "Hard-Hit%": "—",
                "xwOBA": "—",
                "Whiff%": "—",
            }
        )
    if absent_texts:
        texts = pd.concat([texts, pd.DataFrame(absent_texts)], ignore_index=True)
        styles = pd.concat(
            [
                styles,
                pd.DataFrame([{column: _REASON_CSS for column in row} for row in absent_texts]),
            ],
            ignore_index=True,
        )
    total = sum(line.pitches for line in lines)
    if not scope:
        denominator = f"every pitch he threw in the recent form window ({total} pitches)"
    elif total:
        denominator = f"the {total} pitches he threw to {scope} in the recent form window"
    else:
        return (
            texts,
            styles,
            f"{pitcher.full_name} threw no pitches to {scope} in the recent form "
            "window — every pitch on his season board is named absent in this scope.",
        )
    prose = (
        f"Usage is each pitch's share of {denominator}. Dimmed rows sit below the "
        f"{float(QUALIFYING_USAGE_SHARE):.0%} qualifying share in this scope; pitches on "
        "his season board that never reached this scope are named absent, never zeroed "
        "(D-066/§GMF-008)."
    )
    return texts, styles, prose


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
    also the D-080 expanded matchup view: the batter's per-pitch table and
    the pitcher's mirror with its usage-scope toggle (D-066, §GMF-008).
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
            "'not enough data available' (D-068)."
        )

    st.markdown("**Matchup — per-pitch table**")
    if not card.pitch_lines:
        st.caption(
            "No season arsenal coverage for this batter — the per-pitch "
            "table cannot be drawn (source absence, named)."
        )
    else:
        mix_on = st.toggle(
            f"Qualifying pitch mix only (≥{float(QUALIFYING_USAGE_SHARE):.0%} usage)",
            value=False,
            key=f"matchup_mix_{card.player_id}",
            help="Off: every pitch type on his season line. On: only the "
            "qualifying mix — the pitch types at or above the usage share.",
        )
        pitch_texts, pitch_styles = _pitch_line_frames(
            card.pitch_lines, whiff_column="Swing-Str%", qualifying_only=mix_on
        )
        if pitch_texts.empty:
            st.caption("No pitch type meets the qualifying usage share on his season line.")
        else:
            st.dataframe(styled_text_frame(pitch_texts, pitch_styles), hide_index=True)
        st.caption(
            "Season arsenal figures — usage is each pitch's share of what he "
            "has faced this year; HR and Barrel% refresh from the recent form "
            "window. Rows dimmed sit below the qualifying usage share "
            "(D-066/§GMF-008)."
        )

    st.markdown("**Pitcher mirror**")
    pitcher = _opposing_pitcher(game, card) if game is not None else None
    if pitcher is None:
        st.caption(
            "No opposing starter is named for this game — the mirror appears once probables post."
        )
    else:
        side_known = card.batting_side in ("L", "R")
        side_scoped = False
        if side_known:
            side_text = "left" if card.batting_side == "L" else "right"
            side_scoped = st.toggle(
                f"Usage vs {side_text}-handed batters only",
                value=True,
                key=f"mirror_scope_{card.player_id}",
                help="On (default): usage divides by his pitches to batters of "
                "this side. Off: by every pitch he threw in the recent window.",
            )
        else:
            st.caption(
                "His batting side is unresolved for this matchup — the mirror "
                "shows the all-batters scope."
            )
        mirror_texts, mirror_styles, mirror_prose = _pitcher_mirror_frames(
            pitcher, card.batting_side, side_scoped
        )
        if mirror_texts.empty:
            st.caption(mirror_prose)
        else:
            st.dataframe(styled_text_frame(mirror_texts, mirror_styles), hide_index=True)
            st.caption(mirror_prose)

    st.markdown("**Recent exit velocity — event log**")
    threshold_on = st.toggle(
        f"Pitch-mix threshold (≥{float(QUALIFYING_USAGE_SHARE):.0%} usage)",
        value=False,
        key=f"pitch_mix_threshold_{card.player_id}",
        help="Off: every pitch type. On: only the qualifying pitch mix — the "
        "pitch types at or above the usage share across this window — so the "
        "log's rows are filtered to those pitches.",
    )
    if not card.recent_events:
        st.caption("No pitch-by-pitch events for this batter in the form window.")
        return
    sheet, sheet_styles = _exit_velo_frames(card, threshold_on)
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
        "samples, missing components, estimated lineups. Select a row to open "
        "the batter's detail."
    )
    texts, styles, cards = _slugger_frames(board)
    if texts.empty:
        st.info("No batter grades A or S on today's slate.")
        return None
    event = st.dataframe(
        styled_text_frame(texts, styles),
        hide_index=True,
        height=frame_height("Roomy", len(texts)),
        on_select="rerun",
        selection_mode="single-row",
        key=f"live_sluggers_{_selection_epoch()}",
    )
    selected_rows = event.selection.rows
    if not selected_rows:
        st.caption("Select a row to open the batter's detail.")
        return None
    return cards[selected_rows[0]]


def _render_arms(board: SlateBoard) -> None:
    st.caption(
        "Expected starters with their season line and the arsenal they actually "
        "throw (pitch types at or above the qualifying usage share)."
    )
    text_rows: list[dict[str, str]] = []
    style_rows: list[dict[str, str]] = []
    for game in board.games:
        for card, team in (
            (game.home_pitcher, game.home_team),
            (game.away_pitcher, game.away_team),
        ):
            if card is None:
                text_rows.append(
                    {
                        "Game": f"{game.away_team} at {game.home_team}",
                        "Pitcher": "TBD",
                        "Team": team,
                        "Throws": "starter not announced",
                        "ERA": "starter not announced",
                        "WHIP": "starter not announced",
                        "GS": "starter not announced",
                        "K": "starter not announced",
                        "Arsenal": "starter not announced",
                    }
                )
                style_rows.append({"GS": _REASON_CSS, "K": _REASON_CSS})
                continue
            arsenal = " · ".join(
                f"{row.pitch_type} {float(row.usage_share * 100):.0f}%"
                f" (whiff {float(row.whiff_share * 100):.0f}%)"
                for row in card.arsenal
            )
            observed = card.season is not None
            text_rows.append(
                {
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
            )
            style_rows.append({} if observed else {"GS": _REASON_CSS, "K": _REASON_CSS})
    st.dataframe(
        styled_text_frame(pd.DataFrame(text_rows), pd.DataFrame(style_rows)),
        hide_index=True,
        key="live_arms",
    )


def _render_matchups(board: SlateBoard) -> BatterCard | None:
    st.caption(
        "Per game: the venue, the expected starters, and both lineups with "
        "grades. Lineups marked estimated are the club's highest-usage bats "
        "until the posted order arrives. Select a batter row to open their "
        "recent-form detail."
    )
    selected: BatterCard | None = None
    for game in board.games:
        pitchers = " vs ".join(
            card.full_name if card else "TBD" for card in (game.away_pitcher, game.home_pitcher)
        )
        with st.expander(f"{game.away_team} at {game.home_team} — {game.venue_name} · {pitchers}"):
            for label, batters in (("Away", game.away_batters), ("Home", game.home_batters)):
                st.markdown(f"**{label} lineup**")
                text_rows: list[dict[str, str]] = []
                style_rows: list[dict[str, str]] = []
                for card in batters:
                    evaluated = isinstance(card.result, EvaluatedGradeResult)
                    text_rows.append(
                        {
                            "#": (
                                str(card.order_position) if card.order_position is not None else "—"
                            ),
                            "Batter": card.full_name,
                            "Bats": card.bats,
                            "Grade": (card.result.grade.value if evaluated else _NOT_EVALUABLE),
                            "Total": (
                                f"{float(card.result.total_score):.1f}"
                                if evaluated
                                else _NOT_EVALUABLE
                            ),
                            "Lineup": "est." if card.lineup_is_estimate else "",
                        }
                    )
                    style_rows.append({} if evaluated else {"Total": _REASON_CSS})
                event = st.dataframe(
                    styled_text_frame(pd.DataFrame(text_rows), pd.DataFrame(style_rows)),
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    key=f"matchups_{game.game_pk}_{label.lower()}_{_selection_epoch()}",
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
            "Type": game.venue_type.value,
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


def render_live_board() -> None:
    """The four live tabs (D-072). Live only in a deployed environment: a local
    render never becomes a network call, mirroring the weather seam."""
    st.subheader("Today's slate")
    if resolve_environment() == "local":
        st.caption(
            "The live board binds only in a deployed environment: locally it "
            "would be a network call, so it stays unbuilt here. Deployed, this "
            "surface pulls the day's slate, lineups, season boards, form events, "
            "park factors and forecasts from the two approved MLB hosts and the "
            "NWS adapter, then grades every batter under the v1 config (D-071)."
        )
        return
    blot = st.empty()
    blot.markdown(BLOT_HTML, unsafe_allow_html=True)
    board = live_board(date.today().isoformat())
    blot.empty()
    if isinstance(board, FetchFailure):
        st.warning(f"Today's schedule could not be fetched: {board.reason}")
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
        _batter_detail_dialog(selected, _game_of(board, selected))
    if LIVE_WEATHER_DIAGNOSTICS:
        joined = "; ".join(LIVE_WEATHER_DIAGNOSTICS)
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


def main() -> None:
    st.set_page_config(page_title="GreenMachine", layout="wide")
    bridge_secrets_into_environment()
    st.markdown(SHELL_CSS, unsafe_allow_html=True)
    st.markdown(DIAL_CSS, unsafe_allow_html=True)
    st.markdown(BLOT_CSS, unsafe_allow_html=True)
    st.markdown(FIELD_CSS, unsafe_allow_html=True)
    orb, header = st.columns([1, 5])
    with orb:
        st.markdown(ORB_HTML, unsafe_allow_html=True)
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
    render_live_board()


if __name__ == "__main__":
    main()
