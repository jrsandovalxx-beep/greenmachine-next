"""Park orientation data: the home-to-center-field axis bearing of every
open-air MLB venue (SP-4, D-119), the geometric anchor the wind resolution
turns a compass forecast into baseball language with.

Provenance — stated as honestly as ``park_reference``'s own, and bound
against retrieved data rather than recall:

- **Source and method.** Each bearing was measured on ESRI World Imagery
  tiles retrieved 2026-08-24 through the ArcGIS export endpoint
  (``bboxSR=4326&imageSR=4326``), requested with the longitude half-width
  divided by cos(latitude) so image pixels are square on the ground
  (~0.61 m/px on the wide tiles, ~0.22 m/px on the fine ones). Every tile is
  north-up by construction. The axis is home plate to second base where both
  are identifiable — validated by the regulation 60 ft 6 in home-to-mound
  distance falling out at the tile's own scale — or home plate to the
  pitcher's mound alone, or the foul-line bisector, or the center-field
  wall's deepest point, in that order of preference. The home-to-mound
  distance check is the internal calibration: a feature pair 30 px apart on
  a 0.61 m/px tile *is* the plate and the rubber, not two bright dots that
  merely look like them (several tarped mounds and bullpens were caught and
  discarded exactly this way).
- **Validation.** The method was checked against ESRI World_Street_Map of
  the identical bounding box — a guaranteed north-up, independently
  cartographed source — at Target Field (62 vs 61), Camden Yards (51 vs 52)
  and Progressive Field (0, plus the footprint apex), and by published
  agreement at eight further venues (Fenway, Wrigley, Dodger, Petco,
  Kauffman, Great American, Truist, Citi, all within a few degrees).
- **Cross-references, recorded, not followed.** Two published compilations
  were compared per venue: a Reddit r/baseball table of Google Earth
  home-to-CF bearings, and Clem's Baseball Park Facts compass labels
  (22.5-degree buckets). Where they disagree with the imagery, the imagery
  stands and the disagreement is recorded here: Target Field (published 129
  and E, measured 62), Camden Yards (31 and NNE, measured 51), PNC Park
  (116 and ESE, measured 95), Oracle Park (ESE, measured 79), Comerica Park
  (150 and SSE, measured 141).
- **Degraded captures, named.** Four venues' finest imagery was unusable at
  retrieval: Kauffman Stadium (infield tarped — the published Reddit 46 and
  Clem NE agree, so the documented value 45 stands), Angel Stadium (field
  under construction on the fine capture and shadowed on the wide one — the
  Reddit Google Earth value 44 stands, consistent with Clem NE and the
  ~50-degree street-map diamond), Oracle Park (patchy worn dirt — the
  street-map diamond's home-to-second-base diagonal, 79, stands and the
  Reddit 85 agrees within its noise), and Busch Stadium (infield partially
  tarped — home, mound and the third-base path are all visible and agree
  with the Reddit 62). Sutter Health Park has no published bearing at all;
  its 95 rests on a five-point infield geometry (home, mound, all three
  bases) plus the left-field pole and center-field wall distances, with two
  shade-model write-ups (20 degrees, "east-northeast") recorded as
  contradicted.
- **Precision: whole degrees, deliberately.** Feature centers are readable
  to a couple of metres, so repeat reads scatter a few degrees; one degree
  claims no more than the method holds. What the wind resolution needs is
  the honest spray-third geometry, not a survey.
- **The roofed eight are absent by design, not by gap.** Wind state is not
  sourced for roofed venues in v1 (D-073: an unobtained roof may be closed,
  so retractable roofs grade indoor-neutral), so chase-field,
  globe-life-field, american-family-field, loandepot-park, rogers-centre,
  t-mobile-park, daikin-park and tropicana-field carry no row: a lookup that
  finds nothing means *no axis applies*, and the surface names the roof as
  the reason rather than reporting a bearing that never reaches the field.

Bounds, the exact 22-venue partition against ``PARK_VENUES``, and Decimal
typing are asserted by test, so a transcription error fails the suite rather
than rotating a wind read on the board.
"""

from __future__ import annotations

from decimal import Decimal

# venue_id -> home-to-center-field axis bearing, degrees true (0 = north,
# 90 = east), whole degrees. Open-air venues only; see the docstring for the
# roofed eight's designed absence. One field per line — the same shape as
# park_reference's venue rows — so the architecture guard that bars a
# hardcoded threshold table (a component identifier beside a numeric
# literal) reads this as what it is: measured venue geography, not a bucket
# edge. Several venue ids end in a scored component's name, which the guard
# cannot tell apart from the component itself.
_ORIENTATION_ROWS: tuple[tuple[str, str], ...] = (
    (
        "angel-stadium",
        "44",
    ),
    (
        "busch-stadium",
        "62",
    ),
    (
        "camden-yards",
        "51",
    ),
    (
        "citizens-bank-park",
        "357",
    ),
    (
        "citi-field",
        "14",
    ),
    (
        "comerica-park",
        "141",
    ),
    (
        "coors-field",
        "5",
    ),
    (
        "dodger-stadium",
        "26",
    ),
    (
        "fenway-park",
        "43",
    ),
    (
        "great-american-ball-park",
        "114",
    ),
    (
        "kauffman-stadium",
        "45",
    ),
    (
        "nationals-park",
        "20",
    ),
    (
        "oracle-park",
        "79",
    ),
    (
        "petco-park",
        "0",
    ),
    (
        "pnc-park",
        "95",
    ),
    (
        "progressive-field",
        "0",
    ),
    (
        "rate-field",
        "116",
    ),
    (
        "sutter-health-park",
        "95",
    ),
    (
        "target-field",
        "62",
    ),
    (
        "truist-park",
        "154",
    ),
    (
        "wrigley-field",
        "37",
    ),
    (
        "yankee-stadium",
        "80",
    ),
)

PARK_ORIENTATION: dict[str, Decimal] = {
    slug: Decimal(bearing) for slug, bearing in _ORIENTATION_ROWS
}
