# Ballpark Pal park factors — reference capture (parked wind/conditions work)

**Status: reference material only — NOT a ratified source.** Captured from a PO-provided
printout of https://www.ballparkpal.com/Park-Factors-General.php on 2026-08-21
(model years 2023-2025, adjusted for yearly ball changes). Using any of these values in
grading or on a screen requires a DECISIONS.md entry and a SourceRecord first.

Parked features this feeds (PO direction, 2026-08-21):

- Conditions tab: wind shown in baseball terms (blowing out/in, toward which field),
  not raw compass text — needs park orientation mapping (v2 park-orientation memo).
- Wind receptiveness colour coding: GREEN = wind-receptive park + wind blowing out;
  RED = wind-receptive park + wind blowing in; NEUTRAL = park barely affected by wind.
- A detailed per-park view under the Conditions tab including **Contact Rate**
  (and its sibling traits below).

Column notes: factors are percent-style indices (100 = neutral). Wind direction
frequencies are the share of games with wind toward each bearing as printed on the
site (arrow-to-field-direction legend to be confirmed against the site when the
feature is built). Receptiveness is Ballpark Pal's modelled HR-effect sensitivity
to wind In / Out / Overall. Typical Carry is the model's carry adjustment.

## Traits (per park)

| Team | Stadium | HR factor | Altitude (ft) | Outfield | Contact Rate | Contact Quality | Wind Recept. | Variation | Typical Carry |
|---|---|---|---|---|---|---|---|---|---|
| ATL | Truist Park | 96 | 1,050 | Medium | Poor | Great | 2.00 | 0.90 | -0.44% |
| WAS | Nationals Park | 105 | 25 | Medium | Great | Great | 3.11 | 0.98 | -0.64% |
| PHI | Citizens Bank Park | 113 | 9 | Small | Bad | Great | 5.41 | 1.83 | -1.17% |
| TEX | Globe Life Field | 97 | 616 | Medium | Avg | Great | 2.13 | 0.40 | -1.18% |
| LAD | Dodger Stadium | 118 | 267 | Medium | Avg | Great | 2.88 | 0.87 | -1.49% |
| NYY | Yankee Stadium | 108 | 54 | Variable | Avg | Great | 5.43 | 1.95 | -1.50% |
| BOS | Fenway Park | 94 | 20 | Variable | Good | Great | 5.78 | 1.84 | -1.55% |
| KC | Kauffman Stadium | 110 | 750 | X-Large | Great | Good | 2.64 | 1.21 | 0.23% |
| LAA | Angel Stadium | 107 | 160 | Small | Avg | Good | 0.96 | 0.79 | -0.48% |
| MIN | Target Field | 94 | 812 | Medium | Avg | Good | 1.51 | 0.98 | -0.53% |
| BAL | Oriole Park | 98 | 130 | Variable | Great | Good | 3.02 | 1.41 | -0.69% |
| MIL | American Family Fld | 105 | 593 | Medium | Poor | Good | -0.04 | 0.67 | -1.01% |
| TOR | Rogers Centre | 102 | 247 | Medium | Great | Good | -2.39 | 0.81 | -1.67% |
| COL | Coors Field | 116 | 5,183 | X-Large | Great | Avg | 2.63 | 1.36 | 3.75% |
| CIN | Great American BP | 122 | 683 | Small | Bad | Avg | 1.27 | 0.88 | -0.49% |
| STL | Busch Stadium | 88 | 455 | Large | Good | Avg | 3.91 | 1.25 | -0.77% |
| ATH | Sutter Health Park | 120 | 26 | Large | Good | Avg | 3.53 | 1.00 | -0.95% |
| CHW | Rate Field | 100 | 596 | Small | Bad | Avg | 0.90 | 1.18 | -1.06% |
| MIA | LoanDepot Park | 88 | 15 | Large | Good | Avg | 2.06 | 0.30 | -1.07% |
| DET | Comerica Park | 90 | 596 | Large | Avg | Avg | 5.05 | 1.31 | -1.54% |
| SD | Petco Park | 99 | 13 | Medium | Avg | Avg | 2.32 | 1.00 | -1.77% |
| ARI | Chase Field | 92 | 1,082 | Large | Great | Bad | 1.28 | 0.48 | 0.68% |
| PIT | PNC Park | 86 | 743 | Variable | Good | Bad | 3.32 | 1.01 | -0.73% |
| CHC | Wrigley Field | 101 | 596 | Medium | Poor | Bad | 9.15 | 2.67 | -1.85% |
| SEA | T-Mobile Park | 100 | 10 | Small | Poor | Bad | 3.67 | 0.88 | -2.15% |
| TB | Tropicana Field | 97 | 44 | Medium | Poor | Poor | 1.85 | 0.03 | -0.53% |
| CLE | Progressive Field | 98 | 582 | Small | Avg | Poor | 3.22 | 1.51 | -0.77% |
| NYM | Citi Field | 96 | 54 | Medium | Poor | Poor | -0.27 | 1.37 | -1.21% |
| HOU | Daikin Park | 108 | 38 | Variable | Bad | Poor | -1.38 | 0.50 | -1.68% |
| SF | Oracle Park | 84 | 63 | Variable | Good | Poor | 0.90 | 0.81 | -2.30% |

## Wind (frequency = share of games; receptiveness = modelled HR effect)

| Team | Stadium | Avg speed (mph) | Wind In % | Wind Out % | Sideways % | Recept. In | Recept. Out | Recept. Overall |
|---|---|---|---|---|---|---|---|---|
| ATL | Truist Park | 7.1 | 38% | 39% | 23% | -0.62 | 2.61 | 2.00 |
| WAS | Nationals Park | 6.6 | 27% | 44% | 30% | 1.19 | 1.92 | 3.11 |
| PHI | Citizens Bank Park | 7.9 | 22% | 47% | 30% | 4.08 | 1.33 | 5.41 |
| TEX | Globe Life Field | 9.0 | 34% | 31% | 34% | 0.79 | 1.34 | 2.13 |
| LAD | Dodger Stadium | 8.4 | 0% | 99% | 1% | 3.19 | -0.32 | 2.88 |
| NYY | Yankee Stadium | 9.2 | 20% | 44% | 35% | 3.90 | 1.53 | 5.43 |
| BOS | Fenway Park | 7.5 | 24% | 52% | 24% | 1.20 | 4.58 | 5.78 |
| KC | Kauffman Stadium | 9.5 | 31% | 48% | 21% | 1.99 | 0.65 | 2.64 |
| LAA | Angel Stadium | 7.3 | 0% | 98% | 2% | 3.32 | -2.36 | 0.96 |
| MIN | Target Field | 9.1 | 35% | 39% | 26% | -0.11 | 1.62 | 1.51 |
| BAL | Oriole Park | 7.3 | 26% | 45% | 29% | 0.62 | 2.40 | 3.02 |
| MIL | American Family Fld | 8.5 | 46% | 26% | 28% | -0.55 | 0.50 | -0.04 |
| TOR | Rogers Centre | 8.1 | 32% | 48% | 20% | -1.37 | -1.02 | -2.39 |
| COL | Coors Field | 7.6 | 39% | 28% | 33% | 1.81 | 0.82 | 2.63 |
| CIN | Great American BP | 6.9 | 19% | 43% | 38% | 2.87 | -1.60 | 1.27 |
| STL | Busch Stadium | 8.7 | 33% | 38% | 29% | 1.28 | 2.63 | 3.91 |
| ATH | Sutter Health Park | 11.1 | 1% | 92% | 6% | 2.52 | 1.01 | 3.53 |
| CHW | Rate Field | 9.5 | 37% | 26% | 37% | -0.38 | 1.27 | 0.90 |
| MIA | LoanDepot Park | 11.6 | 86% | 5% | 10% | 2.01 | 0.04 | 2.06 |
| DET | Comerica Park | 9.1 | 37% | 28% | 35% | 4.69 | 0.36 | 5.05 |
| SD | Petco Park | 9.0 | 15% | 24% | 61% | 1.64 | 0.68 | 2.32 |
| ARI | Chase Field | 7.0 | 7% | 52% | 40% | 1.09 | 0.19 | 1.28 |
| PIT | PNC Park | 6.4 | 19% | 58% | 23% | 2.48 | 0.84 | 3.32 |
| CHC | Wrigley Field | 9.7 | 50% | 34% | 16% | 4.72 | 4.43 | 9.15 |
| SEA | T-Mobile Park | 5.2 | 32% | 40% | 28% | 1.35 | 2.32 | 3.67 |
| TB | Tropicana Field | - | - | - | - | 1.39 | 0.45 | 1.85 |
| CLE | Progressive Field | 8.4 | 43% | 32% | 25% | 2.47 | 0.75 | 3.22 |
| NYM | Citi Field | 9.6 | 22% | 55% | 23% | -0.43 | 0.16 | -0.27 |
| HOU | Daikin Park | 11.3 | 32% | 61% | 7% | -3.21 | 1.83 | -1.38 |
| SF | Oracle Park | 9.8 | 1% | 98% | 1% | 0.82 | 0.08 | 0.90 |

## Air (game-time averages)

| Team | Stadium | Avg temp (°F) | Avg pressure (mb) | Avg humidity (%) |
|---|---|---|---|---|
| ATL | Truist Park | 82.0 | 1015 | 50.1 |
| WAS | Nationals Park | 78.0 | 1015 | 55.0 |
| PHI | Citizens Bank Park | 76.6 | 1015 | 54.6 |
| TEX | Globe Life Field | 80.8 | 1013 | 41.7 |
| LAD | Dodger Stadium | 77.8 | 1012 | 46.7 |
| NYY | Yankee Stadium | 73.7 | 1015 | 55.7 |
| BOS | Fenway Park | 69.8 | 1015 | 59.8 |
| KC | Kauffman Stadium | 78.5 | 1014 | 55.9 |
| LAA | Angel Stadium | 76.6 | 1013 | 50.8 |
| MIN | Target Field | 72.8 | 1014 | 53.4 |
| BAL | Oriole Park | 76.0 | 1015 | 59.1 |
| MIL | American Family Fld | 76.4 | 1015 | 60.1 |
| TOR | Rogers Centre | 73.4 | 1015 | 59.0 |
| COL | Coors Field | 75.2 | 1012 | 28.4 |
| CIN | Great American BP | 76.2 | 1015 | 61.2 |
| STL | Busch Stadium | 79.4 | 1014 | 57.9 |
| ATH | Sutter Health Park | 80.7 | 1012 | 40.0 |
| CHW | Rate Field | 70.0 | 1015 | 62.9 |
| MIA | LoanDepot Park | 80.5 | 1017 | 58.5 |
| DET | Comerica Park | 71.9 | 1015 | 55.8 |
| SD | Petco Park | 72.2 | 1013 | 62.1 |
| ARI | Chase Field | 88.5 | 1010 | 15.0 |
| PIT | PNC Park | 73.8 | 1015 | 57.9 |
| CHC | Wrigley Field | 69.9 | 1015 | 62.5 |
| SEA | T-Mobile Park | 71.0 | 1016 | 51.3 |
| TB | Tropicana Field | - | - | - |
| CLE | Progressive Field | 70.2 | 1016 | 65.4 |
| NYM | Citi Field | 73.4 | 1015 | 57.0 |
| HOU | Daikin Park | 80.2 | 1015 | 48.3 |
| SF | Oracle Park | 66.4 | 1014 | 64.5 |

## Outcome factors (100 = neutral)

| Team | Stadium | Runs | Hits | HR | XBH | 1B | K | BB |
|---|---|---|---|---|---|---|---|---|
| ATL | Truist Park | 93 | 98 | 96 | 94 | 99 | 102 | 98 |
| WAS | Nationals Park | 104 | 103 | 105 | 103 | 102 | 98 | 96 |
| PHI | Citizens Bank Park | 103 | 100 | 113 | 97 | 99 | 105 | 101 |
| TEX | Globe Life Field | 95 | 97 | 97 | 92 | 99 | 102 | 101 |
| LAD | Dodger Stadium | 100 | 99 | 118 | 98 | 96 | 103 | 93 |
| NYY | Yankee Stadium | 97 | 96 | 108 | 88 | 96 | 102 | 105 |
| BOS | Fenway Park | 112 | 108 | 94 | 121 | 106 | 94 | 100 |
| KC | Kauffman Stadium | 107 | 101 | 110 | 100 | 100 | 91 | 102 |
| LAA | Angel Stadium | 99 | 100 | 107 | 93 | 100 | 104 | 99 |
| MIN | Target Field | 103 | 101 | 94 | 102 | 103 | 98 | 104 |
| BAL | Oriole Park | 109 | 106 | 98 | 107 | 108 | 96 | 98 |
| MIL | American Family Fld | 90 | 93 | 105 | 87 | 92 | 109 | 103 |
| TOR | Rogers Centre | 97 | 98 | 102 | 96 | 99 | 99 | 96 |
| COL | Coors Field | 132 | 114 | 116 | 128 | 110 | 89 | 102 |
| CIN | Great American BP | 110 | 102 | 122 | 102 | 98 | 105 | 105 |
| STL | Busch Stadium | 95 | 100 | 88 | 98 | 103 | 95 | 94 |
| ATH | Sutter Health Park | 115 | 106 | 120 | 115 | 100 | 100 | 101 |
| CHW | Rate Field | 97 | 98 | 100 | 91 | 100 | 101 | 102 |
| MIA | LoanDepot Park | 99 | 100 | 88 | 107 | 101 | 100 | 102 |
| DET | Comerica Park | 99 | 100 | 90 | 99 | 102 | 94 | 101 |
| SD | Petco Park | 97 | 98 | 99 | 93 | 99 | 103 | 104 |
| ARI | Chase Field | 102 | 102 | 92 | 113 | 101 | 98 | 98 |
| PIT | PNC Park | 100 | 100 | 86 | 112 | 99 | 93 | 103 |
| CHC | Wrigley Field | 96 | 97 | 101 | 92 | 98 | 101 | 104 |
| SEA | T-Mobile Park | 87 | 93 | 100 | 84 | 94 | 111 | 100 |
| TB | Tropicana Field | 93 | 96 | 97 | 96 | 96 | 108 | 102 |
| CLE | Progressive Field | 97 | 97 | 98 | 99 | 96 | 101 | 103 |
| NYM | Citi Field | 91 | 94 | 96 | 85 | 97 | 107 | 105 |
| HOU | Daikin Park | 97 | 99 | 108 | 92 | 99 | 105 | 99 |
| SF | Oracle Park | 97 | 102 | 84 | 109 | 103 | 97 | 95 |
