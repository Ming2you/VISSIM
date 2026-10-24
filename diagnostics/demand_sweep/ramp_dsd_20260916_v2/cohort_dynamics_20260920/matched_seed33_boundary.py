"""Exact native boundary/cohort accounting for the beneficial2550 RM state."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import marginal_boundary_timing as a

K, e = Path(__file__).resolve().parent, a.m.e
OUT = K / 'matched_seed33_boundary_v1'
BANK = K / 'matched_meter_midpoint_s33_v2'


def analyze(path, geometry):
    chain = {r['link']:r for r in geometry['chains']['FW_E']}
    ports = {r['connector']:r for r in geometry['boundaries'] if r['road']=='FW_E' and r['kind'] in ('ramp','offramp')}
    source = {r['to_link'] for r in geometry['boundaries'] if r['road']=='FW_E' and r['kind']=='source'}
    terminal = geometry['chains']['FW_E'][-1]
    stamp = path.stat()
    previous = initial = initial_ids = None
    trace, events, prefixes = [], [], {}
    stock_seconds = cohort_seconds = 0
    for t, frame in a.frames(path, set(chain)|set(ports)):
        main = {v:r for v,r in frame.items() if r['link'] in chain}
        if t == a.START:
            initial, initial_ids = frame, set(main)
        else:
            old = {v:r for v,r in previous.items() if r['link'] in chain}
            delta = 0
            for v, row in main.items():
                if v in old:
                    continue
                before = previous.get(v)
                if before and before['link'] in ports and ports[before['link']]['kind']=='ramp':
                    kind = 'merge_'+str(before['link'])
                elif before is None and row['link'] in source:
                    kind = 'source'
                else:
                    raise AssertionError(('Unclassified entry',t,v,before,row))
                events.append(dict(time_s=t,vehicle=v,kind=kind,sign=1));delta += 1
            for v, row in old.items():
                if v in main:
                    continue
                now = frame.get(v)
                if now and now['link'] in ports and ports[now['link']]['kind']=='offramp':
                    kind = 'off_'+str(now['link'])
                elif now is None and row['link']==terminal['link'] and row['pos']+row['speed']/3.6+3>=terminal['length_m']:
                    kind = 'terminal_inferred'
                else:
                    raise AssertionError(('Unclassified exit',t,v,row,now))
                events.append(dict(time_s=t,vehicle=v,kind=kind,sign=-1));delta -= 1
            assert len(main)-len(old)==delta
            stock_seconds += len(main)
            cohort_seconds += len(initial_ids & main.keys())
        trace.append(dict(time_s=t,n=len(main),initial_cohort_n=len(initial_ids & main.keys())))
        if t in (2700,2850,3000):
            moments = Counter();counts = Counter()
            for row in events:
                moments[row['kind']] += row['sign']*(t-row['time_s']+1)/3600
                counts[row['kind']] += 1
            assert abs(stock_seconds/3600-len(initial_ids)*(t-a.START)/3600-sum(moments.values()))<1e-8
            prefixes[str(t)] = dict(ttt_veh_h=stock_seconds/3600, initial_cohort_ttt_veh_h=cohort_seconds/3600,
                                    later_cohort_ttt_veh_h=(stock_seconds-cohort_seconds)/3600,
                                    moments=dict(moments), counts=dict(counts))
        previous = frame
    assert t==a.END and len(trace)==451
    assert (stamp.st_size,stamp.st_mtime_ns)==(path.stat().st_size,path.stat().st_mtime_ns)
    return dict(initial_frame=initial,initial_mainline=len(initial_ids),trace=trace,events=events,prefixes=prefixes,
        source_receipt=dict(path=path.relative_to(e.ROOT).as_posix(),bytes=stamp.st_size,mtime_ns=stamp.st_mtime_ns))


def main():
    OUT.mkdir(exist_ok=False)
    reference=e.load(BANK/'result.json')
    geometry=e.load(BANK/'observations/rm8/geometry.json')
    runs={arm:(BANK/('run_'+arm) if arm!='rm_ramp' else
               K.parent/'state_response_20260919/native_s33_v1/run_rm_ramp') for arm in ('rm8','rm6','rm_ramp')}
    results={};common=None
    for arm,run in runs.items():
        result=analyze(run/'vissim_eval/baseline_001.fzp',geometry)
        frame=result.pop('initial_frame')
        if common is None:common=frame
        else:assert frame==common
        assert abs(result['prefixes']['3000']['ttt_veh_h']-reference['actual'][arm]['component']['mainline'])<1e-8
        e.save(OUT/(arm+'.json'),result);results[arm]=result
        print('COMPLETE',arm,result['prefixes']['3000'],flush=True)
    deltas={}
    for arm in ('rm6','rm_ramp'):
        deltas[arm]={}
        for t in ('2700','2850','3000'):
            ref,row=results['rm8']['prefixes'][t],results[arm]['prefixes'][t]
            difference={k:row[k]-ref[k] for k in ('ttt_veh_h','initial_cohort_ttt_veh_h','later_cohort_ttt_veh_h')}
            difference['boundary_moments']={k:row['moments'].get(k,0)-ref['moments'].get(k,0)
                for k in row['moments'].keys()|ref['moments'].keys()}
            difference['boundary_counts']={k:row['counts'].get(k,0)-ref['counts'].get(k,0)
                for k in row['counts'].keys()|ref['counts'].keys()}
            assert abs(sum(difference['boundary_moments'].values())-difference['ttt_veh_h'])<1e-8
            deltas[arm][t]=difference
    e.save(OUT/'result.json',dict(qualified=False,initial_mainline=results['rm8']['initial_mainline'],
        continuity_steps=1350,identical_initial_frames=True,deltas=deltas,
        status='POST_RUN_ACCOUNTING_NOT_CAUSAL_PREDICTION',future_information_used_as_model_input=False,
        limitations=['Boundary timing contributions are not separable intervention effects.',
                     'Only initial vehicle IDs matched; later cohorts are not paired by numeric ID.',
                     'Component mainline only; ramps/off ports are in the referenced cost result.',
                     'Terminal disappearance checked from last position and speed; no unexplained loss accepted.'],
        source_pins={p.relative_to(e.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (Path(__file__),Path(a.__file__),BANK/'result.json',BANK/'observations/rm8/geometry.json')}))
    print(json.dumps(deltas),flush=True)


if __name__=='__main__':main()
