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

**The parks screen carries two provenances and says so.** Its factor columns
render the pinned Savant manual export with its export date; its roof and
forecast columns are fixture-bound until §GMF-005 binds a live adapter behind
the same seam. Real and fixture data share a table here, which is exactly why
neither is left to be inferred.

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
from importlib import metadata
from pathlib import Path

import streamlit as st

from greenmachine.fixtures import grid_demo_snapshot, parks_demo_snapshot
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
    visible_columns,
)
from greenmachine.inputs import InputSnapshot, Window
from greenmachine.inputs.savant_park_factors import basis_statement
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


def render_shell_fields() -> None:
    """The GMR-004 deployment-verification fields, unchanged in substance."""
    st.markdown(f"**Environment:** {resolve_environment()}")
    st.markdown(f"**Version:** {resolve_version()}")
    st.markdown(f"**Commit:** {resolve_commit()}")


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
    snapshot = parks_demo_snapshot()
    screen = park_frames(snapshot)
    st.subheader("Parks")
    st.caption(
        f"{basis_statement()} A factor shows its plate-appearance sample beside "
        "it — the pinned export spans 13,560 to 31,517 PA, so two factors are "
        "not equally well evidenced (D-014). Initial order is neutral — the "
        "venue's own name — and every ordering is yours to apply in the headers."
    )
    st.caption(
        "Roof state and forecast are **fixture-bound** in this ticket: the weather "
        "seam is one adapter interface with a fixture behind it, and the live NWS "
        "adapter arrives at §GMF-005. Their values are deliberately non-baseball "
        "(OQ-4). Park factors above are the real pinned export; conditions here are not."
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
    st.title("GreenMachine")
    st.caption(
        "Product surfaces per FEATURE_PHASE_PLAN §GMF-002, §GMF-003 and §GMF-004 — "
        "batter data is synthetic fixture (OQ-4), park factors are the pinned "
        "Savant manual export, and conditions are fixture-bound until §GMF-005; "
        "criteria tallies, never predictions (D-015/D-017)."
    )
    render_shell_fields()
    st.divider()
    render_grid()
    st.divider()
    render_metrics_screen(grid_demo_snapshot())
    st.divider()
    render_parks_screen()


if __name__ == "__main__":
    main()
