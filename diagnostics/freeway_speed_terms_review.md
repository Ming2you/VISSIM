# E8 initial 10/30-second speed update: actual terms

The congested t3300 recovery error is driven by the **positive downstream-density-gradient term**, not a desired-speed relaxation toward free flow. The existing FD already requests only 0.02165 km/h at E8, so relaxation subtracts speed. A much less dense averaged E9 adds 16.60752 km/h in the first ten seconds and overcomes that braking. At t1200 the three terms all accelerate E8: relaxation, fast upstream convection, and the lower downstream density. The integrated accounting/signal/observation repairs leave this pattern almost unchanged.

`probe_freeway_speed_terms.py` runs the actual canonical endpoint for one interval from each pure-n7 observed state and its same-time action JSON. It records original function return-frame locals for E7/E8/E9 in the first three ten-second steps. No model function, state, FD fit, parameter, or capacity is replaced. An independent untraced replay is exactly equal for freeway density/speed/flow/lanes, ramp and urban stocks, objective, and TTT. Original input state is unchanged. Across 36 cell-steps (two starts × two configurations × three cells × three steps), the term sum agrees with actual delta-v to <8e−15 km/h and continuity residual is <1e−9 vehicles.

Artifacts: `freeway_speed_terms_{baseline,integrated}_{1200,3300}.json`. Each includes function inputs, individual terms, actual flows/stocks, observed plant rows, source/input hashes, runtime metadata, and explicit signal projection differences. Baseline uses current canonical source with the original n7 configuration flags; it is not a historical source checkout. Its E8 +30-second speeds exactly reproduce the earlier fidelity results (79.550585 at1200 and23.402313 at3300).

| Start | Horizon | E8 baseline km/h | E8 integrated km/h | Actual VISSIM km/h |
|---:|---:|---:|---:|---:|
|1200|0|33.310259|33.310259|33.310259|
|1200|10|67.989186|67.980933|not recorded at10s|
|1200|20|78.377428|78.359526|not recorded at10s|
|1200|30|79.550585|79.626911|45.432410|
|3300|0|4.924904|4.924904|4.924904|
|3300|10|18.855837|18.857056|not recorded at10s|
|3300|20|23.720329|23.722523|not recorded at10s|
|3300|30|23.402313|23.407406|5.009654|

For the integrated run, each row below is a delta in km/h over one ten-second update. E8 lane-drop, merge, and boundary speed caps are all zero in these six updates. Numerical floor residues are at floating-point rounding scale.

| Start | Step end | Relaxation | Convection | Anticipation | Total delta |
|---:|---:|---:|---:|---:|---:|
|1200|10|+16.212380|+13.825521|+4.632774|+34.670674|
|1200|20|−7.714505|+12.017451|+6.075647|+10.378593|
|1200|30|−8.843089|+6.822722|+3.287752|+1.267385|
|3300|10|−2.724028|+0.048660|+16.607519|+13.932152|
|3300|20|−10.465708|−1.413682|+16.744857|+4.865467|
|3300|30|−13.141644|−2.402881|+15.229408|−0.315117|

The actual update parameters are T=10s, tau=18s, L=0.513441km, nu=30km²/h, kappa=40veh/km/lane. These are the loaded n7 values, not the older tau7/delta17.3 calibration described in historical config comments. E8's cell FD uses v_free118.29, critical density25, exponential shape2; two-branch is OFF. The link merge coefficient is0.3 and lane-drop coefficient3.

At1200, E8 has rho28.24208, E9 rho18.50261, upstream E7 speed110.02813, and E8 speed33.31026. The FD desired speed is62.49254. The updater therefore adds16.21238 from relaxation plus13.82552 from upstream convection. At3300, E8 rho103.71660 versus E9 rho30.18847 gives a −73.52813veh/km/lane downstream difference. The exact anticipation formula is `−nu*T/(tau*L)*(rho_next−rho)/(rho+kappa)` (`vendor/NumSim-mine/src/models/metanet.py:99`). Its sign is positive for this observed spatial pattern. Changing tau alone scales both relaxation and anticipation; this evidence does not identify a new tau or justify a parameter change.

E8 has no modeled merge inflow in these replays. Both physical R_F_E branch receipts enter E9; first-step E9 receipts are1080vph at1200 and587.868329vph at3300. E9's corresponding merge penalties are only−0.456608 and−0.066595km/h. E8's current effective lanes are approximately4 and E9 has4, so the positive lane-drop difference is0 at E8. A tiny spill-related lane difference applies the phi term to E7 instead; at3300 its first-step raw penalty is−0.000129km/h and is cancelled by the5km/h floor. There is no separate weaving/lane-changing speed term in this canonical update. These are code-input facts, not proof that all of the physical bottleneck is caused by lane-changing.

The earlier spatial-order audit remains relevant: physical10639 merges in E8, direct10682 diverges in E9, and10681 merges in E9, while the aggregate model places OR_F_E at8 and all R_F_E at9. See `direct_branch_feedback_and_order_design.md`. A less congested averaged E9 can therefore encourage acceleration out of a lane-specific weaving queue even when the real queue persists. Branch-specific accepted receipts, queue stocks, and correct merge/diverge placement are needed to test that representation; moving a whole grouped index or forcing E8 lambda would not isolate the defect.

The speed error immediately becomes a flow/stock error. At3300 E8 modeled total outflow rises2043.087→7886.691→9161.979vph across the three steps. Mainline components are1634.470→6309.353→7329.583; off-ramp components408.617→1577.338→1832.396. All modeled off-ramp demand is accepted; no boundary speed cap fires. The downstream receiving calculation is approximately108000–110000vph and does not bind. With `capacity_drop_discharge_phi=1`, there is no congested per-cell discharge clamp in this branch; the configured6937vph link capacity is not a universal cap on every inter-cell send. This describes the current equations and is not a newly identified physical capacity.

After30s at3300, modeled E8 stock178.318veh and density86.88170 contrast with actual215veh and density104.66871. At1200, modeled47.942veh/density23.36474 contrast with actual76veh/density36.99917. Exact model mass closure does not guarantee correct flow: the excessive modeled discharge is conserved into other stocks or modeled exits.

The integrated replay uses the canonical corrected signal seed projection. Raw SC109 `(0,20,96.5,24.5)` becomes `(0,23.25,90,27.75)` to preserve its150s cycle; other changes are millisecond-grid normalization. These differences are listed explicitly in JSON and prevent calling this a pure isolated physics-only intervention. Nevertheless, the almost identical first30s E8 trajectories and exact original-n7 baseline reproduction show that the new accounting/signal repairs do not remove this recovery mechanism. The two-branch alternative has not been tested here; changing the FD alone cannot be claimed sufficient from these results, especially because the congested original desired speed already brakes E8.

Reproduce each independent process with `python diagnostics/probe_freeway_speed_terms.py --mode integrated --start 3300 --output diagnostics/freeway_speed_terms_integrated_3300.json` (substitute baseline/1200). No optimizer or VISSIM process is launched. The live beta experiments remain separate performance evidence; this diagnostic isolates the internal cause of the known prediction error without promoting a new physical model.
