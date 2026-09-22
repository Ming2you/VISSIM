"""Compare actual NC/RM braking of the identical initial vehicle cohort.

Retrospective identification only. Native targets describe the preceding step;
no target identity or future speed is fed to a model forecast.
"""
from pathlib import Path
from collections import Counter, defaultdict
import bisect
import hashlib
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import first_merge_response as first

K = Path(__file__).resolve().parent
ROOT = K.parents[3]
H = K.parent


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def save(p, value):
    with p.open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2)


def physical(r):
    return tuple(r[k] for k in ('link', 'lane', 'pos', 'lateral', 'speed'))


def normalize(a):
    return dict(vehicle=int(a[1]), link=int(a[2]), lane=int(a[3]), pos=float(a[4]),
        lateral=float(a[5]), speed=float(a[6]), desired=float(a[9]), length=float(a[10]),
        lane_change=a[16], interaction=a[17], target_type=a[18],
        target=int(a[19]) if a[19] else None, original9=tuple(v.encode() for v in a[:9]))


def main():
    out = K / 'paired_native_interaction_v1'
    out.mkdir(exist_ok=False)
    rm_path = K / 'route_state_native_v1/rm_ramp_s23/analysis_v2/interaction_frames.json'
    payload = load(rm_path)
    nc_path = K / 'route_state_native_v1/none_s23/run_retry1/vissim_eval/baseline_001.fzp'
    nc, receipt = first.extended(nc_path)
    rm = {f['time_s']: {int(a[1]): normalize(a) for a in f['rows']} for f in payload['frames']}
    initial = {int(a[1]): normalize(a) for a in payload['global_initial_rows']}
    assert {i:r['original9'] for i,r in initial.items()} == {i:r['original9'] for i,r in nc[2400].items()}
    geometry_path = H / 'controller_response_s23_v1/none/geometry.json'
    geometry = load(geometry_path)
    shifts = {r['link']:r['offset_m'] for r in geometry['chains']['FW_E']}
    cells = sorted((r for r in geometry['cells'] if r['road']=='FW_E'), key=lambda r:r['cell'])
    bounds = [r['end_m'] for r in cells]
    def cell(r):
        return min(len(bounds)-1, bisect.bisect_right(bounds, shifts[r['link']]+r['pos']))
    cohort = {i for i,r in initial.items() if r['link'] in shifts}
    merged = {arm: {} for arm in ('none','rm')}
    series = {'none':nc,'rm':rm}
    # Known initial identities only; later births are not paired by numeric ID.
    for arm, frames in series.items():
        for t in range(2401,2461):
            for vid in initial:
                a,b = frames[t-1].get(vid), frames[t].get(vid)
                if a and b and a['link'] == 10490 and b['link'] in shifts:
                    merged[arm][vid] = t
    targets = set(merged['none']) | set(merged['rm'])
    step_rows, first_diff, targets_by_vehicle = [], {}, defaultdict(set)
    exposure_rows = []
    for t in range(2401,2461):
        totals = {arm:Counter() for arm in series}
        common = []
        for vid in sorted(cohort):
            values = {arm: frames[t].get(vid) for arm,frames in series.items()}
            before = {arm: frames[t-1].get(vid) for arm,frames in series.items()}
            if not all(values.values()) or not all(before.values()):
                continue
            if not all(r['link'] in shifts for r in list(values.values())+list(before.values())):
                continue
            common.append(vid)
            if physical(values['none']) != physical(values['rm']) and vid not in first_diff:
                first_diff[vid] = dict(time_s=t, initial_cell=cell(initial[vid]),
                    arms={a:{k:r[k] for k in r if k!='original9'} for a,r in values.items()})
            for arm,row in values.items():
                dv = row['speed']-before[arm]['speed']
                for region in ('all', 'initial13_14' if cell(initial[vid]) in (13,14) else 'initial_other'):
                    totals[arm][region+'_speed_sum'] += row['speed']
                    totals[arm][region+'_decel_kmh'] += max(0.,-dv)
                    totals[arm][region+'_accel_kmh'] += max(0.,dv)
                    totals[arm][region+'_native_brake_samples'] += row['interaction'].startswith('Brake')
                if row['target_type']=='Vehicle' and row['target'] in targets:
                    targets_by_vehicle[vid].add(row['target'])
                    exposure_rows.append(dict(arm=arm,time_s=t,vehicle=vid,target=row['target'],
                        cell=cell(row),lane=row['lane'],interaction=row['interaction'],
                        speed=row['speed'],delta_speed_kmh=dv,
                        target_merged_s=merged[arm].get(row['target']),
                        target_preceding_step=series[arm][t-1].get(row['target'],{}).get('link')))
        step_rows.append(dict(time_s=t,common_mainline_initial_ids=common,
            arms={a:dict(v) for a,v in totals.items()}))
    comparison=[]
    # All mainline vehicles actually interacting with any observed10490 entrant.
    for vid in sorted(targets_by_vehicle):
        rows = []
        for t in range(2400,2461):
            if vid not in nc[t] or vid not in rm[t]:
                continue
            rows.append(dict(time_s=t,arms={a:{k:r[k] for k in r if k!='original9'}
                for a,frames in series.items() for r in [frames[t][vid]]}))
        comparison.append(dict(vehicle=vid,initial_cell=cell(initial[vid]),
            target_ids=sorted(targets_by_vehicle[vid]),first_difference=first_diff.get(vid),rows=rows))
    by_target=[]
    for target in sorted(targets):
        stats={}
        for arm in series:
            rows=[r for r in exposure_rows if r['arm']==arm and r['target']==target]
            stats[arm]=dict(merge_s=merged[arm].get(target),subjects=sorted({r['vehicle'] for r in rows}),
                samples=len(rows),brake_samples=sum(r['interaction'].startswith('Brake') for r in rows),
                actual_decel_kmh=sum(max(0.,-r['delta_speed_kmh']) for r in rows),
                lanes=dict(Counter(r['lane'] for r in rows)))
        by_target.append(dict(target=target,arms=stats))
    summaries=[]
    for end in (2420,2430,2440,2460):
        samples=[r for r in step_rows if r['time_s']<=end]
        sums={a:Counter() for a in series}
        for r in samples:
            for a,values in r['arms'].items():sums[a].update(values)
        summaries.append(dict(end_s=end,matched_samples=sum(len(r['common_mainline_initial_ids']) for r in samples),
            arms={a:dict(v) for a,v in sums.items()},rm_minus_nc={k:sums['rm'][k]-v for k,v in sums['none'].items()}))
    assert first_diff[17532]['time_s']==2418
    save(out/'steps.json',step_rows)
    save(out/'exposure.json',exposure_rows)
    save(out/'vehicles.json',comparison)
    # Preserve native NC rows required for this bounded comparison, not the rawfile.
    nc_saved={str(t):[{k:r[k] for k in r if k!='original9'} for i,r in frame.items()
                      if i in cohort or i in targets] for t,frame in nc.items()}
    save(out/'nc_frames.json',nc_saved)
    sources=[Path(__file__),Path(first.__file__),rm_path,geometry_path]
    result=dict(qualified=False,initial_rows=len(initial),initial_mainline=len(cohort),
        paired_initial10490_targets=len(targets),first_differences=len(first_diff),
        first_difference_by_vehicle=first_diff,by_target=by_target,prefixes=summaries,
        source_pins={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        nc_source_receipt=receipt,new_native_runs=0,future_input_to_model=False,
        caveats=['Native targets describe preceding step; not a graph of independent causal effects.',
                 'Only initially identical IDs paired; missing/nonmainline samples excluded symmetrically.',
                 'Speed-sum differences and braking exposure are not450s residence-cost attribution.',
                 'All cohorts chosen by initial mainline location; target exposure uses observed outcomes for identification only.'])
    save(out/'result.json',result)
    print(json.dumps({k:result[k] for k in ('initial_rows','initial_mainline','paired_initial10490_targets','first_differences','by_target','prefixes')}))


if __name__=='__main__':main()
