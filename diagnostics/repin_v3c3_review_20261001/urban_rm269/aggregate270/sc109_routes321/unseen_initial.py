"""Retain the completed independent3300 initialization check, not a gain test."""
from pathlib import Path
import json,pickle,hashlib
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_initial320.candidate import install as retime
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_routes321.candidate import install
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal

HERE=Path(__file__).resolve().parent;A=HERE.parent;ROOT=HERE.parents[4]
def main():
    out=HERE/'unseen_initial3300.json';assert not out.exists()
    initial=A/'decision285/execution3300/initial.pickle'
    assert hashlib.sha256(initial.read_bytes()).hexdigest()=='20c62aa6e6e12145a60ff4d0b6ffc01542d8cf5660649518de80704620edcbaf'
    cfg,state,_=pickle.loads(initial.read_bytes())
    protocol=A/'decision285/execution3300/protocol.json'
    p=Path(json.loads(protocol.read_bytes())['state']);raw=json.loads(p.read_bytes())
    fp=p.parent/raw['obs150']['frames']['current']['path']
    assert hashlib.sha256(fp.read_bytes()).hexdigest()==raw['obs150']['frames']['current']['sha256']
    frame=json.loads(fp.read_bytes())
    network=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    timing=retime(cfg,state,raw,frame,network.read_bytes(),adapter._contiguous_stopline_queue(raw,per_lane=True))
    result,receipt=install(cfg,state,raw,frame,network.read_bytes(),timing)
    changed={k for k,v in vars(result).items() if not equal(v,vars(state)[k])}
    assert changed=={'urban_movement_queue','local_observation_summary','gate_initial_route_tags','_control_area_ledger'}
    files=[Path(__file__),initial,protocol,p,fp,network,HERE/'candidate.py',A/'sc109_initial320/candidate.py']
    report=dict(status='complete_unused3300_initialization_only',source_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
                timing=timing,current_routes=receipt,new_forecasts=0,changed_fields=sorted(changed),
                limitation='Different state of seed29; initial state/ownership/tag checks only, not independent-seed or response qualification.')
    report['source_pins'].update(receipt['source_pins'])
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('UNUSED3300',receipt['queue_before'],'->',receipt['queue_after'])

if __name__=='__main__':main()
