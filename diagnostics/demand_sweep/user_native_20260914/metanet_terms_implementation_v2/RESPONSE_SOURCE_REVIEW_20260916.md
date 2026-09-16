# Response source review — 2026-09-16

Static review only, before native four-arm analysis. No native run, process operation, model execution, or source edit was performed. The hashes below identify the reviewed versions, not any later corrections.

## Confirmed source behavior

- Optional `vsl_zone_heads` installs a copied per-road config with a new head at zero-based cell 13, making command head 10 apply to cells 10–12 instead of the old 10–14. Absent the option, the canonical topology stays unchanged. This fixes a material overextension of the actuator's model influence.
- The driver builds all 1350 s initial mainline states, off-port states/cohorts and target-ramp cohorts, and rejects differences between arms. The 1800 s recovery states are arm-specific and expressly not labeled common-state candidate tests.
- History-mode on-ramp arrivals use the prior five completed 30 s windows, not future FZP. Conditional mode uses future realized interface arrivals and explicitly says so. Other seven ramp merge interfaces remain exogenous. No state reset occurs within each 450 s rollout.
- The RM boundary uses actual stopline position, isolates cars already beyond the stopline from new red service restrictions, conserves connector and external backlog, and asks the existing mainline receiving kernel for merge acceptance. No artificial capacity drop, control reward, new coefficient fit or fitted startup-loss term is introduced by this response driver.
- Native distributions remain labeled as IDs; the model retains its existing scalar speed convention. Native OFF is not silently relabeled GREEN in receipts; its numerical g10 service proxy is stated as an unverified hypothesis.
- Predicted/observed component costs use the same 30 s geometry-cell/port residence sampling; native physical-link 1 s residence is separate. Both exclude the other seven on-ramps and urban waiting and therefore cannot certify Ω benefit or GNE selection feasibility.

## Spatial and timing approximations that matter

Native VSL interval is 5386.554–6733.193 m, while selected model cells span 5262.879–6841.743 m. The projection starts about 123.676 m early and ends 108.550 m late. This is now confined to the correct broad approach, but is not exact station-level actuator alignment.

The ramp helper applies a cycle-mean head budget at a 10 s interval end and releases newly served vehicles to merge in a later interval. The actual 6.429 m post-head travel at the supplied 32.404 km/h is about 0.714 s. Thus numerical phase/travel delay can be almost a model step longer than the physical passage; it is not a calibrated startup delay. Compare head and merge counts separately, including first-response timing.

## Important open concern: post-head storage

The helper currently enforces whole-connector storage only. Its 279.032 m length at 6 m spacing provides about 46.505 vehicles, but the 6.429 m from stopline to merge provides only about 1.071 vehicles at the same convention. `apply_head_service` may keep transferring head-ready vehicles into downstream-travelling/merge-ready stock when mainline receiving is poor. That stock stays beyond the head and immune to later red even if it exceeds physical post-head storage. Vehicle conservation still passes.

This can overstate how many vehicles are already committed and make RM appear insensitive. It is a structural concern until predicted downstream+merge-ready maxima and native vehicle positions are checked. It has been raised to the implementation owner and parent.

**Do not fix this by allowing just one storage-sized transfer per 10 s.** That would impose an artificial ~386 veh/h capacity (1.071 veh / 10 s), even though the short post-head section can turn over many times per interval. A correction needs within-interval passage/receiving accounting or a clearly labeled point-queue approximation with an audit of its effect. Diagnose the realized error first; do not force a stronger metering benefit.

## Status

The source's common-state/future-information safeguards and VSL-zone confinement are suitable for a diagnostic. Final response validity remains pending native records, short meaningful tests, and the post-head-stock audit. This review is not a PASS of actuator response accuracy.

## Reviewed SHA-256

- `diagnostics/demand_sweep/user_native_20260914/metanet_terms_implementation_v2/evaluate_native_response.py`: `556a3fa7bfb1293c58befb6b373a16231625e6a37b9f5280397943fa6f527937`.
- `diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py`: `c5438f2e75a11d5b2542c42b6e7d83edb7427a1406517c65ccee0c10086ac9aa`.
- `evaluation/controllers/physical_ramp_boundary.py`: `e229b7732ae5a3ea0314251a8fcc5017353fc1f99c40e10f12699cd1a8a86ef8`.
