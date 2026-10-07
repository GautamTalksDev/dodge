# Method

DODGE answers one question every day: in the next 24 hours, which objects will pass within 5 km of a Starlink satellite, and who owns them?

## 1. Inputs

| Input | Source | Why |
|---|---|---|
| Starlink orbits | CelesTrak SupGP `starlink` | Fitted from the ephemerides SpaceX publishes; far more accurate than radar-based sets |
| Other operators' orbits where published | CelesTrak SupGP: `oneweb`, `kuiper`, `planet`, `ast`, `iridium`, `orbcomm`, `iss`, `css`, `eumetsat`, `telesat` | Same reason |
| Everything else | CelesTrak GP: `active`, `analyst`, `last-30-days`, every object named `DEB`, every object named `R/B` | About 30,000 objects, close to the whole tracked catalog |
| Owner, type, launch | CelesTrak SATCAT | Attribution |

## 2. Selecting one element set per object

* Operator ephemerides (SupGP) beat public sets for the same object.
* Among sets of the same kind, the epoch closest to the screen start `t0` wins. SupGP files can hold several fits per object, some dated ahead.
* Sets older than 7 days at `t0` are dropped (`stale`).
* Objects whose perigee and apogee never reach the Starlink altitude band (with a 25 km margin) are dropped (`outside_band`).
* Public sets for Starlink satellites are dropped. SpaceX coordinates its own fleet, so Starlink to Starlink passes are out of scope.

## 3. Propagation

Every remaining object is propagated with SGP4, through the `sgp4` package. That package is Brandon Rhodes' wrapper of David Vallado's reference C++ code (Vallado et al., *Revisiting Spacetrack Report #3*, AIAA 2006-6753). The grid runs from `t0` for 24 hours at 10 second steps, which is 8,640 steps.

## 4. Finding candidates: a spatial hash

At every step, positions are bucketed into 100 km cubes. For each Starlink, DODGE checks its own cube and the 26 neighbours, then keeps pairs closer than 100 km. This finds exactly the pairs a full distance check would find, and the unit tests prove it on random point clouds, including points on cell edges.

## 5. Closest approach inside a step

For each candidate pair, with relative position **r** and relative velocity **v** at the sample time, the time of closest approach under straight-line relative motion is

```
tau = -(r . v) / (v . v)
```

If `|tau|` falls inside the half-step around the sample, the estimated miss is `|r + v tau|`.

Why a straight line is good enough: two objects 100 km apart in low orbit feel almost the same gravity. Their relative acceleration is about `g * d / r`, roughly 8.4 m/s² × 100 / 6,900, about 0.12 m/s². Over 5 seconds that bends the relative path by about 1.5 m.

## 6. Refinement

Every pass estimated under 10 km is propagated again with SGP4 at 50 ms steps, within plus or minus 6 seconds of the estimate. The minimum distance found there is reported if it is under 5 km. One pair can meet more than once a day, so each pair keeps at most one pass per 10 minute window.

## 7. Attribution

Each pass is joined with the SATCAT entry of the other object:

* **Owner:** the SATCAT owner code, shown as a country or organisation. `TBD` means no owner on record yet.
* **Type:** satellite, rocket body, debris, unknown.
* **Fleet:** name patterns in [`engine/fleets.py`](../engine/fleets.py), for payloads only.
* **Publishes orbits:** whether that day's SupGP list includes the operator's file.

Raw totals mostly follow how much hardware sits at Starlink's altitudes. Every owner and fleet row therefore also shows how many of its objects were screened, and the passes per object.

## 8. Maneuver detection

Between two consecutive element sets of the same object, less than 3 days apart, the semi-major axis should change only as drag predicts from the mean motion derivative. A difference of more than 250 m from that prediction counts as a maneuver, well above the tens of metres of element set noise. Over the last 7 days of recordings, each fleet gets the share of its payloads in Starlink's band that were seen maneuvering. Payloads that never maneuver either cannot (no propulsion) or did not. Either way, Starlink has to be the one that moves. This needs at least two days of history.

## 9. The daily brief

`engine/brief.py` writes a headline and a few sentences from fixed templates filled with the day's computed numbers. No language model is involved, so the brief cannot state anything the data does not contain.

## 10. What the numbers mean, and what they do not

* **Screening grade.** Public element sets for non-Starlink objects are typically accurate to around a kilometre near their epoch, and worse after. A predicted 300 m pass might really be 50 m or 2 km. Single passes are indicative. Totals and per-object rates are robust.
* **Not collision probabilities.** DODGE does not use covariance, so it cannot compute a probability of collision. Operators screen with their own ephemerides and covariance and maneuver on probability, not on a fixed distance. SpaceX uses 3 in 10 million.
* **Not misconduct.** Most passes involve small satellites without propulsion, or old hardware. They are where physics puts them. The conduct questions DODGE tracks are narrower: does an operator publish its orbits, is its hardware registered, and is it leaving stages and debris in busy shells.
* **Public sharing only.** Some operators share ephemerides privately with US Space Command, TraCSS or SpaceX Stargaze. DODGE can only see public sharing.

## References

* Vallado, D., Crawford, P., Hujsak, R., Kelso, T.S., *Revisiting Spacetrack Report #3*, AIAA 2006-6753.
* CelesTrak, [GP data formats and usage](https://celestrak.org/NORAD/documentation/gp-data-formats.php) and [SupGP](https://celestrak.org/NORAD/elements/supplemental/).
* SpaceX semiannual Starlink reports to the FCC: 148,696 avoidance maneuvers from June to November 2025 and 207,152 from December 2025 to May 2026, as reported by [Space.com](https://space.com/space-exploration/satellites/every-spacex-starlink-satellite-has-to-dodge-a-collision-almost-weekly-and-experts-fear-the-worst).
