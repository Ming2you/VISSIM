# Port validation follow-up — PASS

The Important I1 finding in `port_independent_review_20260915.md` is resolved. Review scope was limited to the new validation in `boundary_factory.py` and `DelayedPort`; no actual observation files were reanalysed, no source files were edited, and no native work was performed.

The factory now explicitly rejects nonfinite or negative `off_drain_vph`. The constructor rejects invalid geometry, travel speed, start time and position/speed/lane cohorts. Release and admission validate their inputs before mutating stocks.

Nineteen small synthetic checks passed in one Python `-B` invocation:

- Factory rejects NaN, infinity and negative observed drainage, reproducing the previous NaN fault with a synthetic cutoff-safe history table.
- Constructor rejects NaN capacity, infinite speed, negative start, malformed cohort shape, NaN cohort position and negative position.
- Release rejects NaN/negative service, zero duration and backward time.
- Admission rejects NaN amount, infinite time, negative amount, backward time and capacity overflow.
- Invalid release/admission requests preserve the entire prior internal state. A short valid sequence confirms delayed availability, valid zero service, finite storage and exact vehicle conservation.

The valid-input stock and flow formulas remain unchanged. No reason to refit parameters solely because of these guards was found. This is a scoped correction review, not a new calibration, native trial or full urban forecast validation.
