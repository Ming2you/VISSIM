"""Next-decision loader regression only; the saved1050 traffic is not a held-policy outcome."""
from pathlib import Path
import json
import sys
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers import sdmpc

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PREVIOUS=HERE/'hold900/action_000900.json'
RECORDING=Path('D:/VISSIM_runs/20261003_service66_queuezero_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')

class Checked(BaseException):pass

def check(controller,state,forecast,previous,cfg,mapping,tuning,provenance,previous_path,options,report_path,**kw):
    actual,pins=adapter.load_joint_historical_reference(previous_path,previous,cfg,
        expected_run_id=provenance['run_id'],expected_previous_sim_sec=900.)
    state._sdmpc_interval_sec=150
    prices,receipt=sdmpc.load_prices(previous_path,state,cfg.network.sdmpc_options)
    assert not receipt['committed'] and list(prices)==[0.,0.]
    assert actual['previous'].vsl['FW_E__seg13']==90
    assert len(actual['previous'].ramp_metering)==8
    (HERE/'hold_next_anchor_verified.json').write_text(json.dumps(dict(status='pass',
        history_pins=pins,price_receipt=receipt,eight_ramps=True,fixed_VSL90=True,
        scope='Schema/ownership/previous-command regression only. No prediction and no native application; actual1050 state is reused solely to exercise initialization.'),indent=2),encoding='utf-8')
    raise Checked()

adapter.run_joint_owner_decision=check
sys.argv=[str(Path(adapter.__file__)),'--state-json',str(RECORDING/'state_001050.json'),
    '--previous-action-json',str(PREVIOUS),'--out-action-json',str(HERE/'hold_next/unused.json'),
    '--out-action-csv',str(HERE/'hold_next/unused.csv'),'--controller','wu-link',
    '--mapping-json',str(ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'),
    '--calibration-json',str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'),
    '--tuning-json',str(HERE/'config.json')]
try:adapter.main()
except Checked:print('HOLD_NEXT_ANCHOR_PASS')
else:raise RuntimeError('Expected pre-decision verification interception')
