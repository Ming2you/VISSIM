# Prediction-horizon diagnostic (2026-10-03)

Completed cached observations/predictions only; no new forecast, calibration, FZP scan or VISSIM execution. The live REVIEW96 run was not queried or changed.

- Endpoint east-cell speed MAE at +150/+300/+450 seconds: **15.39 / 16.14 / 16.52 km/h** (10 policy arms across three initial states, seeds67/71/73).
- Endpoint stock MAE: **8.66 / 9.47 / 9.35 vehicles per cell**.
- Disjoint150-second Omega TTT mean absolute relative errors: **0.23 / 2.90 / 7.37%** (six arms, seeds67/73; seed71 interval ledger unavailable in inspected cache).
- These speed/stock values are endpoint errors, not within-interval temporal averages. Speed error rises monotonically in only3/10 arms; it is higher at450 than150 in6/10. Thus aggregate TTT drift grows, but individual state errors do not all grow monotonically.
- First150 aggregate TTT is close while spatial state already differs. This does not validate first150 control ranking.
- Seed67 native-city/RM-release VSL comparison: actual450 DeltaTTT -2.065 vehicle-hours, including -2.01861 in last150; model last150 -0.08255. The first150 difference is effectively zero. Truncating the horizon to150 would omit most observed benefit in this case.

`assessment.json` contains per-arm, per-seed, interval, and candidate difference tables, definitions/limitations, and input SHA256. `assess.py` is the reproducible cached-only calculation. Native CSV integration was reconciled against every stored cumulative increment; model interval sums against full450 totals. No claim of parameter adoption or gain qualification.
