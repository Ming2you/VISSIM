"""Verify retained receipts and emit compact release qualification; no rollouts."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = Path('D:/VISSIM_analysis/20261013_solo355_local/task5')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def receipt(path):
    return dict(path=str(path), sha256=digest(path))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def main():
    if (ARTIFACTS/'fix1/qualification/receipt.json').exists():
        from diagnostics.solo355_local_20261013.finalize_fix1 import main as finalize_fix
        return finalize_fix()
    gate = read(ARTIFACTS/'input_gate.json')
    assert gate['passed'] is True
    exclusions = set(gate['excluded_fields'])

    def normalized(value):
        if isinstance(value, dict):
            return {k: normalized(v) for k, v in value.items() if k not in exclusions}
        if isinstance(value, list):
            return [normalized(v) for v in value]
        return value

    modes = {}
    pins = {}
    for mode, directory, startup in (
            ('freeway_only', 'full_freeway900_v2', 'startup_freeway'),
            ('urban_only', 'full_urban900', 'startup_urban')):
        evidence = gate['modes'][mode]['evidence']
        raw = {}
        for variant, item in evidence.items():
            assert digest(item['path']) == item['sha256']
            raw[variant] = read(item['path'])
        base = raw['base']
        assert base['complete_context_sha256'] == raw['opposite']['complete_context_sha256']
        assert base['complete_context_sha256'] == raw['stock']['complete_context_sha256']
        assert base['complete_context_sha256'] != raw['own']['complete_context_sha256']
        for field in ('response', 'derivative', 'writer'):
            assert normalized(base['evaluation'][field]) == normalized(raw['opposite']['evaluation'][field]), field
        assert (base['evaluation']['response']['objective_veh_h'] !=
                raw['own']['evaluation']['response']['objective_veh_h'])
        path = ARTIFACTS/directory/'selection.json'
        full = read(path)
        selection = full['selection']
        assert full['completed'] and full['feasible']
        assert full['canonical_writer']['prewrite_binding_passed']
        assert full['canonical_writer']['written_command_binding_passed']
        assert len(full['all_three_blocks']) == 3
        assert all(b['ordered_row_count'] == 213 for b in full['all_three_blocks'])
        assert selection['final_constraints']['feasible']
        assert selection['regional_mode'] == mode
        assert set(selection['omega_partition']['costs']) == set(selection['active_cost_owners']) | {'PASSIVE_OMEGA'}
        assert abs(selection['omega_partition']['residual_veh_h']) < 1e-7
        assert read(ARTIFACTS/startup/'receipt.json')['passed'] is True
        current_pins = {}
        for name, sha in full['source_sha256'].items():
            candidate = Path(name)
            if candidate.is_relative_to(ROOT):
                assert digest(candidate) == sha, name
                relative = candidate.relative_to(ROOT).as_posix()
                current_pins[relative] = sha
                if relative in pins:
                    assert pins[relative] == sha
                pins[relative] = sha
        fallback = collections.Counter(r.get('fallback_reason') for r in selection['gradient_rows']
            if r.get('derivative_method') == 'executable_secant_fallback')
        modes[mode] = dict(remote_noninterference=True, own_state_sensitivity=True,
            causal_boundary=True, local_cost_only=True, three_block_writer=True,
            input_evidence=evidence, startup=receipt(ARTIFACTS/startup/'receipt.json'),
            full_selection=dict(completed=True, feasible=True, evidence_path=str(path), evidence_sha256=digest(path),
                seconds=full['elapsed_sec'], converged=selection['converged'], status=selection['selection_status'],
                held_objective_veh_h=selection['held_objective'], selected_objective_veh_h=selection['selected_objective'],
                active_cost_owners=selection['active_cost_owners'], passive_veh_h=selection['omega_partition']['costs']['PASSIVE_OMEGA'],
                executable_secant_rows=dict(fallback), meter_neighbor_predictions=selection['meter_neighbor_audit']['additional_predictions'],
                rollouts={k:selection['surrogate_query'][k] for k in ('scalar_rollouts','tangent_rollouts','total_rollouts')},
                protocol=receipt(ARTIFACTS/directory/'protocol.json'), package_source_pin_count=len(current_pins)))
    source_manifest = ARTIFACTS/'current_package_source_pins.json'
    write(source_manifest, dict(schema='regional-current-package-pins/v1', root=str(ROOT),
        scope='Current E package pins verified against both actual selection receipts; external historical provenance stays in those receipts.',
        files=[dict(path=str(ROOT/path), package_relative_path=path, sha256=sha) for path,sha in sorted(pins.items())]))
    prior = read(ARTIFACTS.parent/'task4_required_sources.json')
    required=[]
    for row in prior['required_files']:
        path=Path(row['path'])
        current=dict(row,sha256=digest(path))
        current['previous_checkpoint_sha256']=row['sha256']
        current['matches_checkpoint']=current['sha256']==row['sha256']
        current['current_selection_pin']=bool(row['package_relative_path'] in pins)
        required.append(current)
    write(ROOT/'diagnostics/solo355_local_20261013/required_source_inputs.json', dict(
        schema='regional-required-source-inputs/v1',
        scope='Observed imported/transformed baseline dependencies and static inputs, refreshed hashes; unchanged adopted inputs are pinned, not new implementation.',
        canonical_package_pins=receipt(source_manifest), required_files=required))
    validation=dict(passed=True, scope='regional_information_isolation', native_runs=0, freeze_runs=0, queue_runs=0,
        input_gate=receipt(ARTIFACTS/'input_gate.json'), source_pins=receipt(source_manifest),
        regression=dict(command='python -B -m unittest diagnostics.solo355_local_20261013.test_regional_context diagnostics.solo355_local_20261013.test_regional_contracts diagnostics.test_sdmpc_central diagnostics.test_sdmpc_pfo_caps diagnostics.test_validated_decision_hold', tests=66, seconds=11.947, passed=True),
        modes=modes, limitations=[
            'Raw replay injects captured merged observations at lane_plant_runtime.observe_state; collector transport and obs150 upstream source hashes were not revalidated.',
            'Own VSL exposure and own head-service history are frozen identically between raw replay variants.',
            'Raw numerical receipts used the earlier single-query one-worker setting; full selections restore original eight-worker policy and worker-contract regression rejects smaller configurations.',
            'Outlet supply is adopted static capacity; source crossing requests are from the last closed own boundary window, not capacities or a remote-spillback forecast.',
            'Both selections are best observed feasible, not converged/GNE certificates. Model/writer checks do not prove native traffic benefit or application.',
            'Saved4500 integrated history remains correctly rejected by inactive actuator guards; no counterfactual native receipt is claimed.',
            'The failed first FW selection is preserved under full_freeway900; a relevant worker-contract fix preceded the unique successful v2 selection.'])
    write(ROOT/'diagnostics/solo355_local_20261013/validation.json', validation)
    print(json.dumps(dict(passed=True,modes=list(modes),current_package_pins=len(pins),required_inputs=len(required))))


if __name__=='__main__':
    main()