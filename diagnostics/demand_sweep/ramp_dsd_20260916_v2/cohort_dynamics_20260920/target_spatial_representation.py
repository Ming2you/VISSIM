"""Can conserved spatial summaries retain the measured target-history signal?

Target-address means are optimistic: they know the currently observed target's
address. Forward exposure uses only the subject's lane/bin and neighboring
current bins. Neither receives future positions, targets or accelerations.
"""
from pathlib import Path
from collections import defaultdict, Counter
import bisect
import hashlib
import json
import math
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import interaction_duration_audit as a

K, e, c = a.K, a.e, a.c
OUT = K/'target_spatial_representation_v1'
FEATURES = ('target_history_bin', 'target_lane_cell_bin', 'target_lane100m_bin', 'forward_lane100m_bin')
EDGES = (-7.2, -1., 1., 7.2)


def grid(geometry):
    geo = {r['cell']: r for r in geometry['cells'] if r['road'] == 'FW_E'}
    bins = []
    for cell, row in sorted(geo.items()):
        count = math.ceil(row['length_km']*10)
        length = row['length_km']/count
        for j in range(count):
            bins.append(dict(cell=cell, length=length, start=row['start_m']+j*length*1000))
    return geo, bins


def summaries(frame, previous, geometry, geo, bins):
    shifts = {r['link']:r['offset_m'] for r in geometry['chains']['FW_E']}
    ends = [b['start']+b['length']*1000 for b in bins]
    groups = {'coarse':defaultdict(list), 'fine':defaultdict(list)}
    address, dv = {}, {}
    for vid, row in frame.items():
        i = min(len(bins)-1, bisect.bisect_right(ends, shifts[row['link']]+row['pos']))
        address[vid] = (bins[i]['cell'], i, row['lane'])
        before = previous.get(vid)
        if before is not None:
            dv[vid] = row['v']-before['v']
        groups['coarse'][bins[i]['cell'],row['lane']].append(vid)
        groups['fine'][i,row['lane']].append(vid)
    values = {}
    for name, bank in groups.items():
        values[name] = {key:dict(n=len(ids), known=sum(i in dv for i in ids),
            speed_sum=sum(frame[i]['v'] for i in ids), accel_sum=sum(dv[i] for i in ids if i in dv))
            for key, ids in bank.items()}
    return address, dv, values


def attach(records, frames, geometry, geo, bins):
    by_time = defaultdict(list)
    for r in records:
        by_time[r['time_s']].append(r)
    metrics = {f:Counter() for f in FEATURES[1:]}
    saved = {}
    for t, rs in by_time.items():
        frame = frames[t]
        address, dv, values = summaries(frame, frames[t-1], geometry, geo, bins)
        for r in rs:
            vid = r['vehicle']; target = frame[vid]['target']
            own_cell, own_bin, own_lane = address[vid]
            target_cell, target_bin, target_lane = address[target]
            estimates = {}
            for feature, name, key in (
                ('target_lane_cell_bin', 'coarse', (target_cell,target_lane)),
                ('target_lane100m_bin', 'fine', (target_bin,target_lane))):
                group = values[name][key]
                estimates[feature] = group['accel_sum']/group['known'] if group['known'] else None
            own = values['fine'][own_bin,own_lane]
            others = own['known']-(vid in dv)
            other_mean = (own['accel_sum']-dv.get(vid,0.))/others if others else None
            downstream = next((values['fine'][j,own_lane] for j in range(own_bin+1,len(bins))
                               if (j,own_lane) in values['fine']), None)
            down_mean = (downstream['accel_sum']/downstream['known']
                         if downstream and downstream['known'] else None)
            # Uniform order in the current bin: probability1/n that the
            # subject is the last vehicle before the next occupied bin.
            # This approximation is tested, not assumed to be a true bound.
            p = 1./own['n']
            estimates['forward_lane100m_bin'] = (None if down_mean is None or (p<1 and other_mean is None)
                else p*down_mean+(1-p)*(other_mean if other_mean is not None else 0.))
            truth = dv.get(target)
            r['target_history_bin'] = -1 if truth is None else bisect.bisect_right(EDGES, truth)
            for feature, value in estimates.items():
                r[feature] = -1 if value is None else bisect.bisect_right(EDGES,value)
                if 2400 <= t <= 2840:
                    m = metrics[feature]
                    m['rows'] += 1
                    if truth is None or value is None:
                        m['unknown'] += 1
                    else:
                        m['known'] += 1
                        m['bin_equal'] += r[feature] == r['target_history_bin']
                        m['squared_error_kmh2'] += (value-truth)**2
                        m['absolute_error_kmh'] += abs(value-truth)
            if t in (2280,2400,2550,2700):
                saved.setdefault(t,[]).append({k:r[k] for k in ('vehicle','cell',*FEATURES)})
    return {f:dict(v) for f,v in metrics.items()}, saved


def evaluate(rs, lo, hi, tables, means, models):
    result = {}
    for f in FEATURES:
        scores = a.score(rs,lo,hi,tables,means,models[f],f)
        result[f] = {h:row[f] for h,row in scores.items()}
        if f == FEATURES[0]:
            result['existing'] = {h:row['existing'] for h,row in scores.items()}
    return result


def main():
    OUT.mkdir(exist_ok=False)
    gp = c.d.H/'controller_response_s23_v1/none/geometry.json'
    network = c.d.H/'source_dsd/baseline.inpx'
    bp = K/'current_interaction_response_v1/training_table.json'
    tp = K/'target_history_audit_v1/training_table.json'
    rp = K/'target_history_audit_v1/result.json'
    geometry = e.load(gp); geo,bins = grid(geometry)
    params = c.g.restart.native_parameters(network)
    doc = e.load(bp); tables,means = a.base_model(doc),doc['global_mean']
    prior = e.load(rp)
    scores, represent, receipts, coverage = {}, {}, {}, {}
    exact = 0
    for arm, folder, lo in (('none','none_s23/run_retry1',899),
                           ('rm_ramp','rm_ramp_s23/run',2249),('vsl','vsl_s23/run_retry1',2249)):
        frames,receipts[arm] = c.g.read(K/'route_state_native_v1'/folder/'vissim_eval/baseline_001.fzp',True,lo)
        rs,coverage[arm] = c.records(frames,geometry,params,900 if arm=='none' else 2250)
        represent[arm],snapshots = attach(rs,frames,geometry,geo,bins)
        e.save(OUT/f'features_{arm}.json',snapshots)
        if arm == 'none':
            models = {f:a.fit(rs,f)[0] for f in FEATURES}
            old = {tuple(r['key']):{int(h):(v['n'],v['mean']) for h,v in r['targets'].items()}
                   for r in e.load(tp)['table']}
            assert models[FEATURES[0]] == old
            e.save(OUT/'models.json',{f:[dict(key=list(k),targets={str(h):dict(n=v[0],mean=v[1]) for h,v in ys.items()})
                for k,ys in table.items()] for f,table in models.items()})
            scores['nc_time_validation'] = evaluate(rs,2100,2400,tables,means,models)
            scores['focused_cell16'] = evaluate([r for r in rs if r['cell']==16 and r['time_s']<2580],2550,2590,tables,means,models)
        label = 'nc_control' if arm=='none' else arm+'_control'
        scores[label] = evaluate(rs,2400,2850,tables,means,models)
        for period in (('nc_time_validation','focused_cell16','nc_control') if arm=='none' else (label,)):
            for h in ('1','5','10'):
                for name in ('existing','target_history_bin'):
                    assert scores[period][name][h] == prior['scores'][period][h][name]
                    exact += 1
        e.save(OUT/f'scores_{arm}.json',{k:v for k,v in scores.items() if arm=='none' or k==label})
        print(json.dumps(dict(arm=arm,score5={k:v['5'] for k,v in scores[label].items()},representation=represent[arm])),flush=True)
        del frames,rs
    sources = [Path(__file__),Path(a.__file__),Path(c.__file__),gp,network,bp,tp,rp,OUT/'models.json']
    e.save(OUT/'result.json',dict(qualified=False,production_adopted=False,new_native_runs=0,
        scores=scores,representation=represent,coverage=coverage,source_receipts=receipts,old_scores_exact=exact,
        source_pins={p.relative_to(c.d.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        training='NC900..2090, labels through2100; proxy models refit on same rows, no controlled outcomes.',
        limitations=['Conditional current-state representation test, not autonomous or450s gain validation.',
            'Target-cell and target100m averages know the current native target address: optimistic information-retention tests.',
            'Forward100m uses own bin/next occupied same-lane bin without target identity; uniform within-bin order is an unvalidated closure.',
            'Means use same-vehicle current-minus-previous speed, not temporal mean-speed differences confounded by transport.',
            'No desired-speed input or future positions, lane changes, targets or velocities are used as features.',
            'Shared inspected seed23; spatial means can contain the target itself and are not independent observations.']))


if __name__ == '__main__':
    main()
