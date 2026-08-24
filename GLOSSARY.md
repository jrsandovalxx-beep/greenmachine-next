# GreenMachine Glossary — Refined v2.1

Every metric the app shows or tracks, in plain terms. Each entry gives a tight definition, then **why it matters for home runs**. Written for someone who watches baseball but has never opened a stats page.

---

## How to read the app first (house terms)

**BBE (batted-ball event)** — A tracked batted ball that produces a result. Home runs count.  
*Why it matters:* Most of our power stats are “per batted ball,” so BBE is the sample size that tells you how much weight to give the rate.

**PA (plate appearance) / BF (batters faced)** — Every trip to the plate, walks included. BF is the same thing from the pitcher’s side.  
*Why it matters:* More trips = more chances to go deep. Opportunity stats live and die on PA.

**INSUFFICIENT** — The app shows the number anyway, but stamps it because the sample is below the agreed floor.  
*Why it matters:* A hot week can lie. The stamp is your reminder that 12 swings don’t mean what 400 do.

**Season / L30 / L14 / L7** — The time window a number covers: full season, last 30 days, last 14, last 7.  
*Why it matters:* Season gives the baseline; L30/L14/L7 show recent form. The shorter the window, the noisier the signal — which is why the app keeps the sample size and INSUFFICIENT state visible.

**vs LHB / vs RHB** — The pitcher’s numbers split by whether the batter hits lefty or righty.  
*Why it matters:* Most pitchers are much easier on one side. Facing the soft side is one of the biggest HR levers that exists.

---

## 1. Batter power metrics

**Barrel / Barrel%** — A batted ball with the ideal combination of exit velocity and launch angle. It requires at least 98 mph exit velocity; the acceptable launch-angle window starts narrow (around 26–30°) and widens as exit velocity rises. Barrel% = barrels per batted ball.  
*Why it matters:* Barrels are the contact type most closely tied to extra-base damage and home runs. League context moves by season, but roughly 8% is ordinary MLB territory; 10%+ is strong and 15%+ is elite power territory.

**Exit velocity (avg EV)** — Average speed of the ball off the bat, in mph.  
*Why it matters:* Harder contact gives the ball more margin to clear the wall. League average sits near 89 mph; 91+ is strong power territory. Very low average EV is a real warning, even when the launch-angle profile looks good.

**EV90 / Max EV** — EV90 is the average of a hitter’s hardest 10% of contact; Max EV is the single hardest ball he’s hit.  
*Why it matters:* Average EV blends routine contact with damage. EV90 and Max EV isolate the top-end thump and tell us whether real raw power exists even when the overall average is modest.

**Hard-Hit%** — Share of batted balls hit 95+ mph.  
*Why it matters:* 95 mph is Statcast’s hard-hit threshold. League context usually sits in the high-30% to low-40% range; 45%+ is strong. But hard contact without useful launch angles can still turn into ground-ball outs.

**Launch angle (LA)** — Vertical angle the ball leaves the bat. 0° is a line at the pitcher’s head, negative is into the ground, 45°+ is a popup.  
*Why it matters:* Almost every homer is hit between roughly 18° and 40°. A 100 mph grounder is an out. Hard contact without lift is the #1 way people talk themselves into bad HR picks.

**The 18° HR floor** — A GreenMachine rule of thumb: ordinary over-the-fence home-run contact usually starts around the high teens in launch angle. Homers below ~18° are rare and require exceptional exit velocity.  
*Why it matters:* Don’t judge a hitter only by *average* launch angle. What matters more is how often he reaches homer-friendly angles with real exit velocity.

**Sweet-Spot%** — Share of batted balls launched between 8° and 32°.  
*Why it matters:* It’s Statcast’s productive launch-angle band, covering many line drives and damage-producing fly balls. Think of it as how often the swing creates an angle that *can* produce damage; it still needs enough exit velocity.

**Attack angle / Ideal Attack Angle% (IAA)** — Attack angle is the vertical path of the bat itself at the moment of contact (or the point where bat and ball paths cross). Statcast’s ideal band is 5–20°. IAA% = share of competitive swings in that band.  
*Why it matters:* This is the swing’s built-in lift. A hitter who repeatedly enters the ideal attack-angle band has a more repeatable path to useful launch angles than one relying on occasional lifted contact.

**Bat speed** — How fast the barrel moves, in mph. Statcast treats 75+ mph as a fast swing.  
*Why it matters:* Bat speed is one of the engines behind exit velocity. Higher bat speed gives a hitter more raw power ceiling; lower bat speed means he needs exceptional efficiency and contact quality to create the same damage.

**Fast-swing rate** — Share of his swings at 75+ mph.  
*Why it matters:* One max-effort swing proves little. A strong fast-swing rate shows that plus bat speed is part of the hitter’s normal swing profile, not a one-off peak.

**Squared-Up%** — How efficiently the hitter converts a swing’s potential into exit velocity, based on bat speed and pitch speed. A swing that reaches at least 80% of its theoretical maximum exit velocity counts as squared up.  
*Why it matters:* For us it’s a **filter, not a green light**. High squared-up + low bat speed can still be a contact-first profile. High squared-up + high bat speed is the combination that creates the most dangerous contact.

**Blast** — A Statcast swing that combines strong bat speed with highly squared-up contact. The official threshold uses a sliding interaction: (squared-up percentage × 100) + bat speed ≥ 164.  
*Why it matters:* It’s one of Statcast’s most damaging contact categories. In recent seasons, blasts have produced roughly a .550+ batting average and 1.100+ slugging percentage.

**Pull Air%** — Share of his tracked air balls (fly balls + line drives in the GreenMachine denominator) hit to the pull side.  
*Why it matters:* Pulled airborne contact is one of the cleanest paths to home-run power because hitters generally do their most damage to the pull side. Always check the denominator: some public sources define a similar-looking pull-air number over *all* batted balls instead.

**Oppo Air%** — Same air-ball denominator as Pull Air%, but hit to the opposite field.  
*Why it matters:* An oppo-power hitter can interact with park dimensions and wind very differently from a pull-heavy hitter. Direction matters because the relevant fence and wind are the ones where *his* damaging air contact actually goes.

**Pulled barrels** — Raw count of barrels hit to the pull side.  
*Why it matters:* It’s a direct short-window count of ideal power contact to the hitter’s strongest damage field. We prefer the raw count in tiny windows so a couple of events don’t masquerade as a stable rate.

**K% (strikeout rate)** — Strikeouts per plate appearance. League average sits near 22%.  
*Why it matters:* You can’t homer if you don’t make contact. Under ~24% is fine for a power bat; 28%+ makes him binary — playable only against pitchers who don’t miss bats (see Whiff%).

**ISO (isolated power)** — Slugging minus batting average: pure extra-base thump.  
*Why it matters:* Strips the singles away so you see power by itself. ~.150 is average; .200+ is a real power bat; .300 in AAA is elite prospect power.

**xwOBA / xISO / xSLG (“expected” stats)** — Expected-output measures built from contact quality rather than only the result on the field. xwOBA uses exit velocity and launch angle on batted balls, adds Sprint Speed on certain contact, and also incorporates real walks, strikeouts and hit-by-pitches.  
*Why it matters:* Expected-vs-actual gaps can flag under- or over-performance, but they are **not a promise that regression happens next game**. We use them as supporting evidence that the underlying contact has been better or worse than the scoreboard results.

**Regression gap (xISO−ISO, xwOBA−wOBA)** — Expected minus actual, over a window.  
*Why it matters:* A positive gap is a **possible under-performance flag**, not a guarantee that a hitter is “due.” We prefer strong underlying contact that has not yet been fully rewarded over blindly chasing a recent hot streak.

**BABIP** — Batting average on balls in play (home runs excluded).  
*Why it matters:* It’s a supporting context stat, not a power stat. A low BABIP beside healthy expected contact can support an under-performance case, but BABIP alone does **not** guarantee positive regression.

**Sprint speed** — Top running speed, ft/s. Around 27 ft/s is ordinary MLB speed; 30+ is elite.  
*Why it matters:* Mostly as a warning label. Fast runners can beat out extra ground-ball hits, so some actual-vs-expected gaps have causes unrelated to home-run power. Don’t treat every wOBA/xwOBA gap as a power signal.

**Call-up line (MiLB ISO / HR pace)** — A fresh call-up’s minor-league power line, shown when he has little or no MLB season sample yet.  
*Why it matters:* It gives us a power prior before the MLB sample is usable. AAA ISO of .200+ is meaningful power and .300+ is extreme, but league and park context matter — especially in high-offense environments such as the PCL.

**“Robbed HR” check** — A GreenMachine house check for very hard, homer-shaped contact that became a deep out instead of a home run.  
*Why it matters:* It flags hitters producing near-HR contact that the raw HR total misses. Treat it as supporting contact evidence, not as a literal count of “home runs that should have happened.”

---

## 2. Pitcher vulnerability metrics

**HR/9** — Home runs allowed per 9 innings, split by batter handedness.  
*Why it matters:* The cleanest “does this guy get taken deep” stat. League starters run roughly 1.1–1.3; **1.50+ vs the relevant side = target**, 0.80 or below = suppressor. Use the last-30-days version too (target 1.80+ there) — pitchers go through homer-prone phases their season line hides.

**GB% (ground-ball rate) / avg LA allowed** — Share of contact against him that stays on the ground; or the average launch angle he allows.  
*Why it matters:* A strong ground-ball profile suppresses over-the-fence home-run opportunity because the ball never gets airborne. Treat 50%+ GB or very low average launch allowed as a major suppression flag; high launch-angle profiles deserve extra attention.

**FB% / HR/FB** — Fly-ball rate allowed, and how often those fly balls become home runs.  
*Why it matters:* Fly balls are the raw material of over-the-fence home runs. A high HR/FB rate is a vulnerability flag, but it can also be noisy in small samples — compare it with barrel quality, park, pitch mix and the pitcher’s longer baseline.

**xISO / xwOBA allowed, by hand** — Expected power/production a pitcher is allowing to lefties vs righties, based heavily on the quality of contact he gives up.  
*Why it matters:* These are more directly tied to contact quality than ERA. When actual results look harmless but the expected-contact profile is much worse, that can expose hidden vulnerability — but it is still evidence, not a guarantee that the next result will regress.

**Barrel% allowed / barrels per fly ball** — How often hitters barrel him, and how many of his air balls are barrels.  
*Why it matters:* Low barrel rates are a suppression signal; a sudden cluster of barrels is a warning. In short windows, keep the raw count and denominator visible so one ugly outing doesn’t masquerade as a stable skill change.

**Whiff% / SwStr% (swinging strikes)** — Whiff% is misses per swing; SwStr% is swinging strikes per pitch. The denominators are different.  
*Why it matters:* This is the contact-opportunity check for strikeout-prone sluggers. A low-whiff pitcher gives a high-K power hitter a better chance to reach contact; a high-whiff arm can prevent the power tool from ever getting involved.

**Called-strike%** — Share of pitches that become called strikes because the hitter doesn’t offer.  
*Why it matters:* It explains one way a pitcher can survive without huge swing-and-miss numbers: command, shape and deception can still steal strikes. A “low-whiff” flag is weaker when the pitcher consistently wins the zone without needing chases.

**BB% (walk rate, pitcher)** — Walks per batter faced.  
*Why it matters:* High walk rates mean extra traffic, more hitter-friendly counts and often shorter outings. Double-digit walk rates deserve attention, especially when paired with poor command or weak swing-and-miss stuff.

**FIP / xFIP / SIERA** — ERA alternatives designed to separate pitcher skill from some of the noise in traditional ERA, using strikeouts, walks, home runs and/or batted-ball context in different ways.  
*Why it matters:* They’re a quick quality check on whether an ugly ERA is supported by the pitcher’s underlying performance. Use them as context beside the HR-specific evidence, not as the HR case by themselves.

**Stuff+ / Location+ / Pitching+** — Model-based pitch-quality grades where 100 is league average. Stuff+ focuses on pitch characteristics, Location+ on command, and Pitching+ combines the broader package.  
*Why it matters:* Best used as a context or change-detection tool. A meaningful drop from a pitcher’s own baseline can justify a deeper look at velocity, movement, location and whiff changes before ERA fully reacts.

**Stuff drift (whiff / velocity / usage change)** — Compares a pitcher’s primary pitches now vs his season baseline: whiff rate, velocity, movement and usage.  
*Why it matters:* The “mirage test.” If recent results changed but the underlying pitch traits did not, we are cautious about calling it a real skill change. When velocity, movement or whiff quality moves with the results, the change deserves more weight.

**Pitch usage % (by batter handedness)** — How often a pitcher throws each pitch type to lefties or righties.  
*Why it matters:* This is the matchup engine. A hitter’s pitch-type strength matters only if the opposing pitcher actually throws that pitch enough to the relevant side. High usage creates repeated exposure; low usage can make an otherwise attractive pitch-type split irrelevant.

---

## 3. Weather & environment

**Park factor (index_hr, by handedness, 3-yr rolling)** — How much a park inflates or suppresses home runs, where 100 = average. Read the number for the *batter’s* side, built from the selected multi-year window.  
*Why it matters:* The same contact can play differently by park, and the effect can differ for lefties and righties. 110+ is a meaningful boost; 90 or below is a meaningful suppressor. Use the handedness-specific factor rather than assuming one park rating fits every hitter.

**Temperature** — Game-time °F.  
*Why it matters:* Warmer air is generally less dense, which helps carry; cold air generally suppresses it. The effect matters most across large temperature differences, not as a literal “+1°F = +1% homers” rule. Treat heat as an environment boost, not something that overrides hitter and pitcher quality by itself.

**Wind (speed + direction, vs his air field)** — Wind resolved against where *this hitter* tends to hit damaging air balls.  
*Why it matters:* “Wind out” is not one-size-fits-all. Wind blowing toward a hitter’s main damage field is much more useful than the same wind blowing somewhere he rarely drives the ball. Direction comes first; speed tells us how strongly to weight it.

**Humidity** — Moisture in the air.  
*Why it matters:* Humidity has a smaller and more complicated effect than temperature or wind. Humid air itself is slightly less dense, but ball storage and other conditions matter too. Treat humidity as a secondary modifier, not a standalone HR signal.

**Precipitation %** — Rain chance.  
*Why it matters:* Not a power stat — a *game-flow* stat. Higher rain risk raises the chance of delays, interrupted starter workloads or changing bullpen exposure. It can reduce the clean matchup we thought we were buying.

**Roof / dome (72°F rule)** — GreenMachine house rule: a closed roof or fixed dome is treated as climate-controlled and neutralized to 72°F unless a better indoor-condition source is available.  
*Why it matters:* Outdoor weather should not create a fake boost inside a closed building. If roof status is unknown, we stay neutral rather than guessing that outdoor conditions apply.

---

## 4. Opportunity & workload

**Lineup slot / PA tier** — Where he bats; top and middle lineup spots generally receive more plate appearances than the bottom third.  
*Why it matters:* Home runs need chances. A hitter projected for an extra plate appearance has another opportunity to access the matchup. Confirmed lineups beat projected ones — always check the `est.` flag.

**Pinch-hit risk** — Whether a platoon partner or bench option could take the hitter’s later plate appearances.  
*Why it matters:* A hitter with real pinch-hit risk may lose the exact late-game PA we were counting on. Bullpen handedness matters because it changes how likely the manager is to make that move.

**Platoon advantage** — The long-running tendency for hitters to perform better against opposite-handed pitchers than same-handed pitchers, though the size of the edge changes by hitter, pitcher and season.  
*Why it matters:* Handedness changes pitch shapes, visibility, pitch mix and which side of the park is easiest to access. Use the actual hitter/pitcher splits when available instead of assuming every platoon edge is identical.

**Bullpen handedness + fatigue** — Which opposing relievers are lefty/righty, who pitched recently, and how heavily they were used.  
*Why it matters:* The matchup doesn’t end when the starter exits. Recent workload can make a reliever less likely to appear or less likely to handle a full inning, changing the handedness and quality of the hitter’s late-game matchups.

**Starter workload (pitch counts, rest)** — Last start’s pitch count, days of rest and recent workload trend.  
*Why it matters:* It helps estimate how long our hitter may actually face the starter. A limited or recently recalled arm can mean earlier bullpen exposure; a fully stretched starter can preserve the original matchup deeper into the game.

**Opener / bulk** — When a reliever starts and a “bulk” arm follows.  
*Why it matters:* The pitcher you’re scouting might only face the lineup once. We show the raw pitch-count facts rather than pretending we can classify it perfectly.

---

## 5. Context & sample-size terms

**Sample floors (15 BBE / 10 BBE / 25 swings / 15 air balls / 15 PA / 40 BBE·80 BF)** — GreenMachine’s minimum samples before a metric loses the INSUFFICIENT stamp: 15 BBE for general Barrel%, EV and Hard-Hit%; 10 BBE for pitch-type Barrel/EV; 25 swings for attack-angle metrics; 15 air balls for Pull Air% (8 in the 7-day window); 15 PA for xwOBA; and 40 BBE or 80 BF for pitcher-vulnerability splits.  
*Why it matters:* Small samples lie confidently. The floors are the line between “usable signal” and “interesting number that still needs a warning label.”

**Stabilization** — The idea that different stats need different sample sizes before they become reasonably reliable measures of skill.  
*Why it matters:* Some metrics stabilize much faster than others: strikeout behavior becomes informative sooner than noisy outcome stats such as BABIP. This is *why* GreenMachine keeps short-window samples visible instead of pretending every L7 rate is equally trustworthy.

**Team splits vs hand (ISO / K%, L15/L30)** — How the opposing *lineup as currently constructed* hits lefties or righties over the last 15/30 days.  
*Why it matters:* Teams change. A lineup that was dangerous in May may be gutted by the trade deadline — recency trimmed to the current roster beats the full-season line. (We compute these in-house from raw stats; third-party metrics like wRC+ never appear on screen.)

**K-interaction (“contact opportunity”)** — Pairing a strikeout-prone hitter with a pitcher who does not generate many swings and misses.  
*Why it matters:* It’s the swing-and-miss tax refund: a low-whiff pitcher gives the hitter a better chance to reach contact and let his power participate. **Do not convert pitcher Whiff% directly into batter BIP%** — the denominators are different; this is an interaction signal, not an arithmetic shortcut.

**BvP (batter vs pitcher history)** — Head-to-head career numbers. We exclude it from primary evaluation.  
*Why it matters:* Typical BvP samples are tiny and unstable, so we do not let them outrank broader hitter skill, pitcher vulnerability or pitch-type matchup evidence. Discipline about what we *don’t* use is part of the edge.

---

*Refined v2.1 — 2026-08-23. Changes from v2: tightened Statcast definitions (Barrel, Blast, Squared-Up, Ideal Attack Angle, Sweet-Spot) to match official language; lightly updated league context; preserved all house rules and sample floors; kept the plain-language tone and the strict “evidence, not guarantee” framing.*
