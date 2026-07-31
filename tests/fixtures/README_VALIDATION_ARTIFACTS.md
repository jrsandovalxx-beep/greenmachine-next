# Validation artifacts — the OQ-4 marker

The fixture trees under this directory carry baked `SampleStatus` values computed from
**validation-only minimums** (2 for `RECENT_7D`, 13 for `LONG_TERM_2Y`). Per the OQ-4
ruling (D-030): **the baked statuses are validation artifacts, never baseball
judgments.** The minimums exist so the suite can exercise sufficiency logic
deterministically; they are baked into archived snapshot content and therefore into
snapshot identity (D-014's recorded trap). They must not be read as, or carried
forward into, approved baseball thresholds — real sample floors are Product Owner
rulings recorded in D-023, D-025 and D-026.

The synthetic configuration fixture keeps its own YAML header stating that its numbers
are deliberately wrong (OQ-2): it transplants as a **test fixture, never
configuration**.

Fixture bytes are pinned by `docs/PORT_MANIFEST.md` and are byte-identical to tag
`legacy-v0.2`. This marker is deliberately its own file so that no fixture byte
changes (GMR-003 scope, D-030).
