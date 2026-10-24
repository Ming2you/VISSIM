"""Cross-check the saved partial readout without reading a live FZP."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np

here = Path(__file__).resolve().parent
read = lambda p: json.loads(p.read_bytes())
summary = read(here / 'summary.json')
assert summary['end_sec'] == 3300 and summary['inside_link_count'] == 701
nc_csv = here.parent / 'current_native_analysis_to8100/nc/area_timeseries.csv'
with nc_csv.open(encoding='utf-8-sig') as f:
    fine = list(csv.DictReader(f))
fine_ttt = float(np.interp(3300, [float(x['sim_sec']) for x in fine],
                           [float(x['ttt_veh_h_cumulative']) for x in fine]))
coarse = summary['comparison_veh_h']['Omega']['nc']
parts = ['FW_E', 'FW_W', 'Omega_other']
for arm in ['nc', 'sdmpc']:
    with (here / f'{arm}_timeseries.csv').open(encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    times = np.array([float(r['sim_sec']) for r in rows])
    stocks = np.array([sum(float(r[p + '_N']) for p in parts) for r in rows])
    direct = float(np.sum((stocks[1:] + stocks[:-1]) * np.diff(times) / 7200))
    expected = summary['comparison_veh_h']['Omega'][arm]
    assert abs(direct - expected) < 1e-8
    assert abs(sum(summary['comparison_veh_h'][p][arm] for p in parts) - expected) < 1e-8

decisions = Path('D:/VISSIM_runs/20261007_goal8_head47right_verified_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
command_checks = []
for t in range(900, 3300, 150):
    stem = decisions / f'action_{t:06d}'
    written = read(Path(str(stem) + '.joint_written.json'))
    action_csv = Path(str(stem) + '.csv')
    receipt_raw = Path(str(stem) + '.json.applied').read_bytes()
    receipt_encoding = 'utf-16' if receipt_raw[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8-sig'
    receipt = receipt_raw.decode(receipt_encoding).splitlines()
    assert int(receipt[0]) == t
    assert Path(receipt[1]).resolve() == action_csv.resolve()
    assert int(receipt[2]) == action_csv.stat().st_size
    assert written['written_command_binding_passed'] and written['prewrite_binding_passed']
    assert hashlib.sha256(action_csv.read_bytes()).hexdigest() == written['expected_csv_sha256']
    assert written['response_kind'] == 'validated_sdmpc'
    command_checks.append(t)
result = dict(status='passed_partial_readout_checks', end_sec=3300,
              coarse_nc_ttt=coarse, fine_nc_ttt=fine_ttt,
              coarse_nc_error_percent=100*(coarse/fine_ttt-1),
              no_control_error_bound_inferred=True,
              command_file_checks_passed=command_checks,
              native_ldp_validation='pending_run_closure',
              fzp_read=False, processes_or_simulation_modified=False)
(here / 'readout_validation.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result))
