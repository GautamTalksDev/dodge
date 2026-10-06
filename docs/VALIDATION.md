# Validation

DODGE is only useful if it finds what is there and nothing that is not. Four independent checks back that up.

## 1. The fast screen misses nothing a brute force finds

`tests/check_recall.py` takes a random sample of real recorded objects. It finds every pass under 5 km by brute force: every pair, every second, then the same 50 ms refinement. Then it runs the fast screen on the same sample and compares.

| Date | Sample | Window | Brute force | Fast screen | Missed |
|---|---|---|---|---|---|
| 2026-10-06 | 1,500 Starlink × 1,500 others | 3 h | 80 | 80 | 0 |

Run it yourself:

```bash
python tests/check_recall.py work/gp-2026-10-06.ndjson.gz --hours 3 --n 1500
```

## 2. The spatial hash is exact

`tests/test_engine.py` compares the spatial hash with a full distance matrix on random point clouds of several sizes and spreads. Some points sit exactly on cell edges, and some are masked out as failed propagations. The two give identical sets of pairs. The test runs in CI before every daily screen, and the screen does not publish if it fails.

## 3. A crafted crossing is found and refined correctly

The same test file builds two orbits that cross: one like a Starlink at 53°, one sun-synchronous at 97.5°. It searches for the phase that makes them pass close, then checks three things:

* the screen finds the pass;
* a 20 ms brute force around the reported time cannot beat the reported distance;
* the straight-line estimate agrees with the SGP4 refinement to within 200 m.

## 4. The totals match physics and SpaceX's own numbers

**Kinetic estimate.** On 6 October 2026 the screen kept about 4,500 non-Starlink objects in the 160 to 600 km band. That band holds about 2.4 × 10¹¹ km³, so the density is about 1.9 × 10⁻⁸ objects per km³. A 5 km miss radius gives a cross-section of 78.5 km², and closing speeds average about 10 km/s. The expected rate of passes under 5 km is then:

```
11,143 Starlinks × 1.9e-8 per km³ × 78.5 km² × 10 km/s ≈ 0.17 per second ≈ 600 per hour
```

The screen found about 12,300 per day, which is 512 per hour. That matches the estimate to within its rough assumptions.

**SpaceX's maneuver count.** The screen finds about 430 passes under 1 km per day, roughly 157,000 a year. SpaceX reported 355,848 avoidance maneuvers from June 2025 to May 2026, at a threshold of 3 in 10 million collision probability. That is far more cautious than a fixed 1 km, since it also covers wider passes with large uncertainty. Same order of magnitude, as expected.

## Known limits

* Public element sets are typically accurate to around a kilometre near epoch. Single predicted passes under a few hundred metres should be read as "close", not as a measured distance.
* The screen does not model maneuvers that happen after the element set epoch. Starlink maneuvers often, so some predicted passes will never happen. That is the point of maneuvering.
* Coverage is limited to what CelesTrak publishes. Objects without public element sets cannot be screened.
