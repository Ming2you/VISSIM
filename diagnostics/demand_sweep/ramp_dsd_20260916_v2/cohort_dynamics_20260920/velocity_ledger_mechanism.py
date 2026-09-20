"""Inspect current within-bin vehicle order behind the measured force error."""
from pathlib import Path
from collections import defaultdict
import bisect
import hashlib
import json
import math
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import velocity_ledger_audit as a

K, e, s, g = a.K, a.e, a.s, a.g
OUT = K/'velocity_ledger_mechanism_v1'


def main():
    OUT.mkdir(exist_ok=False)
    gp=s.d.H/'controller_response_s23_v1/none/geometry.json'
    geometry=e.load(gp);geo={r['cell']:r for r in geometry['cells'] if r['road']=='FW_E'}
    lp=a.OUT/'bin_ledger.json';ledger=e.load(lp)
    selected=[r for r in ledger if r['arm']=='none' and r['start']==2550 and r['cell']==16]
    native=K/'route_state_native_v1/none_s23/run_retry1/vissim_eval/baseline_001.fzp'
    end=s.d.END
    try:
        s.d.END=2580;frames,receipt=g.read(native,True,2519)
    finally:s.d.END=end
    located=s.locate(frames,geometry)
    inputs=s.initial_and_boundary(located,2550,geo,'lane_100m')
    bins=inputs['bins'];ends=[b['start']+1000*b['length'] for b in bins]
    output=[];examples=[]
    by_t=defaultdict(list)
    for row in selected:by_t[row['t']].append(row)
    for t, records in by_t.items():
        now=located[t];address={vid:(min(len(bins)-1,bisect.bisect_right(ends,r['x'])),r['lane'])
                               for vid,r in now.items() if r['cell']>=15}
        lanes=defaultdict(list)
        for vid,r in now.items():lanes[r['lane']].append((r['x'],vid))
        leaders={}
        for lane in lanes.values():
            lane.sort()
            leaders.update({v:w for (_,v),(_,w) in zip(lane,lane[1:])})
        for record in records:
            i,lane=record['i'],record['lane']
            own=[vid for vid,key in address.items() if key==(i,lane)]
            assert len(own)==record['n0']
            down=[vid for vid,key in address.items() if key==(i+1,lane)]
            rows=[]
            for vid in own:
                r=frames[t][vid];lead=leaders.get(vid);target=r['target']
                row=dict(vehicle=vid,x=now[vid]['x'],v=r['v'],interaction=r['interaction'],native_target=target,
                    actual_next_change=(frames[t+1][vid]['v']-r['v']) if vid in frames[t+1] else None,
                    previous_change=(r['v']-frames[t-1][vid]['v']) if vid in frames[t-1] else None)
                if lead is not None:
                    row.update(geometric_leader=lead,leader_v=frames[t][lead]['v'],
                        leader_same_bin=address.get(lead)==(i,lane),
                        geometric_gap_m=now[lead]['x']-now[vid]['x']-frames[t][lead]['length'])
                if target in now:
                    row.update(native_target_v=frames[t][target]['v'],native_target_lane=now[target]['lane'],
                               target_same_bin=address.get(target)==(i,lane))
                rows.append(row)
            row=dict(t=t,i=i,lane=lane,n_current=len(own),n_next=record['n'],
                own_density=len(own)/bins[i]['length'],downstream_density=len(down)/bins[i+1]['length'],
                current_v=record['current_v'],next_bin_v=sum(now[v]['v'] for v in down)/len(down) if down else None,
                model_reaction=record['model_reaction'],actual_destination_reaction=record['actual_reaction'],
                pressure=record['pressure'],vehicles=rows)
            output.append(row)
            if (t,i,lane) in ((2557,6,2),(2562,6,3),(2569,6,3)):examples.append(row)
    summaries=[]
    for name,predicate in (('all',lambda r:True),('positive_pressure_over1',lambda r:r['pressure']>1),
        ('negative_pressure_below_minus1',lambda r:r['pressure']< -1),
        ('wrong_sign',lambda r:r['model_reaction']>1 and r['actual_destination_reaction']< -1)):
        rs=[r for r in output if predicate(r)];vs=[v for r in rs for v in r['vehicles']]
        geometric=[v for v in vs if 'geometric_leader' in v]
        targets=[v for v in vs if 'native_target_v' in v]
        summaries.append(dict(scope=name,bin_rows=len(rs),current_vehicle_seconds=len(vs),
            geometric_known=len(geometric),leader_same_bin=sum(v['leader_same_bin'] for v in geometric),
            overlapping_projection=sum(v['geometric_gap_m']<0 for v in geometric),
            native_target_known=len(targets),native_target_same_bin=sum(v['target_same_bin'] for v in targets),
            geometric_gap_mean=sum(v['geometric_gap_m'] for v in geometric)/len(geometric)))
    e.save(OUT/'current_vehicle_cases.json',output)
    files=[Path(__file__),Path(a.__file__),gp,lp]
    e.save(OUT/'result.json',dict(qualified=False,new_native_runs=0,summaries=summaries,examples=examples,
        source_receipt=receipt,source_pins={p.relative_to(s.d.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        limitations=['Examples chosen after inspecting ledger errors, not a held-out performance test.',
            'Current-bin residents and next-bin reaction labels have different memberships; both are identified explicitly.',
            'Native target/state reflect the previous internal simulation step; do not infer instantaneous causation.',
            'Leader remaining inside a bin is evidence of within-bin heterogeneity, not a zero-capacity rule.',
            'This only diagnoses the existing local100m response and does not prove a proposed replacement law.']))
    print(json.dumps(summaries))


if __name__=='__main__':main()
