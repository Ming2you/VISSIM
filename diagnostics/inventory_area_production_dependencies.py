"""List the integrated area package's pinned inputs and historical test fixtures.

No training FZP is required to run its frozen physics. Historical snapshot
regressions additionally require their archived manifests and previous actions.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]

RUNTIME = {
    'diagnostics/control_area_physics_overlay.json': 'Explicit opt-in physics overlay, merged into base config',
    'diagnostics/control_area_membership.json': 'Physical Omega membership; also read by SC2001 configure',
    'diagnostics/control_area_route_contract_physical_routes.json': 'Base Omega movement/arrival contracts when objective enabled',
    'diagnostics/physical_movement_routes_ver2.json': 'Initial topology repair and verified physical paths',
    'diagnostics/dynamic_area_routes_ver2.json': 'Additional dynamic route topology and calibration hash',
    'diagnostics/dynamic_area_nc13_calibration.json': 'Frozen offline origin priors; byte-hashed by dynamic route evidence',
    'diagnostics/shared_approach_ver2.json': 'Physical link69 storage and native input/route evidence',
    'diagnostics/sc2001_corridor_nc13.json': 'Physical SC2001 corridor and embedded frozen empirical priors',
    'diagnostics/physical_projection_support_635_proposal.json': 'Reviewed deterministic physical supports; strict positive unknown guard plus separately validated route/input partitions',
    'diagnostics/route_choice_corridor_ver2.json': 'Native1129 finite corridor, current-route cohorts and shared69 continuation',
    'diagnostics/route_choice_corridor_1128_ver2.json': 'Native1128 finite corridor and unsignalized local branch',
    'diagnostics/native_internal_inputs_extended_ver2.json': 'All declared internal input sources, native schedules and finite inside generation',
    'diagnostics/native_input_1083_signal_authority_ver2.json': 'Lane-position partition and first selected SC108 signal authority for source21',
    'diagnostics/native_input_1096_route_ver2.json': 'Native1102 fixed path and successive signal service for input1096',
    'diagnostics/native_1096_sc8_gate_ver2.json': 'Native SC8 intermediate red/green timing; no invented saturation capacity',
    'diagnostics/native_input_1093_prehead_ver2.json': 'Native22 routing and shared SC11 p3 before left-turn p4 for input1093',
    'diagnostics/native_1092_1093_branch_calibration.json': 'Explicit frozen seed13 source direction priors; seed14 holdout required',
    'diagnostics/route_choice_corridor_1099_ver2.json': 'Input1086 native200:150 route choices and fixed SC15 clock',
    'diagnostics/route_choice_corridor_1100_ver2.json': 'Input1087 native200:150 route choices and shared source signal budget',
    'diagnostics/route_choice_corridor_1099_sc15_calibrated.json': 'Input1086 bounded native-SC15 service calibration opt-in',
    'diagnostics/route_choice_corridor_1100_sc15_calibrated.json': 'Input1087 bounded native-SC15 service calibration opt-in',
    'diagnostics/native_sc15_service_calibration.json': 'Queued discharge headways fitted outside two held450s windows; seed14 validation pending',
    'diagnostics/physical_phase_authority_ver2.json': 'Three selected signal-group to model-phase repairs',
    'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx': 'Pinned physical network',
    'outputs/urban_storage_capacity_core17legs4b_20260819.json': 'Pinned jam-density source',
    'evaluation/real_world_modi_inventory/urban_input_gate_map_ver2_20260907.csv': 'Pinned native input ownership evidence',
    'evaluation/configs/demand_profiles/ver2_fdsweep_x15_20260907.csv': 'Pinned experiment demand multiplier profile',
}
TEST_DATA = {
    'diagnostics/area_projection_coverage_635.json': 'Complete635 coverage assertions and synthetic support test',
    'diagnostics/physical_projection_support_ver2.json': 'Historical35-support configuration for OFF/old-data regression',
    'diagnostics/observation_projection_config.json': 'Projection-only test overlay',
    'diagnostics/ramp_profile_config_c10639_g5.json': 'Fake-COM invocation harness configuration',
}


def record(path, role, data=None):
    file = ROOT/path
    if data is None:
        data = file.read_bytes()
    return {'path': path, 'role': role, 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest(), 'tracked_at_inventory': path in TRACKED}


if __name__ == '__main__':
    TRACKED = set(subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0'))
    historical = {}
    names = ('codex_nc_s13_6056c94_20260909_retry', 'codex_n7_s13_6056c94_20260909')
    for name in names:
        run = ROOT/'evaluation/runs'/name
        paths = ([run/f'decisions_{name}/state_000900.json'] if name == names[0]
                 else sorted(run.rglob('state_*.json')))
        paths += [run/f'run_provenance_{name}.json', run/f'decisions_{name}/action_000001.json']
        if name == names[1]:
            paths += [run/f'decisions_{name}/action_003150.json']
        for path in paths:
            historical[str(path.relative_to(ROOT)).replace('\\', '/')] = 'Archived observed state/provenance/control used by current state regressions'
    pure = 'evaluation/runs/codex_n7_pure_s13_20260910/decisions_codex_n7_pure_s13_20260910/'
    for suffix in ('csv', 'json'):
        historical[pure+'action_000900.'+suffix] = 'Valid child-output fixture for strict watchdog/VBS test'
    archive = ROOT/'diagnostics/fixtures/control_area_v1.zip'
    if archive.exists():
        with zipfile.ZipFile(archive) as bundle:
            index = json.loads(bundle.read('index.json'))
            historical_rows = [record(row['path'], 'Raw historical regression input retained in the portable archive', bundle.read('raw/'+row['path']))
                               for row in index['files'] if row['kind'] == 'raw_run_file']
    else:
        historical_rows = [record(path, role) for path, role in historical.items()]
    output = {
        'scope': 'Additional integrated area physics/objective package; existing n7 base config, vendor, calibration and mapping dependencies still required.',
        'runtime_inputs': [record(path, role) for path, role in RUNTIME.items()],
        'additional_test_data': [record(path, role) for path, role in TEST_DATA.items()],
        'historical_test_inputs': historical_rows,
        'portable_fixture_archive': 'diagnostics/fixtures/control_area_v1.zip',
        'portable_fixture_bootstrap': 'python -m diagnostics.run_portable_fixture_tests --include-wsh',
        'training_data_not_opened_at_runtime': ['SC2001 training FZP and sc2001_corridor_audit.json', 'Dynamic-route training FZP and recalibration scripts'],
        'clean_checkout_limitations': [
            'The original portable archive supplies its listed historical inputs and fixed source references; its scoped tests are documented in the fixture README.',
            'Bootstrap restores raw bytes and explicitly relocated JSON copies under .review-fixtures without overwrite. Active fixture lookup refuses unlisted historical inputs rather than falling back to originals.',
            'Other historical replay scripts may need additional archives; this bundle is scoped to the tests documented in diagnostics/fixtures/README.md.',
        ],
    }
    target = ROOT/'diagnostics/area_production_required_files.json'
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'runtime_files':len(output['runtime_inputs']),
                      'new_runtime_files':[row['path'] for row in output['runtime_inputs'] if not row['tracked_at_inventory']],
                      'additional_test_files':len(output['additional_test_data']),
                      'historical_fixture_files':len(output['historical_test_inputs']),
                      'historical_fixture_bytes':sum(row['bytes'] for row in output['historical_test_inputs'])},indent=2))
