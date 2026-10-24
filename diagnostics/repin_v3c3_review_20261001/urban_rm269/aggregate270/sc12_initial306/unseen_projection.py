"""Apply the same initializer to saved3300 without fitting or a new rollout."""
from pathlib import Path
import hashlib,json,pickle
from candidate import project, SOURCE
from test_candidate import inputs
from state_check import equal
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers.control_area_objective import get_ledger
HERE=Path(__file__).resolve().parent;A=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    assert not (HERE/'unseen3300.json').exists()
    original=A/'decision285/execution3300/summary.json'
    old=json.loads(original.read_bytes())
    assert old['status']=='complete'
    candidates=[Path(p) for p in old['source_pins'] if Path(p).name=='state_003300.json']
    assert len(candidates)==1,candidates
    raw_path=candidates[0]
    assert sha(raw_path)==old['source_pins'][str(raw_path)]
    initial=A/'decision285/execution3300/initial.pickle'
    cfg,state,_=pickle.loads(initial.read_bytes())
    raw=json.loads(raw_path.read_bytes());frame_path=raw_path.parent/raw['obs150']['frames']['current']['path']
    assert sha(frame_path)==raw['obs150']['frames']['current']['sha256']
    frame=json.loads(frame_path.read_bytes())
    _,_,_,_,net,inside,_=inputs()
    state_bytes=pickle.dumps(state,protocol=5)
    result,receipt=project(state,cfg,raw,frame,net,inside,adapter._contiguous_stopline_queue(raw,per_lane=True))
    assert pickle.dumps(state,protocol=5)==state_bytes
    changed={k for k,v in vars(result).items() if not equal(v,vars(state)[k])}
    assert changed<={'urban_movement_queue','local_observation_summary','gate_initial_route_tags','_control_area_ledger'}
    assert result.urban_arrival_buffer==state.urban_arrival_buffer and result.urban_storage_release_buffer==state.urban_storage_release_buffer
    for side in ('inside','outside'):
        assert abs(sum(x[side] for x in get_ledger(state).stocks.values())-sum(x[side] for x in get_ledger(result).stocks.values()))<1e-8
    out=dict(status='pass_same_initializer_saved3300',scope='Unused by this initialization candidate; not unused by all prior plant studies.',
        changed_fields=sorted(changed),receipt=receipt,forecasts=0,ad=0,native=0,
        unchanged_current_stock=True,unchanged_arrival_release=True,source_pins={str(p):sha(p) for p in
          (original,initial,raw_path,frame_path,HERE/'candidate.py',HERE/'test_candidate.py',Path(__file__))})
    (HERE/'unseen3300.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('UNSEEN3300',receipt)
if __name__=='__main__':main()
