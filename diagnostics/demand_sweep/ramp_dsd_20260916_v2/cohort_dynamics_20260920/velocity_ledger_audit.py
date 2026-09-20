"""Exact offline velocity ledger: mixing, same-vehicle response, and weights.

Future membership supplies evaluation labels only. The unchanged model is
reset to each current native state; this is not an autonomous forecast gate.
"""
from pathlib import Path
from collections import Counter, defaultdict
import bisect
import hashlib
import json
import math
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import target_acceleration_coupling as c

K, e, s, g = c.K, c.e, c.s, c.g
OUT = K / 'velocity_ledger_audit_v1'
STARTS = (2280, 2400, 2550, 2700)


def statistics(rows, names, weight):
    total = sum(r[weight] for r in rows)
    assert total > 0
    return dict(rows=len(rows), weight=total, terms={name:dict(
        bias=sum(r[weight]*r[name] for r in rows)/total,
        rmse=math.sqrt(sum(r[weight]*r[name]**2 for r in rows)/total)) for name in names})


def labels(now, nxt, bins):
    """Mean current velocity of next-bin members plus their actual change."""
    ends = [b['start']+b['length']*1000 for b in bins]
    def address(row):
        return min(len(bins)-1, bisect.bisect_right(ends, row['x'])), row['lane']-1
    groups = defaultdict(list)
    for vid, row in nxt.items():
        if row['cell'] >= 15:
            groups[address(row)].append((vid, row))
    result = {}
    for key, members in groups.items():
        complete = [(vid, row, now[vid]) for vid, row in members if vid in now]
        values = dict(n=len(members), missing_current=len(members)-len(complete),
                      observed_v=sum(r['v'] for _, r in members)/len(members))
        if len(complete) == len(members):
            carrier = sum(before['v'] for _, _, before in complete)/len(complete)
            reaction = sum(row['v']-before['v'] for _, row, before in complete)/len(complete)
            assert abs(carrier+reaction-values['observed_v']) < 1e-10
            groups_count = Counter()
            for vid, row, before in complete:
                prior = address(before) if before['cell'] >= 15 else None
                kind = ('upstream_entry' if prior is None else 'same_bin_lane' if prior == key
                        else 'longitudinal' if prior[1] == key[1] else 'lateral_same_bin' if prior[0] == key[0]
                        else 'longitudinal_and_lateral')
                groups_count[kind] += 1
            values.update(carrier=carrier, reaction=reaction, transitions=dict(groups_count))
        result[key] = values
    return result


def main():
    OUT.mkdir(exist_ok=False)
    gp = s.d.H/'controller_response_s23_v1/none/geometry.json'
    cp = K/'transport_step1_exchange_off_v2/config.json'
    pp = K/'port_travel_fit_v1/selected_parameters.json'
    op = K/'compact_lane_state_v1/states.json'
    geometry, observed = e.load(gp), e.load(op)
    geo = {r['cell']:r for r in geometry['cells'] if r['road']=='FW_E'}
    model = e.load_base_model(geometry, cp)
    cfg = model._config('FW_E', e.load(pp)['parameters']['by_direction']['FW_E'])
    all_bins, all_cells, receipts, unavailable = [], [], {}, []
    prefixes = {'none':'run_retry1', 'rm_ramp':'run', 'vsl':'run_retry1'}
    max_mass = 0.
    for arm, run in prefixes.items():
        path = K/f'route_state_native_v1/{arm}_s23/{run}/vissim_eval/baseline_001.fzp'
        end = s.d.END
        try:
            s.d.END = max(STARTS)+30
            frames, receipts[arm] = g.read(path, True, min(STARTS)-30)
        finally:
            s.d.END = end
        located = s.locate(frames, geometry)
        for start in STARTS:
            for t in range(start, start+30):
                # Explicitly check this initializer's observation requirement;
                # do not catch arbitrary model assertions as missing data.
                lanes = {r['lane'] for r in located[t].values() if r['cell']==14}
                if lanes != {1, 2, 3}:
                    unavailable.append(dict(arm=arm, t=t, reason='missing_upstream_lane', lanes=sorted(lanes)))
                    continue
                inputs = s.initial_and_boundary(located, t, geo, 'lane_100m')
                trace, checks = s.rollout(inputs, cfg, 1, momentum_advection=True, collect_speed_terms=True)
                max_mass = max(max_mass, checks['max_mass_residual'])
                truth = labels(located[t], located[t+1], inputs['bins'])
                by_cell = defaultdict(list)
                for term in checks['speed_terms']:
                    i, lane = term['i'], term['g']
                    label = truth.get((i, lane))
                    if label is None:
                        continue
                    if label['missing_current']:
                        unavailable.append(dict(arm=arm, t=t, i=i, lane=lane,
                                                reason='missing_current_vehicle', **label))
                        continue
                    prediction = term['actual_function_value']
                    reaction = prediction-term['carrier']
                    mixing_error = term['carrier']-label['carrier']
                    reaction_error = reaction-label['reaction']
                    error = prediction-label['observed_v']
                    assert abs(error-mixing_error-reaction_error) < 1e-10
                    row = dict(arm=arm, start=start, t=t, i=i, lane=lane+1,
                        cell=inputs['bins'][i]['cell'], n=label['n'], n0=inputs['n'][i][lane],
                        current_v=inputs['v'][i][lane], actual=label, model=term,
                        mixing_error=mixing_error, reaction_error=reaction_error, error=error,
                        actual_reaction=label['reaction'], model_reaction=reaction,
                        pressure=term['pressure'], relaxation=term['relax'],
                        floor_correction=prediction-(term['carrier']+term['relax']+term['convection']+term['pressure']))
                    all_bins.append(row)
                    by_cell[row['cell']].append(row)
                for cell, rows in by_cell.items():
                    n = sum(r['n'] for r in rows)
                    target = observed[arm]['states'][str(t+1)][str(cell)]
                    # An incomplete destination membership must not be
                    # presented as a whole-cell decomposition.
                    if n != target['n']:
                        unavailable.append(dict(arm=arm, t=t, cell=cell, reason='incomplete_cell', known=n, actual=target['n']))
                        continue
                    actual = sum(r['n']*r['actual']['observed_v'] for r in rows)/n
                    assert abs(actual-target['v']) < 1e-8
                    reweighted = sum(r['n']*r['model']['actual_function_value'] for r in rows)/n
                    mixing = sum(r['n']*r['mixing_error'] for r in rows)/n
                    reaction = sum(r['n']*r['reaction_error'] for r in rows)/n
                    aggregate = trace[0]['cells'][cell]
                    weights = aggregate['v']-reweighted
                    error = aggregate['v']-actual
                    assert abs(error-mixing-reaction-weights) < 1e-8
                    all_cells.append(dict(arm=arm, start=start, t=t, cell=cell, n=n,
                        prediction=aggregate, actual=dict(n=n, v=actual), weight=1,
                        mixing_error=mixing, reaction_error=reaction, composition_weight_error=weights,
                        error=error, stock_error=aggregate['n']-n))
            print('LEDGER', arm, start, flush=True)
        del frames, located
    e.save(OUT/'bin_ledger.json', all_bins)
    e.save(OUT/'cell_ledger.json', all_cells)
    summaries = []
    for arm in prefixes:
        for start in STARTS:
            for scope in ('all15_20', 'cell16'):
                select = lambda row: row['arm']==arm and row['start']==start and (scope=='all15_20' or row['cell']==16)
                bs = [r for r in all_bins if select(r)]
                cs = [r for r in all_cells if select(r)]
                summaries.append(dict(arm=arm, start=start, scope=scope,
                    bins=statistics(bs, ('mixing_error','reaction_error','error','actual_reaction','model_reaction','pressure','relaxation','floor_correction'), 'n'),
                    cells=statistics(cs, ('mixing_error','reaction_error','composition_weight_error','error','stock_error'), 'weight')))
    sources = [Path(__file__), Path(s.__file__), Path(g.__file__), Path(s.d.__file__), gp, cp, pp, op]
    e.save(OUT/'result.json', dict(qualified=False, production_adopted=False, new_native_runs=0,
        forecast_type='one-step reset to current native state, causal model inputs; future membership labels only',
        starts=STARTS, seconds_per_window=30, summaries=summaries, unavailable=unavailable,
        bin_rows=len(all_bins), cell_rows=len(all_cells), max_mass_residual=max_mass,
        source_receipts=receipts,
        source_pins={p.relative_to(s.d.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        limitations=['Not recursive, gain, or full Omega qualification.',
            'Post-treatment states differ; this does not estimate a matched-state causal control effect.',
            'Bin metrics weight actual next vehicle counts, cell metrics weight each cell-second equally.',
            'Composition term includes predicted stock weights and predicted occupied bins absent in reality.',
            'Error terms can cancel; RMSEs are not additive or causal percentages.']))
    print(json.dumps(dict(bin_rows=len(all_bins), cell_rows=len(all_cells), unavailable=len(unavailable), max_mass=max_mass)))


if __name__ == '__main__':
    main()
