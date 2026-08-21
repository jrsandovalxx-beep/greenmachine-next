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
from greenmachine.domain.enums import ComponentId, MissingReason, SampleStatus, WindowProfile
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
from greenmachine.live.mlb_api import FetchFailure, MlbStatsApi
from greenmachine.live.pipeline import BatterCard, GameCard, SlateBoard, build_board
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
from greenmachine.shell import ORB_HTML, SHELL_CSS, TITLE_HTML
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


@st.cache_data(ttl=BOARD_TTL_SECONDS, show_spinner="Building today's slate board...")
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
    )


def _top_bucket_lower(config: GreenMachineConfig, component_id: ComponentId) -> Decimal | None:
    """The lower edge of a component's top bucket — the highlight threshold.

    Read from the loaded configuration, never restated here: the config file
    is the single place thresholds live.
    """
    for component in config.components:
        if component.component_id is component_id:
            for profile in component.profiles:
                if profile.window_profile is WindowProfile.RECENT_7D:
                    block = profile.scoring[0]
                    buckets = getattr(block, "buckets", None)
                    if buckets:
                        return Decimal(str(buckets[-1].lower))
    return None


_MISSING_TEXT: dict[MissingReason, str] = {
    MissingReason.NO_EVENTS_IN_WINDOW: "no events in window",
    MissingReason.SOURCE_UNAVAILABLE: "source unavailable",
    MissingReason.TRACKING_UNAVAILABLE: "tracking unavailable",
    MissingReason.PLAYER_NOT_COVERED: "not covered by source",
    MissingReason.INVALID_SOURCE_VALUE: "invalid source value",
    MissingReason.EXPECTED_PITCHER_UNKNOWN: "starter unknown",
}

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

# Display precision per live-board metric column. Every cell on the live board
# is display text — the value formatted here, or the absence's reason in
# words — because the data grid prints a null as the literal "None" and never
# consults the styler for it (D-076).
_LIVE_METRIC_PRECISION = {
    "Total": 1,
    "EV": 1,
    "Barrel%": 1,
    "Hard-Hit%": 1,
    "Sweet%": 1,
    "Bat Speed": 1,
    "Ideal AA%": 1,
    "Pull-Air%": 1,
    "Park": 0,
}


def _reason_text(component: ComponentId, reasons: dict[ComponentId, MissingReason]) -> str:
    reason = reasons.get(component)
    return _MISSING_TEXT[reason] if reason is not None else "not observed"


def _slugger_frames(
    board: SlateBoard, edges: dict[str, Decimal | None]
) -> tuple[pd.DataFrame, pd.DataFrame, list[BatterCard]]:
    """(texts, styles, cards) — every cell is display text, cards row-aligned.

    A metric cell says the formatted value, or the plain-language reason it is
    absent (D-023/D-025); highlighting is decided here against the edge, at
    build time, where a missing cell is simply never compared. The frame is
    uniformly textual on purpose: the data grid prints a numeric null as the
    literal "None" regardless of the styler, so the text IS the data (D-076).
    The third return is the card behind each row, in row order, so a grid
    selection resolves to a batter without a second ordering to drift (GMF-007).
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
                factor = _side_factor(game, card.batting_side)
                insufficient, missing = _component_flags(card)
                reasons = {
                    obs.component_id: obs.missing_reason for obs in card.result.missing_observations
                }
                statcast = card.statcast
                form = card.form
                evaluated = isinstance(card.result, EvaluatedGradeResult)
                values: dict[str, tuple[Decimal | None, ComponentId | None]] = {
                    "Total": (card.result.total_score if evaluated else None, None),
                    "EV": (
                        statcast.exit_velocity_avg if statcast else None,
                        ComponentId.EXIT_VELOCITY,
                    ),
                    "Barrel%": (
                        statcast.barrel_share * 100 if statcast else None,
                        ComponentId.BARREL_PCT,
                    ),
                    "Hard-Hit%": (
                        statcast.hard_hit_share * 100 if statcast else None,
                        ComponentId.HARD_HIT_PCT,
                    ),
                    "Sweet%": (
                        form.sweet_spot_pct.value if form else None,
                        ComponentId.SWEET_SPOT_PCT,
                    ),
                    "Bat Speed": (
                        form.bat_speed_mph.value if form else None,
                        ComponentId.BAT_SPEED,
                    ),
                    "Ideal AA%": (
                        form.ideal_attack_angle_pct.value if form else None,
                        ComponentId.ATTACK_ANGLE_QUALITY,
                    ),
                    "Pull-Air%": (
                        form.pull_air_pct.value if form else None,
                        ComponentId.PULL_PCT_AIR_BALLS,
                    ),
                    "Park": (
                        factor.factor if factor is not None else None,
                        ComponentId.PARK,
                    ),
                }
                texts: dict[str, str] = {
                    "Batter": card.full_name,
                    "Team": card.team,
                    "Vs": opposing.full_name if opposing else "TBD",
                    "Grade": card.result.grade.value if evaluated else _NOT_EVALUABLE,
                }
                styles: dict[str, str] = {}
                for column, (value, component) in values.items():
                    if value is None:
                        texts[column] = (
                            _NOT_EVALUABLE
                            if component is None
                            else _reason_text(component, reasons)
                        )
                        styles[column] = _REASON_CSS
                        continue
                    numeric = float(value)
                    texts[column] = f"{numeric:.{_LIVE_METRIC_PRECISION[column]}f}"
                    edge = edges.get(column)
                    if edge is not None and numeric >= float(edge):
                        styles[column] = _HIGHLIGHT
                texts["Low sample"] = insufficient
                texts["Missing"] = missing
                texts["Lineup"] = "est." if card.lineup_is_estimate else ""
                text_rows.append(texts)
                style_rows.append(styles)
                cards.append(card)
    return pd.DataFrame(text_rows), pd.DataFrame(style_rows), cards


def _component_flags(card: BatterCard) -> tuple[str, str]:
    """(insufficient-sample tags, missing-with-reason tags) for one card."""
    insufficient = [
        obs.component_id.value
        for obs in card.result.present_observations
        if obs.sample_status is SampleStatus.INSUFFICIENT
    ]
    missing = [
        f"{obs.component_id.value} ({obs.missing_reason.value})"
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


def _render_batter_detail(card: BatterCard) -> None:
    """The batter detail body — GMF-007's portion is the D-068 form section.

    Reachable from the Sluggers and Matchups row selections (D-078); the
    redesign's further blocks (matchup window, per-pitch tables) join this
    view under their own tickets.
    """
    st.markdown(f"**{card.full_name}** — {card.team}")
    st.markdown("**Recent form [L7]**")
    if card.form is None:
        st.caption(
            "Recent form is not covered by source: the form-event feed was not "
            "retrieved for this board, so no window could be resolved."
        )
        return
    texts, styles = _form_section_frames(card.form)
    st.dataframe(styled_text_frame(texts, styles), hide_index=True)
    st.caption(
        "Each metric is the last 7 days [L7]; a metric whose L7 window is "
        "empty falls back to its L14 window, marked '· L14'. A metric below "
        "its sample floor keeps its value with its exact sample and an "
        "INSUFFICIENT marker; one with no observations at either reach reads "
        "'not enough data available' (D-068)."
    )


@st.dialog("Batter detail", width="large", on_dismiss=_bump_selection_epoch)
def _batter_detail_dialog(card: BatterCard) -> None:
    _render_batter_detail(card)


def _render_sluggers(board: SlateBoard, config: GreenMachineConfig) -> BatterCard | None:
    st.caption(
        "Every lineup batter on the slate, graded under the provisional v1 model "
        "(D-071). Green cells are at or above the component's top bucket edge, "
        "read live from the config. 'Low sample' lists components below their "
        "floor — still scored, carrying the advisory. 'Missing' names absences "
        "with their reasons. Estimated lineups are marked 'est.' until orders post."
    )
    edges = {
        "EV": _top_bucket_lower(config, ComponentId.EXIT_VELOCITY),
        "Barrel%": _top_bucket_lower(config, ComponentId.BARREL_PCT),
        "Hard-Hit%": _top_bucket_lower(config, ComponentId.HARD_HIT_PCT),
        "Sweet%": _top_bucket_lower(config, ComponentId.SWEET_SPOT_PCT),
        "Bat Speed": _top_bucket_lower(config, ComponentId.BAT_SPEED),
        "Ideal AA%": _top_bucket_lower(config, ComponentId.ATTACK_ANGLE_QUALITY),
        "Pull-Air%": _top_bucket_lower(config, ComponentId.PULL_PCT_AIR_BALLS),
        "Park": _top_bucket_lower(config, ComponentId.PARK),
    }
    texts, styles, cards = _slugger_frames(board, edges)
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
        st.caption("Select a row to open the batter's recent-form detail.")
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
    board = live_board(date.today().isoformat())
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
        _batter_detail_dialog(selected)
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
