"""Prepare a fixed physical-signal diagnostic from recorded CSV; stdlib only.

No adapter/model import, network write, simulation, or new route is performed.
Existing outputs may only be regenerated when their bytes are identical.
"""
from collections import Counter
from copy import deepcopy
import csv
import hashlib
import io
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'diagnostics/fixed_beta300v3_900_signal_profile'
RUN = ROOT / 'evaluation/runs/codex_contract_beta300_s13_1050_v3_20260910'
DECISIONS = RUN / ('decisions_' + RUN.name)
BASE = ROOT / 'diagnostics/signal_profile_config_zero.json'
PLAN = ROOT / 'outputs/signal_group_actuation_plan_mainline_20260825.json'
EXPECTED_ACTION_SHA = 'becee44cef1cfd96fc0dc7be4be70b3a424210a362f52d87aa9ee70388e9940a'
EXPECTED_JSON_SHA = '48d68ceddc7c4fd4431457b5dcf1ba01ce19e946a696c0360faf8942c3cbd34d'
EXPECTED_BASE_SHA = '5f52ca1c754d6d1be93efaf5434eaed7af8c8c4ed42a2947507aa2b0b56f2b45'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def rows(data):
    return list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))


def main():
    paths = [BASE, PLAN, DECISIONS / 'action_000900.csv', DECISIONS / 'action_000900.json',
             DECISIONS / 'action_001050.csv',
             *[DECISIONS / f'action_{sec:06d}.csv' for sec in (1, 150, 300, 450, 600, 750)],
             RUN / ('run_provenance_' + RUN.name + '.json'),
             ROOT / 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx',
             ROOT / 'evaluation/controllers/diagnostic_signal_profile.py',
             ROOT / 'evaluation/controllers/diagnostic_profile.py',
             ROOT / 'scripts/run_real_world_stackelberg_controller.vbs',
             ROOT / 'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1',
             ROOT / 'diagnostics/signal_readback_cadence.py', Path(__file__)]
    blobs = {p: p.read_bytes() for p in paths}
    assert sha(blobs[BASE]) == EXPECTED_BASE_SHA
    assert sha(blobs[DECISIONS / 'action_000900.csv']) == EXPECTED_ACTION_SHA
    assert sha(blobs[DECISIONS / 'action_000900.json']) == EXPECTED_JSON_SHA
    data = rows(blobs[DECISIONS / 'action_000900.csv'])
    assert Counter(r['kind'] for r in data) == {'vsl': 66, 'signal': 17, 'signal_sg': 122, 'ramp_meter': 8}
    # VSL segment IDs repeat across their physical lane/DSD addresses.
    assert len({tuple(r[k] for k in ('kind', 'id', 'dsd_no', 'sc_no', 'link', 'lane')) for r in data}) == 213
    physical_row_count = len(data)
    assert all(float(r['speed_kph']) == 120.0 for r in data if r['kind'] == 'vsl')
    meter_rows = [r for r in data if r['kind'] == 'ramp_meter']
    assert all(float(r['green_sec']) == 10.0 and float(r['rate_vph']) == 900.0 for r in meter_rows)
    actual = json.loads(blobs[DECISIONS / 'action_000900.json'])
    greens, offsets = {}, {}
    for row in data:
        if row['kind'] != 'signal':
            continue
        signal = row['id']
        offsets[signal] = float(row['offset'])
        assert math.isfinite(offsets[signal]) and offsets[signal] == actual['offsets'][signal]
        for phase in ('p1', 'p2', 'p3', 'p4'):
            key = signal + '_' + phase
            value = float(row[phase + '_green'])
            assert math.isfinite(value) and (value == 0 or 5 <= value <= 90)
            assert value == actual['green_times'][key]
            greens[key] = value
    assert len(greens) == 68 and len(offsets) == 17
    warmup = blobs[DECISIONS / 'action_000001.csv']
    assert all(blobs[DECISIONS / f'action_{sec:06d}.csv'] == warmup for sec in (150, 300, 450, 600, 750))
    assert Counter(r['kind'] for r in rows(warmup)) == {'vsl': 66, 'ramp_meter': 8}
    assert all(float(r['speed_kph']) == 120.0 for r in rows(warmup) if r['kind'] == 'vsl')
    assert all(float(r['green_sec']) == 10.0 and float(r['rate_vph']) == 900.0 for r in rows(warmup) if r['kind'] == 'ramp_meter')
    plan = json.loads(blobs[PLAN])
    plan_content_sha = sha(json.dumps(plan, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())
    template = json.loads(blobs[BASE])
    template['name'] = 'fixed_beta300v3_900_physical_signal_diagnostic_template'
    template['description'] = 'Fixed physical command experiment; no MPC performance or model-validity claim. Derived from the existing diagnostic-signal-profile template.'
    template['control_area_objective'] = {'enabled': False}
    template.pop('prediction', None)
    template.pop('observation', None)
    urban = template['urban']
    urban['physical_signal_contract'] = False
    urban['shared_local_service_pool'] = False
    for key in ('route_choice_corridor', 'native_internal_inputs', 'shared_approach', 'sc2001_corridor', 'preserve_known_wout_routes'):
        urban.pop(key, None)
    for key in ('physical_route_topology', 'dynamic_physical_route_topology', 'physical_phase_authority', 'native_input_signal_authority'):
        urban['movements'].pop(key, None)
    urban['capacity'].pop('head_resource_contract', None)
    urban['capacity']['head_observation'] = {'enabled': False}
    template['actuation']['real_world_signal_control'].update(enabled=True, offset_writer='test_only')
    template['diagnostic'] = {'signal_profile': {}}
    green_document = {'schema': 'fixed-csv-axis-greens/v1',
                      'source_action_csv_sha256': EXPECTED_ACTION_SHA,
                      'source_action_json_sha256': EXPECTED_JSON_SHA, 'green_times': greens}
    green_bytes = encoded(green_document)
    config = deepcopy(template)
    config['name'] = 'fixed_beta300v3_900_physical_signal_diagnostic'
    config['diagnostic']['signal_profile'] = {
        'green_action_json': str((OUT / 'frozen_greens.json').relative_to(ROOT)).replace('\\', '/'),
        'green_action_sha256': sha(green_bytes), 'plan_content_sha256': plan_content_sha,
        'base_writer_offsets_sec': offsets, 'relative_offset_sec': {}, 'green_delta_sec': {},
    }
    output = {'template.json': encoded(template), 'frozen_greens.json': green_bytes, 'config.json': encoded(config)}
    source_pins = {str(p.relative_to(ROOT)).replace('\\', '/'): sha(value) for p, value in blobs.items()}
    manifest = {
        'schema': 'fixed-beta300v3-900-signal-profile/v1', 'status': 'Prepared; actual writer and VISSIM validation pending',
        'controller': 'diagnostic-signal-profile', 'offset_writer': 'test_only',
        'source_run': RUN.name, 'source_sha256': source_pins,
        'outputs': {name: {'path': str((OUT / name).relative_to(ROOT)).replace('\\', '/'), 'sha256': sha(value)} for name, value in output.items()},
        'action900_rows': dict(Counter(r['kind'] for r in data)),
        'signal_greens_sec': greens, 'signal_offsets_sec': offsets,
        'physical_vsl_kph': 120, 'physical_meters': {r['id']: {'sc_no': int(r['sc_no']), 'green_sec': 10, 'rate_vph': 900} for r in meter_rows},
        'warmup': {'controller': 'no-control', 'decision_times_sec': [1, 150, 300, 450, 600, 750],
                   'identical_74_row_csv_sha256': sha(warmup), 'urban_signals': 'native', 'vsl_kph': 120, 'meter_green_sec': 10},
        'interval': {'start_sec': 900, 'end_sec': 1050, 'policy': 'One frozen vector held over [900,1050)',
                     'terminal': 'The recorded 1050 action differs. A diagnostic terminal reapplication of the 900 vector is allowed only after the measured post_step1050; exclude immediate1050 and any later interval.'},
        'required_environment': {'RW_OFFSET_WRITER': 'test_only', 'RW_SIGNAL_READBACK_SEC': '1',
            'RW_SIGNAL_WRITE_ON_CHANGE': '0', 'RW_VEHREC_RESOLUTION': '1', 'RW_VEHICLE_ROUTES': '1',
            'RW_FORCE_STEPWISE': '1', 'RW_QUEUE_COUNTER': '1', 'RW_QUEUE_WINDOW': '1'},
        'disabled_scope': ['Omega objective/ledger', 'physical model signal clock', 'head observation/resource adaptation',
            'shared local service pool', 'native input generation', 'route-choice/shared/SC2001 corridor model', 'physical route support/authority repairs'],
        'enabled_scope': ['Existing CSV writer and VBS row/SG/window/readback validation', 'Fixed all-17 signal greens and writer offsets', 'Full-open physical meters and VSL120'],
        'important_limits': ['configure_runtime still executes, but optional pinned model contracts are explicitly OFF in this diagnostic config',
            'Existing adapter still attempts build_one_step_prediction; no MPC search, and prediction on a variant network is not validation evidence',
            'metadata legitimately differs from the experiment-mode source CSV; all physical columns and parsed SG schedules require exact comparison',
            '1s signal/ramp immediate/post_step readback is supported; VSL readback occurs at command writes, not every second',
            'No variant INPX has been created and no original contract SHA has been replaced'],
        'validation': {'source_csv_json_greens_offsets_equal': True, 'warmup_six_csv_bytes_equal': True,
            'vsl120_and_all_eight_full_open_match': True, 'writer_213_physical_rows': 'pending root check',
            'fake_com_and_live_readback': 'pending', 'model_imports': 0, 'model_execution': 0, 'COM': 0, 'VISSIM': 0},
    }
    output['manifest.json'] = encoded(manifest)
    assert all(p.read_bytes() == data for p, data in blobs.items()), 'source changed during generation'
    OUT.mkdir(exist_ok=True)
    for name, data in output.items():
        target = OUT / name
        if target.exists() and target.read_bytes() != data:
            raise FileExistsError(f'Refuse to replace differing evidence: {target}')
    for name, data in output.items():
        (OUT / name).write_bytes(data)
    print(json.dumps({'status': manifest['status'], 'outputs': len(output), 'signals': len(offsets), 'physical_rows': physical_row_count, 'model_imports': 0}))


if __name__ == '__main__':
    main()
