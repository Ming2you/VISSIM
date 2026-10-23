"""Closed selected arm only: canonical measurement with an exact cached hold.

No simulation, forecasting, fitting, process control, or old-baseline FZP scan.
The native protocol and canonical analyzer on disk remain unchanged.
"""
import hashlib
import importlib.util
import json
import shutil
import sys
import types
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = Path('D:/VISSIM_packages/vsl_multizone355_20261015')
REL = 'diagnostics/sdmpc_n31_20260924/integration_20260926'
SOURCE = ROOT / REL / 'native_pair1200/analyze_pair.py'
SOURCE_SHA = '277f3f90ac568a59e7fb20e34007b265de6f16bb8163a5954c289b1a1009c443'
PROTOCOL = ROOT / REL / 'native_vsl_multizone2250/protocol.json'
RUNS = Path('D:/VISSIM_runs/20261015_vsl_multizone2250_s29')
BASE = Path('E:/VISSIM_analysis/20261011_vsl_response349/causal_off2250_analysis_v2/native_analysis')
OUT = HERE / 'native_analysis'
MODEL = HERE / 'matched_off2250_v3/summary.json'
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf8')


def validate_cache(protocol, baseline):
    assert protocol['arms'] == ['selected']
    assert (protocol['start_sec'], protocol['end_sec'], protocol['seed']) == (2250, 2700, 29)
    assert (baseline['start_sec'], baseline['end_sec'], baseline['recorded_run_end_sec']) == (2250, 2700, 2700)
    assert baseline['physical_area']['sha256'] == protocol['measurement_area']['sha256']
    assert baseline['physical_area']['network_sha256'] == protocol['network_sha256']
    assert baseline['physical_area']['inside_links'] == 701
    assert all(baseline[key] is True for key in ('counterfactual_valid', 'paired_prefix_exact',
        'source_observed_model_inputs_exact', 'original_source_replay_passed', 'existing_forecast_comparison_qualified'))
    assert baseline['arms']['hold']['native_execution_passed']
    assert baseline['prefixes']['hold']['last_time_s'] == 2245.1
    assert baseline['prefixes']['hold']['rows'] > 0


def transform(source):
    old = "        baseline_fzp,=(Path(reused['run'])/'vissim_eval').glob('*.fzp')\n        original_prefix=prefix_digest(baseline_fzp,start,recording_grid=(5,.1))"
    assert source.count(old) == 1
    source = source.replace(old, "        original_prefix=reused_summary['prefixes']['hold']")
    old = "if reused and arm=='hold' and not controlled_reuse:"
    assert source.count(old) == 1
    return source.replace(old, "if reused and arm=='hold':")


def main():
    closure = read(OUT / 'runtime_closure.json')
    assert closure['all_owned_processes_closed'] and closure['wrapper_closed']
    assert closure['owner_exit_code'] == 0 and closure['normal_native_end_sec'] == 2700
    assert closure['arms'] == ['selected'] and Path(closure['runs_root']).resolve() == RUNS.resolve()
    assert closure['processes'] and all(row['owned_process_closed'] for row in closure['processes'])
    assert not (OUT / 'summary.json').exists(), 'Preserve existing completed analysis'
    protocol, baseline = read(PROTOCOL), read(BASE / 'summary.json')
    validate_cache(protocol, baseline)
    assert sha(BASE / 'summary.json') == protocol['reuse_native_baseline']['sha256']
    assert sha(MODEL) == protocol['prediction_sha256']
    assert sha(SOURCE) == SOURCE_SHA
    assert sha(protocol['measurement_area']['path']) == protocol['measurement_area']['sha256']
    assert sha(BASE / 'hold/execution.json') == protocol['controlled_prefix']['execution_sha256']
    prepared = read(HERE / 'native_preparation.json')
    assert sha(PROTOCOL) == prepared['protocol_sha256']
    assert all(row['changed_dsd'] == list(range(59, 67)) and row['city_rm_unchanged'] for row in prepared['physical_command_check'])

    # Use the already-tested observation normalization, not a weaker vehicle-only comparison.
    helper = BASE.parent / 'fresh_vsl_support.py'
    helper_manifest = read(BASE.parent / 'source_manifest.json')
    assert sha(helper) == helper_manifest['support_sha256']
    spec = importlib.util.spec_from_file_location('reused_vsl_observation_support', helper)
    support = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(support)
    old = Path(protocol['reuse_native_baseline']['run'])
    old_provenance = read(protocol['controlled_prefix']['provenance'])
    old_decisions = old / ('decisions_' + old_provenance['name'])
    new_decisions = RUNS / 'selected/decisions_sdmpc31_g_2250_selected_s29'
    checks = []
    for sec in range(150, 2251, 150):
        same = support.observable_signature(read(old_decisions / f'state_{sec:06d}.json'), old_decisions) == support.observable_signature(read(new_decisions / f'state_{sec:06d}.json'), new_decisions)
        checks.append(dict(sim_sec=sec, source_observations_exact=same))
    save(OUT / 'observed_input_qualification.json', dict(checks=checks, passed=all(row['source_observations_exact'] for row in checks),
        transitive_original_OFF_proof=dict(path=str(BASE / 'summary.json'), sha256=sha(BASE / 'summary.json'))))
    assert all(row['source_observations_exact'] for row in checks), 'Native input history differs; no matched model-error claim'

    # An exact same-endpoint cache retains native terminal delay and uninserted counts.
    cache_pins = {}
    for name in ('area_metrics.json', 'area_timeseries.csv', 'execution.json', 'native_errors.json'):
        source, target = BASE / 'hold' / name, OUT / 'hold' / name
        assert not target.exists(), 'Preserve partial analysis; do not duplicate'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        cache_pins[str(source)] = sha(source)
        assert sha(target) == cache_pins[str(source)]
    save(OUT / 'baseline_cache_receipt.json', dict(source=str(BASE), pins=cache_pins, native_end_sec=2700,
        membership_sha256=protocol['measurement_area']['sha256'], fzp_rescanned=False))
    rows = {row['name']: row for row in read(MODEL)['results']}
    model_metadata = OUT / 'prediction_metadata.json'
    save(model_metadata, dict(delta_omega_veh_h=rows['selected']['ttt_veh_h'] - rows['hold']['ttt_veh_h'],
        delta_tracked_outside_veh_h=sum(rows['selected']['outside_costs'].values()) - sum(rows['hold']['outside_costs'].values()),
        source=str(MODEL), source_sha256=sha(MODEL)))

    sys.path.insert(0, str(ROOT))
    module = types.ModuleType('closed_multizone_canonical_analysis')
    module.__file__ = str(SOURCE)
    sys.modules[module.__name__] = module
    exec(compile(transform(SOURCE.read_text(encoding='utf-8-sig')), str(SOURCE), 'exec'), module.__dict__)
    original_load = module.load
    def load(path):
        value = original_load(path)
        if Path(path).resolve() == PROTOCOL.resolve():
            value['prediction_summary'] = str(model_metadata)
        return value
    module.load = load
    sys.argv = [str(SOURCE), '--replay-protocol', str(PROTOCOL), '--runs-root', str(RUNS),
                '--output-dir', str(OUT), '--membership-json', protocol['measurement_area']['path']]
    module.main()
    result = read(OUT / 'summary.json')
    result.update(source_observed_model_inputs_exact=True, observed_input_checks=checks,
        original_source_replay_passed=result['original_initial_history_exact'],
        existing_forecast_comparison_qualified=result['counterfactual_valid'],
        baseline_fzp_rescanned=False, canonical_source_sha256=SOURCE_SHA)
    result['limitations'].append('Only DSD59..66 differ after2250; old hold cache has the same2700 endpoint and area. Conditional response, not autonomous policy improvement.')
    save(OUT / 'summary.json', result)


if __name__ == '__main__':
    main()
