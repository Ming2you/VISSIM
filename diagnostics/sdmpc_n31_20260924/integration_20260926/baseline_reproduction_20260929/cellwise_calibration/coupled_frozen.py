"""Verify a frozen cellwise fit in the current coupled plant; never refit."""
import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPANDED = '--expanded-joint' in sys.argv[1:]
OUT = HERE/('coupled_expanded_joint' if EXPANDED else 'coupled_latest')
LABEL = 'expanded_joint' if EXPANDED else 'frozen159'
I = HERE.parents[1]
ROOT = I.parents[2]


def read(p):
    return json.loads(p.read_bytes())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(name, value):
    p = OUT/name
    assert not p.exists(), p
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')


def prepare():
    from evaluation.controllers import lane_plant_runtime as lpr
    OUT.mkdir(exist_ok=True)
    assert not list(OUT.iterdir()), 'Preserve any previous prepared results'
    base_path = I/'baseline_reproduction_20260929/sc1001_native_choices/candidate_config.json'
    frozen_path = HERE/('expanded_joint/eval_036/reference_config.json' if EXPANDED
                       else 'jacobian_step/trust_0.15/reference_config.json')
    cfg = read(base_path)
    manifest_path = ROOT/cfg['freeway']['lane_plant']
    manifest = read(manifest_path)
    prior_path = ROOT/manifest['sources']['reference_config']['path']
    prior, frozen = read(prior_path), read(frozen_path)
    assert {k for k in prior if prior[k] != frozen[k]} == {'freeway'}
    assert {k for k in prior['freeway'] if prior['freeway'][k] != frozen['freeway'][k]} == {'physical_cell_fd', 'state_response'}
    assert prior['freeway'].keys() == frozen['freeway'].keys()
    assert prior['freeway']['physical_cell_fd'].get('FW_W') == frozen['freeway']['physical_cell_fd'].get('FW_W')
    assert prior['freeway']['state_response'].get('FW_W') == frozen['freeway']['state_response'].get('FW_W')
    candidate = copy.deepcopy(manifest)
    candidate['sources']['reference_config'] = dict(path=frozen_path.relative_to(ROOT).as_posix(), sha256=sha(frozen_path))
    candidate['qualification'] = f'Frozen cellwise {LABEL} tested with current coupled routing; NOT gain qualified or production adopted.'
    write('candidate_manifest.json', candidate)
    cfg['freeway']['lane_plant'] = (OUT/'candidate_manifest.json').relative_to(ROOT).as_posix()
    write('candidate_config.json', cfg)
    old = lpr.load_sources(manifest_path)
    new = lpr.load_sources(OUT/'candidate_manifest.json')
    assert old['parameters'] == new['parameters']
    assert old['geometry'] == new['geometry']
    assert old['port_profile'] == new['port_profile']
    effective = {}
    for road in ('FW_E', 'FW_W'):
        net = new['component']._config(road, new['parameters']['by_direction'][road]).network
        prior_net = old['component']._config(road, old['parameters']['by_direction'][road]).network
        assert new['component'].cell_fd.get(road) == frozen['freeway']['physical_cell_fd'].get(road)
        assert net.freeway_state_response.get(road) == frozen['freeway']['state_response'].get(road)
        if road == 'FW_W':
            assert net.freeway_segment_params[road] == prior_net.freeway_segment_params[road]
            assert net.freeway_state_response.get(road) == prior_net.freeway_state_response.get(road)
        effective[road] = dict(segment_params=net.freeway_segment_params[road],
                               state_response=net.freeway_state_response.get(road))
    write('effective_parameters.json', effective)
    pins = {str(p): sha(p) for p in (base_path, frozen_path, manifest_path, prior_path,
                                    OUT/'candidate_manifest.json', OUT/'candidate_config.json')}
    core = ['evaluation/controllers/lane_plant_runtime.py', 'evaluation/controllers/lane_freeway_runtime.py',
            'evaluation/controllers/freeway_fd.py', 'evaluation/controllers/area_freeway_accounting.py',
            'evaluation/controllers/physical_movement_routes.py', 'evaluation/controllers/physical_ramp_boundary.py',
            'evaluation/controllers/runtime_setup.py', 'evaluation/controllers/vissim_stackelberg_adapter.py',
            'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py',
            'diagnostics/sdmpc_n31_20260924/integration_20260926/probe_selected_arrival_path.py']
    write('protocol.json', dict(previous_goal_turn=('PROGRESS: expanded joint fit and six component checks completed' if EXPANDED else 'NO_PROGRESS: explanation of existing calibration results only'),
        hypothesis='Frozen cellwise response fit may improve mainline response after native urban routing correction; assess full Omega and ramp cost together.',
        base_config=str(base_path), source_pins=pins, core_sha256={p:sha(ROOT/p) for p in core},
        network_sha256=manifest['sources']['network']['sha256'], planned_forecasts=6,
        new_fit=False, new_native=0, optimizer_iterations=0, production_adopted=False,
        evidence_scope='Seed47 hold/release at2700 and seed43 four arms at2250, autonomous450s. Previously inspected checks, not blind holdout.',
        selection_rule='No selection or further coefficient search from these results; compare frozen bundle against current coupled baseline.'))
    print(json.dumps(dict(prepared=str(OUT), effective_east_cells=len(effective['FW_E']['segment_params']), western_fd_and_response_exact=True)))


def compare():
    import gzip
    import statistics
    protocol = read(OUT/'protocol.json')
    pins = {}

    def load(p):
        pins[str(p)] = sha(p)
        return read(p)

    truth = load(I/'baseline_reproduction_20260929/sc1001_native_choices/comparison.json')
    report = {}
    mass = 0.
    for seed, at in ((47, 2700), (43, 2250)):
        old_dir = I/f'closedloop_recorded{at}_lever450_trace10484_sc1001_native_s{seed}_v1'
        new_dir = I/f'closedloop_recorded{at}_lever450_trace10484_{LABEL}_s{seed}_v1'
        old, new = load(old_dir/'summary.json'), load(new_dir/'summary.json')
        old_runtime, new_runtime = load(old_dir/'runtime.json'), load(new_dir/'runtime.json')
        assert old_runtime['initial_source_sha256'] == new_runtime['initial_source_sha256']
        assert old['start_sec'] == new['start_sec'] == at
        assert old['duration_sec'] == new['duration_sec'] == 450
        assert not new['future_observation_inputs'] and not new['native_started'] and new['optimizer_iterations'] == 0
        rows, ramp_rows = [], []
        for key, r in new['results'].items():
            b = old['results'][key]
            assert b['commands'] == r['commands']
            assert r['validation']['all_actuator_and_step_constraints_checked']
            assert r['executed_control_blocks'] == [0, 1, 2]
            arm = ('hold' if key == 'held_actual' else 'release') if seed == 47 else ('nc' if key == 'held_actual' else key)
            for ramp, values in r['ramps'].items():
                mass = max(mass, abs(values['residual']))
                native = next(v['actual'] for v in truth[f'seed{seed}']['ramps'] if v['case'] == key and v['ramp'] == ramp)
                ramp_rows.append(dict(case=key, arm=arm, ramp=ramp, actual=native, before=b['ramps'][ramp], after=values))
            cost = next(v for v in truth[f'seed{seed}']['costs'] if v['case'] == key)
            traces = []
            for folder in (old_dir, new_dir):
                path = folder/(key+'_RM_C10484_trace.json.gz')
                pins[str(path)] = sha(path)
                traces.append(json.loads(gzip.decompress(path.read_bytes())))
            assert traces[0]['initial_stock'] == traces[1]['initial_stock']
            row = dict(case=key, actual_delta_omega=cost['actual_delta_omega'])
            for label, item, summary in (('before', b, old), ('after', r, new)):
                baseline = summary['results']['held_actual']
                row[label] = dict(omega=item['ttt_omega_veh_h'],
                    delta_omega=item['ttt_omega_veh_h']-baseline['ttt_omega_veh_h'],
                    outside=item['tracked_outside_residence_veh_h'],
                    delta_outside=item['tracked_outside_residence_veh_h']-baseline['tracked_outside_residence_veh_h'],
                    delta_fw_e=item['cost_by_stock']['freeway:FW_E']-baseline['cost_by_stock']['freeway:FW_E'],
                    delta_ramp10484=item['cost_by_stock']['ramp:RM_C10484']-baseline['cost_by_stock']['ramp:RM_C10484'],
                    delta_all_ramps=sum(v-baseline['cost_by_stock'].get(k, 0.) for k,v in item['cost_by_stock'].items() if k.startswith('ramp:')),
                    wall_sec=item['wall_sec'])
                row[label]['delta_other_omega'] = row[label]['delta_omega']-row[label]['delta_fw_e']-row[label]['delta_ramp10484']
            rows.append(row)
        report[f'seed{seed}'] = dict(costs=rows, ramps=ramp_rows,
            rank={label:[r['case'] for r in sorted(rows, key=lambda r:r['actual_delta_omega'] if label == 'actual' else r[label]['delta_omega'])]
                  for label in ('actual', 'before', 'after')},
            ramp_mae={label:{m:statistics.mean(abs(r[label][m]-r['actual'][m]) for r in ramp_rows)
                       for m in ('arrival', 'merge', 'final_stock')} for label in ('before', 'after')})
    # Prefix through2700 was verified identical in the matched native pair.
    # Difference of the saved0..3150 link ledgers is therefore the450s effect.
    native = {arm:load(I/f'native_rm_observation2700_writerfix_v3/analysis/{arm}/area_metrics.json') for arm in ('hold','release')}
    manifest = load(OUT/'candidate_manifest.json')
    geometry = load(ROOT/manifest['sources']['geometry']['path'])
    east = {str(x['link']) for x in geometry['chains']['FW_E']}
    delta = lambda links:sum(native['release']['physical_link_residence'][link]['ttt_veh_h']-native['hold']['physical_link_residence'][link]['ttt_veh_h'] for link in links)
    total = native['release']['ttt_veh_h']-native['hold']['ttt_veh_h']
    decomposition = dict(delta_omega=total, delta_fw_e=delta(east), delta_ramp10484=delta(['10484']))
    decomposition['delta_other_omega'] = total-decomposition['delta_fw_e']-decomposition['delta_ramp10484']
    assert abs(total-next(r['actual_delta_omega'] for r in report['seed47']['costs'] if r['case']=='release_actual')) < 1e-8
    assert mass < 1e-7
    for path, pin in protocol['source_pins'].items():
        assert sha(Path(path)) == pin, path
    for path, pin in protocol['core_sha256'].items():
        assert sha(ROOT/path) == pin, path
    for path, pin in pins.items():
        assert sha(Path(path)) == pin, path
    report.update(native47_decomposition=decomposition, max_ramp_mass_residual=mass,
        frozen_coefficients=True, new_forecasts=6, new_fit=False, new_native=0,
        gain_qualified=False, production_adopted=False, source_pins=pins,
        core_unchanged=True, future_observation_inputs=False,
        limitations='Previously inspected states, not blind holdout. Full Omega with tracked outside separately; no SDMPC optimizer/AD/native validation in this comparison.')
    write('comparison.json', report)
    print(json.dumps({k:{'costs':v['costs'],'rank':v['rank'],'ramp_mae':v['ramp_mae']} for k,v in report.items() if k.startswith('seed')}, indent=2))
    print(json.dumps(dict(native47_decomposition=decomposition, max_ramp_mass_residual=mass)))


if __name__ == '__main__':
    compare() if '--compare' in sys.argv else prepare()
