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
import importlib
import os
import subprocess
import sys
import tempfile
import threading
import traceback
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from functools import lru_cache
from importlib import metadata
from pathlib import Path
from typing import Any, NamedTuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# D-155: __main__ is the one file the host can never serve stale —
# Streamlit re-executes it on every run and never caches its bytecode,
# which is why app-file edits always deployed while package edits went
# stale. The bytecode-root redirect must live HERE: D-154 kept it inside
# deploy_bootstrap, and the host's root __pycache__ served the bootstrap
# itself from D-153 bytecode (a module cannot protect its own cache),
# taking every guard below down with it.
# D-156 makes the redirect UNCONDITIONAL: the host precompiles bytecode
# under PYTHONPYCACHEPREFIX, so a guard that fires only on None skips
# exactly when it matters. Only a prefix this process created is trusted.
if sys.pycache_prefix is None or "gm_pycache_" not in sys.pycache_prefix:
    sys.pycache_prefix = tempfile.mkdtemp(prefix="gm_pycache_")


# D-157: the host can import our modules BEFORE this file's first line
# runs — D-156's forensics caught deploy_bootstrap loaded from bytecode
# whose cache path was computed while the prefix was still None, i.e.
# before the redirect above existed. No line here can run earlier than
# that pre-import, so the guard works the other direction: record what
# was pre-loaded, and evict any of it that is stale (the wrong
# DEPLOY_EPOCH marker) so the imports below re-execute from source
# under our cache root.
#
# D-158/D-159: the eviction runs AT MOST ONCE PER DEPLOY EPOCH, under a
# process-wide lock — and the epoch key matters because the host's
# process OUTLIVES deploys: D-159's forensics caught one process serving
# two commits (the same mkdtemp prefix across pushes — file-watcher
# reruns instead of reboots), and D-158's process-wide flag disabled the
# eviction exactly when the new deploy needed it. Within one epoch a
# re-check never fires — D-158's bug was a rerun evicting a
# half-initialized package mid-import, leaving two savant module objects
# (the PicklingError). Only FULLY initialized roots are judged: a
# half-initialized module is an import in flight under our redirect,
# joined through the per-module import locks, never evicted. __main__'s
# globals are rebuilt on every rerun, so the epoch flag and its lock
# live on sys — the one object every rerun and session thread shares.
def _deploy_epoch() -> str:
    """The deploy epoch is the checkout's own commit sha (D-162): every
    deploy moves it by construction, so the once-per-epoch eviction no
    longer depends on anyone remembering to bump a literal — the
    D-160/D-161 deploy kept 159, the stale module set survived the
    rerun, and the PicklingError returned within the hour. Git first,
    then GM_COMMIT, else "unknown" — a blind read can only match an
    equally blind marker, so a total miss simply never evicts."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parent,
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
    return env_value or "unknown"


_EXPECTED_DEPLOY_EPOCH = _deploy_epoch()
_PRELOADED_OURS = tuple(
    name
    for name in sys.modules
    if name == "deploy_bootstrap" or name == "greenmachine" or name.startswith("greenmachine.")
)
if getattr(sys, "_gm_eviction_epoch", None) != _EXPECTED_DEPLOY_EPOCH:
    _eviction_lock = getattr(sys, "_gm_eviction_lock", None)
    if _eviction_lock is None:
        _eviction_lock = threading.Lock()
        sys._gm_eviction_lock = _eviction_lock  # type: ignore[attr-defined]
    with _eviction_lock:
        if getattr(sys, "_gm_eviction_epoch", None) != _EXPECTED_DEPLOY_EPOCH:
            sys._gm_eviction_epoch = _EXPECTED_DEPLOY_EPOCH  # type: ignore[attr-defined]
            # The marker check reads the two ROOTS only (importing any
            # submodule imports its parents first, so a stale pre-load
            # always shows at the root).
            if any(
                getattr(getattr(sys.modules[root], "__spec__", None), "_initialized", True)
                and getattr(sys.modules[root], "DEPLOY_EPOCH", None) != _EXPECTED_DEPLOY_EPOCH
                for root in ("deploy_bootstrap", "greenmachine")
                if root in sys.modules
            ):
                importlib.invalidate_caches()
                for _preloaded in _PRELOADED_OURS:
                    # Never pop a module mid-import: importlib re-registers
                    # it on completion (the pop would break that import
                    # outright). An in-flight import here already read its
                    # source under our redirect, so it finishes fresh.
                    _module = sys.modules.get(_preloaded)
                    if getattr(getattr(_module, "__spec__", None), "_initialized", True):
                        sys.modules.pop(_preloaded, None)
                # Every cached object built from the evicted modules is
                # now a foreign-class object — the cache_resource Savant
                # client's methods keep the old module globals, which is
                # the PicklingError's other half. main() clears both
                # caches once, right after the fresh imports below.
                sys._gm_cache_clear_pending = True  # type: ignore[attr-defined]

# D-153/D-155: the deploy bootstrap sweeps stale bytecode from the
# checkout's src tree before any greenmachine import can load it — it
# must stay ahead of every greenmachine import below (isort keeps it
# here: the import block's earliest plain module). The redirect above
# guarantees this import itself loads fresh from source.
import deploy_bootstrap as _deploy_bootstrap
import pandas as pd
import streamlit as st

from greenmachine.common.clock import SystemClock
from greenmachine.config.loader import load_config
from greenmachine.config.schema import GreenMachineConfig
from greenmachine.domain.enums import Category, Grade, SampleStatus
from greenmachine.domain.grade_result import EvaluatedGradeResult, GradeResult
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
from greenmachine.inputs.park_reference import PARK_VENUES
from greenmachine.inputs.savant_park_factors import basis_statement, read_factors
from greenmachine.inputs.wind_receptiveness import WindReceptiveness, read_receptiveness
from greenmachine.live.backtest import (
    BacktestRow,
    outcomes_for_day,
    roi_per_unit,
    slate_as_of,
    tally_grades,
)
from greenmachine.live.form import BARREL_CLASSIFICATION, FormSection, FormValue, is_pull_air
from greenmachine.live.grading import QUALIFYING_USAGE_SHARE, ROOFED_VENUE_NEUTRAL_FAHRENHEIT
from greenmachine.live.mlb_api import FetchFailure, GameLogEntry, MlbStatsApi
from greenmachine.live.pipeline import (
    MATCHUP_WINDOW_DAYS,
    SEASON_IDS_PER_REQUEST,
    BatterCard,
    BatterGridLine,
    GameCard,
    PitcherCard,
    PitcherRecentLine,
    PitcherSeasonReads,
    PitchLine,
    SlateBoard,
    StarterWorkload,
    build_board,
    season_breakup_lines,
)
from greenmachine.live.savant import BaseballSavant, PitchEvent
from greenmachine.live.transport import UrllibTransport as MlbTransport
from greenmachine.live.wind import resolved_wind_mph, spray_field_bearing, wind_field_words
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


_SLATE_ZONE = "America/Phoenix"


def slate_today() -> date:
    """The viewer's "today", not the server's (D-112).

    The cloud host runs on UTC, so a bare ``date.today()`` rolls the slate
    to tomorrow in the early evening for every US viewer. The slate's day
    is read in the PO's home zone — Arizona, UTC-7 year-round (no daylight
    saving), one switch away from any other US zone. If the host lacks the
    tz database, the fixed -7 offset is exactly Arizona's rule.
    """
    try:
        return datetime.now(ZoneInfo(_SLATE_ZONE)).date()
    except ZoneInfoNotFoundError:
        return datetime.now(timezone(timedelta(hours=-7))).date()


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


# ---------------------------------------------------------------------------
# D-136 (PO): the morning refresh. The season sources update overnight, so
# the board trusts one morning's answer for the whole day — "refresh every
# morning whenever savant and the rest update their numbers from day
# before." Per D-139 the anchor flips at 09:00 UTC — 5:00 AM Eastern
# through the baseball season (EDT; 4 AM in winter) — the earliest hour
# that still clears the West Coast finishes and the sources' overnight
# publishes; earlier risks caching day-old numbers for the whole day. A
# future date clicked mid-day still loads on request, exactly as before:
# the anchor governs the season sources, never the slate itself.

SEASON_DATA_REFRESH_HOUR_UTC = 9

# Anchored entries live past midnight so the anchor — not the wall clock —
# decides when a season answer goes stale; a finalized day's event file
# gets the same long read because it never changes once the morning update
# has landed.
SEASON_DATA_TTL_SECONDS = 26 * 3600
FINAL_DAY_EVENTS_TTL_SECONDS = 26 * 3600


def _season_data_anchor(now: datetime) -> str:
    """The ISO date the season sources were last trusted (D-136): today
    once the morning update has landed, yesterday before it."""
    day = (
        now.date() if now.hour >= SEASON_DATA_REFRESH_HOUR_UTC else (now - timedelta(days=1)).date()
    )
    return day.isoformat()


class _SeasonFetchError(Exception):
    """A season-source failure carried OUT of the cache: st.cache_data never
    caches a raised call, so a morning transient refetches on the next
    build instead of poisoning the whole anchored day (D-136)."""

    def __init__(self, failure: FetchFailure) -> None:
        super().__init__(failure.reason)
        self.failure = failure


def _season_source_call(kind: str, params: tuple[object, ...]) -> object:
    """The one place the anchored kinds reach the real clients."""
    api, savant = live_mlb_adapters()
    if kind == "statcast_batters":
        return savant.fetch_statcast_batters(year=int(params[0]), minimum=int(params[1]))
    if kind == "batted_ball":
        return savant.fetch_batted_ball(year=int(params[0]), minimum=int(params[1]))
    if kind == "expected_stats":
        return savant.fetch_expected_stats(year=int(params[0]))
    if kind == "sprint_speed":
        return savant.fetch_sprint_speed(year=int(params[0]))
    if kind == "squared_up":
        return savant.fetch_squared_up(year=int(params[0]), minimum=int(params[1]))
    if kind == "pitcher_expected_stats":
        return savant.fetch_pitcher_expected_stats(year=int(params[0]))
    if kind == "statcast_pitchers":
        return savant.fetch_statcast_pitchers(year=int(params[0]))
    if kind == "pitch_arsenal":
        return savant.fetch_pitch_arsenal(
            kind=params[0],  # type: ignore[arg-type]  # the two call sites pass the literals
            year=int(params[1]),
        )
    if kind == "bat_tracking":
        return savant.fetch_bat_tracking(
            year=int(params[0]),
            minimum=int(params[1]),
            start=str(params[2]),
            end=str(params[3]),
        )
    if kind == "season_hitting":
        return api.fetch_season_hitting(tuple(int(p) for p in params))
    if kind == "season_pitching":
        return api.fetch_season_pitching(tuple(int(p) for p in params))
    raise ValueError(f"unknown season source kind: {kind}")


@st.cache_data(ttl=SEASON_DATA_TTL_SECONDS, show_spinner=False)
def _season_fetch(kind: str, anchor: str, params: tuple[object, ...]) -> object:
    """One day-anchored season-source fetch (D-136): the anchor date is
    part of the cache key, so the morning flip — and only the flip —
    refetches. Failures raise out of the cache; the proxies translate
    them back to the FetchFailure values the pipeline already handles."""
    result = _season_source_call(kind, params)
    if isinstance(result, FetchFailure):
        raise _SeasonFetchError(result)
    return result


class _DayAnchoredSavant:
    """The Savant client with its season-bulk boards day-anchored (D-136).

    Only the fetches ``build_board`` makes against the overnight-updated
    season sources are wrapped — one fetch per anchor day serves every
    board build until the morning flip. Everything else (the per-day
    event feed, the per-player dialog fetch) delegates untouched.
    """

    def __init__(self, inner: BaseballSavant, anchor: str) -> None:
        self._inner = inner
        self._anchor = anchor

    def __getattr__(self, name: str) -> object:
        return getattr(self._inner, name)

    def _season(self, kind: str, params: tuple[object, ...]) -> object:
        try:
            return _season_fetch(kind, self._anchor, params)
        except _SeasonFetchError as exc:
            return exc.failure

    def fetch_statcast_batters(self, *, year: int, minimum: int = 0) -> object:
        return self._season("statcast_batters", (year, minimum))

    def fetch_batted_ball(self, *, year: int, minimum: int = 0) -> object:
        return self._season("batted_ball", (year, minimum))

    def fetch_expected_stats(self, *, year: int) -> object:
        return self._season("expected_stats", (year,))

    def fetch_sprint_speed(self, *, year: int) -> object:
        return self._season("sprint_speed", (year,))

    def fetch_squared_up(self, *, year: int, minimum: int = 0) -> object:
        return self._season("squared_up", (year, minimum))

    def fetch_pitcher_expected_stats(self, *, year: int) -> object:
        return self._season("pitcher_expected_stats", (year,))

    def fetch_statcast_pitchers(self, *, year: int) -> object:
        return self._season("statcast_pitchers", (year,))

    def fetch_pitch_arsenal(self, *, kind: str, year: int) -> object:
        return self._season("pitch_arsenal", (kind, year))

    def fetch_bat_tracking(
        self, *, year: int, minimum: int = 0, start: str = "", end: str = ""
    ) -> object:
        return self._season("bat_tracking", (year, minimum, start, end))


class _DayAnchoredMlbApi:
    """The MLB client with its two season fetches day-anchored (D-136).

    The slate, batting orders, and recent logs delegate LIVE — the morning
    refresh is about the season sources, and the game logs must stay
    intraday-fresh for the D-130 slate-day money tag.
    """

    def __init__(self, inner: MlbStatsApi, anchor: str) -> None:
        self._inner = inner
        self._anchor = anchor

    def __getattr__(self, name: str) -> object:
        return getattr(self._inner, name)

    def _season(self, kind: str, params: tuple[object, ...]) -> object:
        try:
            return _season_fetch(kind, self._anchor, params)
        except _SeasonFetchError as exc:
            return exc.failure

    def fetch_season_hitting(self, player_ids: tuple[int, ...]) -> object:
        return self._season("season_hitting", tuple(player_ids))

    def fetch_season_pitching(self, player_ids: tuple[int, ...]) -> object:
        return self._season("season_pitching", tuple(player_ids))


@st.cache_data(ttl=FINAL_DAY_EVENTS_TTL_SECONDS, show_spinner=False)
def _final_day_events(day_iso: str, year: int) -> object:
    """A finalized day's pitches (D-136): once the morning update has
    landed, that day never changes again."""
    _, savant = live_mlb_adapters()
    return savant.fetch_pitch_events(year=year, day=day_iso)


@st.cache_data(ttl=DAY_EVENTS_TTL_SECONDS, show_spinner=False)
def _recent_day_events(day_iso: str, year: int) -> object:
    """A still-resolving day's pitches (D-136): today and yesterday until
    the morning update lands — the hourly read, as before."""
    _, savant = live_mlb_adapters()
    return savant.fetch_pitch_events(year=year, day=day_iso)


def _day_events(day_iso: str, year: int, anchor: str) -> object:
    """Route by finality (D-136): days before the anchor are final and
    cache long; the anchor day and later still resolve and keep the
    hourly read."""
    if day_iso < anchor:
        return _final_day_events(day_iso, year)
    return _recent_day_events(day_iso, year)


@st.cache_data(ttl=DAY_EVENTS_TTL_SECONDS, show_spinner=False)
def _season_pitch_events(
    player_id: int, role: str, slate_iso: str
) -> tuple[PitchEvent, ...] | FetchFailure:
    """One player's regular-season pitch record through the slate day
    (D-129): the batter detail dialog's lazy per-side season split and,
    with ``role="pitcher"``, the starter cards' season-scope side rows
    (D-143) — one Savant query per player, cached per slate day and shared
    by both reads. The FetchFailure reaches the caller so the breakup names
    its absence and the board build names its diagnostic instead of
    inventing a split."""
    _, savant = live_mlb_adapters()
    year = int(slate_iso[:4])
    result = savant.fetch_player_pitch_events(
        year=year,
        role=role,  # type: ignore[arg-type]  # the two call sites pass the literals
        player_id=player_id,
        start=f"{year}-03-01",
        end=slate_iso,
    )
    return result


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

    def read(venue: ParkVenue, at: datetime) -> object | None:
        if not live or len(diagnostics) >= WEATHER_FAILURE_CIRCUIT_BREAKER:
            return None
        try:
            # D-131: ask for the forecast covering first pitch, not the hour
            # the board happened to be built in.
            field = adapter.forecast_for(venue, at)
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
def live_board(slate_iso: str, batter_window_days: int) -> SlateBoard | FetchFailure:
    """Assemble and grade the slate; cached so a rerun is not a refetch.
    D-128 (PO): the cache key is the slate AND the Matchups tab's batter
    window — a new window is a fresh build, exactly like a new date.
    D-136 (PO): the build reads the season sources through the day-anchored
    proxies, so a rebuild every fifteen minutes costs the slate, the
    orders, the logs, the recent event days and the weather — the season
    boards come off the morning's anchor."""
    api, savant = live_mlb_adapters()
    slate_date = date.fromisoformat(slate_iso)
    year = slate_date.year
    anchor = _season_data_anchor(datetime.now(UTC))

    def fetch_day(day: date) -> object:
        return _day_events(day.isoformat(), year, anchor)

    def fetch_pitcher_season_events(pid: int) -> object:
        # D-143 (PO): one probable's full-season pitch record — the starter
        # cards' season-scope side rows. Cached per slate day and shared
        # with the dialog's breakup read.
        return _season_pitch_events(pid, "pitcher", slate_iso)

    weather_diagnostics: list[str] = []
    board = build_board(
        api=_DayAnchoredMlbApi(api, anchor),  # type: ignore[arg-type]
        savant=_DayAnchoredSavant(savant, anchor),  # type: ignore[arg-type]
        slate_date=slate_date,
        as_of=datetime.now(UTC),
        config=production_config(),
        batter_window_days=batter_window_days,
        fetch_day_events=fetch_day,  # type: ignore[arg-type]
        temperature_for=_temperature_lookup(weather_diagnostics),  # type: ignore[arg-type]
        park_factors=park_factor_table(),
        wind_for=_wind_lookup(weather_diagnostics),  # type: ignore[arg-type]
        humidity_for=_humidity_lookup(weather_diagnostics),  # type: ignore[arg-type]
        fetch_pitcher_season_events=fetch_pitcher_season_events,  # type: ignore[arg-type]
    )
    LIVE_WEATHER_DIAGNOSTICS[slate_iso] = weather_diagnostics
    return board


# D-128 (PO): the Matchups tab's timeframe selector — the year choice
# returns the grid to the season sources; the recent window counts back
# in weeks (to 12) or months (to 3). The widget keys live in session
# state and the board build resolves the window BEFORE any widget
# renders, so a first run builds the default thirty-day record and a
# changed selector rebuilds on the rerun — no selectboxes anywhere.
_MATCHUPS_SEASON_LABEL = "2026 season"
_MATCHUPS_RECENT_LABEL = "Recent window"


def _matchups_window_days() -> int:
    """The batter window behind the board build (D-128): the default
    thirty days when the selector shows the season view (the grade's
    ratified L30 basis) or before the widget first renders; the
    selector's own count otherwise — weeks times seven, months capped at
    three (times thirty)."""
    if st.session_state.get("matchups_view_mode") != _MATCHUPS_RECENT_LABEL:
        return MATCHUP_WINDOW_DAYS
    count = int(st.session_state.get("matchups_window_count", 4))
    if st.session_state.get("matchups_window_unit") == "months":
        return min(count, 3) * 30
    return count * 7


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

# Opaque red for the shortlist's veto-side tags (v2.2, D-114): reads that
# argue against the home run — the ground-ball profile, the suppressor, the
# binary/high-K cautions. Green says good for the HR, red says bad for it.
_VETO_CSS = "background-color: #a41616; color: #ffe9e9"

# ---------------------------------------------------------------------
# D-127 (PO): researched cell-grading bands on every metric table
# ---------------------------------------------------------------------

# Six opaque band fills — three green, three red. The extremes ARE the
# console's existing highlight/veto pair, so a researched "elite" cell and
# a ratified green read speak one color language; the unfilled theme cell
# is the neutral middle. Opaque like the pair — the data grid composites
# alpha backgrounds over white, which read as washed-out blocks.
_BAND_G3_CSS = _HIGHLIGHT  # elite — dark green (PO: dark green = elite)
_BAND_G2_CSS = "background-color: #35590f; color: #e2f5c8"  # strong
_BAND_G1_CSS = "background-color: #2a4418; color: #cfe4b8"  # above average
_BAND_R1_CSS = "background-color: #4d2620; color: #e8c8c0"  # below average
_BAND_R2_CSS = "background-color: #77201c; color: #ffd9d4"  # poor
_BAND_R3_CSS = _VETO_CSS  # very poor — dark red (PO: dark red = very poor)


class _BandSpec(NamedTuple):
    """One metric's six researched bucket edges in its raw units.

    ``direction == "high"``: bigger is better for the home run — a value at
    or above g3/g2/g1 lands the elite/strong/above-average green, a value
    under r1/r2/r3 the below-average/poor/very-poor red, and anything
    between r1 and g1 stays neutral. ``"low"`` mirrors it (whiff, GB%).
    ``kind`` drives the caption formatting: "pct" prints the fraction
    edges as percents, "avg" as three-digit rates, "num" plain.

    The edges are researched baselines — 2025 league figures, with the
    ratified v2.2 line as the edge where one exists — NOT firing lines.
    Every edge prints on its surface (D-079) and the per-metric
    derivations live in DECISIONS D-127.
    """

    direction: str
    g3: float
    g2: float
    g1: float
    r1: float
    r2: float
    r3: float
    kind: str = "num"


def _band_css(spec: _BandSpec, value: float) -> str | None:
    """The band fill for one value — None in the neutral middle."""
    if spec.direction == "high":
        if value >= spec.g3:
            return _BAND_G3_CSS
        if value >= spec.g2:
            return _BAND_G2_CSS
        if value >= spec.g1:
            return _BAND_G1_CSS
        if value < spec.r3:
            return _BAND_R3_CSS
        if value < spec.r2:
            return _BAND_R2_CSS
        if value < spec.r1:
            return _BAND_R1_CSS
        return None
    if value <= spec.g3:
        return _BAND_G3_CSS
    if value <= spec.g2:
        return _BAND_G2_CSS
    if value <= spec.g1:
        return _BAND_G1_CSS
    if value > spec.r3:
        return _BAND_R3_CSS
    if value > spec.r2:
        return _BAND_R2_CSS
    if value > spec.r1:
        return _BAND_R1_CSS
    return None


# The batter-grid scale (Matchups, both views). Derivations (2025 league
# research, DECISIONS D-127): league average EV 88.8 mph, the v2.2
# power-profile line at 91 as the elite edge; barrels ≈ 5.8% of plate
# appearances league-wide (8.6% of batted balls over ~0.75 BBE per PA);
# hard-hit ≈ 40% league; AVG .245 / SLG .404 / ISO .158 / wOBA .313 with
# xwOBA tracking it; pull-air ≈ 31% of measurable air balls (17.8% of
# batted balls pulled in the air over a 57.6% air share) with the elite
# edge past the ratified 40% spray line. D-145 (PO): K % replaced
# Swing-Str % — strikeouts per plate appearance, league ≈ 22.2% (2025),
# anchored to the ratified v2.2 K reads: the 22% unlock anchor is the
# above-average edge, the 28% binary read the poor edge, the 30% high-K
# caution the very-poor edge. Oppo Air % carries
# no quality scale — a fit read against the park, not a grade — and the
# counting columns are volume, not quality: both stay neutral, and the
# caption says so.
_GRID_BANDS: dict[str, _BandSpec] = {
    "EV": _BandSpec("high", 91, 90, 89, 88, 87, 85.5),
    "LA": _BandSpec("high", 17, 14.5, 12.5, 10.5, 8.5, 6),
    "Barrel/PA %": _BandSpec("high", 0.09, 0.07, 0.058, 0.045, 0.032, 0.02, "pct"),
    "Hard-Hit %": _BandSpec("high", 0.52, 0.46, 0.42, 0.36, 0.32, 0.28, "pct"),
    "AVG": _BandSpec("high", 0.285, 0.265, 0.252, 0.235, 0.220, 0.205, "avg"),
    "SLG": _BandSpec("high", 0.500, 0.450, 0.420, 0.380, 0.350, 0.310, "avg"),
    "ISO": _BandSpec("high", 0.240, 0.200, 0.170, 0.140, 0.115, 0.090, "avg"),
    "Pull Air %": _BandSpec("high", 0.43, 0.38, 0.33, 0.27, 0.22, 0.17, "pct"),
    "xwOBA": _BandSpec("high", 0.370, 0.345, 0.325, 0.300, 0.280, 0.260, "avg"),
    "K %": _BandSpec("low", 0.15, 0.185, 0.22, 0.26, 0.28, 0.30, "pct"),
}

# The pitcher scale (the Arms tab and the starter header cards) — read as
# vulnerability: the greener the cell, the more forgiving the arm. League
# 2025: HR/9 ≈ 1.16 between the ratified gas (≥ 1.50, the elite edge) and
# suppressor (≤ 0.80, inside the poor band) lines; barrels 8.6% of batted
# balls; hard-hit ≈ 40% of batted balls (the same contact-quality league
# mean as the batter scale, mirrored around it: a full band above 40% is
# elite forgiving, the observed team spread bottoms out near 38% so the
# red edges sit just under it); average LA allowed ≈ 12° between the
# ratified fly-vulnerable (≥ 18°, the elite edge) and ground-ball (≤ 8°)
# lines; ISO .158; the air share (fly balls plus line drives) 50.5%; the
# ground-ball share 42.4% between the ratified < 40% gas ceiling and the
# ≥ 50% profile line (extreme ≥ 55%, the very-poor edge). D-128 (PO):
# wOBA and ISO left the pitcher tables — xwOBA and xISO stay — so their
# specs left the registry with them, and Hard-Hit % joined.
_PITCHER_BANDS: dict[str, _BandSpec] = {
    "xwOBA": _BandSpec("high", 0.350, 0.330, 0.320, 0.300, 0.285, 0.270, "avg"),
    "HR/9": _BandSpec("high", 1.50, 1.30, 1.15, 1.00, 0.90, 0.70),
    "BRL%": _BandSpec("high", 0.110, 0.095, 0.080, 0.070, 0.055, 0.040, "pct"),
    "Hard-Hit %": _BandSpec("high", 0.46, 0.43, 0.40, 0.37, 0.34, 0.30, "pct"),
    "LA": _BandSpec("high", 18, 15, 13, 11, 9, 6),
    "xISO": _BandSpec("high", 0.190, 0.170, 0.155, 0.140, 0.120, 0.100, "avg"),
    "Air %": _BandSpec("high", 0.56, 0.52, 0.48, 0.44, 0.40, 0.35, "pct"),
    "GB %": _BandSpec("low", 0.35, 0.39, 0.42, 0.46, 0.50, 0.55, "pct"),
}

# The Conditions scale: the hand-split HR factor between the ratified park
# lines (boost ≥ 110, strong ≥ 115 — the strong and elite edges; wrong-side
# ≤ 90, strong ≤ 85 — the poor and very-poor edges).
_FACTOR_BAND = _BandSpec("high", 115, 110, 104, 96, 90, 85)

# The six ratified temperature awards worn as the six bands — the one
# v2.2-ratified color scale on the board (D-121's bands, D-127's colors).
_TEMP_AWARD_CSS = {
    "0": _BAND_R3_CSS,
    "0.25": _BAND_R2_CSS,
    "0.5": _BAND_R1_CSS,
    "1": _BAND_G1_CSS,
    "1.25": _BAND_G2_CSS,
    "1.5": _BAND_G3_CSS,
}


def _band_scale_text(spec: _BandSpec) -> str:
    """One metric's six edges as caption/hover text (D-079): 'elite ≥ 91 ·
    strong ≥ 90 · above avg ≥ 89 · below avg < 88 · poor < 87 · very poor
    < 85.5' — the inequality flips for a lower-is-better metric."""

    def edge(value: float) -> str:
        if spec.kind == "pct":
            return f"{value * 100:g}%"
        if spec.kind == "avg":
            text = f"{value:.3f}"
            return text[1:] if text.startswith("0") else text
        return f"{value:g}"

    green, red = ("≤", ">") if spec.direction == "low" else ("≥", "<")
    return (
        f"elite {green} {edge(spec.g3)} · strong {green} {edge(spec.g2)} · "
        f"above avg {green} {edge(spec.g1)} · below avg {red} {edge(spec.r1)} · "
        f"poor {red} {edge(spec.r2)} · very poor {red} {edge(spec.r3)}"
    )


def _apply_bands(
    styles: dict[str, str],
    bands: dict[str, _BandSpec],
    values: dict[str, Decimal | None],
) -> None:
    """Fill the still-unstyled valued cells with their researched band
    (D-127). Every existing style wins — a named absence, the amber
    INSUFFICIENT advisory and the ratified green all outrank a bucket."""
    for column, raw in values.items():
        if raw is None or column in styles:
            continue
        css = _band_css(bands[column], float(raw))
        if css is not None:
            styles[column] = css


# Neon-green money tag (D-130, PO): a "$" beside a shortlist batter who
# homered on the slate day being viewed — a pre-game board tags nobody.
# Text shadow gives the neon glow; no background, so the cell keeps its
# theme fill.


class _FieldWind(NamedTuple):
    """The D-129 field-frame extras for ``field_wind_html``: the wind in
    field words plus the axis/bearing pair that rotates the flow to the
    drawn field — all three None when any reading is missing, so the panel
    keeps its compass frame."""

    words: str | None
    from_degrees: float | None
    axis_degrees: float | None


def _field_wind(game: GameCard) -> _FieldWind:
    """Resolve the field-frame wind for one game: open air, a measured
    park axis and a parsed from-bearing all present, or nothing."""
    if (
        game.venue_type is VenueType.OPEN_AIR
        and game.wind_from_degrees is not None
        and game.park_orientation_degrees is not None
    ):
        return _FieldWind(
            words=wind_field_words(game.wind_from_degrees, game.park_orientation_degrees),
            from_degrees=float(game.wind_from_degrees),
            axis_degrees=float(game.park_orientation_degrees),
        )
    return _FieldWind(None, None, None)


def _conditions_text(game: GameCard) -> tuple[str, bool]:
    """(text, is-absent) for the shortlist's weather column (D-126, PO): the
    start-time temperature plus the wind in plain field words — "84°F ·
    12 mph out to right" — resolved on the measured park axis. Without the
    axis the compass reading stands in; a roofed venue keeps the indoor
    neutral value; nothing sourced, the plain reason, never an invention."""
    if game.venue_type is not VenueType.OPEN_AIR:
        return "roofed — indoor neutral value", False
    parts: list[str] = []
    if game.temperature_fahrenheit is not None:
        parts.append(f"{float(game.temperature_fahrenheit):.0f}°F")
    speed = game.wind_speed_mph
    if speed is not None:
        if speed <= 0:
            parts.append("calm")
        elif game.wind_from_degrees is not None and game.park_orientation_degrees is not None:
            words = wind_field_words(game.wind_from_degrees, game.park_orientation_degrees)
            parts.append(f"{float(speed):.0f} mph {words}")
        elif game.wind_direction:
            parts.append(f"{float(speed):.0f} mph {game.wind_direction.upper()}")
        else:
            parts.append(f"{float(speed):.0f} mph")
    if not parts:
        return "source unavailable", True
    return " · ".join(parts), False


# D-109 / v2.2 (D-114): the shortlist tags' firing lines, printed in the tab
# caption (the D-079 pattern — a surface prints every emphasis line it
# uses). v2.2 re-lined the K reads: the unlock needs K% ≥ 22% against a
# low-whiff arm (whiff ≤ 20%); ≥ 28% without that matchup is the binary
# profile; ≥ 30% is the high-K caution. These supersede the O-8 lines.
_K_UNLOCK_SHARE = Decimal("0.22")
_BINARY_K_SHARE = Decimal("0.28")
_HIGH_K_SHARE = Decimal("0.30")
_LOW_WHIFF_SHARE = Decimal("0.20")
# v2.2 (D-115): the batter-side tag lines. The x-gap flag is an
# under-performance read only — xISO-ISO ≥ +.050 or xwOBA-wOBA ≥ +.015,
# superseding D-110's .030 absolute-value tag; barrel-elite needs barrel%
# ≥ 15 over ≥ 50 season BBE; the power profile needs season avg EV ≥ 91
# mph AND bat speed ≥ 73 mph; actual-over-expected is context only
# (wOBA-xwOBA ≥ ~.040 with sprint ≥ 28 ft/s); contact-first flips to the
# v2.2 veto — squared-up ≥ 35% of competitive swings with a sub-70 bat
# speed, superseding D-110's ≥ 72 mph context tag.
_X_ISO_GAP_LINE = Decimal("0.05")
_X_WOBA_GAP_LINE = Decimal("0.015")
_BARREL_ELITE_SHARE = Decimal("0.15")
_BARREL_ELITE_MIN_BBE = 50
_POWER_EV_LINE = Decimal("91")
_POWER_BAT_SPEED_LINE = Decimal("73")
_AOE_WOBA_GAP_LINE = Decimal("0.04")
_AOE_SPRINT_LINE = Decimal("28")
# D-125 (PO): x-gap reliability bands. Builder-judgment bands informed by
# the ratified stabilization anchors (ISO ~160 AB, BB% ~120 PA — an L30
# window is too noisy for a gap read) — NOT v2.2 firing lines, and both
# lines print in the captions that render them (D-079). The gaps stay
# descriptive; the band stops a May gap and an August gap reading alike.
_GAP_READABLE_PA = 200
_GAP_ESTABLISHED_PA = 400
_SQUARED_UP_LINE = Decimal("0.35")
_CONTACT_BAT_SPEED_LINE = Decimal("70")
_TOP5_SLOT = 5

# v2.2 (D-118): the park and weather tag lines. The park reads use the
# hand-split home-run factor for the batter's resolved side (D-065) —
# boost at ≥ 110 (strong ≥ 115), wrong-side at ≤ 90 (strong ≤ 85). The
# weather reads fire only on open-air venues with a live temperature —
# heat boost at ≥ 85°F (strong ≥ 90°F), cold suppress below 45°F. A
# roofed stadium is the indoor neutral value and a missing reading is a
# silent tag, never an invented one.
_PARK_BOOST_LINE = Decimal("110")
_PARK_BOOST_STRONG_LINE = Decimal("115")
_WRONG_SIDE_PARK_LINE = Decimal("90")
_WRONG_SIDE_PARK_STRONG_LINE = Decimal("85")
_HEAT_BOOST_LINE = Decimal("85")
_HEAT_BOOST_STRONG_LINE = Decimal("90")
_COLD_SUPPRESS_LINE = Decimal("45")

# v2.2 wind reads (SP-4, D-119): the forecast resolved against the batter's
# dominant air field on the measured home-to-CF axis (PARK_ORIENTATION).
# WIND_ASSIST at ≥ 8 mph resolved out toward his air field (strong ≥ 12);
# WIND_KILL at ≥ 10 mph resolved in, or an out-wind of ≥ 8 mph resolved
# toward the opposite corner ("out-wind opposing his air field" — the v2.2
# table names no number for the opposing case, so it borrows the assist
# line and the caption says so). The severe COLD_SUPPRESS below 38°F needs
# an in-wind along the axis of ≥ 5 mph. A roofed venue, an unmeasured axis,
# an unparseable compass reading, or a spray record under the ratified
# floors (5 air balls L7 / 15 L14+; D-133) is a silent tag, never an invented one.
_WIND_ASSIST_LINE = Decimal("8")
_WIND_ASSIST_STRONG_LINE = Decimal("12")
_WIND_KILL_IN_LINE = Decimal("10")
_SEVERE_COLD_LINE = Decimal("38")
_SEVERE_COLD_WIND_IN_LINE = Decimal("5")

# v2.2 spray-alignment reads (SP-4, D-120): PULL_AIR_MATCH at a pull-air
# share ≥ 40% with the same-side HR factor at the park-boost line — his air
# contact goes where the park boosts his side; OPPO_AIR_MATCH at an
# oppo-air share strictly over 20% read against the OPPOSITE-side factor —
# the Walker exception: an oppo-power bat reads as the other hand for the
# park, because his damaging air contact goes to that field. The "+ wind"
# rider joins when the forecast also resolves out to the matching field at
# the wind-assist line. The spray record is the form section's floored
# shares, as for the wind reads; an insufficient record is a silent tag.
_PULL_AIR_SHARE_LINE = Decimal("40")
_OPPO_AIR_SHARE_LINE = Decimal("20")

# The ratified pitch-type sample floor (10 BBE) for the breakup table's
# per-pitch EV and Air% — below it the INSUFFICIENT treatment, never hidden.
_MIN_BBE_PITCH_TYPE = 10

# D-111 / v2.2 (D-114): the starter header cards' and Arms tab's emphasis
# and sample lines, each printed on its surface (the D-079 pattern). Green
# marks the digest's pitcher-vulnerability reads only: HR/9 at or above 1.5
# (v2.2's season target, superseding the 1.4 line), and wOBA above xwOBA —
# no invented bands. The L30 side rows carry the ratified
# pitcher-vulnerability floor (50 batters faced / 30 batted balls; D-134);
# contact reads carry the general 15-BBE floor. Below a floor the value
# stays visible under the amber INSUFFICIENT advisory, never hidden (D-068).
_HR9_LINE = Decimal("1.5")
# v2.2 (D-114): the pitcher-side tag lines — the suppressor at HR/9 ≤ 0.80,
# the ground-ball profile at season avg LA allowed ≤ 8° or an L30 ground-
# ball share ≥ 50% of classified BBE (the season boards publish no GB%, so
# the share reads the L30 event record), the fly-vulnerable flag at avg LA
# allowed ≥ 18°, and the gas profile at HR/9 ≥ 1.5 with an L30 ground-ball
# share under 40%.
_HR9_SUPPRESSOR_LINE = Decimal("0.8")
_GB_PROFILE_LA_LINE = Decimal("8")
_GB_PROFILE_SHARE_LINE = Decimal("0.50")
_GB_PROFILE_EXTREME_LINE = Decimal("0.55")
_FB_VULNERABLE_LA_LINE = Decimal("18")
_PITCHER_GAS_GB_CEILING = Decimal("0.40")
# D-134 (PO): the vulnerability floor drops from 80/40 to 50/30 per side —
# researched against the 2026-08-26 slate's probables (14 starters, 6-11
# starts each over the two-month record): the 80-BF line marked 12 of 28
# side-rows INSUFFICIENT, and a regular's lighter side over ~7 outings
# sits around 70-90 BF (sampled median 75). 50 is the "last 7 outings"
# baseline the PO asked for — the genuinely thin sampled side (24 BF in
# a 6-start record) stays marked, and 30 BBE keeps the pair proportional
# (a walk-heavy line can't clear on batters faced alone).
_VULN_MIN_BF = 50
_VULN_MIN_BBE = 30
_MIN_BBE_CONTACT = 15


def _ordinal(position: int) -> str:
    """The lineup-slot ordinal — never "1th"."""
    if 10 <= position % 100 <= 20:
        return f"{position}th"
    return f"{position}" + {1: "st", 2: "nd", 3: "rd"}.get(position % 10, "th")


def _air_field(card: BatterCard) -> tuple[str, str] | None:
    """(field, name) of the batter's dominant air field, or None.

    The spray record is the form section's pull/oppo air shares — L7 falling
    back to L14 under the ratified floors (5 air balls L7 per D-133, 15 at
    L14+) —
    because the season view publishes no spray read (D-116). Those shares
    are D-071's signed halves over measurable air balls (a dead-center ball
    claims no direction), so "dominant" is the larger of pull, oppo, and
    the dead-center remainder — in practice a pull or oppo side. The field
    is "pull", "center", or "oppo" for `spray_field_bearing`; the name is
    the field as the batter faces it — a right-hander's pull is "left", a
    left-hander's "right". None when the side, the form section, or a
    sufficient spray record is absent: the wind tags stay silent rather
    than resolve against an invented field.
    """
    side = card.batting_side
    form = card.form
    if side not in ("L", "R") or form is None:
        return None
    spray = form.pull_air_pct
    if not spray.sufficient or spray.value is None:
        return None
    pull_share = spray.value
    oppo = form.oppo_air_pct
    oppo_share = oppo.value if oppo is not None and oppo.value is not None else Decimal("0")
    center_share = Decimal("100") - pull_share - oppo_share
    if pull_share >= center_share and pull_share >= oppo_share:
        field = "pull"
    elif oppo_share >= center_share:
        field = "oppo"
    else:
        field = "center"
    return field, _field_name(side, field)


def _field_name(side: str, field: str) -> str:
    """The spray third as the batter faces it: a right-hander's pull is
    "left", a left-hander's "right"; center rides the axis."""
    if field == "center":
        return "center"
    return "left" if (field == "pull") == (side == "R") else "right"


def _wind_rider_text(game: GameCard, side: str, match_field: str) -> str:
    """', wind {x} mph out to {field}' when the forecast resolves out to
    the matching spray third at the assist line — else nothing, and the
    tag simply fires without the rider (D-120)."""
    axis = game.park_orientation_degrees
    wind_from = game.wind_from_degrees
    wind_speed = game.wind_speed_mph
    if not (
        game.venue_type is VenueType.OPEN_AIR
        and axis is not None
        and wind_from is not None
        and wind_speed is not None
    ):
        return ""
    resolved = resolved_wind_mph(
        wind_speed, wind_from, spray_field_bearing(axis, side, match_field)
    )
    if resolved < _WIND_ASSIST_LINE:
        return ""
    return f", wind {float(resolved):.0f} mph out to {_field_name(side, match_field)}"


def _pitcher_profile_tags(opposing: PitcherCard) -> tuple[list[str], list[str]]:
    """(boosters, vetoes) — the pitcher-side reads (D-114): HR/9 is a
    season-scope read (the event record publishes no innings); the
    ground-ball share reads the event record because the season boards
    publish no GB% — the last three months since D-142 (PO) rewindowed the
    starter's recent reads; the firing conditions are unchanged. D-116
    (PO): the GB% number itself lives on the Arms tab only — these tags
    keep their firing conditions but never quote the share. Shared by the
    shortlist tags and the popup's pitcher bubbles (D-129) so the two
    surfaces can never disagree about a line."""
    boosters: list[str] = []
    vetoes: list[str] = []
    reads = opposing.season_reads
    hr9 = reads.home_run_per_nine if reads is not None else None
    season_la = reads.avg_launch_angle if reads is not None else None
    recent = opposing.recent_overall
    gb_share = recent.ground_ball_share if recent is not None else None
    if gb_share is not None and gb_share >= _GB_PROFILE_SHARE_LINE:
        extreme = "extreme " if gb_share >= _GB_PROFILE_EXTREME_LINE else ""
        vetoes.append(f"air allowed: low — {extreme}ground-ball profile (3-month record)")
    elif season_la is not None and season_la <= _GB_PROFILE_LA_LINE:
        vetoes.append(
            f"air allowed: low — ground-ball profile (avg LA {float(season_la):.1f}°, season)"
        )
    if hr9 is not None and hr9 <= _HR9_SUPPRESSOR_LINE:
        vetoes.append(f"suppressor: HR/9 {float(hr9):.2f} (season)")
    if (
        hr9 is not None
        and hr9 >= _HR9_LINE
        and gb_share is not None
        and gb_share < _PITCHER_GAS_GB_CEILING
    ):
        boosters.append(f"gas: HR/9 {float(hr9):.2f} (season)")
    if season_la is not None and season_la >= _FB_VULNERABLE_LA_LINE:
        boosters.append(f"fly-ball vulnerable: avg LA {float(season_la):.1f}° (season)")
    return boosters, vetoes


def _pitcher_tag_lists(pitcher: PitcherCard) -> tuple[list[str], list[str], list[str]]:
    """(advisories, boosters, vetoes) for the popup's pitcher area (D-129,
    PO): HIS reads as Sluggers-style bubble tags — the same D-114 firing
    conditions the shortlist's pitcher-side tags use (green argues for the
    home run, red against), the low-whiff arm read, and the neutral
    sample notes (grey)."""
    profile_boosters, vetoes = _pitcher_profile_tags(pitcher)
    boosters: list[str] = []
    whiff = pitcher.season_whiff_weighted
    if whiff is not None and whiff <= _LOW_WHIFF_SHARE:
        boosters.append(f"low-whiff arm: arsenal whiff {float(whiff) * 100:.1f}% (season)")
    boosters.extend(profile_boosters)
    advisories: list[str] = []
    if pitcher.season_reads is None:
        advisories.append("no season record")
    workload = pitcher.workload
    if workload is not None and workload.thin_sample:
        count = workload.starts_in_window
        advisories.append(
            f"thin sample: {count} start" + ("" if count == 1 else "s") + " in the 3-month record"
        )
    return advisories, boosters, vetoes


def _card_tag_lists(
    card: BatterCard,
    opposing: PitcherCard | None,
    *,
    game: GameCard | None = None,
) -> tuple[list[str], list[str], list[str]]:
    """(advisories, boosters, vetoes) as lists — the shortlist's bubble
    tags (D-126): the neutral advisories and absences, the reads that argue
    FOR the home run (green bubbles), and the reads that argue AGAINST it
    (red). Each list item is one self-contained tag. The park and weather
    reads (D-118) need the game; without one they stay silent."""
    advisories: list[str] = []
    boosters: list[str] = []
    vetoes: list[str] = []
    insufficient, missing = _component_flags(card)
    if insufficient:
        advisories.append(f"low sample: {insufficient}")
    if missing:
        advisories.append(f"missing: {missing}")
    if card.lineup_is_estimate:
        advisories.append("est. lineup")
    if card.order_position is not None:
        slot = f"bats {_ordinal(card.order_position)}"
        slot += " (est.)" if card.lineup_is_estimate else ""
        # v2.2 (D-115): a top-5 slot is a booster — the 4-5 PA tier.
        # D-146 (PO): the leadoff "extra look at the starter" tag is
        # removed completely. Later slots stay neutral advisories.
        if card.order_position <= _TOP5_SLOT:
            boosters.append(slot)
        else:
            advisories.append(slot)
    pa = card.season.plate_appearances if card.season is not None else 0
    # v2.2 K reads (D-114): the unlock needs K% ≥ 22% AND a low-whiff arm
    # (≤ 20%); without that matchup, ≥ 28% reads binary and ≥ 30% is the
    # high-K caution. A missing whiff read is not a low-whiff arm.
    k_share = card.season_k_share
    whiff = opposing.season_whiff_weighted if opposing is not None else None
    low_whiff_arm = whiff is not None and whiff <= _LOW_WHIFF_SHARE
    if low_whiff_arm:
        assert whiff is not None  # narrowing for the f-string
        boosters.append(f"low-whiff arm: arsenal whiff {float(whiff) * 100:.1f}% (season)")
    if k_share is not None:
        if k_share >= _K_UNLOCK_SHARE and low_whiff_arm:
            assert whiff is not None
            boosters.append(
                f"high-K bat vs low-whiff arm: K% {float(k_share) * 100:.1f} "
                f"({pa} PA), arsenal whiff {float(whiff) * 100:.1f}%"
            )
        elif k_share >= _HIGH_K_SHARE:
            vetoes.append(f"high-K profile: K% {float(k_share) * 100:.1f} ({pa} PA)")
        elif k_share >= _BINARY_K_SHARE:
            vetoes.append(f"binary K profile: K% {float(k_share) * 100:.1f} ({pa} PA)")
    # v2.2 pitcher-side reads (D-114): one shared helper, so the shortlist
    # tags and the popup's pitcher bubbles (D-129) can never disagree about
    # a firing condition.
    if opposing is not None:
        profile_boosters, profile_vetoes = _pitcher_profile_tags(opposing)
        boosters.extend(profile_boosters)
        vetoes.extend(profile_vetoes)
    # v2.2 (D-115): the x-gap flag — an under-performance read, so the
    # positive side only (expected above actual); both gaps always shown,
    # no expected-stats row, no tag. D-125: the reliability band rides the
    # sample, and a suppressive home park attaches its why-rider — the
    # expected stats are park-neutral, so a tough home park can hold a
    # positive gap open without any regression coming.
    gaps = card.season_gaps
    if gaps is not None and (
        gaps.xiso_minus_iso >= _X_ISO_GAP_LINE or gaps.xwoba_minus_woba >= _X_WOBA_GAP_LINE
    ):
        tag = (
            f"x-gap: xISO {_signed_avg_text(gaps.xiso_minus_iso)}, "
            f"xwOBA {_signed_avg_text(gaps.xwoba_minus_woba)} "
            f"(season, {gaps.plate_appearances} PA · {_gap_band(gaps.plate_appearances)})"
        )
        home_factor = _home_park_hr_factor(card.team, card.batting_side)
        if home_factor is not None and home_factor.factor <= _WRONG_SIDE_PARK_LINE:
            tag += (
                f"; home park HR factor {float(home_factor.factor):.0f} "
                f"({card.batting_side}HB) can hold the gap open — x-stats are park-neutral"
            )
        boosters.append(tag)
    # Barrel-elite and the power profile read the season Statcast board;
    # both carry the v2.2 power-badge gate (≥ 50 BBE, BBE-denominated).
    statcast = card.statcast
    if statcast is not None and statcast.batted_ball_events >= _BARREL_ELITE_MIN_BBE:
        if statcast.barrel_share >= _BARREL_ELITE_SHARE:
            boosters.append(
                f"barrel {float(statcast.barrel_share) * 100:.1f}% "
                f"({statcast.batted_ball_events} BBE)"
            )
        if (
            statcast.exit_velocity_avg >= _POWER_EV_LINE
            and card.squared_up_bat_speed is not None
            and card.squared_up_bat_speed >= _POWER_BAT_SPEED_LINE
        ):
            boosters.append(
                f"power profile: EV {float(statcast.exit_velocity_avg):.1f} mph, "
                f"bat speed {float(card.squared_up_bat_speed):.1f} mph (season)"
            )
    # Actual-over-expected is context only (v2.2): no automatic
    # attribution — it rides the neutral column. D-125: the advisory now
    # names every structural reason present (the expected stats are
    # direction-blind and park-neutral, and footspeed beats them on the
    # ground), so an over-performance with a known driver stops reading
    # like regression due. No reason present, no tag.
    if gaps is not None and gaps.xwoba_minus_woba <= -_AOE_WOBA_GAP_LINE:
        aoe_reasons: list[str] = []
        if card.sprint_speed_fps is not None and card.sprint_speed_fps >= _AOE_SPRINT_LINE:
            aoe_reasons.append(f"sprint {float(card.sprint_speed_fps):.1f} ft/s")
        form = card.form
        pull_air = form.pull_air_pct if form is not None else None
        if (
            pull_air is not None
            and pull_air.sufficient
            and pull_air.value is not None
            and pull_air.value >= _PULL_AIR_SHARE_LINE
        ):
            aoe_reasons.append(
                f"pull-air {float(pull_air.value):.0f}% "
                f"({pull_air.sample} air balls L{pull_air.window_games})"
            )
        home_factor = _home_park_hr_factor(card.team, card.batting_side)
        if home_factor is not None and home_factor.factor >= _PARK_BOOST_LINE:
            aoe_reasons.append(
                f"home park HR factor {float(home_factor.factor):.0f} ({card.batting_side}HB)"
            )
        if aoe_reasons:
            advisories.append(
                f"actual over expected: wOBA {_signed_avg_text(-gaps.xwoba_minus_woba)} "
                f"over xwOBA (season, {gaps.plate_appearances} PA · "
                f"{_gap_band(gaps.plate_appearances)}) — likely structural: "
                f"{'; '.join(aoe_reasons)}; x-stats are park-neutral and direction-blind"
            )
    # Platoon advantage (v2.2): the batter's resolved side against the
    # starter's throwing hand — a contact-quality signal, with the 2025
    # anomaly caveat stated in the caption.
    throws = opposing.throws if opposing is not None else None
    if card.batting_side is not None and throws is not None and card.batting_side != throws:
        boosters.append(f"platoon advantage: bats {card.batting_side} vs {throws}P")
    # Robbed (v2.2, aligned to D-113's column): 375+ ft balls that stayed
    # in the park over his last 7 games played — a raw count, never a rate.
    mix = card.mix_line
    if mix is not None and mix.robbed_hr_count:
        boosters.append(f"robbed: {mix.robbed_hr_count} at 375+ ft stayed in the park (L7)")
    # v2.2 contact-first veto: squared-up high with a sub-70 bat speed is a
    # contact profile, not a power profile.
    squared = card.squared_up_share
    if (
        squared is not None
        and squared >= _SQUARED_UP_LINE
        and card.squared_up_bat_speed is not None
        and card.squared_up_bat_speed < _CONTACT_BAT_SPEED_LINE
    ):
        vetoes.append(
            f"contact-first profile: squared-up {float(squared) * 100:.1f}% "
            f"({card.squared_up_swings} swings), "
            f"bat speed {float(card.squared_up_bat_speed):.1f} mph"
        )
    # v2.2 park & weather reads (D-118): the hand-split home-run factor for
    # the batter's resolved side, and the open-air temperature. A roofed
    # venue or a missing reading is a silent tag, never an invented one.
    if game is not None:
        factor = _side_factor(game, card.batting_side)
        if factor is not None:
            side_text = f"{card.batting_side}HB"
            if factor.factor >= _PARK_BOOST_LINE:
                strong = "strong " if factor.factor >= _PARK_BOOST_STRONG_LINE else ""
                boosters.append(
                    f"park boost: {strong}HR factor {float(factor.factor):.0f} ({side_text})"
                )
            elif factor.factor <= _WRONG_SIDE_PARK_LINE:
                strong = "strong " if factor.factor <= _WRONG_SIDE_PARK_STRONG_LINE else ""
                vetoes.append(
                    f"wrong-side park: {strong}HR factor {float(factor.factor):.0f} ({side_text})"
                )
        temp = game.temperature_fahrenheit
        open_air = game.venue_type is VenueType.OPEN_AIR
        axis = game.park_orientation_degrees
        wind_from = game.wind_from_degrees
        wind_speed = game.wind_speed_mph
        # The in-axis resolution powers the severe-cold read; it needs no
        # spray record — a cold in-wind knocks the ball down wherever it
        # was headed.
        in_axis: Decimal | None = None
        if open_air and axis is not None and wind_from is not None and wind_speed is not None:
            in_axis = resolved_wind_mph(wind_speed, wind_from, axis)
        if open_air and temp is not None:
            if temp >= _HEAT_BOOST_LINE:
                strong = "strong " if temp >= _HEAT_BOOST_STRONG_LINE else ""
                boosters.append(f"heat boost: {strong}{float(temp):.0f}°F")
            elif temp < _COLD_SUPPRESS_LINE:
                if (
                    temp < _SEVERE_COLD_LINE
                    and in_axis is not None
                    and in_axis <= -_SEVERE_COLD_WIND_IN_LINE
                ):
                    vetoes.append(
                        f"cold suppress: severe {float(temp):.0f}°F "
                        f"+ wind in {float(-in_axis):.0f} mph"
                    )
                else:
                    vetoes.append(f"cold suppress: {float(temp):.0f}°F")
        # Wind reads (SP-4, D-119; D-161, PO): the forecast resolved on
        # the measured park axis. D-161 (PO): a wind plainly out to
        # center is a buff for EVERYBODY — at ≥ 8 mph resolved along the
        # axis every batter reads the assist, spray record or not, and
        # the away-corner kill never fires on it. (2026-08-31 at Wrigley:
        # an SW wind 8° off the axis put "wind kill: out to right" on
        # Suzuki while the weather column read "out to center" — the
        # column was the honest one.) Otherwise the reads resolve against
        # the batter's dominant air field: assist out toward it, kill in
        # from it, kill out to the opposite corner; first match wins. A
        # center-dominant spray has no opposite corner, and without a
        # sufficient spray record there is no field to resolve toward —
        # both stay silent.
        if open_air and axis is not None and wind_from is not None and wind_speed is not None:
            direction = game.wind_direction
            raw = (
                f"{direction.upper()} {float(wind_speed):.0f} mph"
                if direction
                else f"{float(wind_speed):.0f} mph"
            )
            center_out = wind_field_words(wind_from, axis) == "out to center"
            if center_out and in_axis is not None and in_axis >= _WIND_ASSIST_LINE:
                strong = "strong " if in_axis >= _WIND_ASSIST_STRONG_LINE else ""
                boosters.append(
                    f"wind assist: {strong}{float(in_axis):.0f} mph out to center ({raw})"
                )
            else:
                side = card.batting_side
                air = _air_field(card)
                if air is not None and side is not None:
                    field, field_name = air
                    resolved = resolved_wind_mph(
                        wind_speed, wind_from, spray_field_bearing(axis, side, field)
                    )
                    if resolved >= _WIND_ASSIST_LINE:
                        strong = "strong " if resolved >= _WIND_ASSIST_STRONG_LINE else ""
                        boosters.append(
                            f"wind assist: {strong}{float(resolved):.0f} mph "
                            f"out to {field_name} ({raw})"
                        )
                    elif resolved <= -_WIND_KILL_IN_LINE:
                        vetoes.append(
                            f"wind kill: {float(-resolved):.0f} mph in from {field_name} ({raw})"
                        )
                    elif field != "center" and not center_out:
                        opposing_field = "oppo" if field == "pull" else "pull"
                        opposing_name = "right" if field_name == "left" else "left"
                        opposing_resolved = resolved_wind_mph(
                            wind_speed,
                            wind_from,
                            spray_field_bearing(axis, side, opposing_field),
                        )
                        if opposing_resolved >= _WIND_ASSIST_LINE:
                            vetoes.append(
                                f"wind kill: {float(opposing_resolved):.0f} mph out to "
                                f"{opposing_name}, away from his air field ({raw})"
                            )
        # Spray-alignment reads (v2.2, D-120): his air contact going where
        # the park boosts. Pull-air match on the same-side factor;
        # oppo-air match on the OPPOSITE-side factor (the Walker
        # exception). The spray record is the form section's floored
        # shares; an insufficient record or a neutral factor is silent.
        # (A side outside L/R reads a None factor and stays silent.)
        side = card.batting_side
        form = card.form
        if side is not None and form is not None:
            pull_v = form.pull_air_pct
            oppo_v = form.oppo_air_pct
            if (
                pull_v.sufficient
                and pull_v.value is not None
                and oppo_v is not None
                and oppo_v.sufficient
                and oppo_v.value is not None
            ):
                sample_text = f"{pull_v.sample} air balls L{pull_v.window_games}"
                # D-144 (PO): the pull-air match tag is retired — removed
                # completely at the PO's direction. The oppo-air match (an
                # oppo-power read against the opposite-side factor) stays.
                other = "L" if side == "R" else "R"
                other_factor = _side_factor(game, other)
                if (
                    oppo_v.value > _OPPO_AIR_SHARE_LINE
                    and other_factor is not None
                    and other_factor.factor >= _PARK_BOOST_LINE
                ):
                    boosters.append(
                        f"oppo-air match: {float(oppo_v.value):.0f}% oppo air "
                        f"({sample_text}), reads as {other}HB: factor "
                        f"{float(other_factor.factor):.0f}"
                        f"{_wind_rider_text(game, side, 'oppo')}"
                    )
    return advisories, boosters, vetoes


def _card_tags(
    card: BatterCard,
    opposing: PitcherCard | None,
    *,
    game: GameCard | None = None,
) -> tuple[str, str, str]:
    """The same three tag lists joined with " · " — the flat form the tag
    tests assert against; the Sluggers tab renders the lists as hoverable
    bubbles (D-126), so the interpunct-inside-a-tag caution is historical."""
    advisories, boosters, vetoes = _card_tag_lists(card, opposing, game=game)
    return " · ".join(advisories), " · ".join(boosters), " · ".join(vetoes)


# D-126 (PO): the shortlist's tag bubbles — pill markup, injected once per
# render. Green argues for the home run, red against it, grey a note; the
# native hover (title) carries the full read with its samples, and the
# neon money span marks a homer on the viewed slate day (D-130, PO) —
# before that day's games go final, no tag shows at all.
_SLUGGERS_CSS = """
<style>
.gm-pill{display:inline-block;border-radius:999px;padding:0 9px;margin:1px 2px;
font-size:.78rem;line-height:1.55;white-space:nowrap;cursor:help}
.gm-pill-for{background:#2f5d0f;color:#eaffcf}
.gm-pill-against{background:#7d1616;color:#ffe9e9}
.gm-pill-note{background:#39423c;color:#c8d2cb}
.gm-money{color:#39ff14;text-shadow:0 0 8px #39ff14;font-weight:700;white-space:nowrap}
.gm-grade{background:#427010;color:#eaffcf;border-radius:4px;padding:1px 8px;font-weight:700}
.gm-dim{color:#7d8f84;font-style:italic}
.gm-head{font-size:.78rem;color:#9fb3a6;font-weight:600;white-space:nowrap;cursor:help}
</style>
"""

# The shortlist's column ratios and headers (D-126, PO's order): identity
# and the pitcher he faces, the bubble tags, the conditions, then the
# reads — Park factor, Form Score (D-132: the actual graded subtotal),
# Grade last — and the More button that opens the detail popup.
_SLUGGER_SPECS = [1.7, 0.55, 1.6, 1.6, 3.6, 1.9, 0.85, 0.95, 0.7, 0.8]
_SLUGGER_HEADERS = (
    "Batter",
    "HR",
    "Team",
    "Versus",
    "Tags",
    "Weather",
    "Park factor",
    "Form Score",
    "Grade",
    "",
)


def _pill_label(text: str) -> str:
    """The bubble's short face: the tag's own name when it carries one
    before a colon ("x-gap", "power profile", "low sample"), else the
    whole tag when it is short enough to be its own face ("barrel 16.1%
    (320 BBE)"). The full read always rides the hover, so a truncated
    face loses nothing."""
    head, sep, _ = text.partition(":")
    if sep and len(head) <= 28:
        return head
    if len(text) <= 34:
        return text
    return text[:33].rstrip() + "..."


def _tag_pills(
    advisories: list[str], boosters: list[str], vetoes: list[str]
) -> tuple[tuple[str, str, str], ...]:
    """(label, kind, full-read) triples in the old columns' order — the
    reads FOR the home run, the reads AGAINST it, then the notes — so the
    bubble row keeps the D-114 reading order without the columns."""
    pills: list[tuple[str, str, str]] = []
    for kind, tags in (("for", boosters), ("against", vetoes), ("note", advisories)):
        for text in tags:
            pills.append((_pill_label(text), kind, text))
    return tuple(pills)


def _pills_html(pills: tuple[tuple[str, str, str], ...]) -> str:
    return " ".join(
        f'<span class="gm-pill gm-pill-{kind}" '
        f'title="{html.escape(explanation, quote=True)}">{html.escape(label)}</span>'
        for label, kind, explanation in pills
    )


class _SluggerRow(NamedTuple):
    """One shortlist row's render materials (D-126): the card and game for
    the detail dialog, plus every cell's text precomputed (the view never
    derives)."""

    card: BatterCard
    game: GameCard
    versus: str
    money_day: str | None
    money_iso: str | None
    pills: tuple[tuple[str, str, str], ...]
    weather: str
    weather_absent: bool
    factor_text: str
    factor_absent: bool
    # D-146 (PO): the raw batter-side HR factor for the park-factor sort —
    # None when the venue publishes no split (the text names the absence).
    factor_value: Decimal | None = None


def _slugger_rows(board: SlateBoard) -> list[_SluggerRow]:
    """The D-084 shortlist as render rows: grades A and S only. Per-batter
    metrics live in the batter detail popup (D-084); the row keeps the
    identity cells, the bubble tags, the weather, the park factor, the Form
    Score placeholder and the grade — in the PO's D-126 order."""
    rows: list[_SluggerRow] = []
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
                weather, weather_absent = _conditions_text(game)
                advisories, boosters, vetoes = _card_tag_lists(card, opposing, game=game)
                money_iso = card.homered_on_slate_day
                money_day = None
                if money_iso is not None:
                    _, month, day = money_iso.split("-")
                    money_day = f"{int(month)}/{int(day)}"
                rows.append(
                    _SluggerRow(
                        card=card,
                        game=game,
                        versus=opposing.full_name if opposing else "TBD",
                        money_day=money_day,
                        money_iso=money_iso,
                        pills=_tag_pills(advisories, boosters, vetoes),
                        weather=weather,
                        weather_absent=weather_absent,
                        factor_text=(
                            f"{float(factor.factor):.0f}" if factor is not None else "not covered"
                        ),
                        factor_absent=factor is None,
                        factor_value=factor.factor if factor is not None else None,
                    )
                )
    return rows


# D-146 (PO): the shortlist's sort choices — highest at the top on every
# one. Grade is the default: S before A, the total score breaking ties.
_SLUGGER_SORTS = ("Grade", "Park factor", "Form Score")
_SLUGGER_GRADE_RANK = {Grade.S: 0, Grade.A: 1, Grade.B: 2, Grade.C: 3, Grade.D: 4}


def _sorted_slugger_rows(rows: list[_SluggerRow], sort: str) -> list[_SluggerRow]:
    """D-146 (PO): order the shortlist — highest first on every choice.
    Grade: S before A, then the total score. Park factor: the batter-side
    HR factor, an uncovered park last. Form Score: the graded form
    subtotal, a missing one last. Grade-then-name breaks every tie so the
    order never wobbles between refreshes."""

    def grade_rank(row: _SluggerRow) -> int:
        return _SLUGGER_GRADE_RANK.get(row.card.result.grade, 9)

    def total(row: _SluggerRow) -> Decimal:
        result = row.card.result
        return result.total_score if isinstance(result, EvaluatedGradeResult) else Decimal(0)

    if sort == "Park factor":
        return sorted(
            rows,
            key=lambda row: (
                row.factor_value is None,
                -(row.factor_value if row.factor_value is not None else Decimal(0)),
                grade_rank(row),
                -total(row),
                row.card.full_name,
            ),
        )
    if sort == "Form Score":
        return sorted(
            rows,
            key=lambda row: (
                _form_points(row.card.result) is None,
                -(_form_points(row.card.result) or Decimal(0)),
                grade_rank(row),
                -total(row),
                row.card.full_name,
            ),
        )
    return sorted(rows, key=lambda row: (grade_rank(row), -total(row), row.card.full_name))


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


_VENUE_BY_TEAM = {venue.team: venue for venue in PARK_VENUES}
_HOME_SIDES = {"L": Handedness.LEFT, "R": Handedness.RIGHT}


def _home_park_hr_factor(team: str, side: str | None) -> ParkFactor | None:
    """D-125: the hand-split HR factor at the batter's HOME park — the
    why-rider behind an x-gap read. The season gaps accumulate half their
    plate appearances there, and the expected stats are park-neutral, so
    an extreme home park can hold a gap open on its own. Tonight's venue
    factor is the D-118 tag's business; this one explains the gap. A side
    outside L/R or a venue outside the snapshot reads a silent None."""
    handedness = _HOME_SIDES.get(side or "")
    venue = _VENUE_BY_TEAM.get(team)
    if handedness is None or venue is None or venue.savant_venue_id is None:
        return None
    return park_factor_table().get(venue.savant_venue_id, {}).get(handedness)


# --------------------------------------------------------------------------
# GMF-007: the recent-form section (D-068) behind the batter detail dialog
# --------------------------------------------------------------------------

# Display precision per form metric: the rates and angles at one decimal,
# matching the live board.
# The recent-form table's scale (D-129, PO), in the table's own display
# units (percent-points, mph, degrees). The rates' edges are
# window-independent — a per-contact quality read means the same over
# seven days as over a season; what moves with the window is the sample,
# and the INSUFFICIENT marker already carries that. Research (live 2026
# league boards, qualified hitters, pulled 2026-08-25): barrels 7.8% of
# batted balls on average (P75 10.3, P90 13.2); average EV 88.8 (P90
# 91.8) — the D-127 grid edges confirmed, reused; attack angle averages
# 10.2° (P25 7.8, P75 12.5); the ideal attack-angle share averages 51%
# (P25 45.5, P75 57.1, P90 61.5); the pull-air share reuses the D-127
# grid edges (same metric, same denominator). Oppo Air % stays neutral —
# a fit read against the park, never a quality grade (D-127). Pulled BRL
# is a raw count against D-116's one-pulled-barrel week: 1/2/3+ land the
# three greens, 0 stays neutral — never red, 0 is not cold.
# D-144 (PO): AtkAng left the table; Pull % joined — pulled measurable
# CONTACTS per 100 (the air reads' measurability over all batted balls).
# The green anchor is the PO's line: 40. The spread mirrors the Pull Air %
# band spacing around a ~36-37% league-average pull share (qualified
# hitters, 2026 Savant boards) — 36 is the neutral midpoint, so the reds
# open below it.
_FORM_BANDS: dict[str, _BandSpec] = {
    "Barrel%": _BandSpec("high", 13, 10, 8.5, 6, 4, 2.5),
    "EV": _BandSpec("high", 91, 90, 89, 88, 87, 85.5),
    "IdealAtkAng%": _BandSpec("high", 60, 56, 53, 47, 43, 39),
    "Pull %": _BandSpec("high", 48, 44, 40, 36, 32, 28),
    "Pull Air %": _BandSpec("high", 43, 38, 33, 27, 22, 17),
}
_FORM_SCALE_TEXT = "; ".join(
    f"{name} — {_band_scale_text(spec)}" for name, spec in _FORM_BANDS.items()
)
_FORM_HELP: dict[str, str] = {
    "AB": (
        "At-bats over the window — plate appearances less walks, hit by "
        "pitches, sacrifices and interference (D-144)."
    ),
    "H": "Hits over the window — singles, doubles, triples and home runs (D-144).",
    "Barrel%": (
        "Barrels per 100 batted balls over the window. "
        f"Cell colors: {_band_scale_text(_FORM_BANDS['Barrel%'])}."
    ),
    "EV": (
        "Average exit velocity in mph over the window's batted balls. "
        f"Cell colors: {_band_scale_text(_FORM_BANDS['EV'])}."
    ),
    "IdealAtkAng%": (
        "Per 100 competitive swings, how many land in the ideal 5-20° "
        f"attack-angle band. Cell colors: {_band_scale_text(_FORM_BANDS['IdealAtkAng%'])}."
    ),
    "Pull %": (
        "Pulled batted balls per 100 measurable contacts (coordinates "
        "and a known batting side — the air reads' measurability over "
        "ALL batted balls, D-144). Cell colors: "
        f"{_band_scale_text(_FORM_BANDS['Pull %'])}."
    ),
    "Pull Air %": (
        "Pulled air balls per 100 measurable air balls (fly balls, line "
        "drives and popups with hit coordinates and a known batting "
        f"side). Cell colors: {_band_scale_text(_FORM_BANDS['Pull Air %'])}."
    ),
    "Oppo Air %": (
        "Opposite-field air balls over the identical measurable-air "
        "denominator. No cell colors — a fit read against the park, not "
        "a quality grade (D-127)."
    ),
    "Form Score": (
        "His actual form score from the grade: the recent-form reads "
        "scored against the category max (2 in v1; weights may change — "
        "D-132, PO)."
    ),
}
_FORM_PRECISION = {
    "Barrel%": 1,
    "EV": 1,
    "IdealAtkAng%": 1,
    "Pull %": 1,
    "Pull Air %": 1,
    "Oppo Air %": 1,
}

# D-078's wording for a metric with no observations at either window reach.
_FORM_ABSENT_TEXT = "not enough data available"


def _form_max_points(config: GreenMachineConfig) -> Decimal:
    """The form category's maximum from the one approved config (D-132)."""
    return next(
        allocation.max_points
        for allocation in config.allocations.categories
        if allocation.category is Category.FORM
    )


def _form_points(result: GradeResult) -> Decimal | None:
    """The batter's graded form subtotal as a number (D-132) — None without
    an evaluated grade or a form category. D-146 (PO): the Sluggers sort
    reads this, so the cell text and the sort can never disagree."""
    if not isinstance(result, EvaluatedGradeResult):
        return None
    return next(
        (
            score.points_awarded
            for score in result.category_scores
            if score.category is Category.FORM
        ),
        None,
    )


def _form_score_text(result: GradeResult, form_max: Decimal) -> str | None:
    """The batter's graded form subtotal as 'points / max' (D-132, PO): the
    placeholder dash is dead — the cell shows the actual form score the
    grade already computed (max 2 in v1; weights and scoring may change in a
    future version). None when there is no evaluated grade to read, so the
    cell names the absence rather than inventing a number."""
    points = _form_points(result)
    if points is None:
        return None
    return f"{format(points.normalize(), 'f')} / {format(form_max.normalize(), 'f')}"


def _form_section_frames(
    form: FormSection, form_score_text: str | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(texts, styles) for ``styled_text_frame`` — D-068's one-row section,
    re-columned by D-144 (PO): the AB/H volume counts open it, Pull %
    (all-contact pull share) sits before Pull Air %, and the AtkAng and
    Pulled BRL columns left. Before that D-129 (PO): SwSp% and Hard% left the table, the Form
    Score closes it with the actual graded form subtotal (D-132, PO — the
    D-124 placeholder dash is dead), and every graded rate wears its
    researched band (the six-bucket
    D-127 scale; the form edges are window-independent, derivations in
    DECISIONS D-129). A metric present and sufficient shows its value; one
    resolved on the L14 fallback names the window ("· L14"); one below its
    sample floor keeps its value with its exact sample and an INSUFFICIENT
    marker on amber — present, never absent (D-023/D-025); one with no
    observations at either reach reads "not enough data available" (D-078).
    An amber INSUFFICIENT cell and a named absence always outrank a band.
    """
    texts: dict[str, str] = {}
    styles: dict[str, str] = {}
    # D-144 (PO): the volume counts open the table — plain integers, the
    # L14 fallback named; no bands (volume is context, not quality).
    for count_column, count_metric in (("AB", form.at_bats), ("H", form.hits)):
        if count_metric is None or count_metric.value is None:
            texts[count_column] = _FORM_ABSENT_TEXT
            styles[count_column] = _REASON_CSS
        else:
            texts[count_column] = str(int(count_metric.value)) + (
                " · L14" if count_metric.window_games == 14 else ""
            )
    fields: tuple[tuple[str, FormValue | None], ...] = (
        ("Barrel%", form.barrel_pct),
        ("EV", form.exit_velocity),
        ("IdealAtkAng%", form.ideal_attack_angle_pct),
        ("Pull %", form.pull_pct),
        ("Pull Air %", form.pull_air_pct),
        ("Oppo Air %", form.oppo_air_pct),
    )
    for column, metric in fields:
        if metric is None or metric.value is None:
            texts[column] = _FORM_ABSENT_TEXT
            styles[column] = _REASON_CSS
            continue
        value_text = f"{float(metric.value):.{_FORM_PRECISION[column]}f}"
        if not metric.sufficient:
            texts[column] = f"{value_text} · n={metric.sample} · INSUFFICIENT"
            styles[column] = _INSUFFICIENT_CSS
        elif metric.window_games == 14:
            texts[column] = f"{value_text} · L14"
        else:
            texts[column] = value_text
    _apply_bands(
        styles,
        _FORM_BANDS,
        {
            column: (metric.value if metric is not None else None)
            for column, metric in fields
            if column in _FORM_BANDS  # Oppo Air % stays neutral (a fit read)
        },
    )
    # D-132 (PO): the actual graded form subtotal out of the category's max
    # closes the table — the D-124 placeholder dash is dead. A card with no
    # evaluated grade names the absence rather than inventing a number.
    if form_score_text is None:
        texts["Form Score"] = "not evaluated"
        styles["Form Score"] = _REASON_CSS
    else:
        texts["Form Score"] = form_score_text
    return pd.DataFrame([texts]), pd.DataFrame([styles])


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
# D-129 (PO): a pulled barrel in the log wears the same green family as a
# home run, one shade down — the counter's events made visible (a pulled
# barrel that IS a home run keeps the HR fill).
_PULLED_BARREL_CSS = "background-color: #3d5a1e; color: #eaffcf; font-weight: 700"


def _is_pulled_barrel(event: PitchEvent) -> bool:
    """One event a pulled barrel (D-116's exact convention): air-ball
    contact to the pull side in the barrel classification band."""
    return is_pull_air(event) and event.launch_speed_angle == BARREL_CLASSIFICATION


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
        elif _is_pulled_barrel(event):
            styles["Event"] = _PULLED_BARREL_CSS
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


def _gap_band(plate_appearances: int) -> str:
    """The D-125 reliability band behind an x-gap read: thin under 200 PA,
    readable 200-399, established at 400+ (the lines print in the captions)."""
    if plate_appearances >= _GAP_ESTABLISHED_PA:
        return "established"
    if plate_appearances >= _GAP_READABLE_PA:
        return "readable"
    return "thin"


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
.gm-breakup tr.gm-row-good td { background: rgba(63, 125, 50, 0.30); }
.gm-breakup tr.gm-row-bad td { background: rgba(125, 34, 28, 0.32); }
</style>
"""

_BREAKUP_GREENS = frozenset({_BAND_G3_CSS, _BAND_G2_CSS, _BAND_G1_CSS})
_BREAKUP_REDS = frozenset({_BAND_R1_CSS, _BAND_R2_CSS, _BAND_R3_CSS})


def _breakup_row_verdict(pitcher_line: PitchLine, batter_line: PitchLine | None) -> str:
    """The row's combined read (D-129, PO): green when his xwOBA with the
    pitch sits in a green vulnerability band AND the batter's SLG against
    it sits in a green band — both halves argue for the home run; red when
    both sit in red bands; anything else neutral. A row earns a verdict
    only with 10+ batted balls on BOTH halves (the ratified per-pitch
    contact floor, D-109) — a thin row stays neutral rather than grading
    noise."""
    if pitcher_line.batted_balls < _MIN_BBE_PITCH_TYPE:
        return ""
    if batter_line is None or batter_line.batted_balls < _MIN_BBE_PITCH_TYPE:
        return ""
    pitcher_css = (
        _band_css(_PITCHER_BANDS["xwOBA"], float(pitcher_line.expected_woba))
        if pitcher_line.expected_woba is not None
        else None
    )
    batter_css = (
        _band_css(_GRID_BANDS["SLG"], float(batter_line.slugging))
        if batter_line.slugging is not None
        else None
    )
    if pitcher_css in _BREAKUP_GREENS and batter_css in _BREAKUP_GREENS:
        return "gm-row-good"
    if pitcher_css in _BREAKUP_REDS and batter_css in _BREAKUP_REDS:
        return "gm-row-bad"
    return ""


def _arsenal_breakup_html(
    pitcher_lines: tuple[PitchLine, ...],
    batter_lines: dict[str, PitchLine],
    *,
    threshold: float,
    pitcher_scope_label: str,
    batter_scope_label: str,
) -> str:
    """The arsenal breakup table (D-129, PO): one row per pitch the starter
    threw this season at or above the usage threshold — rows below it hide,
    and the threshold slider stays. Every metric on a row derives from one
    scope of each player's season pitch record (§GMF-008): the default
    reads the matchup's hands — his pitches to the batter's side, the
    batter's pitches seen from the starter's hand — and the all-hands
    toggle rebases every figure, never just the usage. The pitcher half
    drops ISO for xISO (mean expected SLG minus expected BA over the
    scope's batted balls — the arsenal board cannot split by hand) and
    adds the raw barrel count; the batter half swaps PA for AB and Hits,
    puts LA right after Hits, then barrel rate and EV, and adds the
    pull/oppo air reads. A pitch the batter has not seen dashes rather
    than vanishing. Returns "" when no pitch clears the threshold, so the
    surface names that instead of rendering an empty table.
    """
    rows: list[str] = []
    for line in pitcher_lines:
        if float(line.usage_share) < threshold:
            continue
        batter = batter_lines.get(line.pitch_type)
        if batter is None:
            batter_cells = ["<td>0</td>"] + ["<td>—</td>"] * 14
        else:
            # Per-pitch contact shape (D-109): the ratified 10-BBE
            # pitch-type floor — below it the value keeps its exact sample
            # with an INSUFFICIENT marker; an empty denominator dashes.
            insufficient_note = ""
            if 0 < batter.batted_balls < _MIN_BBE_PITCH_TYPE:
                insufficient_note = f" · n={batter.batted_balls} · INSUFFICIENT"
            la_text = (
                (f"{float(batter.mean_launch_angle):.1f}°" + insufficient_note)
                if batter.mean_launch_angle is not None
                else "—"
            )
            ev_text = (
                (f"{float(batter.mean_launch_speed):.1f}" + insufficient_note)
                if batter.mean_launch_speed is not None
                else "—"
            )
            barrel_text = (
                (_pct_text(batter.barrel_share) + insufficient_note)
                if batter.barrel_share is not None
                else "—"
            )
            hard_hit_text = (
                (_pct_text(batter.hard_hit_share) + insufficient_note)
                if batter.hard_hit_share is not None
                else "—"
            )
            pull_air_text = (
                (_pct_text(batter.pull_air_share) + insufficient_note)
                if batter.pull_air_share is not None
                else "—"
            )
            oppo_air_text = (
                (_pct_text(batter.oppo_air_share) + insufficient_note)
                if batter.oppo_air_share is not None
                else "—"
            )
            batter_cells = [
                f"<td>{batter.at_bats if batter.at_bats is not None else '—'}</td>",
                f"<td>{batter.hits if batter.hits is not None else '—'}</td>",
                f"<td>{la_text}</td>",
                f"<td>{barrel_text}</td>",
                f"<td>{ev_text}</td>",
                f"<td>{_avg_text(batter.batting_average)}</td>",
                f"<td>{_avg_text(batter.slugging)}</td>",
                f"<td>{_avg_text(batter.iso)}</td>",
                f"<td>{batter.home_runs if batter.home_runs is not None else '—'}</td>",
                f"<td>{hard_hit_text}</td>",
                f"<td>{_avg_text(batter.expected_woba)}</td>",
                f"<td>{_pct_text(batter.whiff_share)}</td>",
                f"<td>{pull_air_text}</td>",
                f"<td>{oppo_air_text}</td>",
            ]
        batter_cells[0] = batter_cells[0].replace("<td>", '<td class="gm-half-boundary">', 1)
        verdict = _breakup_row_verdict(line, batter)
        row_class = f' class="{verdict}"' if verdict else ""
        name = html.escape(line.pitch_name or line.pitch_type or "— (untagged)")
        xiso_text = _avg_text(line.expected_iso)
        rows.append(
            f"<tr{row_class}><td>{name}</td><td>{float(line.usage_share):.1%}</td>"
            f"<td>{line.plate_appearances}</td>"
            f"<td>{_avg_text(line.batting_average)}</td>"
            f"<td>{_avg_text(line.slugging)}</td>"
            f"<td>{xiso_text}</td>"
            f"<td>{_avg_text(line.woba)}</td>"
            f"<td>{_avg_text(line.expected_woba)}</td>"
            f"<td>{_pct_text(line.whiff_share)}</td>"
            f"<td>{_pct_text(line.strikeout_share)}</td>"
            f"<td>{_pct_text(line.hard_hit_share)}</td>"
            f"<td>{line.barrel_count if line.barrel_count is not None else '—'}</td>"
            + "".join(batter_cells)
            + "</tr>"
        )
    if not rows:
        return ""
    header = (
        '<tr class="gm-halves"><th colspan="2"></th>'
        f'<th colspan="11" class="gm-half">Pitcher — {html.escape(pitcher_scope_label)}</th>'
        f'<th colspan="14" class="gm-half gm-half-boundary">Batter — '
        f"{html.escape(batter_scope_label)}</th></tr>"
        '<tr class="gm-cols"><th>Pitch</th><th>Usage%</th>'
        "<th>PA</th><th>AVG</th><th>SLG</th><th>xISO</th><th>wOBA</th><th>xwOBA</th>"
        "<th>Whiff%</th><th>K%</th><th>Hard-Hit%</th><th>BRL</th>"
        '<th class="gm-half-boundary">AB</th><th>H</th><th>LA</th><th>Barrel%</th><th>EV</th>'
        "<th>AVG</th><th>SLG</th><th>ISO</th><th>HR</th><th>Hard-Hit%</th><th>xwOBA</th>"
        "<th>Swing-Str%</th><th>Pull Air%</th><th>Oppo Air%</th></tr>"
    )
    return (
        '<div class="gm-breakup-wrap"><table class="gm-breakup"><thead>'
        + header
        + "</thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


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
    """The batter detail body (D-084): the 2D park with its live wind in
    field words (D-129), the expected starter's card and bubble tags
    beside it (D-129), the D-068 form section, and the recent
    exit-velocity sheet behind the pitch-mix threshold toggle.

    Reachable from the Sluggers and Matchups More buttons (D-078/D-128),
    it is also the D-080 expanded matchup view, rebuilt by D-129 (PO):
    both halves of the arsenal breakup read each player's season pitch
    record — the matchup's hands by default, all hands on the toggle,
    every metric rebased — over one lazy query per player, with one
    threshold slider driving the breakup's rows and the event log's
    pitch-mix filter.
    """
    st.markdown(f"**{card.full_name}** — {card.team}")
    pitcher = _opposing_pitcher(game, card) if game is not None else None

    # D-129 (PO): the park panel and the expected starter's details sit
    # side by side — the same starter card the Matchups tab carries, with
    # his reads as Sluggers-style bubble tags under it.
    park_column, pitcher_column = st.columns([1, 1])
    with park_column:
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
            field_wind = _field_wind(game)
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
                    wind_words=field_wind.words,
                    wind_from_degrees=field_wind.from_degrees,
                    axis_degrees=field_wind.axis_degrees,
                ),
                unsafe_allow_html=True,
            )
    with pitcher_column:
        st.markdown("**Expected starter**")
        if game is None:
            st.caption("No game on today's slate board — no opposing starter to read.")
        else:
            sp_recent = st.toggle(
                "Starter metrics: recent form (last 3 months) — season is the default",
                value=False,
                key=f"sp_recent_popup_{card.player_id}",
                help=(
                    "D-111, rewindowed to three months by D-142 (PO); D-143 "
                    "(PO): the toggle flips all three rows. Season: the "
                    "overall row reads the season boards; the side rows read "
                    "his full-season pitch record per batting side. Recent: "
                    "all three rows read the last three months of kept pitch "
                    "events. A pitch record publishes no innings and no "
                    "per-event expected SLG, so HR/9 and xISO live on the "
                    "season overall row only — the HR count shows instead."
                ),
            )
            opposing_team = game.away_team if card.team == game.home_team else game.home_team
            _sp_card(
                pitcher,
                opposing_team,
                recent=sp_recent,
                key_suffix=f"_popup_{card.player_id}",
            )
            if pitcher is not None:
                pills = _tag_pills(*_pitcher_tag_lists(pitcher))
                if pills:
                    st.markdown(_SLUGGERS_CSS + _pills_html(pills), unsafe_allow_html=True)
                    st.caption(
                        "His reads (D-114/D-129): the same firing conditions "
                        "the shortlist's pitcher-side tags use — green argues "
                        "for the home run, red against, grey a note. Hover a "
                        "bubble for the full read."
                    )

    st.markdown("**Recent form [L7]**")
    if card.form is None:
        st.caption(
            "Recent form is not covered by source: the form-event feed was not "
            "retrieved for this board, so no window could be resolved."
        )
    else:
        texts, styles = _form_section_frames(
            card.form,
            _form_score_text(card.result, _form_max_points(production_config())),
        )
        st.dataframe(
            styled_text_frame(texts, styles),
            hide_index=True,
            column_config=_column_help(texts.columns, _FORM_HELP),
        )
        st.caption(
            "Each metric reads his last 7 games played [L7] — off-days "
            "never slide the window (D-163, PO); a metric whose L7 window is "
            "empty falls back to his last 14 games [L14], marked '· L14'. A "
            "metric below "
            "its sample floor keeps its value with its exact sample and an "
            "INSUFFICIENT marker; one with no observations at either reach reads "
            "'not enough data available' (D-068). AB and H are the window's "
            "plain volume counts (D-144). Pull % = pulled share of measurable "
            "CONTACTS (all batted balls with coordinates and a known batting "
            "side); Pull Air % and Oppo Air % share the narrower measurable-"
            "air denominator (fly balls, line drives and popups). The "
            "air-ball floor splits by window: 5 at L7 (D-133), 15 at "
            "L14 (v2.2). D-129 (PO): SwSp% and Hard% left this table, and "
            "D-144 (PO) took the AtkAng and Pulled BRL columns with it; the "
            "Form "
            "Score closes it with the actual graded subtotal (D-132), and "
            "**cell colors** grade "
            "the rates on researched 2026 league scales — the edges: "
            + _FORM_SCALE_TEXT
            + ". Oppo Air % stays neutral (a fit read), and the AB/H counts "
            "carry no colors (volume, not quality). An amber "
            "INSUFFICIENT cell and a named absence always outrank a band."
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
        + (
            f" · {pitcher.full_name} (throws {pitcher.throws})"
            if pitcher is not None and pitcher.throws
            else f" · {pitcher.full_name}"
            if pitcher is not None
            else ""
        )
    )
    if pitcher is None:
        st.caption(
            "No opposing starter is named for this game — the breakup appears once probables post."
        )
    else:
        # D-129 (PO): both halves read each player's SEASON pitch record,
        # fetched lazily on the dialog open (one query per player, cached
        # per slate day) — the published boards carry no per-hand split
        # (their hand filter is inert, verified 2026-08-25), so the split
        # is computed pipeline-side over the same record (§GMF-008).
        assert game is not None  # a named starter only exists with a game
        side_known = card.batting_side in ("L", "R") and pitcher.throws in ("L", "R")
        side_text = "left" if card.batting_side == "L" else "right"
        all_hands = st.toggle(
            "All pitches, all hands",
            value=False,
            key=f"arsenal_allhands_{card.player_id}",
            disabled=not side_known,
            help=(
                "Off (default): only the pitches he threw to "
                f"{side_text}-handed batters this season, and the batter's "
                f"season record against pitches from {throws_text}-handed "
                "pitching — every metric rebased to that hand, never just "
                "the usage. On: both full season records, all hands (D-129)."
                if side_known
                else "Unavailable without a known batting side on both "
                "cards — the table reads all hands."
            ),
        )
        hand_filter = side_known and not all_hands
        if not side_known:
            reason = (
                "A switch hitter bats from both sides"
                if card.batting_side == "S"
                else "A batting side is not on record for both cards"
            )
            st.caption(f"{reason} — the breakup reads both full season records, all hands.")
        slate_iso = game.scheduled_start_utc.date().isoformat()
        pitcher_events = _season_pitch_events(pitcher.player_id, "pitcher", slate_iso)
        batter_events = _season_pitch_events(card.player_id, "batter", slate_iso)
        if isinstance(pitcher_events, FetchFailure) or isinstance(batter_events, FetchFailure):
            st.caption(
                "The season pitch record could not be retrieved for one of "
                "these players — the breakup stays off rather than invent "
                "a split."
            )
        elif not pitcher_events:
            st.caption("No regular-season pitches on record for him this year.")
        else:
            pitcher_lines, batter_lines = season_breakup_lines(
                pitcher_events,
                batter_events,
                batter_side=card.batting_side,
                pitcher_throws=pitcher.throws,
                hand_filter=hand_filter,
            )
            table_html = _arsenal_breakup_html(
                pitcher_lines,
                batter_lines,
                threshold=threshold,
                pitcher_scope_label=(
                    f"season vs {card.batting_side}HB" if hand_filter else "season, all hands"
                ),
                batter_scope_label=(
                    f"season vs {pitcher.throws}HP" if hand_filter else "season, all hands"
                ),
            )
            if not table_html:
                st.caption(
                    f"No pitch clears the {threshold_pct}% usage line on this "
                    "scope — lower the threshold slider to bring rows back."
                )
            else:
                st.markdown(_BREAKUP_CSS + table_html, unsafe_allow_html=True)
                st.caption(
                    "One row per pitch he threw at or above the usage line "
                    "on the named scope — every figure on a row comes from "
                    "that same scope of the season pitch record, so the two "
                    "toggle positions can never disagree about a "
                    "denominator (D-129). xISO: mean expected SLG minus "
                    "expected BA over the scope's batted balls — the "
                    "arsenal board publishes no per-hand split, so a dash "
                    "means no batted ball carried both readings. BRL is "
                    "the raw barrel count. A pitch the batter has not seen "
                    "dashes instead of hiding. Per-pitch contact reads "
                    "carry the ratified 10-BBE pitch-type floor — below it "
                    "the value keeps its exact sample with an INSUFFICIENT "
                    "marker (D-109). **Row colors (D-129, PO):** a row "
                    "goes green when his xwOBA with the pitch sits in a "
                    "green vulnerability band AND the batter's SLG against "
                    "it sits in a green band, red when both sit in red "
                    "bands — only with 10+ batted balls on both halves; "
                    "anything else stays neutral."
                )
                st.caption(
                    "LA (D-124): the batter's mean launch angle against "
                    "that pitch over the season record. v2.2 reads 23°+ "
                    "against a pitch as strong, 30° elite, and 18° as the "
                    "HR launch floor (below it, home runs need ~115 mph "
                    "EV) — an average is context for those reads, never a "
                    "firing line itself."
                )
            st.caption(
                f"Season records: his {len(pitcher_events)} pitches, the "
                f"batter's {len(batter_events)} seen — regular season "
                f"through {slate_iso}."
            )
        # v2.2's stuff-drift caption (D-123, SP-3): the primary pitch's
        # season-to-window whiff and usage facts. The mirage caution ships
        # as this caption alone — no mirage or decay wording on screen.
        drift = pitcher.stuff_drift
        if drift is not None:
            whiff_window_text = (
                f"{float(drift.whiff_window) * 100:.0f}%"
                if drift.whiff_window is not None
                else "no swings at it"
            )
            usage_window_text = (
                f"{float(drift.usage_window) * 100:.0f}%"
                if drift.usage_window is not None
                else "no typed pitches"
            )
            st.caption(
                f"Stuff drift — primary pitch {drift.pitch_name}: whiff "
                f"{float(drift.whiff_season) * 100:.0f}% season → "
                f"{whiff_window_text} 3M ({drift.pitches_in_window} pitches "
                f"3M), usage {float(drift.usage_season) * 100:.0f}% → "
                f"{usage_window_text}."
            )
    if pitcher is not None:
        # v2.2's workload echo (D-123, SP-3): the same raw facts the Arms
        # columns carry — never a cap claim.
        if pitcher.workload is None:
            st.caption("Workload — no start record in the lookback window.")
        else:
            last_text, last_three_text = _workload_facts(pitcher.workload)
            st.caption(f"Workload — last start: {last_text} · last 3 starts: {last_three_text}.")

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
    st.caption(
        "Green Event cells (D-129, PO): dark green a home run, the lighter "
        "green a pulled barrel — barrel-band contact to the pull side, the "
        "Pulled BRL counter's events made visible. The EV column heats at "
        "88 / 95 / 100 mph."
    )


@st.dialog("Batter detail", width="large")
def _batter_detail_dialog(card: BatterCard, game: GameCard | None) -> None:
    _render_batter_detail(card, game)


def _render_sluggers(board: SlateBoard, config: GreenMachineConfig) -> BatterCard | None:
    st.caption(
        "The shortlist (D-084): only batters graded A or S under the provisional "
        "v1 model (D-071). **Tags** are bubbles (D-126, PO — the For-HR and "
        "Against-HR columns are gone): green bubbles argue for the home run, "
        "red against it, grey the notes (low samples, missing components, "
        "estimated lineups, the lineup slot) — hover any bubble for the full "
        "read with its samples. Park factor is the batter-side home-run "
        "factor; weather is the start-time reading with the wind in field "
        "words (out to right, in to home, left to right) resolved on the "
        "measured park axis. A neon **$ with its date** marks a batter who "
        "homered on this slate day — it appears once his game goes final, "
        "so a slate whose games have not begun shows no tags at all "
        "(D-130). **More** opens the batter's detail. "
        "Firing lines — K reads: the unlock needs K% ≥ 22% of season plate "
        "appearances AND an arsenal-wide whiff ≤ 20%, both; without that "
        "matchup K% ≥ 28% reads binary and ≥ 30% is the high-K caution. "
        "Pitcher reads: low-whiff arm at whiff ≤ 20%; gas at season HR/9 "
        "≥ 1.50 with a three-month ground-ball share under 40% of classified "
        "BBE; fly-ball vulnerable at a season avg launch angle allowed "
        "≥ 18°; the ground-ball profile at a three-month ground-ball share "
        "≥ 50% (extreme ≥ 55%) or a season avg LA allowed ≤ 8°; the "
        "suppressor at season HR/9 ≤ 0.80. The season boards publish no "
        "ground-ball share, so that read is recent-only — the last two "
        "months since D-128 (PO) — and the GB% value itself reads on the "
        "Arms tab, recent view only (D-116). Batter reads (v2.2, D-115): the "
        "x-gap flag is under-performance evidence — xISO-ISO ≥ +.050 or "
        "xwOBA-wOBA ≥ +.015, both sides of a gap off the same "
        "expected-statistics board — descriptive, not predictive, with a "
        "reliability band off the season sample (D-125: thin under "
        "200 PA, readable 200-399, established 400+) and a rider when a "
        "suppressive home park (HR factor ≤ 90) can hold the gap open; "
        "barrel elite at barrel% ≥ 15 over "
        "≥ 50 season BBE; the power profile at season EV ≥ 91 mph AND "
        "bat speed ≥ 73 mph; a top-5 slot is the 4-5 PA tier (D-146, PO: "
        "the leadoff extra-look tag is gone); platoon advantage reads "
        "the batter's side "
        "against the starter's hand (+28 wOBA pts LHB vs RHP, +16 RHB vs "
        "LHP long-run — 2025 broke the RHB pattern for the first time in "
        "20+ years, so it stays a contact-quality signal); robbed counts "
        "375+ ft balls that stayed in the park over his last 7 games played. "
        "Contact-first is a veto: squared-up ≥ 35% of competitive swings "
        "with a sub-70 mph bat speed — a contact profile, not power. "
        "Actual over expected (wOBA-xwOBA ≥ ~.040) is context only — "
        "the advisory names the structural reasons present (sprint "
        "≥ 28 ft/s, pull-air ≥ 40% of measurable air balls, home park "
        "HR factor ≥ 110), because the expected stats are park-neutral "
        "and direction-blind; no reason, no tag (D-125). "
        "Park & weather reads (v2.2, D-118): the park boost at a "
        "batter-side HR factor ≥ 110 (strong ≥ 115), the wrong-side park "
        "at ≤ 90 (strong ≤ 85); the heat boost at ≥ 85°F (strong ≥ 90°F) "
        "and the cold suppress below 45°F, open-air venues only — a "
        "roofed stadium is the indoor neutral value. "
        "Wind reads (D-119; D-161, PO): the forecast resolved on the "
        "measured park axis. A wind plainly out to center at ≥ 8 mph "
        "resolved along the axis (strong ≥ 12) is a wind assist for "
        "EVERY batter — spray record or not — and the away-corner kill "
        "never fires on it. Otherwise the reads resolve against the "
        "batter's dominant air field — pull or oppo, the larger half of "
        "his measurable air balls in the form record (5 air balls L7 / "
        "15 at L14+): the wind assist at ≥ 8 mph resolved out toward "
        "his field (strong ≥ 12), the wind kill at ≥ 10 mph resolved "
        "in from it or ≥ 8 mph resolved out to the opposite corner "
        "(the v2.2 table names no number for the opposing case, so it "
        "borrows the assist line), and the severe cold suppress below "
        "38°F with an in-wind ≥ 5 mph along the axis. A roofed venue "
        "or, off the center-out read, an insufficient spray record "
        "carries no wind read. "
        "Spray-alignment reads (D-120): the oppo-air match at an oppo "
        "share over 20% of measurable air balls (the same signed halves "
        "as the wind reads) read against the OPPOSITE-side factor — an "
        "oppo-power "
        "bat reads as the other hand for the park, because his damaging "
        'air contact goes to that field; a "wind … out to" rider joins '
        "when the forecast also resolves out to the matching field at "
        "≥ 8 mph. **Form Score** is his actual graded form subtotal out "
        "of the category max — 2 in v1, and the weights may change in a "
        "future version (D-132, PO; the D-124 placeholder dash is dead). "
        "Hover any column header for its one-line definition."
    )
    rows = _slugger_rows(board)
    if not rows:
        st.info(f"No batter grades A or S on the {board.official_date} slate.")
        return None
    # D-146 (PO): the shortlist loads highest grades at the top and sorts
    # on grade, park factor or form — highest first on every choice.
    sort = st.radio(
        "Sort by",
        _SLUGGER_SORTS,
        key="sluggers_sort",
        horizontal=True,
        help=(
            "D-146 (PO). Grade — the default: S before A, the total score "
            "breaking ties. Park factor: the batter-side HR factor, an "
            "uncovered park last. Form Score: the graded form subtotal, a "
            "missing one last."
        ),
    )
    rows = _sorted_slugger_rows(rows, sort)
    # D-126 (PO): the shortlist as bubble rows, not a data grid — the tag
    # columns became hoverable pills, and a More button per row replaces
    # the row-select box. Header cells carry the same one-line definitions
    # on hover (the glossary dict below).
    st.markdown(_SLUGGERS_CSS, unsafe_allow_html=True)
    header = st.columns(_SLUGGER_SPECS)
    for column, name in zip(header, _SLUGGER_HEADERS, strict=True):
        if name:
            definition = _SLUGGERS_HELP.get(name, "")
            column.markdown(
                f'<span class="gm-head" title="{html.escape(definition, quote=True)}">'
                f"{html.escape(name)}</span>",
                unsafe_allow_html=True,
            )
    selected: BatterCard | None = None
    form_max = _form_max_points(config)
    for row in rows:
        cells = st.columns(_SLUGGER_SPECS, vertical_alignment="center")
        cells[0].markdown(html.escape(row.card.full_name), unsafe_allow_html=True)
        if row.money_day is not None:
            cells[1].markdown(
                f'<span class="gm-money" title="Homered on this slate day '
                f'({row.money_iso}) (D-130)">${row.money_day}</span>',
                unsafe_allow_html=True,
            )
        cells[2].markdown(html.escape(row.card.team), unsafe_allow_html=True)
        cells[3].markdown(html.escape(row.versus), unsafe_allow_html=True)
        if row.pills:
            cells[4].markdown(_pills_html(row.pills), unsafe_allow_html=True)
        weather = html.escape(row.weather)
        cells[5].markdown(
            f'<span class="gm-dim">{weather}</span>' if row.weather_absent else weather,
            unsafe_allow_html=True,
        )
        factor = html.escape(row.factor_text)
        cells[6].markdown(
            f'<span class="gm-dim">{factor}</span>' if row.factor_absent else factor,
            unsafe_allow_html=True,
        )
        # D-132 (PO): the actual graded form subtotal out of its max — the
        # placeholder dash is dead, never an invented number. (Every row is
        # graded A/S, so an evaluated result is guaranteed; the dim dash is
        # the defensive absence, not a state a reader should meet.)
        form_text = _form_score_text(row.card.result, form_max)
        cells[7].markdown(
            form_text if form_text is not None else '<span class="gm-dim">—</span>',
            unsafe_allow_html=True,
        )
        cells[8].markdown(
            f'<span class="gm-grade">{row.card.result.grade.value}</span>',
            unsafe_allow_html=True,
        )
        if cells[9].button("More", key=f"more_{board.official_date}_{row.card.player_id}"):
            selected = row.card
    if selected is None:
        st.caption("More opens the batter's detail.")
    return selected


# Absence texts that appear in otherwise-plain cells on the Arms and Backtest
# tables. Every such cell takes the one muted reason style, so an absence reads
# the same wherever it appears on the board (the D-076 colour discipline).
_ABSENCE_TEXTS = frozenset(
    {
        "starter not announced",
        "not yet observed",
        "no batters graded",
        "—",
        "no start record in the lookback window",
    }
)


def _absence_styles(texts: dict[str, str]) -> dict[str, str]:
    """Per-cell reason CSS for every cell whose text names an absence."""
    return {column: _REASON_CSS for column, text in texts.items() if text in _ABSENCE_TEXTS}


# D-128 (PO): the pitcher tables drop wOBA and ISO (xwOBA and xISO stay)
# and add Hard-Hit %.
_ARMS_METRIC_COLUMNS = (
    "PA",
    "BBE",
    "xwOBA",
    "HR",
    "HR/9",
    "BRL%",
    "Hard-Hit %",
    "LA",
    "xISO",
    "Air %",
)

# D-116 (PO): GB% lives on the Arms tab's recent view only — the season
# scope does not carry the column at all, since no season board publishes
# the split. Air % stays on both scopes (season names its absence) because
# it predates the ruling. D-128 (PO): the recent read is the last two
# months now.
_ARMS_RECENT_METRIC_COLUMNS = (*_ARMS_METRIC_COLUMNS, "GB %")


def _arms_season_metrics(
    reads: PitcherSeasonReads | None,
) -> tuple[dict[str, str], dict[str, str]]:
    """The season starter-metric columns on the Arms tab (D-111): samples
    as their own columns (D-014), every absence named, green only on the
    digest's pitcher-vulnerability read, amber contact reads below the
    ratified 15-BBE floor (D-068). D-128 (PO): wOBA and ISO left the
    pitcher tables — xwOBA and xISO stay — and Hard-Hit % joined, so the
    wOBA-over-xwOBA highlight went with its column."""
    if reads is None:
        dash = {column: "—" for column in _ARMS_METRIC_COLUMNS}
        return dash, {column: _REASON_CSS for column in dash}
    texts = {
        "PA": str(reads.plate_appearances) if reads.plate_appearances else "—",
        "BBE": str(reads.batted_ball_events) if reads.batted_ball_events else "—",
        "xwOBA": _avg_text(reads.expected_woba),
        "HR": str(reads.home_runs) if reads.home_runs is not None else "—",
        "HR/9": (
            f"{float(reads.home_run_per_nine):.2f}" if reads.home_run_per_nine is not None else "—"
        ),
        "BRL%": _pct_text(reads.barrel_share),
        "Hard-Hit %": _pct_text(reads.hard_hit_share),
        "LA": (
            f"{float(reads.avg_launch_angle):.1f}°" if reads.avg_launch_angle is not None else "—"
        ),
        "xISO": _avg_text(reads.expected_iso),
        # The season Statcast board against publishes no air-ball split
        # (its fbld/gb columns are exit velocities) — the season air share
        # names its absence; the recent events carry the real split.
        "Air %": "—",
    }
    styles = {column: _REASON_CSS for column, text in texts.items() if text == "—"}
    if reads.home_run_per_nine is not None and reads.home_run_per_nine >= _HR9_LINE:
        styles["HR/9"] = _HIGHLIGHT
    if 0 < reads.batted_ball_events < _MIN_BBE_CONTACT:
        for column in ("BRL%", "Hard-Hit %", "LA"):
            if texts[column] != "—":
                styles[column] = _INSUFFICIENT_CSS
    # D-127 (PO): the researched vulnerability bands fill the rest.
    _apply_bands(
        styles,
        _PITCHER_BANDS,
        {
            "xwOBA": reads.expected_woba,
            "HR/9": reads.home_run_per_nine,
            "BRL%": reads.barrel_share,
            "Hard-Hit %": reads.hard_hit_share,
            "LA": reads.avg_launch_angle,
            "xISO": reads.expected_iso,
        },
    )
    return texts, styles


def _arms_recent_metrics(
    line: PitcherRecentLine | None,
) -> tuple[dict[str, str], dict[str, str]]:
    """The recent-form starter-metric columns on the Arms tab (D-111) —
    the last three months of kept events (D-142, PO; two months under D-128,
    L30 before). The
    scope publishes no innings and no per-event expected SLG, so HR/9 and
    xISO name their absences and the HR count shows instead; amber contact
    reads below the ratified 15-BBE floor (D-068)."""
    if line is None:
        dash = {column: "—" for column in _ARMS_RECENT_METRIC_COLUMNS}
        return dash, {column: _REASON_CSS for column in dash}
    texts = {
        "PA": str(line.plate_appearances),
        "BBE": str(line.batted_balls),
        "xwOBA": _avg_text(line.expected_woba),
        "HR": str(line.home_runs),
        "HR/9": "—",
        "BRL%": _pct_text(line.barrel_share),
        "Hard-Hit %": _pct_text(line.hard_hit_share),
        "LA": (
            f"{float(line.avg_launch_angle):.1f}°" if line.avg_launch_angle is not None else "—"
        ),
        "xISO": "—",
        "Air %": _pct_text(line.air_ball_share),
        "GB %": _pct_text(line.ground_ball_share),
    }
    styles = {column: _REASON_CSS for column, text in texts.items() if text == "—"}
    if 0 < line.batted_balls < _MIN_BBE_CONTACT:
        for column in ("BRL%", "Hard-Hit %", "LA"):
            if texts[column] != "—":
                styles[column] = _INSUFFICIENT_CSS
    # GB % shares over classified batted balls, so its floor reads the
    # classified count, not the looser BBE sample.
    if 0 < line.classified_batted_balls < _MIN_BBE_CONTACT and texts["GB %"] != "—":
        styles["GB %"] = _INSUFFICIENT_CSS
    # D-127 (PO): the researched vulnerability bands fill the rest.
    _apply_bands(
        styles,
        _PITCHER_BANDS,
        {
            "xwOBA": line.expected_woba,
            "BRL%": line.barrel_share,
            "Hard-Hit %": line.hard_hit_share,
            "LA": line.avg_launch_angle,
            "Air %": line.air_ball_share,
            "GB %": line.ground_ball_share,
        },
    )
    return texts, styles


def _render_arms(board: SlateBoard) -> None:
    st.caption(
        "Expected starters with their season line and the arsenal they actually "
        "throw (pitch types at or above the qualifying usage share)."
    )
    recent_view = st.toggle(
        "Recent form — the metric columns read the last 3 months of kept "
        "events; season is the default",
        value=False,
        key="arms_recent_view",
        help=(
            "D-111, rewindowed to three months by D-142 (PO): the "
            "recent-form read is the last three months. Season metrics read "
            "the expected-statistics "
            "and Statcast boards against plus the statsapi season line. The "
            "event scope publishes no innings (HR/9 stays a season read, "
            "the HR count shows) and no per-event expected SLG (xISO stays "
            "a season read). The recent view also adds the GB % column "
            "(D-116)."
        ),
    )
    st.caption(
        "Starter metrics (D-111): green marks the digest's "
        "pitcher-vulnerability read — HR/9 ≥ 1.5 (season, v2.2). Amber: "
        "contact reads below the ratified 15-BBE floor — value shown, "
        "advisory attached (D-068). PA and BBE carry every rate's sample "
        "(D-014). Per the PO (D-128) the pitcher tables drop wOBA and ISO "
        "— xwOBA and xISO stay — and add Hard-Hit %, the 95+ mph share of "
        "batted balls against. Air % is the fly-ball-plus-line-drive share "
        "of the recent record's batted balls against — the ground-ball "
        "profile's air mirror; the season board publishes no air split, so "
        "the season scope names the absence and Air % reads recent only. "
        "GB % is the ground-ball share of the recent record's classified "
        "batted balls against — the ground-ball profile's own number; it "
        "reads recent only and the season scope does not carry the column "
        "(D-116). Last start and Last 3 starts are the raw workload facts "
        "off the pitching game log (v2.2, D-123): a last start at 100+ "
        "pitches is named a workload flag — a fact, never a cap claim, and "
        "a cap is only a cap if the team announced one. Fewer than three "
        "counts means fewer starts in the 31-day record. **Cell colors "
        "(D-127, PO):** the metric cells grade vulnerability on the "
        "researched 2025 scale — greener is more forgiving, three greens "
        "to dark at elite, three reds to dark at very poor; the ratified "
        "green reads above outrank a band, and an amber INSUFFICIENT cell "
        "or a named absence outranks both. The edges: " + _PITCHER_SCALE_TEXT + "."
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
                    "Last start": "starter not announced",
                    "Last 3 starts": "starter not announced",
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
            last_start_text, last_three_text = _workload_facts(card.workload)
            texts["Last start"] = last_start_text
            texts["Last 3 starts"] = last_three_text
            metric_texts, metric_styles = (
                _arms_recent_metrics(card.recent_overall)
                if recent_view
                else _arms_season_metrics(card.season_reads)
            )
            texts = _insert_after(texts, "K", metric_texts)
            text_rows.append(texts)
            style_rows.append({**_absence_styles(texts), **metric_styles})
    arms_frame = pd.DataFrame(text_rows)
    st.dataframe(
        styled_text_frame(arms_frame, pd.DataFrame(style_rows)),
        hide_index=True,
        column_config=_column_help(arms_frame.columns, _ARMS_HELP),
        key="live_arms",
    )


def _workload_facts(workload: StarterWorkload | None) -> tuple[str, str]:
    """The v2.2 workload lines (D-123, SP-3) — one wording for the Arms
    columns and the dialog echo, so the two surfaces cannot drift. Raw
    facts only: a last start at or past the ratified line is named a
    workload flag, and no cap claim ever rides the numbers. No start in
    the lookback names the absence."""
    if workload is None:
        return "no start record in the lookback window", "—"
    days = workload.days_since_last_start
    day_text = "1 day ago" if days == 1 else f"{days} days ago"
    last = f"{workload.last_start_pitches} pitches, {day_text}"
    if workload.workload_flag:
        last += " · workload flag"
    last_three = "/".join(str(count) for count in workload.last_starts) + " pitches"
    return last, last_three


def _insert_after(texts: dict[str, str], after: str, additions: dict[str, str]) -> dict[str, str]:
    """A copy of the cells dict with ``additions`` placed right behind the
    ``after`` column — column order on this grid is dict insertion order."""
    out: dict[str, str] = {}
    for column, text in texts.items():
        out[column] = text
        if column == after:
            out.update(additions)
    return out


# D-124: the star marks a metric carrying a ratified v2.2 firing line — the
# season view stars the power-profile EV and the two regression gaps, the
# recent-window view stars the two spray shares. One source of truth: the
# grid's own rename and the hover-help config both read these maps.
# D-125 (PO): the gap columns left the grid, so EV is the season view's
# only starred metric — the regression reads live as Sluggers tags.
_GRID_STARS_SEASON = {"EV": "EV ★"}
_GRID_STARS_WINDOW = {"Pull Air %": "Pull Air % ★", "Oppo Air %": "Oppo Air % ★"}

# D-124: every batter-grid column's one-line definition, shown on header
# hover. Unstarred keys — the view's star rename maps them to the headers
# actually showing.
_MATCHUPS_HELP: dict[str, str] = {
    "#": "Confirmed lineup slot.",
    "Batter": "The batter's name.",
    "Bats": "Batting side.",
    "AB": "At-bats over the scope.",
    "H": "Hits over the scope.",
    "Barrels": "Barrel count — ideal exit-velocity-plus-launch-angle contact.",
    "HR": "Home runs over the scope.",
    "EV": (
        "Average exit velocity in mph. The v2.2 power profile reads "
        "≥ 91 mph with a bat speed ≥ 73 mph. "
        f"Cell colors (researched 2025 baselines, D-127): {_band_scale_text(_GRID_BANDS['EV'])}."
    ),
    "LA": (
        "Season average launch angle — context, not a firing line: v2.2 "
        "reads the share of contact above the 18° HR floor, never the average. "
        f"Cell colors (researched 2025 baselines, D-127): {_band_scale_text(_GRID_BANDS['LA'])}."
    ),
    "Barrel/PA %": (
        "Barrels per plate appearance over the scope. "
        f"Cell colors (researched 2025 baselines, D-127): "
        f"{_band_scale_text(_GRID_BANDS['Barrel/PA %'])}."
    ),
    "Hard-Hit %": (
        "Share of batted balls at 95+ mph. "
        f"Cell colors (researched 2025 baselines, D-127): "
        f"{_band_scale_text(_GRID_BANDS['Hard-Hit %'])}."
    ),
    "AVG": (
        "Batting average over the scope. "
        f"Cell colors (researched 2025 baselines, D-127): {_band_scale_text(_GRID_BANDS['AVG'])}."
    ),
    "SLG": (
        "Slugging over the scope. "
        f"Cell colors (researched 2025 baselines, D-127): {_band_scale_text(_GRID_BANDS['SLG'])}."
    ),
    "ISO": (
        "Isolated power — slugging minus batting average — over the scope. "
        f"Cell colors (researched 2025 baselines, D-127): {_band_scale_text(_GRID_BANDS['ISO'])}."
    ),
    "Robbed HR": (
        "375+ ft balls that stayed in the park — a raw count, never a "
        "rate. Always his last 7 games played, even on the season view "
        "(D-128 / D-164, PO): the season sources publish no per-ball "
        "distances, so the count keeps its event-record basis on both "
        "views."
    ),
    "Pull Air %": (
        "Savant's season published pulled-air share of ALL batted "
        "balls, read raw on every view (D-160, PO) — the recent and "
        "season rows both carry the season card's spray profile, so "
        "the two never disagree. ≥ 40% with a boosting same-side park "
        "factor reads the pull-air match (v2.2). "
        f"Cell colors (researched 2025 baselines, D-127): "
        f"{_band_scale_text(_GRID_BANDS['Pull Air %'])}."
    ),
    "Straight Air %": (
        "Savant's season published straight-away air share of ALL "
        "batted balls, read raw on every view (D-160, PO). No cell "
        "colors: a fit read, not a quality grade."
    ),
    "Oppo Air %": (
        "Savant's season published opposite-field air share of ALL "
        "batted balls, read raw on every view (D-160, PO) — over 20% "
        "reads against the opposite-side factor (v2.2). No cell "
        "colors: a fit read against the park, not a quality grade "
        "(D-127)."
    ),
    "xwOBA": (
        "Expected wOBA from contact quality over the scope. "
        f"Cell colors (researched 2025 baselines, D-127): {_band_scale_text(_GRID_BANDS['xwOBA'])}."
    ),
    # D-145 (PO): K % replaced Swing-Str % on the matchup tables.
    "K %": (
        "Strikeouts per plate appearance over the scope (D-145, PO — the "
        "Swing-Str % column left for it). The v2.2 K reads: the unlock "
        "needs a season K% ≥ 22% with an arsenal-wide whiff ≤ 20%, both; "
        "matchup K% ≥ 28% reads binary, ≥ 30% is the high-K caution. "
        f"Cell colors (researched 2025 baselines, D-127): "
        f"{_band_scale_text(_GRID_BANDS['K %'])}."
    ),
    "Grade": (
        "The provisional v1 grade — the L30 computation on the season view; "
        "on a recent window it reads the same window the columns read (D-128)."
    ),
    "Total": "The provisional v1 model's total score.",
    "Lineup": "'est.' marks an estimated lineup.",
}


def _pitcher_help(definition: str, column: str) -> str:
    """One pitcher-metric hover: its definition plus the vulnerability
    color scale (D-127) — greener cells are more forgiving arms."""
    return (
        f"{definition} Cell colors read vulnerability — greener is more "
        f"forgiving (researched 2025 baselines, D-127): "
        f"{_band_scale_text(_PITCHER_BANDS[column])}."
    )


# D-111's starter header-card columns on hover (D-124's pattern, D-127's
# color scales). D-128 (PO): wOBA and ISO left the pitcher tables, and
# Hard-Hit % joined.
_SP_HELP: dict[str, str] = {
    "Scope": ("The row's window and samples — PA/BF and BBE over the named scope."),
    "xwOBA": _pitcher_help("Expected wOBA allowed from contact quality.", "xwOBA"),
    "HR": "Home runs allowed over the scope.",
    "HR/9": _pitcher_help(
        "Home runs allowed per nine innings — a season read; the event scope publishes no innings.",
        "HR/9",
    ),
    "BRL%": _pitcher_help("Barrels allowed per batted ball.", "BRL%"),
    "Hard-Hit %": _pitcher_help(
        "Share of batted balls against at 95+ mph (D-128, PO).", "Hard-Hit %"
    ),
    "LA": _pitcher_help("Average launch angle allowed.", "LA"),
    "xISO": _pitcher_help(
        "Expected isolated power allowed — a season read; the event scope "
        "publishes no per-event expected SLG.",
        "xISO",
    ),
}

# The Arms tab's full column set on hover — the card metrics plus the
# identity, workload and recent-only columns.
_ARMS_HELP: dict[str, str] = {
    **_SP_HELP,
    "Game": "Tonight's matchup.",
    "Pitcher": "The expected starter — TBD until probables post.",
    "Team": "His club on this slate.",
    "Throws": "Throwing hand.",
    "ERA": "Earned run average over the season.",
    "WHIP": "Walks plus hits per inning over the season.",
    "GS": "Games started over the season.",
    "K": "Strikeouts over the season.",
    "PA": "Plate appearances against over the scope — the rates' sample (D-014).",
    "BBE": "Batted-ball events against over the scope — the contact reads' sample (D-014).",
    "Air %": _pitcher_help(
        "Fly-ball-plus-line-drive share of the recent record's batted balls "
        "against — a three-month read (D-142); the season board publishes no "
        "air split.",
        "Air %",
    ),
    "GB %": _pitcher_help(
        "Ground-ball share of the recent record's classified batted balls "
        "against — a three-month read (D-116/D-128, rewindowed D-142).",
        "GB %",
    ),
    "Arsenal": "The pitches he actually throws, at or above the qualifying usage share.",
    "Last start": "The workload line for his most recent start (D-123).",
    "Last 3 starts": "The workload line across his last three starts (D-123).",
}

# The Conditions columns on hover (D-124's pattern, D-127's color scales).
_CONDITIONS_HELP: dict[str, str] = {
    "Game": "Tonight's matchup.",
    "Venue": "The ballpark.",
    "Type": "Open air, retractable roof or fixed roof.",
    "HR factor (LHB)": (
        "The left-handed home-run factor with its plate-appearance sample: "
        "100 is neutral. "
        f"Cell colors (the ratified park lines, D-127): {_band_scale_text(_FACTOR_BAND)}."
    ),
    "HR factor (RHB)": (
        "The right-handed home-run factor with its plate-appearance sample: "
        "100 is neutral. "
        f"Cell colors (the ratified park lines, D-127): {_band_scale_text(_FACTOR_BAND)}."
    ),
    "n": "The left-handed factor's plate-appearance sample (D-014).",
    "n ": "The right-handed factor's plate-appearance sample (D-014).",
    "Temp °F": "The start-time reading; a roofed venue grades at an assumed 72°F, labelled.",
    "Temp band": (
        "The v2.2 temperature band and its raw award — the cell wears the "
        "award's color: <45 dark red · 45-64 red · 65-74 light red · "
        "75-84 light green · 85-89 green · ≥90 dark green (ratified, D-121/D-127)."
    ),
    "Humidity": "A secondary modifier, never a standalone badge.",
    "Wind": (
        "The raw forecast reading — green when the wind helps at a "
        "wind-receptive park, red when it hurts (D-122)."
    ),
    "Wind recept.": (
        "The modelled HR-effect sensitivity to wind (Ballpark Pal, display only — it never grades)."
    ),
}

# D-127's caption fragments, built once from the registries so a moved
# edge can never drift from its printed line (D-079).
_GRID_SCALE_TEXT = "; ".join(
    f"{name} — {_band_scale_text(spec)}" for name, spec in _GRID_BANDS.items()
)
_PITCHER_SCALE_TEXT = "; ".join(
    f"{name} — {_band_scale_text(spec)}" for name, spec in _PITCHER_BANDS.items()
)

_SLUGGERS_HELP: dict[str, str] = {
    "Batter": "The batter's name.",
    "HR": (
        "A neon $ with a date marks a batter who homered on this slate "
        "day — it appears once his game goes final, so a slate whose "
        "games have not begun shows no tags at all (D-130)."
    ),
    "Team": "His club on this slate.",
    "Versus": "The expected opposing starter — TBD until probables post.",
    "Tags": (
        "Bubble reads: green argues for the home run, red against it, "
        "grey a note (low samples, missing components, estimated lineup, "
        "the slot). Hover a bubble for the full read with its samples."
    ),
    "Grade": "The provisional v1 grade — only A and S make this shortlist (D-084).",
    "Form Score": (
        "His actual form score from the grade: the recent-form reads scored "
        "against the category max — 2 in v1, weights may change (D-132, PO)."
    ),
    "Park factor": (
        "The batter-side home-run factor: 100 is neutral, ≥ 110 boosts, ≤ 90 suppresses (v2.2)."
    ),
    "Weather": (
        "The start-time reading: temperature, and the wind resolved on the "
        "park's measured axis in field words — out to right, in to home, "
        "left to right. A roofed stadium reads the indoor neutral value."
    ),
}


def _column_help(
    columns: Iterable[str], help_map: dict[str, str], stars: dict[str, str] | None = None
) -> dict[str, Any]:
    """st.column_config help entries for one grid (D-124): every header
    carries its one-line definition. The star rename matches the grid's own;
    entries naming columns the frame does not carry drop out."""
    renamed = {(stars or {}).get(name, name): text for name, text in help_map.items()}
    return {
        name: st.column_config.TextColumn(help=renamed[name]) for name in columns if name in renamed
    }


def _grid_line_cells(
    line: BatterGridLine | None, *, include_gaps: bool = False
) -> tuple[dict[str, str], dict[str, str]]:
    """One batter's metric cells for the matchups grid (D-079). A None
    scope or a None rate renders as a named absence, never an invented
    zero; a scope missing at every reach states 'no data available'
    (D-081). ``include_gaps`` is the season view's alone: the season
    average launch angle rides after EV (D-124), and the D-110 regression
    gaps left the grid for the Sluggers tags (D-125, PO). Starred headers
    mark the metrics carrying a ratified v2.2 firing line (D-124)."""
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
            "Robbed HR": "—",
            "Pull Air %": "—",
            "Straight Air %": "—",
            "Oppo Air %": "—",
            "xwOBA": "—",
            "K %": "—",
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
            # D-160 (PO): pull, straight and oppo all read the season
            # board's published of-BBE shares, raw, on every view.
            "Straight Air %": (
                _pct_text(line.straight_air_share) if line.straight_air_share is not None else None
            ),
            "Oppo Air %": (
                _pct_text(line.oppo_air_share) if line.oppo_air_share is not None else None
            ),
            "xwOBA": _avg_text(line.expected_woba) if line.expected_woba is not None else None,
            # D-145 (PO): K % — strikeouts per plate appearance over the
            # scope — replaced Swing-Str % on the matchup tables.
            "K %": (_pct_text(line.strikeout_share) if line.strikeout_share is not None else None),
        }
        texts = {
            "AB": str(line.at_bats),
            "H": str(line.hits),
            "Barrels": str(line.barrels) if line.barrels is not None else "—",
            "HR": str(line.home_runs),
            # D-097's counting number, redefined by the PO 2026-08-24:
            # robbed HRs — 375+ ft balls that stayed in the park, last 7
            # games played — a raw count, never a rate.
            "Robbed HR": (str(line.robbed_hr_count) if line.robbed_hr_count is not None else "—"),
        }
        styles = {}
        if line.barrels is None:
            styles["Barrels"] = _REASON_CSS
        if line.robbed_hr_count is None:
            styles["Robbed HR"] = _REASON_CSS
        for column, text in rate_texts.items():
            if text is None:
                texts[column] = "—"
                styles[column] = _REASON_CSS
            else:
                texts[column] = text
        # D-127 (PO): the researched bands grade every valued rate cell.
        # Straight Air % and Oppo Air % stay neutral — fit reads, not
        # quality grades (D-127/D-128).
        _apply_bands(
            styles,
            _GRID_BANDS,
            {
                "EV": line.exit_velocity,
                "Barrel/PA %": line.barrel_per_pa,
                "Hard-Hit %": line.hard_hit_share,
                "AVG": line.batting_average,
                "SLG": line.slugging,
                "ISO": line.iso,
                "Pull Air %": line.pull_air_share,
                "xwOBA": line.expected_woba,
                "K %": line.strikeout_share,
            },
        )
    if include_gaps:
        # D-124: the season Statcast board's average launch angle, after EV.
        # Context, never a firing line — v2.2 reads the share of contact
        # above the HR launch floor, which the season boards do not publish.
        launch_angle = line.avg_launch_angle if line is not None else None
        if launch_angle is None:
            texts = _insert_after(texts, "EV", {"LA": "—"})
            styles["LA"] = _REASON_CSS
        else:
            texts = _insert_after(texts, "EV", {"LA": f"{float(launch_angle):.1f}°"})
            # D-127: an average carries no firing line, but it still wears
            # its researched bucket (the edges print in the caption).
            css = _band_css(_GRID_BANDS["LA"], float(launch_angle))
            if css is not None:
                styles.setdefault("LA", css)
        # D-125 (PO): the D-110 regression gaps no longer grid — they read
        # as Sluggers tags with reliability bands and a home-park rider.
        # ISO and xwOBA themselves stay (PO: keep both).
    # D-124: a star on the header marks a metric that carries a ratified
    # v2.2 firing line (each line prints in the tab caption). LA stays
    # unstarred — an average carries no line.
    stars = _GRID_STARS_SEASON if include_gaps else _GRID_STARS_WINDOW
    texts = {stars.get(column, column): text for column, text in texts.items()}
    styles = {stars.get(column, column): css for column, css in styles.items()}
    return texts, styles


# D-111's starter header card: the overall row (Season, or the last two
# months on the recent-form toggle) plus the two always-recent side rows,
# with the drawn stadium between the two starters' cards. D-128 (PO): the
# pitcher tables drop wOBA and ISO — xwOBA and xISO stay — and add
# Hard-Hit %.
_SP_CARD_COLUMNS = ("Scope", "xwOBA", "HR", "HR/9", "BRL%", "Hard-Hit %", "LA", "xISO")


def _sp_season_row(reads: PitcherSeasonReads | None) -> tuple[dict[str, str], dict[str, str]]:
    """The season-scope row of a starter header card (D-111). Samples ride
    the Scope label beside the rates they basis (D-014); a missing source's
    cells name the absence, never an invented zero. Green marks only the
    digest's pitcher-vulnerability read; contact reads below the ratified
    15-BBE floor keep their values under the amber advisory (D-068)."""
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
        "xwOBA": _avg_text(reads.expected_woba),
        "HR": str(reads.home_runs) if reads.home_runs is not None else "—",
        "HR/9": (
            f"{float(reads.home_run_per_nine):.2f}" if reads.home_run_per_nine is not None else "—"
        ),
        "BRL%": _pct_text(reads.barrel_share),
        "Hard-Hit %": _pct_text(reads.hard_hit_share),
        "LA": (
            f"{float(reads.avg_launch_angle):.1f}°" if reads.avg_launch_angle is not None else "—"
        ),
        "xISO": _avg_text(reads.expected_iso),
    }
    styles = {column: _REASON_CSS for column, text in texts.items() if text == "—"}
    if reads.home_run_per_nine is not None and reads.home_run_per_nine >= _HR9_LINE:
        styles["HR/9"] = _HIGHLIGHT
    if 0 < reads.batted_ball_events < _MIN_BBE_CONTACT:
        for column in ("BRL%", "Hard-Hit %", "LA"):
            if texts[column] != "—":
                styles[column] = _INSUFFICIENT_CSS
        styles["Scope"] = _INSUFFICIENT_CSS
        label += " · INSUFFICIENT"
    # D-127 (PO): the researched vulnerability bands fill the rest.
    _apply_bands(
        styles,
        _PITCHER_BANDS,
        {
            "xwOBA": reads.expected_woba,
            "HR/9": reads.home_run_per_nine,
            "BRL%": reads.barrel_share,
            "Hard-Hit %": reads.hard_hit_share,
            "LA": reads.avg_launch_angle,
            "xISO": reads.expected_iso,
        },
    )
    return {"Scope": label, **texts}, styles


def _sp_recent_row(
    label: str,
    line: PitcherRecentLine | None,
    *,
    vulnerability_floor: bool = False,
    empty_text: str = "no recent record",
) -> tuple[dict[str, str], dict[str, str]]:
    """One event-scope row of a starter header card (D-111) — the toggle's
    overall row, or a side row — over the last three months of kept events
    (D-142, PO), or the full season off his season pitch record (D-143, PO;
    ``empty_text`` names the absence for that scope). The event scope
    publishes no innings and no per-event expected SLG, so HR/9 and xISO
    name their absences and the HR count shows instead.
    ``vulnerability_floor`` is the side rows' ratified 50-BF / 30-BBE line
    (D-134); the overall row carries the general 15-BBE contact floor.
    Below a floor the values stay visible under the amber advisory, never
    hidden (D-068)."""
    dash = {column: "—" for column in _SP_CARD_COLUMNS[1:]}
    if line is None:
        return {"Scope": f"{label} — {empty_text}", **dash}, {
            column: _REASON_CSS for column in dash
        }
    full_label = f"{label} — {line.plate_appearances} BF · {line.batted_balls} BBE"
    texts = {
        "xwOBA": _avg_text(line.expected_woba),
        "HR": str(line.home_runs),
        "HR/9": "—",
        "BRL%": _pct_text(line.barrel_share),
        "Hard-Hit %": _pct_text(line.hard_hit_share),
        "LA": (
            f"{float(line.avg_launch_angle):.1f}°" if line.avg_launch_angle is not None else "—"
        ),
        "xISO": "—",
    }
    styles = {column: _REASON_CSS for column, text in texts.items() if text == "—"}
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
    # D-127 (PO): the researched vulnerability bands fill the rest.
    _apply_bands(
        styles,
        _PITCHER_BANDS,
        {
            "xwOBA": line.expected_woba,
            "BRL%": line.barrel_share,
            "Hard-Hit %": line.hard_hit_share,
            "LA": line.avg_launch_angle,
        },
    )
    return {"Scope": full_label, **texts}, styles


def _sp_card(card: PitcherCard | None, team: str, *, recent: bool, key_suffix: str = "") -> None:
    """One starter header card (D-111): name, team, and hand over the scope
    rows. An unannounced starter names the absence. D-142 (PO): the
    recent-form read is the last three months (L30 before D-128). D-143
    (PO): the toggle flips all three rows — the season side rows read his
    full-season pitch record. D-129 (PO): the
    batter detail popup reuses this card beside the stadium — ``key_suffix``
    keeps its widget key distinct from the tab copy behind the dialog."""
    if card is None:
        st.markdown(f"**{team} starter**")
        st.caption("starter not announced")
        return
    throws = f" · throws {card.throws}" if card.throws else ""
    st.markdown(f"**{card.full_name}** — {team}{throws}")
    # D-143 (PO): the toggle drives ALL THREE rows — season (default) or
    # the three-month recent record. The season side rows come off his
    # full-season pitch record (no board publishes a per-side season
    # split), so they carry the event scope's named absences: HR/9 and
    # xISO stay on the season-boards overall row, the HR count shows.
    overall = (
        _sp_recent_row("3M", card.recent_overall) if recent else _sp_season_row(card.season_reads)
    )
    if recent:
        side_rows = [
            _sp_recent_row("vs L (3M)", card.recent_vs_left, vulnerability_floor=True),
            _sp_recent_row("vs R (3M)", card.recent_vs_right, vulnerability_floor=True),
        ]
    else:
        side_rows = [
            _sp_recent_row(
                "vs L (season)",
                card.season_vs_left,
                vulnerability_floor=True,
                empty_text="no season record",
            ),
            _sp_recent_row(
                "vs R (season)",
                card.season_vs_right,
                vulnerability_floor=True,
                empty_text="no season record",
            ),
        ]
    rows = [overall, *side_rows]
    sp_frame = pd.DataFrame([row for row, _ in rows])
    st.dataframe(
        styled_text_frame(
            sp_frame,
            pd.DataFrame([style for _, style in rows]),
        ),
        hide_index=True,
        column_config=_column_help(sp_frame.columns, _SP_HELP),
        key=f"sp_card_{card.player_id}_{'recent' if recent else 'season'}{key_suffix}",
    )
    # v2.2's thin-sample caution (D-123, SP-3): a window spanning at most
    # two starts names itself beside the hand splits.
    workload = card.workload
    if workload is not None and workload.thin_sample:
        count = workload.starts_in_window
        st.caption(
            f"3-month record: {count} start" + ("" if count == 1 else "s") + " — a thin "
            "sample: check who he faced."
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
    field_wind = _field_wind(game)
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
            wind_words=field_wind.words,
            wind_from_degrees=field_wind.from_degrees,
            axis_degrees=field_wind.axis_degrees,
        ),
        unsafe_allow_html=True,
    )


# D-145 (PO): the matchup grid as one HTML row per batter with its More
# button at the row's end — the Sluggers layout. The metric cells keep the
# D-127 band fills (inline styles now), the headers keep their D-124 hover
# definitions as title attributes, and a star still marks a ratified v2.2
# firing line. The 22-column st.dataframe could not carry in-row buttons,
# so the rows of five buttons under each grid are gone.
_MATCHUPS_GRID_CSS = """
<style>
.gm-grid{width:100%;border-collapse:collapse;table-layout:fixed}
.gm-grid th{padding:2px 3px;font-size:.72rem;color:#9fb3a6;font-weight:600;
white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:help;
border-bottom:1px solid #2c3a30;text-align:left}
.gm-grid td{padding:2px 3px;font-size:.76rem;white-space:nowrap;overflow:hidden;
text-overflow:ellipsis;border-bottom:1px solid #1e2922}
</style>
"""

# Each row's two Streamlit columns: the metric table, then the More button.
_GRID_ROW_SPECS = [13.5, 1.0]

# Identity and result columns take fixed shares of the row; the metric
# columns split the rest evenly.
_GRID_COL_WIDTHS = {"#": 2.8, "Batter": 10, "Bats": 3.6, "Grade": 5, "Total": 5, "Lineup": 4.2}


def _grid_colgroup(columns: Iterable[str]) -> str:
    """One <colgroup> shared by the header and every row table of a matchup
    grid, so the per-row tables' columns align (table-layout: fixed)."""
    listed = list(columns)
    fixed = sum(_GRID_COL_WIDTHS.get(column, 0.0) for column in listed)
    flex = [column for column in listed if column not in _GRID_COL_WIDTHS]
    share = (100.0 - fixed) / len(flex) if flex else 0.0
    return (
        "<colgroup>"
        + "".join(
            f'<col style="width:{_GRID_COL_WIDTHS.get(column, share):g}%">' for column in listed
        )
        + "</colgroup>"
    )


def _grid_header_html(columns: list[str], help_map: dict[str, str]) -> str:
    """The header row as an HTML table — hover a header for its one-line
    definition (D-124, as a title attribute now)."""
    cells = "".join(
        f'<th title="{html.escape(help_map.get(column, ""), quote=True)}">'
        f"{html.escape(column)}</th>"
        for column in columns
    )
    return (
        f'<table class="gm-grid">{_grid_colgroup(columns)}<thead><tr>{cells}</tr></thead></table>'
    )


def _grid_row_html(columns: list[str], texts: dict[str, str], styles: dict[str, str]) -> str:
    """One batter's grid row as an HTML table — every cell keeps its text,
    and the D-127 band/absence fills ride as inline styles."""
    cells = "".join(
        (
            f'<td style="{styles[column]}">{html.escape(texts.get(column, ""))}</td>'
            if column in styles
            else f"<td>{html.escape(texts.get(column, ''))}</td>"
        )
        for column in columns
    )
    return f'<table class="gm-grid">{_grid_colgroup(columns)}<tr>{cells}</tr></table>'


def _render_matchups(board: SlateBoard) -> BatterCard | None:
    window_days = _matchups_window_days()
    season_view = st.session_state.get("matchups_view_mode") != _MATCHUPS_RECENT_LABEL
    st.markdown(_MATCHUPS_GRID_CSS, unsafe_allow_html=True)
    st.caption(
        "One row per batter against the expected starter. His mix is the "
        "whole-season arsenal against ALL hands off the arsenal board "
        "(D-128, PO) — a named fallback reads his recent record when no "
        "board exists. On the recent-window view the batter's columns "
        "read his window events against the starter's hand of pitching: "
        "every pitch type by default (D-145, PO), or only the qualifying "
        "mix — pitches at or above 14% of the mix's usage — when the "
        "pitch-filter toggle below is on; the scope actually used is "
        "named under each game. The grid's window is yours below: the "
        "2026 season sources by default, or a recent window counted in "
        "weeks (to 12) or months (to 3) — the grade stays the L30 "
        "computation on the season view and follows the window "
        "otherwise. A wider window takes longer to build the first time "
        "(each day is one fetch; the board then caches). Tap a batter's "
        "**More** button at the end of his row (D-145, PO) to open his "
        "recent-form detail. Hover any column "
        "header for its one-line definition. A **★** on a header marks a "
        "metric carrying a ratified v2.2 firing line (D-124) — recent "
        "view: Pull Air % at ≥ 40% of measurable air balls with a "
        "boosting same-side park factor reads the pull-air match, Oppo "
        "Air % over 20% reads against the opposite-side factor (D-120); "
        "season view: EV at ≥ 91 mph with a bat speed ≥ 73 mph reads "
        "the power profile. The regression gaps (xISO-ISO, xwOBA-wOBA) "
        "no longer grid — they read as Sluggers tags with a reliability "
        "band and a home-park rider (D-125, PO); ISO and xwOBA themselves "
        "stay. The season view's LA is the batter's season average "
        "launch angle — context, deliberately unstarred: v2.2 reads the "
        "share of contact above the 18° HR launch floor, never the "
        "average, and the season boards publish no share."
    )
    st.caption(
        "**Cell colors (D-127, PO):** every rate cell wears one of six "
        "researched bands — three greens, dark green at elite; three "
        "reds, dark red at very poor; the unfilled cell neutral — graded "
        "against 2025 league baselines (derivations in DECISIONS D-127); "
        "where an edge is a ratified v2.2 line the column's hover says "
        "so. The edges: "
        + _GRID_SCALE_TEXT
        + ". Straight Air % and Oppo Air % stay neutral — fit reads "
        "against the park, not quality grades — and the counting columns "
        "(AB, H, Barrels, HR, Robbed HR) are volume, not quality, so "
        "they carry no color. An amber INSUFFICIENT cell and a named "
        "absence always outrank a band."
    )
    mode_col, count_col, unit_col, pitch_col = st.columns([3, 2, 2, 3])
    with mode_col:
        mode = st.radio(
            "Batter window",
            (_MATCHUPS_SEASON_LABEL, _MATCHUPS_RECENT_LABEL),
            key="matchups_view_mode",
            horizontal=True,
            help=(
                "D-128 (PO). The year reads every batter's season sources. "
                "The recent window reads his events against the starter's "
                "hand of pitching over the counted days — every pitch type, "
                "or only the qualifying mix when the pitch-filter toggle "
                "is on (D-145, PO) — and the grade follows "
                "that window (it stays L30 on the season view)."
            ),
        )
    recent = mode == _MATCHUPS_RECENT_LABEL
    with count_col:
        st.number_input(
            "How far back",
            min_value=1,
            max_value=12,
            value=4,
            step=1,
            key="matchups_window_count",
            disabled=not recent,
            help="1-12 weeks, or 1-3 months.",
        )
    with unit_col:
        st.radio(
            "Counted in",
            ("weeks", "months"),
            key="matchups_window_unit",
            horizontal=True,
            disabled=not recent,
        )
    with pitch_col:
        # D-145 (PO): the usage-threshold toggle on the main matchup
        # tables. Off (the PO's default): every pitch type the batter saw
        # enters the scope — "all hands with all their pitches". On: only
        # the starter's qualifying mix (≥14% of the mix's usage).
        qualifying_only = st.toggle(
            "Pitch filter: qualifying mix only (≥14% usage)",
            value=False,
            key="matchups_pitch_threshold",
            disabled=not recent,
            help=(
                "D-145 (PO). Off — the default: the recent-window columns "
                "read every pitch type the batter saw from the starter's "
                "hand of pitching; the starter's whole season arsenal "
                "against all hands enters unfiltered. On: only his "
                "qualifying mix pitches (at or above 14% of the mix's "
                "usage). Reads the recent-window view only — the season "
                "view's columns come from the season boards, never the "
                "pitch filter."
            ),
        )
    if recent:
        st.caption(
            f"Reading the last {window_days} days"
            + (
                " — months cap at 3, so the counter reads 3."
                if st.session_state.get("matchups_window_unit") == "months"
                and int(st.session_state.get("matchups_window_count", 4)) > 3
                else "."
            )
        )
    selected: BatterCard | None = None
    for game in board.games:
        pitchers = " vs ".join(
            card.full_name if card else "TBD" for card in (game.away_pitcher, game.home_pitcher)
        )
        with st.expander(f"{game.away_team} at {game.home_team} — {game.venue_name} · {pitchers}"):
            sp_recent = st.toggle(
                "Starter metrics: recent form (last 3 months) — season is the default",
                value=False,
                key=f"sp_recent_{game.game_pk}",
                help=(
                    "D-111, rewindowed to three months by D-142 (PO); D-143 "
                    "(PO): the toggle flips all three rows. Season: the "
                    "overall row reads the season boards; the side rows read "
                    "his full-season pitch record per batting side. Recent: "
                    "all three rows read the last three months of kept pitch "
                    "events. A pitch record publishes no innings and no "
                    "per-event expected SLG, so HR/9 and xISO live on the "
                    "season overall row only — the HR count shows instead."
                ),
            )
            away_column, field_column, home_column = st.columns([5, 4, 5])
            with away_column:
                _sp_card(game.away_pitcher, game.away_team, recent=sp_recent)
            with field_column:
                _stadium_panel(game)
            with home_column:
                _sp_card(game.home_pitcher, game.home_team, recent=sp_recent)
            st.caption(
                "Starter cards (D-111): the overall row reads the season "
                "boards (expected-statistics and Statcast boards against, "
                "statsapi season line) or, on the toggle, the last three "
                "months of kept events (D-142, PO); the side rows flip with "
                "it — season side splits read his full-season pitch record "
                "(D-143, PO). Green marks only the digest's "
                "pitcher-vulnerability read — HR/9 ≥ 1.5 (v2.2). The "
                "event scope publishes no innings and no per-event "
                "expected SLG, so HR/9 and xISO stay season reads and the "
                "HR count shows instead. Per the PO (D-128) the pitcher "
                "tables drop wOBA and ISO — xwOBA and xISO stay — and add "
                "Hard-Hit %, the 95+ mph share of batted balls against. "
                "Amber: below the ratified floor — 50 BF / 30 BBE on a "
                "side row (D-134), 15 BBE on contact reads — value shown, "
                "advisory attached (D-068). **Cell colors (D-127, PO):** "
                "the metric cells grade vulnerability on the researched "
                "2025 scale — greener is more forgiving; the ratified "
                "green reads above outrank a band. The edges: " + _PITCHER_SCALE_TEXT + "."
            )
            for label, batters, opposing_card in (
                ("Away", game.away_batters, game.home_pitcher),
                ("Home", game.home_batters, game.away_pitcher),
            ):
                st.markdown(f"**{label} lineup**")
                if batters:
                    throws_text = (
                        {"R": "right", "L": "left"}.get(opposing_card.throws, "")
                        if opposing_card is not None
                        else ""
                    )
                    hand_text = (
                        f"{throws_text}-handed pitching"
                        if throws_text
                        else "the starter's hand of pitching"
                    )
                    if opposing_card is None:
                        scope_text = "no expected starter named — no mix to line up against"
                    elif batters[0].mix_label:
                        scope_text = f"vs {opposing_card.full_name}'s mix — {batters[0].mix_label}"
                    else:
                        scope_text = f"vs {opposing_card.full_name} — no mix record at any reach"
                    st.caption(
                        f"Scope: {scope_text}. "
                        + (
                            "Columns read the batter's season sources "
                            "(D-110's regression gaps moved to the "
                            "Sluggers tags, D-125) — except Robbed HR: "
                            "always the last 7 games played of his event "
                            "record, on both views (D-128 / D-164, PO)."
                            if season_view
                            else (
                                f"Columns read the batter's last {window_days} days "
                                f"against {hand_text}, filtered to that "
                                "mix's qualifying pitches (≥14% usage) — "
                                "except Robbed HR: 375+ ft balls that "
                                "stayed in the park, last 7 games played."
                                if qualifying_only
                                else (
                                    f"Columns read the batter's last {window_days} days "
                                    f"against {hand_text} — every pitch "
                                    "type (D-145, PO; the pitch-filter "
                                    "toggle above restricts to the "
                                    "qualifying mix) — except Robbed HR: "
                                    "375+ ft balls that stayed in the "
                                    "park, last 7 games played."
                                )
                            )
                        )
                    )
                rows: list[tuple[BatterCard, dict[str, str], dict[str, str]]] = []
                for card in batters:
                    # D-098: no Form column here — the full form section is one
                    # tap away in the batter detail, so the grid stays lean.
                    evaluated = isinstance(card.result, EvaluatedGradeResult)
                    if season_view:
                        line = card.season_line
                    elif qualifying_only:
                        line = card.mix_line
                    else:
                        # D-145 (PO): every pitch type — the default scope.
                        line = card.mix_line_all
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
                    styles = dict(metric_styles)
                    if not evaluated:
                        styles["Total"] = _REASON_CSS
                    rows.append((card, texts, styles))
                if rows:
                    # D-145 (PO): the Sluggers layout — each row is its own
                    # one-line table with the More button at its end; the
                    # 22-column st.dataframe could not carry in-row buttons,
                    # so the rows of five under the grid are gone. Header
                    # hovers keep the D-124 definitions as title attributes,
                    # and the cells keep the D-127 band fills inline.
                    columns = list(rows[0][1])
                    stars = _GRID_STARS_SEASON if season_view else _GRID_STARS_WINDOW
                    help_by_header = {
                        stars.get(name, name): text for name, text in _MATCHUPS_HELP.items()
                    }
                    head = st.columns(_GRID_ROW_SPECS, vertical_alignment="center")
                    head[0].markdown(
                        _grid_header_html(columns, help_by_header), unsafe_allow_html=True
                    )
                    for card, texts, styles in rows:
                        cells = st.columns(_GRID_ROW_SPECS, vertical_alignment="center")
                        cells[0].markdown(
                            _grid_row_html(columns, texts, styles), unsafe_allow_html=True
                        )
                        if selected is None and cells[1].button(
                            "More",
                            key=(
                                f"more_{board.official_date}_{game.game_pk}_"
                                f"{label.lower()}_{card.player_id}"
                            ),
                        ):
                            selected = card
    return selected


# v2.2 ratified temperature bands (2026-08-23), mirrored from the weather
# component's config buckets so the Conditions tab can print the edges per
# D-079: <45 → 0 (cold suppression) · 45-64 → 0.25 · 65-74 → 0.5 ·
# 75-84 → 1 · 85-89 → 1.25 · ≥90 humidity-supported → 1.5. The award is
# capped at the component max 1.0 (the PO's 2026-08-24 "cap for now"
# ruling), so the 85+ bands grade 1 — the labels keep the raw band values
# visible with the cap named. The ≥90 band's humidity support has no
# ratified line; it is reported, never resolved.
_TEMP_BANDS: tuple[tuple[Decimal, str, str], ...] = (
    (Decimal("45"), "<45", "0"),
    (Decimal("65"), "45-64", "0.25"),
    (Decimal("75"), "65-74", "0.5"),
    (Decimal("85"), "75-84", "1"),
    (Decimal("90"), "85-89", "1.25"),
    (Decimal("1000"), "≥90", "1.5"),
)


def _temp_band_entry(temp_f: Decimal) -> tuple[str, str]:
    """(edges, raw award) of the v2.2 band one reading lands in."""
    _, edges, raw = next(band for band in _TEMP_BANDS if temp_f < band[0])
    return edges, raw


def _temp_band(temp_f: Decimal) -> str:
    """The v2.2 temperature-band label for one reading — '{edges} → {raw}',
    with the cap named when the raw band exceeds the component max."""
    edges, raw = _temp_band_entry(temp_f)
    return f"{edges} → {raw}" + (" · capped at 1" if Decimal(raw) > 1 else "")


# Wind receptiveness (D-082's parked colour rule, shipped as D-122): the
# Conditions wind cell goes green when the wind in its current direction
# helps the HR environment at a wind-receptive park, red when it hurts,
# and stays neutral when the park barely notices wind or the breeze is
# calm. Neither cut has a ratified number, so the build lines are chosen
# and disclosed: |receptiveness| ≥ 1 (the capture runs -3.2 to 9.2; under
# 1 is the barely-affected band) and ≥ 4 mph resolved along the park axis
# (Ballpark Pal's own calmest speed bucket is 0-3 mph).
_WIND_RECEPTIVE_LINE = Decimal("1")
_WIND_CALM_LINE = Decimal("4")


@lru_cache(maxsize=1)
def _wind_receptiveness() -> dict[str, WindReceptiveness]:
    """The pinned Ballpark Pal receptiveness table, read once per process."""
    return read_receptiveness()


def _wind_effect_css(receptiveness: WindReceptiveness | None, resolved: Decimal | None) -> str:
    """The D-082 wind-cell colour: green when the wind in its current
    direction helps this park's HR environment, red when it hurts, ""
    for neutral. The read is direction-specific — an out-wind judges
    ``recept_out``, an in-wind ``recept_in`` — because the model's signs
    differ by direction at the same park."""
    if receptiveness is None or resolved is None:
        return ""
    directional = receptiveness.recept_out if resolved > 0 else receptiveness.recept_in
    if abs(directional) < _WIND_RECEPTIVE_LINE or abs(resolved) < _WIND_CALM_LINE:
        return ""
    return _HIGHLIGHT if directional > 0 else _VETO_CSS


def _render_conditions(board: SlateBoard) -> None:
    st.caption(
        "Parks and conditions. A park factor carries its plate-appearance "
        "sample beside it (D-014). Temperature bands (v2.2, ratified "
        "2026-08-23): <45°F → 0 (cold suppression) · 45-64 → 0.25 · "
        "65-74 → 0.5 · 75-84 → 1 · 85-89 → 1.25 · ≥90°F humidity-supported "
        "→ 1.5 — the award is capped at the component max 1.0, so the 85+ "
        "bands grade 1 and the raw band values read as labels; the ≥90 "
        "band's humidity support has no ratified line and is not resolved. "
        "Humidity is a secondary modifier, never a standalone badge. Wind "
        "is the raw forecast reading — the resolved assist/kill reads live "
        "on the Sluggers tags. A roofed venue grades at an assumed 72°F — "
        "an assumption, labelled, never a forecast. "
        "Wind receptiveness (Ballpark Pal, model years 2023-2025, captured "
        "2026-08-21 — display only, it never grades): the modelled "
        "HR-effect sensitivity to wind, quoted Overall and read per "
        "direction — the Wind cell goes green when the current wind helps "
        "at a wind-receptive park (receptiveness at or past ±1) and red "
        "when it hurts, only with ≥ 4 mph resolved along the park axis; "
        "under either line it stays neutral. **Cell colors (D-127, PO):** "
        "the factor cells wear six researched bands whose edges ARE the "
        "ratified park lines — "
        + _band_scale_text(_FACTOR_BAND)
        + " — and the Temp band cell wears its award's color, the one "
        "v2.2-ratified color scale on the board: <45 dark red · 45-64 "
        "red · 65-74 light red · 75-84 light green · 85-89 green · ≥90 "
        "dark green. The sample columns carry no color — a count is "
        "volume, not quality."
    )
    text_rows: list[dict[str, str]] = []
    style_rows: list[dict[str, str]] = []
    numeric_columns = ("HR factor (LHB)", "n", "HR factor (RHB)", "n ")
    for game in board.games:
        left = game.home_run_factor_left
        right = game.home_run_factor_right
        roofed = game.venue_type is not VenueType.OPEN_AIR
        receptiveness = _wind_receptiveness().get(game.venue_id)
        values: dict[str, tuple[float | int | None, str]] = {
            "HR factor (LHB)": (float(left.factor) if left else None, "not covered"),
            "n": (left.plate_appearances if left else None, "not covered"),
            "HR factor (RHB)": (float(right.factor) if right else None, "not covered"),
            "n ": (right.plate_appearances if right else None, "not covered"),
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
                # D-127 (PO): the factor cells wear the researched band —
                # its edges are the ratified park lines. The sample
                # columns stay neutral (a count is volume, not quality).
                if column in ("HR factor (LHB)", "HR factor (RHB)"):
                    css = _band_css(_FACTOR_BAND, float(value))
                    if css is not None:
                        styles[column] = css
        # The weather cells (v2.2, D-121): the reading, the band it lands
        # in, and the secondary modifiers. A roof feeds the assumed 72°F —
        # labelled in the cell, never dressed as a forecast; a missing
        # open-air reading names the source gap.
        temp = game.temperature_fahrenheit
        if roofed:
            texts["Temp °F"] = f"{float(ROOFED_VENUE_NEUTRAL_FAHRENHEIT):.0f}°F assumed"
            styles["Temp °F"] = _REASON_CSS
            texts["Temp band"] = _temp_band(ROOFED_VENUE_NEUTRAL_FAHRENHEIT)
            styles["Temp band"] = _REASON_CSS
        elif temp is not None:
            texts["Temp °F"] = f"{float(temp):.0f}"
            texts["Temp band"] = _temp_band(temp)
            # D-127 (PO): the band cell wears its ratified award's color —
            # the six v2.2 temperature bands ARE the six color bands.
            styles["Temp band"] = _TEMP_AWARD_CSS[_temp_band_entry(temp)[1]]
        else:
            texts["Temp °F"] = "source unavailable"
            styles["Temp °F"] = _REASON_CSS
            texts["Temp band"] = "source unavailable"
            styles["Temp band"] = _REASON_CSS
        humidity = game.relative_humidity_percent
        if humidity is not None:
            texts["Humidity"] = f"{float(humidity):.0f}%"
        else:
            texts["Humidity"] = "roofed — not sourced" if roofed else "source unavailable"
            styles["Humidity"] = _REASON_CSS
        wind_speed = game.wind_speed_mph
        if wind_speed is not None:
            direction = game.wind_direction
            texts["Wind"] = (
                f"{float(wind_speed):.0f} mph {direction}"
                if direction
                else f"{float(wind_speed):.0f} mph"
            )
            # D-122's colour rule: the forecast resolved along the park
            # axis, judged by the direction-specific receptiveness.
            axis = game.park_orientation_degrees
            wind_from = game.wind_from_degrees
            resolved = (
                resolved_wind_mph(wind_speed, wind_from, axis)
                if axis is not None and wind_from is not None
                else None
            )
            effect = _wind_effect_css(receptiveness, resolved)
            if effect:
                styles["Wind"] = effect
        else:
            texts["Wind"] = "roofed — not sourced" if roofed else "source unavailable"
            styles["Wind"] = _REASON_CSS
        if receptiveness is not None:
            texts["Wind recept."] = f"{float(receptiveness.recept_overall):.2f}"
        else:
            texts["Wind recept."] = "not covered"
            styles["Wind recept."] = _REASON_CSS
        text_rows.append(texts)
        style_rows.append(styles)
    conditions_frame = pd.DataFrame(text_rows)
    st.dataframe(
        styled_text_frame(conditions_frame, pd.DataFrame(style_rows)),
        hide_index=True,
        column_config=_column_help(conditions_frame.columns, _CONDITIONS_HELP),
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
    # D-112: "today" is the viewer's Arizona day, never the server's UTC day.
    today = slate_today()
    title_col, nav_col = st.columns([3, 2])
    with nav_col:
        chosen = st.date_input(
            "Slate date",
            value=today,
            min_value=today - timedelta(days=30),
            max_value=today + timedelta(days=7),
            key="slate_date_choice",
            help="Slate dates run on Arizona time (MST, UTC-7 year-round).",
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
    # D-128 (PO): the board builds on the Matchups tab's batter window —
    # the selector's session state is read before its widgets render, so a
    # changed window rebuilds on the rerun (a fresh build, then cached).
    # D-150: an unexpected build failure degrades to a named surface with
    # the full traceback — the host's redacted crash page hid the D-149
    # TypeError's real frame for a whole diagnostic round. The tabs already
    # degrade this way (D-075); the build itself now does too. Owner-only
    # app: a traceback names code paths, never secrets.
    try:
        board = live_board(slate_date.isoformat(), _matchups_window_days())
    except Exception:
        blot.empty()
        st.error("The slate board build failed unexpectedly (D-150).")
        st.code(traceback.format_exc())
        # D-150 diagnostics: WHERE the installed package resolves from and
        # what signature it actually carries. D-156: every probe is
        # isolated — the surface itself crashed on the host (a stale
        # bootstrap module missing the constants the probes referenced),
        # which hid the very forensics meant to explain the failure. No
        # single probe may ever take this surface down again.
        import hashlib
        import inspect
        import sys as _sys
        from pathlib import Path as _Path

        import greenmachine.live.pipeline as _pipeline

        module_path = _Path(_pipeline.__file__ or "")
        repo_root = module_path.parents[3] if len(module_path.parents) > 3 else module_path

        def _git(*args: str) -> str:
            ran = subprocess.run(
                ["git", "-C", str(repo_root), *args], capture_output=True, text=True
            )
            return (ran.stdout or ran.stderr or "").strip()

        diag_lines: list[str] = []

        def _probe(label: str, probe: Callable[[], object]) -> None:
            try:
                diag_lines.append(f"{label}: {probe()}")
            except Exception as probe_error:
                diag_lines.append(f"{label}: <probe failed: {probe_error!r}>")

        _probe("pipeline module file", lambda: module_path)
        _probe(
            "build_board parameters",
            lambda: sorted(inspect.signature(_pipeline.build_board).parameters),
        )
        _probe(
            "working-file sha256",
            lambda: hashlib.sha256(module_path.read_bytes()).hexdigest()[:16],
        )
        _probe(
            "HEAD blob sha256",
            lambda: hashlib.sha256(
                subprocess.run(
                    ["git", "-C", str(repo_root), "show", "HEAD:src/greenmachine/live/pipeline.py"],
                    capture_output=True,
                ).stdout
            ).hexdigest()[:16],
        )
        _probe("git HEAD", lambda: _git("rev-parse", "--short", "HEAD"))
        _probe("git status", lambda: _git("status", "--porcelain")[:600] or "clean")
        _probe(
            "git log pipeline.py",
            lambda: _git("log", "--oneline", "-3", "--", "src/greenmachine/live/pipeline.py"),
        )
        # D-156: the bytecode layer's full state, every piece named. The
        # host precompiles bytecode under PYTHONPYCACHEPREFIX (root-owned,
        # surviving git syncs and env rebuilds); these probes exist so a
        # stale serve names its own layer on the crash page.
        _probe("pycache prefix (effective)", lambda: _sys.pycache_prefix)
        _probe("PYTHONPYCACHEPREFIX (env)", lambda: os.environ.get("PYTHONPYCACHEPREFIX"))
        _probe("pre-loaded before entrypoint ran", lambda: _PRELOADED_OURS or "none")
        # D-158/D-159: module-identity postmortem. The PicklingError that
        # surfaced after D-157 ("not the same object as ...PitchArsenalRow")
        # means two module objects existed for one dotted name; if it ever
        # recurs, these probes name both objects and the guard's state.
        _probe(
            "eviction epoch (process vs expected)",
            lambda: f"{getattr(_sys, '_gm_eviction_epoch', '<unset>')} vs {_EXPECTED_DEPLOY_EPOCH}",
        )
        _probe(
            "cache clear pending",
            lambda: getattr(_sys, "_gm_cache_clear_pending", False),
        )

        def _savant_identity() -> str:
            client = live_mlb_adapters()[1]
            method_globals = client.fetch_pitch_arsenal.__func__.__globals__
            built_with = method_globals.get("PitchArsenalRow")
            current = getattr(_sys.modules.get("greenmachine.live.savant"), "PitchArsenalRow", None)
            return (
                f"client builds rows with id={id(built_with)}, sys.modules holds "
                f"id={id(current)}, same={built_with is current}"
            )

        _probe("savant row-class identity", _savant_identity)
        _probe("modules named *savant*", lambda: sorted(n for n in _sys.modules if "savant" in n))
        _probe("bootstrap module file", lambda: getattr(_deploy_bootstrap, "__file__", "?"))
        _probe("bootstrap module cached", lambda: getattr(_deploy_bootstrap, "__cached__", "?"))
        _probe("pipeline module cached", lambda: getattr(_pipeline, "__cached__", "?"))
        _probe(
            "cache_from_source (computed now)",
            lambda: importlib.util.cache_from_source(str(module_path)),
        )

        def _startup_actors() -> str:
            import site

            pieces = [
                f"sitecustomize={getattr(_sys.modules.get('sitecustomize'), '__file__', None)}",
                f"usercustomize={getattr(_sys.modules.get('usercustomize'), '__file__', None)}",
            ]
            for base in site.getsitepackages():
                for pth in sorted(_Path(base).glob("*.pth")):
                    text = pth.read_text(encoding="utf-8", errors="replace").strip()
                    pieces.append(f"{pth.name}: {text[:150]!r}")
            return " | ".join(pieces)

        _probe("startup actors (.pth/customize)", _startup_actors)
        _probe("sys.path", lambda: " | ".join(_sys.path))
        _probe(
            "bootstrap sweep",
            lambda: (
                "removed "
                f"{getattr(_deploy_bootstrap, 'SWEPT_COUNT', '<missing>')}, leftover "
                f"{getattr(_deploy_bootstrap, 'LEFTOVER_CACHES', '<missing>')}"
            ),
        )

        def _pyc_header() -> str:
            cache_tag = _sys.implementation.cache_tag
            pyc = module_path.parent / "__pycache__" / f"{module_path.stem}.{cache_tag}.pyc"
            if not pyc.is_file():
                return "no bytecode file beside the source"
            header = pyc.read_bytes()[:16]
            flags = int.from_bytes(header[4:8], "little")
            mode = (
                f"hash-based ({'checked' if flags & 0b10 else 'UNCHECKED'})"
                if flags & 0b1
                else "timestamp"
            )
            stat = pyc.stat()
            return (
                f"{pyc.name} — {mode}, header {header.hex()}, "
                f"owner-writable={bool(stat.st_mode & 0o200)}, "
                f"mtime={datetime.fromtimestamp(stat.st_mtime, UTC):%Y-%m-%d %H:%M}"
            )

        _probe("bytecode beside source", _pyc_header)
        st.code("\n".join(diag_lines))
        return
    blot.empty()
    if isinstance(board, FetchFailure):
        st.warning(f"The {slate_date.isoformat()} schedule could not be fetched: {board.reason}")
        return
    st.caption(
        f"Slate of {board.official_date}, assembled {board.as_of:%H:%M UTC}. "
        f"{len(board.games)} game(s). Board refreshes every "
        f"{BOARD_TTL_SECONDS // 60} minutes; form windows hourly; the season "
        "sources refresh each morning (5 AM Eastern) — a future date loads "
        "on request (D-136/D-139)."
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
    snapshot — real values, digest-verified on read, with the acquisition date
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
        "it — the pinned snapshot spans 6,995 to 21,365 PA, so two factors are "
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


def _absent_weather(venue: ParkVenue, at: datetime) -> None:
    """The backtest's weather binding (D-095): weather is not reconstructed
    for a past slate, so every conditions read is absent — two arguments
    because D-131's game-time readers receive first pitch even here, where
    the answer is always the same named absence (D-135)."""
    return None


@st.cache_data(ttl=DAY_EVENTS_TTL_SECONDS, show_spinner=False)
def _backtest_board(slate_iso: str) -> SlateBoard | FetchFailure:
    """Regrade a past slate as of the prior evening (D-095). Weather is not
    reconstructed: temperature and wind bind as absent, and the affected
    components name that absence like any other."""
    api, savant = live_mlb_adapters()
    slate_date = date.fromisoformat(slate_iso)
    year = slate_date.year
    # D-136: a past slate's season sources are the same overnight-updated
    # boards the live build reads — the day-anchored proxies serve a
    # backtest range without refetching each day of it.
    anchor = _season_data_anchor(datetime.now(UTC))

    def fetch_day(day: date) -> object:
        return _day_events(day.isoformat(), year, anchor)

    return build_board(
        api=_DayAnchoredMlbApi(api, anchor),  # type: ignore[arg-type]
        savant=_DayAnchoredSavant(savant, anchor),  # type: ignore[arg-type]
        slate_date=slate_date,
        as_of=slate_as_of(slate_date),
        config=production_config(),
        fetch_day_events=fetch_day,  # type: ignore[arg-type]
        temperature_for=_absent_weather,  # type: ignore[arg-type]
        park_factors=park_factor_table(),
        wind_for=_absent_weather,  # type: ignore[arg-type]
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
    # D-112: the backtest's "last N days" counts back from the viewer's
    # Arizona day too, so an evening run never skips a finished slate.
    dates = [slate_today() - timedelta(days=d) for d in range(1, days + 1)]
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


@st.cache_data(show_spinner=False)
def _glossary_markdown() -> str:
    """D-117: the glossary lives in GLOSSARY.md next to this app so the
    plain-language wording can be revised without touching code. A missing
    file is a named absence, not a crash."""
    try:
        return (Path(__file__).resolve().parent / "GLOSSARY.md").read_text(encoding="utf-8")
    except OSError:
        return "The glossary file is not available in this deployment."


# D-117: every metric already states its own math on its surface (D-079); the
# glossary answers the next question — what the metric means and why it
# matters — from the "?" button beside Backtest (the PO's "back text").
@st.dialog("Glossary", width="large")
def _render_glossary() -> None:
    st.markdown(_glossary_markdown())


def main() -> None:
    # D-159: an eviction at the entrypoint invalidates every cached object
    # built from the old module set — clear both caches once, before
    # anything reads them (st is imported by the time main runs).
    if getattr(sys, "_gm_cache_clear_pending", False):
        sys._gm_cache_clear_pending = False  # type: ignore[attr-defined]
        st.cache_data.clear()
        st.cache_resource.clear()
    st.set_page_config(page_title="GreenMachine", layout="wide")
    bridge_secrets_into_environment()
    st.markdown(SHELL_CSS, unsafe_allow_html=True)
    st.markdown(DIAL_CSS, unsafe_allow_html=True)
    st.markdown(BLOT_CSS, unsafe_allow_html=True)
    st.markdown(FIELD_CSS, unsafe_allow_html=True)
    orb, header, action = st.columns([1, 5, 1.4])
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
        view_button, glossary_button = st.columns([4, 1])
        with view_button:
            if st.session_state.get("view") == "backtest":
                if st.button("← Board", key="view_board"):
                    st.session_state["view"] = "board"
                    st.rerun()
            elif st.button("Backtest", key="view_backtest"):
                st.session_state["view"] = "backtest"
                st.rerun()
        # D-117: the glossary sits beside the view button on both views — the
        # "?" opens the plain-language metric glossary in a dialog.
        with glossary_button:
            if st.button(
                "?",
                key="open_glossary",
                help="Glossary — every metric in plain terms",
            ):
                _render_glossary()
    if st.session_state.get("view") == "backtest":
        _render_backtest()
    else:
        render_live_board()


if __name__ == "__main__":
    main()
