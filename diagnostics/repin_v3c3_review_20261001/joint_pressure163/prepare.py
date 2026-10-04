"""One frozen combination justified by162, no further fit or grid."""
import copy
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'proposal.json').exists()
    assert h.read(h.R/'exit_pressure161/completion.json')['status']=='complete_rejected'
    assert h.read(h.R/'neighbor_split162/status.json')['status']=='complete_conditional_only'
    pins={str(Path(__file__)):h.sha(__file__)}
    def read(path):pins[str(path)]=h.sha(path);return h.read(path)
    parent=h.R/'exit_pressure161/candidate'
    original=read(parent/'reference_config.json');config=copy.deepcopy(original)
    manifest=read(parent/'manifest.json');fit=read(h.R/'recovery_terms137/proposal.json')
    read(h.R/'neighbor_split162/summary.json');read(h.R/'exit_pressure161/assessment.json')
    branch=config['freeway']['state_response']['FW_E']['cell_overrides']['22']['anticipation']
    assert branch['downstream_ge_local']==fit['before']
    branch['downstream_ge_local']=fit['after']
    dest=HERE/'candidate';dest.mkdir();h.save(dest/'reference_config.json',config)
    manifest['sources']['reference_config']=dict(path=(dest/'reference_config.json').relative_to(h.ROOT).as_posix(),sha256=h.sha(dest/'reference_config.json'))
    manifest['qualification']='Unqualified163 one fixed161+137 local pressure combination.Requires exact157 physics;not a production manifest.'
    h.save(dest/'manifest.json',manifest)
    restored=copy.deepcopy(config)
    restored['freeway']['state_response']['FW_E']['cell_overrides']['22']['anticipation']['downstream_ge_local']=fit['before']
    assert restored==original
    protected=read(h.R/'exit_pressure161/forecast/protocol.json')
    for p,digest in {**pins,**protected['protected_sha256']}.items():assert h.sha(p)==digest,p
    assert h.sha(protected['STOP']['path'])==protected['STOP']['sha256']
    h.save(HERE/'proposal.json',dict(
        previous_goal_turn='PROGRESS160/161 completed.162 separates upstream20 and downstream22 errors,neither single neighbor restores21 reaction.',
        hypothesis='161 corrected20 local pressure but leaves22 own excessive pressure documented137/138. Test both measured-state proposals once on same shared receiving/finite-feedback dynamics. This is an interaction test,not evidence that isolated rejected candidates work.',
        difference=dict(cell=22,branch='downstream_ge_local',before=fit['before'],after=fit['after']),
        fixed='Exact161 configuration except22ge copies frozen137 value;exact158 physical source. No new fitted values,FD,capacity,action bonus,receiving/storage/merge/head/queue/exposure/cost changes.',
        budget=dict(parity450=1,autonomous450=8,total450=9,new_fits=0,new_native=0,new_FZP=0),
        gate='Existing meaningful signs,response>=10%improvement,absolute<=110%148,choice<=.5,physical conservation andlocal discharge;also inspect degradation of RM vs161. If fail,no factor/threshold/combination grid.',
        limitations='137 alone weakened RM and failed VSL;retained as failed evidence. Previously inspected29/67 are not blind. Conditional upstream/downstream probes do not prove an autonomous or conservative gain.',
        source_pins=pins,protected_sha256=protected['protected_sha256'],STOP=protected['STOP'],
        new_fits=0,production_adopted=False))
    print('163 fixed22nu_ge',fit['before'],'->',fit['after'],'other161config unchanged,one fixed combination,9forecasts budget')


if __name__=='__main__':main()
