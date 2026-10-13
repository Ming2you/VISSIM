"""Current-model independent-state RM check using cached physical native costs."""
import gzip, hashlib, importlib.util, json, pickle, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
NATIVE = I / 'native_rm_observation2700_writerfix_v3/analysis'
OUTPUT = HERE / 'forecast2700_v3'
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    assert not (HERE / 'review.json').exists()
    sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
    spec = importlib.util.spec_from_file_location('boundary280', HERE.parent / 'matched280/review.py')
    audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)
    summary = read(OUTPUT / 'summary.json')
    assert summary['status'] == 'complete' and summary['forecasts'] == 2
    assert all(sha(p) == digest for p, digest in summary['source_pins'].items())
    cfg, state, forecast = pickle.loads((OUTPUT / 'initial.pickle').read_bytes())
    membership = ROOT / read(HERE / 'config.json')['control_area_objective']['membership_path']
    inside = set(map(str, read(membership)['inside_links']))
    assert len(inside) == 701
    native = read(NATIVE / 'summary.json')
    assert native['counterfactual_valid'] and native['paired_prefix_exact']
    assert all(x['native_execution_passed'] for x in native['arms'].values())
    metrics = {a: read(NATIVE / a / 'area_metrics.json') for a in ('hold', 'release')}
    link_keys = set(metrics['hold']['physical_link_residence']) | set(metrics['release']['physical_link_residence'])
    native_delta = {k: metrics['release']['physical_link_residence'].get(k, {}).get('ttt_veh_h', 0.) -
                      metrics['hold']['physical_link_residence'].get(k, {}).get('ttt_veh_h', 0.) for k in link_keys}
    # The verified exact common prefix cancels even after membership changes.
    # These are per-link full-run residence differences, NOT absolute450s costs.
    old = read(ROOT / 'diagnostics/repin_v3c3_review_20261001/rm47_service66_response/assessment.json')
    observed = dict(old['release_minus_hold']['native'])
    observed['omega'] = sum(v for k, v in native_delta.items() if k in inside)
    observed['outside'] = sum(v for k, v in native_delta.items() if k not in inside)
    rows = {}
    boundaries = {}
    for arm, item in summary['results'].items():
        response = json.loads(gzip.decompress((OUTPUT / (arm + '.response.json.gz')).read_bytes()))
        stocks = read(OUTPUT / (arm + '.stocks.json'))
        boundaries[arm] = audit.model_boundary(response, stocks, item['omega_ttt_veh_h'], cfg)
        costs = item['costs_by_stock']
        flows = defaultdict(float)
        for t in response['transfers']:
            source, target = t['source'], t['target']
            if target == 'freeway:FW_E':
                if source == 'origin:FW_E': flows['source'] += t['vehicles']
                elif source and source.startswith('merge_pending:'): flows['merge'] += t['vehicles']
            if source == 'freeway:FW_E':
                if target == 'external:terminal:FW_E': flows['terminal'] += t['vehicles']
                elif target and target.startswith('transit:exchange:off:'): flows['off'] += t['vehicles']
        rows[arm] = dict(omega=item['omega_ttt_veh_h'], east=costs['freeway:FW_E'], west=costs['freeway:FW_W'],
            ramps=sum(v for k, v in costs.items() if k.startswith('ramp:')),
            ramp10484=costs['ramp:RM_C10484'], final_east=stocks[-1]['stocks']['freeway:FW_E']['inside'],
            **flows)
        assert item['resource_max_exceedance'] < 1e-7
        assert item['writer_three_blocks'] and item['conservation_states'] == 4
        assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
        assert all(item['shared_constraints'][k]['target'] == 0 for k in ('np', 'nuf'))
    delta = {k: rows['release'][k] - rows['hold'][k] for k in rows['hold']}
    # Executed sequences differ only in10484 physical RM commands.
    commands = {}
    for arm in ('hold', 'release'):
        commands[arm] = [read(NATIVE.parent / arm / 'commands' / f'action_{t:06}.json') for t in (2700, 2850, 3000)]
    for hold, release in zip(commands['hold'], commands['release']):
        for k in ('green_times', 'offsets', 'vsl', 'N_P_star', 'N_UF_star', 'inflow_outflow_allocation'):
            assert hold[k] == release[k], k
        for key in hold['ramp_metering']:
            if key != 'RM_C10484': assert hold['ramp_metering'][key] == release['ramp_metering'][key]
    result = dict(status='complete_fixed_command_validation_not_full_goal', comparison='release minus hold',
        seed=47, window=[2700, 3150], model=rows, model_delta=delta, native_delta=observed,
        native_physical_link_delta=native_delta, whole_omega_membership=701,
        whole_omega_reaggregation='Cached whole physical link residence with verified exact common prefix cancelling; no FZP scan',
        physical_conservation_and_writer_passed=True,
        np_nuf_scope='Native replay commands carry zero placeholder targets, not PFO-selected caps. Raw NP/NUF checks are false. No SDMPC feasibility or selection claim.',
        physical_direction_check={k: delta[k] * observed[k] > 0 for k in ('omega', 'east', 'ramps', 'merge', 'off', 'terminal')},
        absolute_gain_error_veh_h=abs(delta['omega'] - observed['omega']),
        forecasts=2, forecast_compute_seconds=sum(x['wall_sec'] for x in summary['results'].values()),
        optimization_iterations=0, native_runs=0, fits=0, fzp_rescans=0,
        limitations=['Seed47 was used in earlier model development; unused by this new time-step implementation, not a blind holdout.',
            'Only10484 varies;10681 acts as a fixed background meter. Does not complete10681 urban spillback/decision validation.',
            'Native5s sampled residence and model10s endpoint costs differ in quadrature.',
            'LSA failure remains; native execution uses previously authorized LDP evidence.',
            '5s sample last4.9s tail hold retained; this is not exact continuous TTT.',
            'Large component directions preserved but the net effect is only about2vehh; no coefficient fitting to this sign.'],
        source_pins={str(p): sha(p) for p in [Path(__file__), membership, NATIVE / 'summary.json',
             OUTPUT / 'summary.json', *[NATIVE / a / 'area_metrics.json' for a in metrics],
             ROOT / 'diagnostics/repin_v3c3_review_20261001/rm47_service66_response/assessment.json']})
    for name, value in [('boundary_identity.json', boundaries), ('review.json', result)]:
        (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
    print(json.dumps({k: result[k] for k in ('status','model_delta','native_delta','physical_direction_check','forecast_compute_seconds')},ensure_ascii=False))

if __name__ == '__main__': main()
