"""One-second mainline residence accounting for the matched2550s RM pair.

Retrospective evidence only. Interface moments are accounting contributions,
not causal effects of independently changing each interface.
"""
from pathlib import Path
from collections import Counter, defaultdict
import bisect
import csv
import hashlib
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import matched_meter_increment as m

HERE, START, END = m.HERE, m.START, m.END


def frames(path, links):
    frame, last, active = {}, None, False
    with path.open('rb') as f:
        for line in f:
            if line.startswith(b'$VEHICLE:'):
                assert len(line.strip().split(b';')) == 9
                active = True
                continue
            if not active or not line.strip():
                continue
            t = float(line.partition(b';')[0])
            if t < START:
                continue
            if t > END:
                break
            assert t == int(t)
            t = int(t)
            if last is not None and t != last:
                assert t == last+1
                yield last, frame
                frame = {}
            last = t
            values = line.rstrip().split(b';')
            link = int(values[2])
            if link not in links:
                continue
            vid = int(values[1])
            assert vid not in frame
            frame[vid] = dict(link=link, lane=int(values[3]), pos=float(values[4]), speed=float(values[6]))
    assert last == END
    yield last, frame


def audit(arm, geometry):
    path = m.BANK / f'run_{arm}' / 'vissim_eval/baseline_001.fzp'
    stamp = path.stat()
    chain = {r['link']:r for r in geometry['chains']['FW_E']}
    source = {r['to_link'] for r in geometry['boundaries'] if r['road']=='FW_E' and r['kind']=='source'}
    ports = {r['connector']:r for r in geometry['boundaries'] if r['road']=='FW_E' and r['kind'] in ('ramp','offramp')}
    terminal = geometry['chains']['FW_E'][-1]
    bounds = [r['end_m'] for r in geometry['cells'] if r['road']=='FW_E']
    with (m.BANK/'analysis'/arm/'stocks_1s.csv').open(encoding='utf-8-sig') as f:
        stock_record = {int(r['time_s']):int(r['FW_E_n']) for r in csv.DictReader(f)}
    data = m.e.ObservationData(m.BANK/'observations'/arm)
    previous, initial_ids, cohort_seconds, cohort_last = {}, set(), Counter(), {}
    trace, events = [], []
    entry_events, exit_events = Counter(), Counter()
    cell_seconds = Counter()
    for t, frame in frames(path, set(chain)|set(ports)):
        # Keep the previous published whole-link1s cost AND separately track
        # negative-position source rows excluded by geometric location.
        main = {vid:r for vid,r in frame.items() if r['link'] in chain}
        assert len(main) == stock_record[t], (arm,t,'one-second stock')
        negative = sum(chain[r['link']]['offset_m']+r['pos']<0 for r in main.values())
        if t == START:
            initial_ids = set(main)
        else:
            old = {vid:r for vid,r in previous.items() if r['link'] in chain}
            changes = Counter()
            for vid,r in main.items():
                if vid in old:
                    continue
                before = previous.get(vid)
                if before and before['link'] in ports and ports[before['link']]['kind']=='ramp':
                    name='merge_'+str(before['link'])
                elif r['link'] in source and before is None:
                    name='source'
                else:
                    raise AssertionError(('Unknown mainline entry',arm,t,vid,before,r))
                changes[name]+=1;entry_events[t,name]+=1
                events.append(dict(time_s=t,vehicle=vid,kind=name,sign=1,initial_vehicle=vid in initial_ids))
            for vid,r in old.items():
                if vid in main:
                    continue
                now=frame.get(vid)
                if now and now['link'] in ports and ports[now['link']]['kind']=='offramp':
                    name='off_'+str(now['link'])
                elif now is None and r['link']==terminal['link'] and r['pos']+r['speed']/3.6+3>=terminal['length_m']:
                    name='terminal_inferred'
                else:
                    raise AssertionError(('Unknown mainline exit',arm,t,vid,r,now))
                changes[name]-=1;exit_events[t,name]+=1
                events.append(dict(time_s=t,vehicle=vid,kind=name,sign=-1,initial_vehicle=vid in initial_ids))
            assert len(main)-len(old)==sum(changes.values())
            for vid,r in main.items():
                cohort_seconds[vid]+=1
                cohort_last[vid]=t
                cell=min(20,max(0,bisect.bisect_right(bounds,chain[r['link']]['offset_m']+r['pos'])))
                cell_seconds[(t,cell)]+=1
            if t%30==0:
                for c in range(21):
                    expected=next(r['n_veh'] for r in data.cells[t] if r['road']=='FW_E' and r['cell']==c)
                    # The canonical locator excludes negative source rows.
                    assert cell_seconds[t,c]-(negative if c==0 else 0)==expected,(arm,t,c)
        trace.append(dict(time_s=t,n=len(main),negative_source_positions=negative,
                          initial_cohort_n=sum(vid in initial_ids for vid in main)))
        previous=frame
    assert len(trace)==451
    assert (stamp.st_size,stamp.st_mtime_ns)==(path.stat().st_size,path.stat().st_mtime_ns)
    result={}
    for end in (2700,2850,3000):
        selected=[r for r in trace if START<r['time_s']<=end]
        moments=Counter();counts=Counter()
        for r in events:
            if r['time_s']<=end:
                moments[r['kind']]+=r['sign']*(end-r['time_s']+1)/3600
                counts[r['kind']]+=1
        ttt=sum(r['n'] for r in selected)/3600
        identity=trace[0]['n']*(end-START)/3600+sum(moments.values())
        assert abs(ttt-identity)<1e-8
        result[str(end)]=dict(ttt_veh_h=ttt,located_ttt_veh_h=ttt-sum(r['negative_source_positions'] for r in selected)/3600,
            initial_cohort_ttt=sum(r['initial_cohort_n'] for r in selected)/3600,
            later_cohort_ttt=sum(r['n']-r['initial_cohort_n'] for r in selected)/3600,
            end_n=selected[-1]['n'],moments=dict(moments),counts=dict(counts),identity_residual=ttt-identity,
            cell_ttt={str(c):sum(n for (t,j),n in cell_seconds.items() if j==c and t<=end)/3600 for c in range(21)})
    return dict(prefix=result,events=events,trace=trace,initial_ids=sorted(initial_ids),
                initial_cohort_residence_s={str(v):cohort_seconds[v] for v in sorted(initial_ids)},
                initial_cohort_last_mainline_s={str(v):cohort_last.get(v,START) for v in sorted(initial_ids)},
                receipt=dict(path=str(path.relative_to(m.e.ROOT)),bytes=stamp.st_size,mtime_ns=stamp.st_mtime_ns),
                checks=dict(one_second_stock=451,cell_snapshots=315,continuity=450,unknown_transitions=0))


def main():
    out=HERE/'marginal_boundary_timing_v1';out.mkdir(exist_ok=False)
    geometry=m.e.ObservationData(m.BANK/'observations/rm8').geometry
    records={}
    for arm in m.ARMS:
        records[arm]=audit(arm,geometry)
        m.e.save(out/f'{arm}.json',records[arm])
        print('AUDITED',arm,records[arm]['prefix']['3000']['ttt_veh_h'],flush=True)
    a,b=records['rm8'],records['rm_ramp']
    assert a['initial_ids']==b['initial_ids']
    result={}
    for t in a['prefix']:
        base,ctl=a['prefix'][t],b['prefix'][t]
        moments={k:ctl['moments'].get(k,0)-base['moments'].get(k,0) for k in base['moments'].keys()|ctl['moments'].keys()}
        delta=ctl['ttt_veh_h']-base['ttt_veh_h']
        assert abs(sum(moments.values())-delta)<1e-8
        result[t]=dict(delta_ttt=delta,delta_located_ttt=ctl['located_ttt_veh_h']-base['located_ttt_veh_h'],
            delta_initial_cohort=ctl['initial_cohort_ttt']-base['initial_cohort_ttt'],
            delta_later_cohort=ctl['later_cohort_ttt']-base['later_cohort_ttt'],
            signed_moment_differences=moments,delta_end_n=ctl['end_n']-base['end_n'],
            delta_counts={k:ctl['counts'].get(k,0)-base['counts'].get(k,0) for k in base['counts'].keys()|ctl['counts'].keys()},
            delta_cell_ttt={k:ctl['cell_ttt'][k]-base['cell_ttt'][k] for k in base['cell_ttt']})
    ranked=sorted([dict(vehicle=int(v),delta_residence_s=b['initial_cohort_residence_s'][v]-s,
                        base_s=s,controlled_s=b['initial_cohort_residence_s'][v])
                   for v,s in a['initial_cohort_residence_s'].items()],key=lambda r:abs(r['delta_residence_s']),reverse=True)
    m.e.save(out/'result.json',dict(status='RETROSPECTIVE_BOUNDARY_TIMING',qualified=False,prefix=result,
        initial_vehicle_residence_differences=ranked,
        accounting='Each prefix recomputes its own (prefix_end-event_time+1) weights. Contributions are bookkeeping,not independent causal effects.',
        scope='FW_E mainline1s whole-link convention matches archived stock CSV;located alternative excludes negative source coordinates.',
        new_native_runs=0,production_changes=0,
        pins={p.relative_to(m.e.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),HERE/'matched_meter_increment.py']}))
    print('PREFIX',result,flush=True)


if __name__=='__main__':
    main()
