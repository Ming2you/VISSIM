"""Restore the pre134 measured-merge coefficient after163 density-braking test."""
import copy
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'proposal.json').exists()
    assert h.read(h.R/'joint_pressure163/assessment.json')['status']=='complete_rejected'
    pins={str(Path(__file__)):h.sha(__file__)}
    def read(path):pins[str(path)]=h.sha(path);return h.read(path)
    parent=h.R/'joint_pressure163/candidate'
    original=read(parent/'reference_config.json');config=copy.deepcopy(original);manifest=read(parent/'manifest.json')
    measured=read(h.R/'lane_state132/eval_01/reference_config.json')
    read(h.R/'joint_pressure163/assessment.json');read(h.R/'onset_reaction134/proposal.json')
    old=config['freeway']['state_response']['FW_E']['cell_overrides']['21']['delta_merge']
    value=measured['freeway']['state_response']['FW_E']['cell_overrides']['21']['delta_merge']
    assert old==0. and value>0.
    config['freeway']['state_response']['FW_E']['cell_overrides']['21']['delta_merge']=value
    dest=HERE/'candidate';dest.mkdir();h.save(dest/'reference_config.json',config)
    manifest['sources']['reference_config']=dict(path=(dest/'reference_config.json').relative_to(h.ROOT).as_posix(),sha256=h.sha(dest/'reference_config.json'))
    manifest['qualification']='Unqualified164 restore original132 accepted-merge delta21 after163;requires exact157 physical source. No adoption.'
    h.save(dest/'manifest.json',manifest)
    restored=copy.deepcopy(config);restored['freeway']['state_response']['FW_E']['cell_overrides']['21']['delta_merge']=old
    assert restored==original
    protected=read(h.R/'joint_pressure163/forecast/protocol.json')
    for p,digest in {**pins,**protected['protected_sha256']}.items():assert h.sha(p)==digest,p
    assert h.sha(protected['STOP']['path'])==protected['STOP']['sha256']
    h.save(HERE/'proposal.json',dict(
        previous_goal_turn='PROGRESS160/161.162 neighbor split and163 fixed two-sided correction completed;163 reverses RM loss sign.',
        hypothesis='134 set delta21 to0 while old neighbor pressure overbraked.163 relaxes that pressure and loses RM preventive response. Isolate whether carrying the zero-delta compensation removed the actual-merge mechanism;restore original132 value once.',
        difference=dict(cell=21,parameter='delta_merge',before=old,after=value),
        fixed='Exact163 parameters exceptdelta21 restores132 calibrated value;exact157 physics. Actual accepted merge,not desired ramp demand,drives the term. No capacity or controller reward;all flow/storage/ramp/head/exposure/cost laws unchanged.',
        budget=dict(parity450=1,autonomous450=8,total450=9,new_fits=0,new_native=0,new_FZP=0),
        gate='Same meaningful signs,response>=10%improvement,absolute<=110%148,choice<=.5 andphysical/local discharge checks. Compare163 RM sign as well. No delta sweep,threshold search or repeated combination after result.',
        limitations='Restoring a prior fitted parameter is a mechanism test,not proof merging caused all native loss.134 coefficient0 may have compensated other errors. Previous29/67 cases are notblind;independent/fullOmega/SDMPC remain.',
        source_pins=pins,protected_sha256=protected['protected_sha256'],STOP=protected['STOP'],new_fits=0,production_adopted=False))
    print('164 restore actual-merge delta21',old,'->',value,'exact132 coefficient,one fixed test,9forecasts budget')


if __name__=='__main__':main()
