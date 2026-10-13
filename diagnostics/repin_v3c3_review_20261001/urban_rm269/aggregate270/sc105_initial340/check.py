"""Current records only: three saved states, conservation and repeat rejection."""
from pathlib import Path
import hashlib,json,pickle
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc105_initial340 import candidate
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.transfer331.inputs import load
from evaluation.controllers import vissim_stackelberg_adapter as adapter

HERE=Path(__file__).resolve().parent;A=HERE.parent;ROOT=HERE.parents[4]

def main():
    np=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    network=np.read_bytes();pins={str(np):hashlib.sha256(network).hexdigest()};results={}
    for at in (3300,2400,2700):
        if at==2700:
            path=A/'validation338/forecast2700_v6/initial.pickle'
            source=Path('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47')
        else:
            path=A/f'transfer331/build{at}_v2/initial.pickle'
            source=Path(json.loads((path.parent/'summary.json').read_bytes())['source'])
        cfg,state,_=pickle.loads(path.read_bytes());pins[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        raw,frame,current_pins=load(source,at);pins.update(current_pins)
        before=pickle.dumps((cfg,state),protocol=5)
        lanes=adapter._contiguous_stopline_queue(raw,per_lane=True)
        changed,receipt=candidate.install(cfg,state,raw,frame,network,lanes)
        assert pickle.dumps((cfg,state),protocol=5)==before
        assert all(x['ready'] or x['due_sec']>at for x in receipt['vehicles'])
        assert all(sum(v.values())<=changed.urban_arrival_buffer[candidate.TARGET][t]+1e-8
                   for t,v in changed.gate_initial_route_tags[candidate.TARGET].items())
        if at==3300:
            assert (receipt['physical_vehicles'],receipt['ready_before'],receipt['ready_after'],receipt['moved_queue_to_storage'])==(56,36,10,26)
            q={m:sum(v.get('movement:'+m,0) for v in receipt['new_support'].values()) for m in candidate.MOVES}
            assert q['SC105_N_SC1002_to_E_SC1']==10 and sum(q.values())==10
        try:candidate.install(cfg,changed,raw,frame,network,lanes)
        except ValueError as exc:assert str(exc)=='Duplicate route owner'
        else:raise AssertionError('Duplicate projection accepted')
        results[str(at)]=receipt
        print('SC105_INITIAL',at,{k:receipt[k] for k in ('physical_vehicles','ready_before','ready_after','moved_queue_to_storage','retained_posthead')},flush=True)
    for p in (Path(__file__),Path(candidate.__file__)):pins[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    result=dict(status='passed_three_states',results=results,source_pins=pins,forecasts=0,native_runs=0,fits=0)
    (HERE/'check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
