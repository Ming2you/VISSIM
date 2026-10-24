"""Reproduce the closed NC1350 error without a simulator or optimizer."""
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers import vsl_exposure_history as history

verify_fixed = '--verify-fixed-history' in sys.argv
folder = Path('D:/VISSIM_runs/20260926_sd31_closedloop3000/nc/decisions_sdmpc31_nc3000_s29')
output = HERE/('nc1350_fixed_history' if verify_fixed else 'nc1350_failure')
output.mkdir(exist_ok=True)
original = history.constrain_nominal


def capture(exposure, floors, maximum):
    try:
        return original(exposure, floors, maximum)
    except ZeroDivisionError:
        rows = []
        for i, (row, floor) in enumerate(zip(exposure.cohorts, floors)):
            total, nominal = sum(row.values()), row.get(maximum, 0.)
            if floor > nominal and total == nominal:
                rows.append(dict(cell=i, cohort=row, floor=floor, total=total,
                                 needed=floor-nominal, other=total-nominal))
        (output/'numerical_failure.json').write_text(json.dumps(rows, indent=2))
        raise


history.constrain_nominal = capture
for key, value in dict(RW_DECISION_FAIL_FAST='1', RW_MAINLINE_SG_ONLY='1',
                       RW_OFFSET_WRITER='experiment', RW_RAMP_AMBER_SEC='0').items():
    os.environ[key] = value
sys.argv = [str(Path(adapter.__file__)), '--state-json', str(folder/'state_001350.json'),
            '--previous-action-json', str(folder/'action_001200.json'),
            '--out-action-json', str(output/'action_001350.json'),
            '--out-action-csv', str(output/'action_001350.csv'),
            '--mapping-json', str(ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'),
            '--detector-mapping-json', str(ROOT/'evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json'),
            '--calibration-json', str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'),
            '--tuning-json', str(HERE/'selected/config_n31_v2.json'), '--controller', 'no-control']
class HistoryVerified(Exception):
    pass


write_bytes = Path.write_bytes
def intercept_receipt(path, data):
    target = folder/'obs150/vsl_cohorts_001350.json'
    if path.resolve() == target.resolve():
        receipt = json.loads(data)
        write_bytes(output/'verified_history.json', data)
        print(json.dumps({'fixed_history_initialized': True, 'audit': receipt['audit'],
                          'original_run_modified': False, 'controller_optimization_run': False}))
        raise HistoryVerified()
    if path.resolve().is_relative_to(folder.resolve()):
        raise AssertionError('Unexpected write to the preserved failed run: '+str(path))
    return write_bytes(path, data)


if verify_fixed:
    Path.write_bytes = intercept_receipt
try:
    adapter.main()
    if verify_fixed:
        raise AssertionError('Expected causal-history write checkpoint was not reached')
except HistoryVerified:
    if not verify_fixed:
        raise
finally:
    Path.write_bytes = write_bytes
