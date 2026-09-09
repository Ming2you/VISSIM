"""Validate real production-collector envelopes against independent native reads."""
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.controllers.vehicle_routes import complete_vehicle_routes
from scripts.tests.test_b1a_vbs_verified_capture_static import procedure


def main():
    folder = ROOT/'diagnostics/vehicle_route_collector_native_20260910_01'
    output = ROOT/'diagnostics/vehicle_route_collector_qualification.json'
    if output.exists():
        raise FileExistsError(output)
    run = json.loads((folder/'manifest.json').read_text(encoding='utf-8-sig'))
    if not run['passed'] or run['source_changes']:
        raise AssertionError('Native collector probe did not finish with unchanged sources')
    generated = json.loads((ROOT/'diagnostics/vehicle_route_collector_native_probe.manifest.json').read_text(encoding='utf-8'))
    runner = ROOT/'scripts/run_real_world_stackelberg_controller.vbs'
    source = runner.read_text(encoding='utf-8-sig')
    for name, expected in generated['extracted_procedure_sha256'].items():
        if hashlib.sha256(procedure(source, name).encode('utf-8')).hexdigest() != expected:
            raise AssertionError('Extracted production collector helper changed: '+name)
    physical = defaultdict(list)
    with (folder/'routes.csv.physical.csv').open(encoding='utf-8', newline='') as stream:
        for row in csv.DictReader(stream):
            link, lane = row['lane'].split('-')
            physical[float(row['sim_sec'])].append({'veh_no': int(row['veh_no']), 'link_no': int(link),
                'lane_no': int(lane), 'position_m': float(row['pos_m']), 'speed_kph': float(row['speed_kph'])})
    captures = []
    for line in (folder/'routes.csv.jsonl').read_text(encoding='utf-8').splitlines():
        envelope = json.loads(line)
        sec = envelope['sim_sec_before']
        records = physical.pop(sec, [])
        raw = {'sim_sec': sec, 'vehicle_routes': envelope, 'vehicle_records': {
            'complete': True, 'collection_count_before': len(records), 'collection_count_after': len(records),
            'capture_sim_sec_before': sec, 'capture_sim_sec_after': sec, 'record_count': len(records),
            'records': records, 'full_network_link_counts': dict(Counter(str(row['link_no']) for row in records))}}
        by_id = complete_vehicle_routes(raw, required=True)
        captures.append({'sim_sec': sec, 'physical_and_route_count': len(records),
            'observed_no_current_route': sum(row['route_no'] is None for row in by_id.values()),
            'observed_decision_1128': sum(row['route_decision_no'] == 1128 for row in by_id.values()),
            'observed_decision_1129': sum(row['route_decision_no'] == 1129 for row in by_id.values()),
            'id_time_count_alignment_pass': True})
    assert not physical
    assert [row['sim_sec'] for row in captures] == [0, 1, 150, 300, 450, 600, 750, 900, 1050]
    earlier = ROOT/'diagnostics/vehicle_route_com_probe_20260910_01/routes.csv'
    same_trajectory_sample = (folder/'routes.csv').read_bytes() == earlier.read_bytes()
    assert same_trajectory_sample, 'The native qualification trajectory sample changed'
    paths = [runner, Path(__file__), ROOT/'evaluation/controllers/vehicle_routes.py',
             ROOT/'evaluation/controllers/projection_support.py', earlier,
             ROOT/'diagnostics/vehicle_route_collector_native_probe.manifest.json',
             *[path for path in folder.iterdir() if path.is_file()]]
    result = {'scope': generated['scope'], 'passed': True, 'captures': captures,
        'matching_vehicle_observations': sum(row['physical_and_route_count'] for row in captures),
        'prior_native_trajectory_sample_byte_identical': same_trajectory_sample,
        'actual_elapsed_sec': run['elapsed_sec'], 'startup_timeout_sec': run['startup_timeout_sec'],
        'source_changes_during_actual_run': run['source_changes'],
        'limitations': ['Native seed13 with original native demand and signals; not an MPC performance arm.',
            'Actual production route serializer and its helpers ran against COM. Full WriteStateJson and full controller replay are separate validations.',
            'Physical envelope used by the Python check is assembled from independent measured No/Lane/Pos/Speed rows. No physical values or route identities are synthesized.',
            'Observation totals repeat vehicles across captures; they are not unique vehicle totals or calibrated route fractions.'],
        'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}}
    output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_sha256','limitations')}))


if __name__ == '__main__':
    main()
