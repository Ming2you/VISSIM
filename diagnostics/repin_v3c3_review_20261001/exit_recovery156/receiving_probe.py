"""Conditional shared-node closure from131/152 caches, never rollout inputs."""
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent
assert not (HERE/'receiving_probe.json').exists()
paths=[h.R/'exit_sending131/attempt2/steps.json',h.R/'receiving_lane152/steps.json',h.F/'route_inventory/mapping31.json']
pins={str(p):h.sha(p) for p in paths}
exits,receiving,mapping=[h.read(p) for p in paths]
bounds=mapping['freeway_model_links']['FW_E']['segment_bounds_m'];length=bounds[21]-bounds[20]
bykey={(r['arm'],round(r['lo'],6)):r for r in receiving if r['lane']==1}
rows=[]
for e in exits:
    r=bykey[e['case'],round(e['start'],6)]
    assert abs(e['end']-r['hi'])<1e-7
    n=e['native_lane_n'];ne=e['n0'];v=e['native_lane_v']
    request=ne*v*5/(3.6*length);through=(n-ne)*v*5/(3.6*length)
    assert abs(request-e['qmean'])<1e-8
    out=dict(arm=e['case'],lo=e['start'],hi=e['end'],request=request,through_request=through,
        actual_off=e['physical_exit'],actual_merge=r['physical_merge'],supply_left5=r['supply_left5'],
        supply_trapezoid5=r['supply_trapezoid5'])
    for label,supply in [('left',r['supply_left5']),('trapezoid',r['supply_trapezoid5'])]:
        for suffix,merge in [('observed_merge',r['physical_merge']),('zero_merge',0.)]:
            room=max(0.,supply-merge)
            factor=min(1.,room/through) if through>1e-12 else 1.
            out[label+'_'+suffix]=request*factor
    rows.append(out)
windows=[]
for arm in ('release','release_vsl90'):
    for lo,hi in ((2700.1,2820.1),(2820.1,2970.1),(2970.1,3120.1)):
        z=[r for r in rows if r['arm']==arm and lo-1e-6<=r['lo']<hi-1e-6]
        assert len(z)==round((hi-lo)/5)
        keys=['request','through_request','actual_off','actual_merge','supply_left5','supply_trapezoid5',
              'left_observed_merge','trapezoid_observed_merge','left_zero_merge','trapezoid_zero_merge']
        windows.append(dict(arm=arm,lo=lo,hi=hi,**{k:sum(r[k] for r in z) for k in keys},
            observed_merge_exceeds_current_left_supply_bins=sum(r['actual_merge']>r['supply_left5'] for r in z)))
for p,digest in pins.items():assert h.sha(p)==digest,p
h.save(HERE/'receiving_probe_steps.json',rows)
h.save(HERE/'receiving_probe.json',dict(status='complete_conditional_diagnostic',windows=windows,input_sha256=pins,
    future_actual_used_only_in_diagnostic=True,forecasts=0,adopted=False,
    formula='off_request * min(1, max(0, current_lane21_supply - observed5smerge) / through_request); if no through request, factor1.',
    limits='5s frozen-state approximation and observed future5s merges; not an autonomous prediction, admissible control, or rigorous trajectory-wide capacity bound. Left/trapezoid supply bracket is sensitivity only, not a confidence interval. Zero-merge reference removes only the reservation at the same states; it is not a physically realized RM run. Off branch storage is deliberately omitted in this optimistic node check.'))
for w in windows:print(w)
