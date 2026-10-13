"""Three recorded states: legacy parity and independent-owner coverage."""
from pathlib import Path
from copy import deepcopy
import hashlib,json,pickle

from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.corridor339 import project
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.transfer331.inputs import load
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers.control_area_objective import get_ledger

HERE=Path(__file__).resolve().parent
A=HERE.parent
ROOT=HERE.parents[4]


def main():
    network_path=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    network=network_path.read_bytes()
    pins={str(network_path):hashlib.sha256(network).hexdigest()}
    result={}
    for at in (2400,3300,2700):
        if at==2700:
            path=A/'validation282/forecast2700_v3/initial.pickle'
            source=Path('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47')
        else:
            folder=A/f'transfer331/build{at}_v2'
            path=folder/'canonical.pickle'
            source=Path(json.loads((folder/'summary.json').read_bytes())['source'])
        cfg,state,forecast=pickle.loads(path.read_bytes())
        pins[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        raw,frame,current_pins=load(source,at);pins.update(current_pins)
        lanes=adapter._contiguous_stopline_queue(raw,per_lane=True)
        initial=pickle.dumps(state,protocol=5)
        changed,receipt=project.install(cfg,state,raw,frame,network,lanes)
        assert pickle.dumps(state,protocol=5)==initial
        if at!=2700:
            legacy=deepcopy(state)
            timing=project.timing.install(cfg,legacy,raw,frame,network,lanes)
            legacy,_=project.routes.install(cfg,legacy,raw,frame,network,timing)
            differences=[k for k in set(vars(legacy))|set(vars(changed))
                         if not equal(getattr(legacy,k,None),getattr(changed,k,None))]
            assert not differences,(at,differences)
            receipt['legacy_state_exact']=True
        else:
            assert receipt['source_vehicles']==42
            assert receipt['ownership']['21']['source_vehicles']==12
            assert receipt['ownership']['21']['rule']=='exact_current_native_head_partition'
            assert receipt['ownership']['10293']['source_vehicles']==1
            shared=[r for r in receipt['vehicles'] if r['link']=='10293']
            assert len(shared)==2 and all(r['owned_vehicles']==.5 and not r['known_sc109_turn'] for r in shared)
            assert receipt['ownership']['10293']['other_owners']=={'storage:SC107_to_SC108':1.}
            assert changed.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']['21']==state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']['21']
            assert get_ledger(changed).stocks['storage:SC107_to_SC108']==get_ledger(state).stocks['storage:SC107_to_SC108']
            assert all(r['new_due_sec']>at for r in receipt['vehicles'])
        result[str(at)]=receipt
        print('COHORT_CHECK',at,receipt['source_vehicles'],receipt.get('legacy_state_exact'),flush=True)
    report=dict(status='passed_three_recorded_states',states=result,source_pins=pins,
                forecasts=0,native_runs=0,new_fits=0,projection_only=True)
    (HERE/'check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':main()
