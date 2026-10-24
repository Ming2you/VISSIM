"""Same-cohort native reaction audit of the local population closure.

Reuses frozen NC-trained predictors. Native future rows are labels only.
No refit, controller, actuator or network changes; no gain qualification.
"""
from pathlib import Path
from collections import defaultdict, Counter
import ast, bisect, hashlib, math, sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import speed_population as p
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import current_gap_history as h


def summary(rows, name):
    error = [r['predicted'][name] - r['actual_dv'] for r in rows]
    return dict(n=len(rows), rmse_kmh=math.sqrt(sum(x*x for x in error)/len(error)),
                bias_kmh=sum(error)/len(error)) if error else dict(n=0)


def main():
    out = p.d.HERE / 'population_reaction_audit_v1'
    out.mkdir(exist_ok=False)
    gp = p.d.H / 'controller_response_s23_v1/none/geometry.json'
    geometry = p.d.e.load(gp)
    geo = {r['cell']: r for r in geometry['cells'] if r['road'] == 'FW_E'}
    network = p.d.H / 'source_dsd/baseline.inpx'
    parameters = h.g.restart.native_parameters(network)
    model_path = p.d.HERE / 'speed_population_increment_s10_v1/model.json'
    doc = p.d.e.load(model_path)
    grid = np.array(doc['grid'])
    kernels = {ast.literal_eval(k): np.array(v) for k, v in doc['kernels'].items()}
    expected = {k: v @ np.tile(grid, 3) for k, v in kernels.items()}
    base_path = p.d.HERE / 'current_gap_response_v1/training_table.json'
    base_doc = p.d.e.load(base_path)
    base = [{tuple(r['key']): r['targets'] for r in base_doc['models'][name]} for name in h.g.MODES]
    means = base_doc['global_mean']
    history_path = p.d.HERE / 'current_gap_history_v1/training_table.json'
    history_doc = p.d.e.load(history_path)
    banks = {name: {tuple(r['key']): {int(k): (v['n'], v['mean']) for k, v in r['targets'].items()}
                   for r in rows} for name, rows in history_doc['models'].items()}
    source = p.d.HERE / 'route_state_native_v1/none_s23/run_retry1/vissim_eval/baseline_001.fzp'
    frames, receipt = h.g.read(source, True, 2099)
    records, coverage, _ = h.g.build(frames, geometry, parameters, 2100)
    h.attach(records, frames)
    observed_path = p.d.HERE / 'compact_lane_state_v1/states.json'
    observed = p.d.e.load(observed_path)['none']['states']
    names = ('population', 'speed_density', 'history', 'gap_relative', 'gap_relative_history')
    grouped = defaultdict(list)
    rows = []
    for record in records:
        t, vid, cell = record['time_s'], record['vehicle'], record['cell']
        if cell not in p.m.CELLS:
            continue
        current = frames[t][vid]
        previous = frames[t-1].get(vid)
        ph = p.phase(current['v'], previous['v'] if previous else None)
        stats = {int(c): r for c, r in observed[str(t)].items()}
        context = p.contexts(stats, cell, geo)
        dv_pop = sum(w * expected[context][j] for j, w in p.encode(current['v'], ph, grid)) - current['v']
        prediction = dict(population=dv_pop)
        for name, mode in (('speed_density', 0), ('gap_relative', 1)):
            prediction[name] = h.g.predict(record, base, means, mode, '1')[0]
        for name in h.NAMES:
            prediction[name] = h.predict(record, name, 1, banks, base, means)
        row = dict(time_s=t, cell=cell, vehicle=vid, current_speed=current['v'],
                   actual_dv=record['labels'][1], predicted=prediction,
                   future_lane_change=record['future_lane_change'])
        rows.append(row)
        grouped[t, cell].append(row)
    cell_rows = []
    for (t, cell), rs in sorted(grouped.items()):
        cell_rows.append(dict(time_s=t, cell=cell, n=len(rs),
            total_native_n=observed[str(t)][str(cell)]['n'],
            current_speed=observed[str(t)][str(cell)]['v'],
            actual_dv=sum(r['actual_dv'] for r in rs)/len(rs),
            predicted={name: sum(r['predicted'][name] for r in rs)/len(rs) for name in names}))
    scores = {}
    for period, lo, hi in (('time_validation', 2100, 2400), ('control_period_nc', 2400, 2850)):
        selected = [r for r in rows if lo <= r['time_s'] < hi]
        cells = [r for r in cell_rows if lo <= r['time_s'] < hi]
        scores[period] = dict(vehicle={name: summary(selected, name) for name in names},
            cell_cohort={name: summary(cells, name) for name in names},
            low_speed_cell_cohort={name: summary([r for r in cells if r['current_speed'] < 60], name) for name in names},
            no_next_second_lane_change={name: summary([r for r in selected if not r['future_lane_change']], name) for name in names})
    example = [r for r in cell_rows if r['cell'] == 16 and 2550 <= r['time_s'] < 2580]
    example_scores = {name: summary(example, name) for name in names}
    # Perturb labels/scoring flags on a real record. Predictor features and
    # history stay current; they must not consume either future field.
    canary = records[len(records)//2]
    before = [h.predict(canary, name, 1, banks, base, means) for name in h.NAMES]
    changed = {**canary, 'labels': {1: 123456.}, 'future_lane_change': not canary['future_lane_change']}
    assert before == [h.predict(changed, name, 1, banks, base, means) for name in h.NAMES]
    files = [Path(__file__), Path(p.__file__), Path(h.__file__), Path(h.g.__file__), gp, network,
             model_path, base_path, history_path, observed_path]
    p.d.e.save(out / 'result.json', dict(status='CONDITIONAL_REACTION_ATTRIBUTION_NOT_GAIN', scores=scores,
        focused_cell16_2550_2580=example, focused_scores=example_scores, coverage=coverage,
        same_cohort_rows=len(rows), scored_cell_cohorts=len(cell_rows), source_receipt=receipt,
        pins={str(x.relative_to(p.d.ROOT)): hashlib.sha256(x.read_bytes()).hexdigest() for x in files},
        limitations=['All methods use identical eligible current vehicles and next1s labels, excluding missing geometric leaders or overlapping projections.',
            'This predicts the speed change of the same current cohort, not next-cell speed including transport.',
            'Current native gaps and prior speed are supplied at every cutoff; no autonomous gap forecast or gain result is claimed.',
            'Population model trained930..2099; existing gap/history tables trained900..2090. Frozen tables reused, so training rows differ.',
            'Only inspected seed23NC; no held-out-seed qualification.'],
        qualified=False, new_native_runs=0, production_changes=0))
    print('SCORES', scores, flush=True)
    print('FOCUSED', example_scores, flush=True)


if __name__ == '__main__':
    main()
