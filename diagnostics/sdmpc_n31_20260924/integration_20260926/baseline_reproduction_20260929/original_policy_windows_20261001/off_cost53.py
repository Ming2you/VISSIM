"""Saved-state off-ramp cost attribution; no rollout or future forecast input."""
import csv
import gzip
import json
from pathlib import Path
from diagnostics.sdmpc_n31_20260924.integration_20260926 import replay_congested_component as r

HERE = Path(__file__).resolve().parent
OUT = HERE / 'off_cost53_v2'
OUT.mkdir(exist_ok=False)
CW = HERE.parent / 'cellwise_calibration'
records = r.load(CW / 'additional_admission_s53.json')['records']
pins = {str(Path(__file__)): r.sha(__file__)}
rows = []
bins = []
for rec in records:
    pp = CW / 'freeway_first/expanded_seed53/expanded' / (rec['arm'] + '_prediction.json.gz')
    cp = Path(rec['truth']) / 'ports_30s.csv'
    pins.update({str(p): r.sha(p) for p in (pp, cp, Path(rec['input']))})
    with gzip.open(pp, 'rt') as f:
        pred = json.load(f)
    with cp.open(encoding='utf-8-sig', newline='') as f:
        obs = list(csv.DictReader(f))
    args, kw = r.read_primitive_capture(rec['input'], rec['sha256'])
    t0, t1 = rec['cutoff'], rec['cutoff'] + rec['horizon']
    for off in ['10481', '10483', '10643', '10682']:
        actual = [x for x in obs if x['connector'] == off and t0 < float(x['window_end_s']) <= t1 + 1e-7]
        model = {round(x['time_s'], 6): x for x in pred['ports'] if x['connector'] == off}
        assert len(actual) == 15
        assert all(float(x['unresolved_absences_veh']) == 0 for x in actual)
        initial = float(actual[0]['start_n_veh'])
        assert initial == len(kw['port_dynamics']['initial_cohorts'][off])
        previous = dict(n_veh=initial, admitted_veh=0., departed_veh=0.)
        totals = {kind: dict(a=0., d=0., ttt=0., weighted_a=0., weighted_d=0.) for kind in ['actual', 'model']}
        for x in actual:
            start, end = float(x['window_start_s']), float(x['window_end_s'])
            y = model[round(end, 6)]
            assert abs(end-start-30.) < 1e-6
            a = float(x['arrivals_veh']); d = float(x['departures_veh'])
            ma = y['admitted_veh']-previous['admitted_veh']; md = y['departed_veh']-previous['departed_veh']
            n0, n1 = float(x['start_n_veh']), float(x['end_n_veh'])
            assert abs(n1-n0-a+d) < 1e-7
            assert abs(y['n_veh']-previous['n_veh']-ma+md) < 1e-7
            w = (t1-(start+end)/2)/3600
            item = dict(arm=rec['arm'], off=off, start=start, end=end,
                        actual_a=a, actual_d=d, model_a=ma, model_d=md,
                        actual_n=n1, model_n=y['n_veh'])
            bins.append(item)
            for kind, aa, dd, nn0, nn1 in [('actual',a,d,n0,n1),('model',ma,md,previous['n_veh'],y['n_veh'])]:
                z = totals[kind]
                z['a'] += aa; z['d'] += dd
                z['ttt'] += (nn0+nn1)*(end-start)/7200
                z['weighted_a'] += aa*w; z['weighted_d'] += dd*w
            previous = y
        for kind, z in totals.items():
            assert abs(z['ttt']-(initial*(t1-t0)/3600+z['weighted_a']-z['weighted_d'])) < 1e-7
        caps = [float(x['off_capacity_vph'][off]) for x in args[1]]
        drains = [float(x['off_drain_vph'][off]) for x in args[1]]
        rows.append(dict(arm=rec['arm'], off=off, initial=initial, actual=totals['actual'], model=totals['model'],
                         input_entry_proxy_min_vph=min(caps), input_entry_proxy_max_vph=max(caps),
                         drainage_min_vph=min(drains), drainage_max_vph=max(drains),
                         initial_travel_speed_kmh=kw['port_dynamics']['travel_speed_kmh'][off]))

contrasts=[]
for arm, reference in [('release','hold'),('hold_vsl90','hold'),('release_vsl90','hold_vsl90')]:
    for off in ['10481','10483','10643','10682']:
        a=next(x for x in rows if x['arm']==reference and x['off']==off)
        b=next(x for x in rows if x['arm']==arm and x['off']==off)
        delta={kind:{k:b[kind][k]-a[kind][k] for k in a[kind]} for kind in ['actual','model']}
        error={k:delta['model'][k]-delta['actual'][k] for k in delta['actual']}
        assert abs(error['ttt']-error['weighted_a']+error['weighted_d'])<1e-7
        contrasts.append(dict(arm=arm, reference=reference, off=off, delta=delta, error=error))
for p,h in pins.items():
    assert r.sha(p)==h
integration=HERE.parent.parent
native_dir=integration/'native_rm_observation2700_writerfix_v3/analysis'
proof_path=native_dir/'summary.json'
proof=r.load(proof_path)
assert proof['paired_prefix_exact'] and proof['counterfactual_valid']
pointer=integration/'expanded036_9000_20260930/loss_early1500/lane84/ind47_base/output.json'
full_dir=Path(r.load(pointer)['output'])
native={arm:r.load(native_dir/arm/'area_metrics.json') for arm in ['hold','release']}
full={arm:r.load(full_dir/(name+'.json')) for arm,name in [('hold','held_actual'),('release','release_actual')]}
groups_path=r.ROOT/r.load(CW/'expanded_joint/eval_036/manifest.json')['off_groups']
groups=r.load(groups_path)['groups']
coupled=[]
for group, spec in groups.items():
    for branch in ['signal','direct']:
        off=spec[branch+'_connector']
        key='storage:'+('lane_off_'+off if branch=='direct' else group+'_storage')
        assert all(full[arm]['first_interval']['offramps'][off]['storage']==key.removeprefix('storage:') for arm in full)
        actual=native['release']['physical_link_residence'][off]['ttt_veh_h']-native['hold']['physical_link_residence'][off]['ttt_veh_h']
        forecast=full['release']['cost_by_stock'][key]-full['hold']['cost_by_stock'][key]
        coupled.append(dict(off=off,model_stock=key,actual_delta_ttt=actual,model_delta_ttt=forecast,error=forecast-actual))
for p in [proof_path,pointer,groups_path,*[native_dir/a/'area_metrics.json' for a in native],*[full_dir/(n+'.json') for n in ['held_actual','release_actual']]]:
    pins[str(p)]=r.sha(p)
r.save(OUT/'summary.json',dict(rows=rows,contrasts=contrasts,pins=pins,identity_checks=240,
                             new_forecasts=0,new_native=0,future_input=False,
                             scope='East four off-ramp connectors; exact30s cost accounting, not causal attribution.',
                             coupled47=coupled,
                             coupled_scope='Eight off-ramp deltas in full coupled2700-3150. Native full-run costs have an exact common prefix, which cancels in differences. Do not compare those native absolute costs to450s model costs.',
                             correction='v1 service_min/max labels were off ENTRY proxies; v2 separates them from actual off_drain_vph. Prior v1 outputs and executed source preserved.'))
r.save(OUT/'bins.json',bins)
(OUT/'source_executed.py.txt').write_bytes(Path(__file__).read_bytes())
print(json.dumps(dict(drainage=[dict(arm=x['arm'],off=x['off'],rate=x['drainage_min_vph']) for x in rows],coupled47=coupled),ensure_ascii=False),flush=True)
