"""Fixed population structure, different NC calibration regime coverage.

Train only NCseed33, early and full recorded day. Evaluate inspected seed23
without feeding its future into either fit. This is development, not holdout.
"""
from pathlib import Path
import ast, hashlib, math, sys, xml.etree.ElementTree as ET
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import speed_population as p


def main():
    out = p.d.HERE / 'crossseed_population_v1'
    out.mkdir(exist_ok=False)
    network23 = p.d.H / 'rules_4500_s23_v1/prepared_none/network/baseline.inpx'
    network33 = p.d.H / 'state_response_20260919/native_s33_v1/prepared_none/network/baseline.inpx'
    roots = [ET.parse(x).getroot() for x in (network23, network33)]
    assert roots[0].find('simulation').get('randSeed') == '23'
    assert roots[1].find('simulation').get('randSeed') == '33'
    for root in roots:
        root.find('simulation').set('randSeed', '0')
    assert ET.tostring(roots[0]) == ET.tostring(roots[1]), 'Physical preparation differs beyond seed'
    run33 = p.d.e.load(p.d.H / 'state_response_20260919/native_s33_v1/run_none/run.json')
    command33 = p.d.e.load(p.d.H / 'state_response_20260919/native_s33_v1/none.json')
    assert run33['exit_code'] == 0 and run33['terminal_sec'] >= 4500
    assert not command33['meter_commands'] and not command33['vsl_commands']
    geometry_path = p.d.H / 'controller_response_s23_v1/none/geometry.json'
    geometry = p.d.e.load(geometry_path)
    geo = {r['cell']: r for r in geometry['cells'] if r['road'] == 'FW_E'}
    grid, _ = p.grid_from_network(network33)
    rho_max = p.d.e.load(p.d.HERE / 'compact_lane_state_v1/result.json')['rho_max']
    source33 = p.d.H / 'state_response_20260919/native_s33_v1/run_none/vissim_eval/baseline_001.fzp'
    old_end = p.d.END
    try:
        p.d.END = 4500
        frames, receipt33 = p.g.read(source33, False, 899)
    finally:
        p.d.END = old_end
    models = {}
    training = {}
    for label, last in (('nc33_early', 2099), ('nc33_full', 4499)):
        populations, native, tables, counts = p.extract(frames, geometry, grid, True,
            'increment', (-1., 1.), 'mean_speed', (930, last))
        kernels, fallback = p.compile_kernel(tables, grid, 3, 'mean_speed')
        selected = [row for t, cells in native.items() if 930 <= t <= last for c, row in cells.items() if c in p.m.CELLS]
        training[label] = dict(first_cutoff_s=930, last_cutoff_s=last, last_label_s=last+1, counts=counts,
            low_mean_speed_cell_seconds=sum(r['v'] < 60 for r in selected),
            total_cell_seconds=len(selected), mean_speed_quantiles=np.quantile([r['v'] for r in selected], [0, .01, .1, .5, 1]).tolist())
        p.d.e.save(out / f'{label}_model.json', dict(grid=grid.tolist(), kernels={str(k): v.tolist() for k, v in kernels.items()},
            tables=[{str(k): v.tolist() for k, v in bank.items()} for bank in tables],
            phase_count=3, context_mode='mean_speed', transition_kind='increment', min_support=p.MIN_SUPPORT,
            fallback_rows=fallback, training=training[label]))
        models[label] = kernels
        del populations, native, tables
        print('TRAINED', label, training[label], flush=True)
    del frames
    initials_path = p.d.HERE / 'speed_population_increment_s10_mean_speed_v1/initials.json'
    observations_path = p.d.HERE / 'compact_lane_state_v1/states.json'
    initial = p.d.e.load(initials_path)
    known = p.d.e.load(observations_path)
    scores = {}
    for name, kernels in models.items():
        scores[name] = []
        for arm, starts in initial.items():
            for start_s, item in starts.items():
                start = int(start_s)
                trace, final = p.rollout({int(c): np.array(v) for c, v in item['populations'].items()},
                    item['rate'], geo, rho_max, grid, kernels, context_mode='mean_speed')
                errors = []
                nerrors = []
                for entry in trace:
                    native = known[arm]['states'][str(start + entry['step'])]
                    for c in p.m.CELLS:
                        errors.append(entry['states'][c]['v'] - native[str(c)]['v'])
                        nerrors.append(entry['states'][c]['n'] - native[str(c)]['n'])
                scores[name].append(dict(arm=arm, start_s=start, speed_rmse=math.sqrt(sum(v*v for v in errors)/len(errors)),
                    n_mae=sum(abs(x) for x in nerrors)/len(nerrors), final_states=trace[-1]['states'],
                    final_queue=trace[-1]['inlet_queue'], max_mass_residual=max(abs(r['mass_residual']) for r in trace)))
        print('AUTONOMOUS', name, [(r['arm'], r['start_s'], round(r['speed_rmse'], 3)) for r in scores[name]], flush=True)
    # A disjoint-seed time-validation slice uses the SAME observed current
    # populations and boundary history for both already-frozen fitted models.
    source23 = p.d.H / 'rules_4500_s23_v1/run_none/vissim_eval/baseline_001.fzp'
    frames, receipt23 = p.g.read(source23, False, 2099)
    ps, native, _, counts23 = p.extract(frames, geometry, grid, False, 'increment', (-1., 1.), 'mean_speed')
    del frames
    conditional = {}
    for name, kernels in models.items():
        errors = []
        for t in range(2100, 2400):
            rate = sum(known['none']['entry'][str(s)] for s in range(t-29, t+1))/30
            nxt, _, _ = p.step(ps[t], rate, 0., geo, rho_max, grid, kernels, 'mean_speed')
            for c in p.m.CELLS:
                errors.append(p.moments(nxt[c], grid)['v'] - native[t+1][c]['v'])
        conditional[name] = dict(n=len(errors), speed_rmse=math.sqrt(sum(e*e for e in errors)/len(errors)))
    paths = [Path(__file__), Path(p.__file__), network23, network33, geometry_path, initials_path, observations_path,
             out/'nc33_early_model.json', out/'nc33_full_model.json']
    p.d.e.save(out / 'result.json', dict(status='CROSSSEED_NC_CALIBRATION_DEVELOPMENT_NOT_QUALIFIED',
        training=training, autonomous=scores, seed23_time_validation=conditional,
        source_receipts=dict(train_nc33=receipt33, test_nc23=receipt23), count_test_nc23=counts23,
        normalized_network_seed_only_equal=True, native_run33_terminal_sec=run33['terminal_sec'],
        pins={str(x.relative_to(p.d.ROOT)): hashlib.sha256(x.read_bytes()).hexdigest() for x in paths},
        limitations=['Both seed23 and33 have already been inspected; this is not independent fresh-seed qualification.',
            'Only NCseed33 data fits either model. Its later times are a separate training realization, never future observations from targetseed23.',
            'Fixed model structure and hyperparameters; early/full transfer separates seed change from congestion-regime training coverage.',
            'Local6cell30s gate only. No actual future seed23 boundary or speed is fed to rollouts.',
            'Upstream lever response, full450s costs, off-ramp/ramp waiting and canonical integration remain unqualified.'],
        qualified=False, new_native_runs=0, production_changes=0))
    print('CONDITIONAL', conditional, flush=True)


if __name__ == '__main__':
    main()
