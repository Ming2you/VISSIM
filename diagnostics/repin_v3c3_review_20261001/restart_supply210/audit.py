"""Decompose the unadopted phase closure using saved states only.

No fitting, rollout, native run or FZP scan. Future cached endpoints are labels,
never model inputs. A crossing observed between snapshots is a lower bound on
forward through crossings, not a complete accepted-flow/off-ramp measurement.
"""
from collections import Counter, defaultdict
import ctypes
import gzip
import json
import math
from pathlib import Path
import time

import numpy as np
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent
OLD = h.R / 'phase_joint183/endpoint209'


def parts(n, dn, ds, length, down_length, critical, down_critical, jam):
    own = max(0., (n / length - critical) / (jam - critical))
    down = max(0., (dn / down_length - down_critical) / (jam - down_critical))
    slow = ds / dn if dn else 0.
    return own, down, slow, min(1., max(own, down, slow))


def grouped(rows, model=False):
    groups = defaultdict(list)
    for z in rows:
        groups[z['case'], z['cell'], z['lane'], z['window']].append(z)
    out = []
    for (case, cell, lane, window), zz in sorted(groups.items()):
        x = dict(case=case, cell=cell, lane=lane, window=window, samples=len(zz))
        for key in ('n', 's', 'p', 'own', 'down', 'down_slow', 'rho', 'down_rho'):
            x['mean_' + key] = float(np.mean([z[key] for z in zz]))
        x.update(max_p=max(z['p'] for z in zz),
                 p_above_095=sum(z['p'] >= .95 for z in zz),
                 own_strictly_dominant=sum(z['own'] > max(z['down'], z['down_slow']) + 1e-10 for z in zz))
        if model:
            for key in ('formation', 'release', 'beta', 'beta_without_own',
                        'macro_target', 'moving_target', 'space_change', 'slow_net_transport'):
                x['mean_' + key] = float(np.mean([z[key] for z in zz]))
        else:
            keys = ('slow_visible', 'slow_stayers', 'restart_visible', 'restart_stayers',
                    'slow_missing', 'past_forward_crossing_lower_bound',
                    'moving_visible', 'moving_stayers', 'onset_visible', 'onset_stayers',
                    'moving_missing')
            x.update({key: sum(z[key] for z in zz) for key in keys})
            x['restart_fraction_visible'] = x['restart_visible']/x['slow_visible'] if x['slow_visible'] else None
            x['restart_fraction_stayers'] = x['restart_stayers']/x['slow_stayers'] if x['slow_stayers'] else None
        out.append(x)
    return out


def main():
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    start = time.perf_counter()
    assert not (HERE / 'completion.json').exists()
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers.freeway_geometry import cell_lengths_km
    common.setup()
    manifest = h.R / 'lane_state132/eval_01/manifest.json'
    ctx = lpr.load_sources(manifest)
    cfg = ctx['component']._config('FW_E', ctx['parameters']['by_direction']['FW_E'])
    fd = cfg.network.freeway_segment_params['FW_E']
    jam = cfg.network.rho_max
    lengths = cell_lengths_km(cfg.network, 'FW_E', 31)
    config = dict(jam=jam, lengths=lengths, critical=[fd[i]['rho_crit'] for i in range(31)])
    core = h.read(h.R/'recovery_memory206/protocol.json')['source_sha256']
    stop = h.read(OLD/'protocol.json')['STOP']
    assert all(h.sha(h.ROOT/p) == v for p, v in core.items())
    assert h.sha(stop['path']) == stop['sha256']
    inputs = {str(manifest): h.sha(manifest)}
    protocol = dict(question='Does own-cell density suppress restart even when downstream pressure is smaller, and are autonomous states within observed support?',
        prior_review='209 corrected endpoint likelihood but refitted autonomous phase candidate failed; no repeat coefficient grid.',
        prior_sources=['upstream_worklog/07_fww_sc1001eb/fww-struct/P_PLANT.md',
                       'phase_equilibrium181/README.md', 'coupled_recovery158/README.md'],
        definitions='Cells20--24/lane1--3; S is native speed<5 or the candidate latent slow subset. These are not guaranteed equivalent.',
        calculations='Pressure decomposition, observed5s label eligibility, predicted phase balances and local rate-only ablation. No autonomous counterfactual.',
        caveats=['Removal of own pressure from beta is an algebraic sensitivity only, not an adopted rule or a VSL gain.',
                 'Native endpoint labels miss unobserved within5s events; unavailable vehicles are censored, not assumed to restart.',
                 'Past forward crossings exclude unobserved/off-ramp exits and are only a lower bound.',
                 'Observed current states do not prove endogenous receiving/release closure.',
                 '29early training versus29late forecast are different states;43/67 are previously examined, not blind.'],
        budget=dict(fits=0, forecasts=0, native=0, FZP=0), STOP=stop, source_sha256=core)
    h.save(HERE/'protocol.json', protocol)
    native = []
    source92 = h.read(h.R/'state_information92/protocol.json')['inputs']
    cases = {k: h.ROOT/source92[k]['path'] for k in ('29_none', '29_vsl', '43_none', '43_vsl')}
    pins208 = h.read(h.R/'stop_episodes208/summary.json')['input_sha256']
    for name, digest in pins208.items():
        p = Path(name); assert h.sha(p) == digest
        cases['67_' + p.name.removesuffix('_frames.json.gz')] = p
    for case, path in cases.items():
        inputs[str(path)] = h.sha(path)
        d = h.read(path); ix = {k:i for i,k in enumerate(d['fields'])}
        vi = ix['speed'] if 'speed' in ix else ix['speed_kmh']
        ci, li = ix['cell'], ix['lane']
        frames = {round(float(t),6):v for t,v in d['frames'].items()}
        times = sorted(frames)
        for t, tn in zip(times, times[1:]):
            assert abs(tn-t-5) < 1e-8
            now, future = frames[t], frames[tn]
            previous = frames.get(round(t-5,6), {})
            bins = defaultdict(dict)
            for vid,z in now.items(): bins[z[ci],z[li]][vid] = z
            for i in range(20,25):
                for lane in (1,2,3):
                    own, downstream = bins[i,lane], bins[i+1,lane]
                    n = len(own); s = sum(z[vi]<5 for z in own.values())
                    dn = len(downstream); ds = sum(z[vi]<5 for z in downstream.values())
                    po,pd,ps,p = parts(n,dn,ds,lengths[i],lengths[i+1],fd[i]['rho_crit'],fd[i+1]['rho_crit'],jam)
                    z = dict(case=case,time=t,cell=i,lane=lane,window=int(round(t-times[0],6)//150),n=n,s=s,dn=dn,ds=ds,
                             own=po,down=pd,down_slow=ps,p=p,rho=n/lengths[i],down_rho=dn/lengths[i+1])
                    for state, test in [('slow',lambda v:v<5),('moving',lambda v:v>=5)]:
                        current = {vid:v for vid,v in own.items() if test(v[vi])}
                        visible = {vid:v for vid,v in current.items() if vid in future}
                        stayers = {vid:v for vid,v in visible.items() if future[vid][ci]==i and future[vid][li]==lane}
                        endpoint = 'restart' if state=='slow' else 'onset'
                        z.update({state+'_visible':len(visible),state+'_stayers':len(stayers),
                                  state+'_missing':len(current)-len(visible),
                                  endpoint+'_visible':sum(not test(future[vid][vi]) for vid in visible),
                                  endpoint+'_stayers':sum(not test(future[vid][vi]) for vid in stayers)})
                    z['past_forward_crossing_lower_bound'] = sum(v[ci]==i and v[li]==lane and vid in now and now[vid][ci]>i
                                                               for vid,v in previous.items())
                    native.append(z)
    models = []; max_pressure_error = 0.; max_balance_error = 0.
    paths = []
    for mode in ('operator_train', 'refit_train'):
        rates = h.read(OLD/mode/'coefficients.json')
        paths.extend((mode, p, rates) for p in (OLD/mode/'forecast/queue').glob('*_phase.json.gz'))
    old_rates = h.read(h.R/'phase_equilibrium181/coefficients.json')
    paths.extend(('old181', h.R/'phase_equilibrium181/forecast/queue'/f's67_late_{arm}_phase.json.gz', old_rates)
                 for arm in ('hold','hold_vsl90','release','release_vsl90'))
    for mode, path, rates in paths:
        inputs[str(path)] = h.sha(path)
        data = h.read(path)
        ev = {(round(e['time_s'],6),e['cell'],e['lane']):e for e in data['events']}
        rows = {(round(e['time_s'],6),e['cell'],e['lane']):e for e in data['rows']}
        first = min(t for t,i,lane in ev)
        for (t,i,lane),e in ev.items():
            if i==25: continue  # downstream26 has no 1s lane phase trace
            downstream = ev[t,i+1,lane]
            n,s,dn,ds = e['n0'],e['s0'],downstream['n0'],downstream['s0']
            po,pd,ps,p = parts(n,dn,ds,lengths[i],lengths[i+1],fd[i]['rho_crit'],fd[i+1]['rho_crit'],jam)
            max_pressure_error = max(max_pressure_error, abs(p-e['pressure']))
            b = e['balance']; balance = s+b[0]-b[1]+b[2]-b[3]+b[4]-b[5]
            nxt = rows[round(t+1,6),i,lane]
            max_balance_error = max(max_balance_error, abs(balance-nxt['s']))
            beta = rates['release_per_sec']*(1-p)
            models.append(dict(case=mode+'/'+path.name.removesuffix('_phase.json.gz'),time=t,cell=i,lane=lane,
                window=int(round(t-first,6)//150),n=n,s=s,dn=dn,ds=ds,own=po,down=pd,down_slow=ps,p=p,
                rho=n/lengths[i],down_rho=dn/lengths[i+1],formation=e['onset'],release=e['release'],
                beta=beta,beta_without_own=rates['release_per_sec']*(1-min(1.,max(pd,ps))),
                macro_target=e['macro_target'],moving_target=e['moving_target'],
                space_change=n-e['n_next'],slow_net_transport=b[0]-b[1]+b[2]-b[3]))
    assert max_pressure_error < 1e-10 and max_balance_error < 1e-8
    support = []
    for case in sorted({z['case'] for z in native}):
        zz = [z for z in native if z['case']==case]
        support.append(dict(case=case,rows=len(zz),max_p=max(z['p'] for z in zz),
            p95=float(np.quantile([z['p'] for z in zz],.95)),p_ge095=sum(z['p']>=.95 for z in zz),
            slow_exposure=sum(z['s'] for z in zz),
            high_p_slow_exposure=sum(z['s'] for z in zz if z['p']>=.95),
            high_p_restart_visible=sum(z['restart_visible'] for z in zz if z['p']>=.95)))
    h.save(HERE/'config.json',config)
    h.save(HERE/'input_pins.json', inputs)
    for name, rows in [('native',native),('model',models)]:
        with gzip.open(HERE/f'{name}_rows.json.gz','wt',encoding='utf8') as f: json.dump(rows,f,allow_nan=False)
    h.save(HERE/'native_summary.json',grouped(native))
    h.save(HERE/'model_summary.json',grouped(models,True))
    h.save(HERE/'support.json',support)
    assert all(h.sha(h.ROOT/p)==v for p,v in core.items()) and h.sha(stop['path'])==stop['sha256']
    completion = dict(status='COMPLETE_SAVED_STATE_PRESSURE_DECOMPOSITION',native_rows=len(native),model_rows=len(models),
        pressure_max_error=max_pressure_error,balance_max_error=max_balance_error,
        fits=0,forecasts=0,new_native_runs=0,FZP_reads=0,production_adopted=False,
        protected_sources=len(core),old_STOP_preserved=True,elapsed_s=time.perf_counter()-start,
        goal='ACTIVE_NOT_QUALIFIED')
    h.save(HERE/'completion.json',completion)
    print(json.dumps(completion));print(json.dumps(support))


if __name__=='__main__': main()
