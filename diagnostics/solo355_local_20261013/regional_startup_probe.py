
"""Saved1s canonical startup: native writer, no decision or prediction allowed."""
import os
os.environ.update(RW_OFFSET_WRITER='experiment',RW_MAINLINE_SG_ONLY='1',RW_RAMP_AMBER_SEC='0')
import argparse,json,sys
from pathlib import Path
from unittest.mock import patch
from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc
p=argparse.ArgumentParser();p.add_argument('--mode',required=True);p.add_argument('--output',required=True)
a=p.parse_args();out=Path(a.output);out.mkdir(exist_ok=False)
root=Path.cwd();decisions=Path('E:/VISSIM_runs/20261012_adopted355_window_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
sys.argv=[adapter.__file__,'--state-json',str(decisions/'state_000001.json'),
    '--out-action-json',str(out/'action.json'),'--out-action-csv',str(out/'action.csv'),
    '--mapping-json',str(root/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'),
    '--detector-mapping-json',str(root/'evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json'),
    '--calibration-json',str(root/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'),
    '--tuning-json',str(root/('diagnostics/solo355_local_20261013/'+a.mode+'_config.json')),'--controller','wu-link']
with patch.object(sdmpc,'solve',side_effect=AssertionError('Startup optimization forbidden')),patch.object(
        adapter,'run_joint_owner_decision',side_effect=AssertionError('Startup decision forbidden')),patch.object(
        adapter,'build_one_step_prediction',side_effect=AssertionError('Startup prediction forbidden')):
    adapter.main()
row=json.loads((out/'action.json').read_text(encoding='utf-8'))
assert row['metadata']['regional_startup_baseline'] is True
assert row['prediction']['status']=='not_requested'
(out/'receipt.json').write_text(json.dumps(dict(passed=True,mode=a.mode,sim_sec=1,
    canonical_adapter_main=True,optimization_calls=0,prediction_calls=0,native_runs=0,
    written_csv=str(out/'action.csv')),indent=2),encoding='utf-8')
