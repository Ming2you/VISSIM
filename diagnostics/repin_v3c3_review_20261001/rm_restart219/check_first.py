"""Run the actual modified decision at the saved first native control state."""
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DEC=Path('D:/VISSIM_runs/20261004_sdmpc_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')


def main():
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,obs150_contract as oc
    original=oc.write_derived
    def read_only(raw,derived):
        p=oc.resolve(raw[oc.RAW_STATE_KEY],oc.derived_path(derived['sim_sec']))
        assert p.read_bytes()==oc.derived_bytes(derived)
        return p
    oc.write_derived=read_only
    out=HERE/'first900';out.mkdir(exist_ok=True)
    assert not (out/'action_000900.json').exists()
    sys.argv=[str(Path(adapter.__file__)),'--state-json',str(DEC/'state_000900.json'),
        '--previous-action-json',str(DEC/'action_000750.json'),
        '--out-action-json',str(out/'action_000900.json'),'--out-action-csv',str(out/'action_000900.csv'),
        '--mapping-json',str(ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'),
        '--calibration-json',str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'),
        '--tuning-json',str(HERE/'config.json'),'--controller','wu-link']
    try:adapter.main()
    finally:oc.write_derived=original
    selection=json.loads((out/'action_000900.joint.json').read_bytes())['selection']
    binding=json.loads((out/'action_000900.joint_written.json').read_bytes())
    assert binding['written_command_binding_passed']
    assert selection['finite_neighbor_audit_performed'] and selection['feasible']
    assert selection['meter_neighbor_audit']['additional_predictions'] <= 20
    old=json.loads((DEC/'action_000900.joint.json').read_bytes())['selection']
    assert abs(selection['held_objective']-old['held_objective']) < 1e-7
    (HERE/'first900_verified.json').write_text(json.dumps(dict(status='PASS',
        held_objective_parity=True,
        selected_objective=selection['selected_objective'],constraints=selection['final_constraints'],
        meter_neighbor_audit=selection['meter_neighbor_audit'],written_command_binding=True,
        source='recorded900 from previous run; offline calculation, not new native control'),indent=2),encoding='utf-8')


if __name__=='__main__':main()
