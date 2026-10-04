"""Small read-only live checkpoint; no FZP/COM or process intervention."""
from pathlib import Path
import csv
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
BASE = Path('D:/VISSIM_runs')
NAMES = ('20261002_service66_s29_9000', '20261003_service66_posthead_s29_9000')
ROOTS = [BASE / name / 'sdmpc' for name in NAMES]
DIRS = [root / 'decisions_sdmpc31_sdmpc9000_s29' for root in ROOTS]
pins = {}

def read(path):
    raw = path.read_bytes()
    pins[str(path)] = hashlib.sha256(raw).hexdigest()
    return raw

def doc(path):
    return json.loads(read(path))

states = [doc(folder / 'state_001650.json') for folder in DIRS]
physical = [key for key in states[0] if key not in
            ('network_path', 'run_provenance', 'obs150', 'lane_plant_observation')]
assert all(states[0][key] == states[1][key] for key in physical)
observation = ('schema', 'sim_sec', 'k', 'window', 'simres_steps_per_sec',
               'ground_truth_windows', 'detectors', 'detectors_cum',
               'detectors_last_equal', 'rule_crosscheck', 'linkeval_volume_veh_h',
               'signal_log', 'source_cumulative_vehs')
assert all(states[0]['obs150'][key] == states[1]['obs150'][key] for key in observation)
frames = [doc(folder / 'lane_observations/frame_001650.json') for folder in DIRS]
assert frames[0].keys() == frames[1].keys()
assert all(frames[0][key] == frames[1][key] for key in frames[0] if key != 'run_id')
assert frames[1]['complete'] and len(frames[1]['vehicles']) == 4567
binding = doc(DIRS[1] / 'action_001650.joint_written.json')
assert binding['prewrite_binding_passed'] and binding['written_command_binding_passed']
assert binding['ordered_row_count'] == 213
csv_path = DIRS[1] / 'action_001650.csv'
raw = read(csv_path)
assert pins[str(csv_path)] == binding['expected_csv_sha256']
applied_raw = read(DIRS[1] / 'action_001650.json.applied')
assert applied_raw.startswith(b'\xff\xfe')
applied = applied_raw.decode('utf-16').splitlines()
assert float(applied[0]) == 1650 and Path(applied[1]) == csv_path and int(applied[2]) == len(raw)
rows = list(csv.DictReader(raw.decode('utf-8-sig').splitlines()))
old_rows = list(csv.DictReader(read(DIRS[1] / 'action_001500.csv').decode('utf-8-sig').splitlines()))
meters = {row['id']: float(row['green_sec']) for row in rows if row['kind'] == 'ramp_meter'}
old_meters = {row['id']: float(row['green_sec']) for row in old_rows if row['kind'] == 'ramp_meter'}
assert len(meters) == 8 and meters.keys() == old_meters.keys()
assert all(abs(green - old_meters[ramp]) <= 2 for ramp, green in meters.items())
vsl = {row['id']: float(row['speed_kph']) for row in rows if row['kind'] == 'vsl'}
assert set(vsl.values()) <= {50, 60, 70, 80, 90, 100, 110}
budget = doc(DIRS[1] / 'action_001650.decision_budget.json')
assert budget['output_completed'] and budget['output_error'] is None
log_path = ROOTS[1] / 'runlog_sdmpc31_sdmpc9000_s29.txt'
# Append-only live log is evidence for this checkpoint, not a stable source pin.
with log_path.open('rb') as stream:
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(max(0, size - 8192))
    tail = stream.read().decode('utf-8-sig', errors='replace')
times = [float(value) for value in re.findall(r'actual_sim_sec=([0-9.]+)', tail)]
assert times and max(times) > 1650
result = dict(status='initialization_failure_point_passed_in_native_run',
    last_observed_sim_sec=max(times), physical_state_fields_equal=physical,
    observation_fields_equal=observation, full_vehicle_frame_equal_except_run_id=True,
    previous_failed_run_preserved=True, writer_binding_passed=True,
    runner_application_acknowledged=True, native_LDP_VSL_execution_audit_pending=True,
    controller_wall_sec=budget['wall_sec'], ramp_greens=meters, vsl_commands=vsl,
    observations_future_for_control=False, pins=pins,
    completed_9000=False, gain_qualified=False, goal='ACTIVE / NOT_QUALIFIED')
target = HERE / 'native1650_verified.json'
assert not target.exists()
target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({key: result[key] for key in
    ('status', 'last_observed_sim_sec', 'controller_wall_sec', 'ramp_greens', 'vsl_commands')}))
